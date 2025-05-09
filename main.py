import streamlit as st
import imaplib
import smtplib
import email
from email.message import EmailMessage
from email.header import decode_header
import os
import ast
import re
import json
import unicodedata
import google.generativeai as genai
import requests
from dotenv import load_dotenv

# --- Configuration ---
USERNAME = "ml.project.ie@gmail.com"
PASSWORD = "ucjeravgzupoqyra"


load_dotenv("variables.env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

genai.configure(api_key=GEMINI_API_KEY)
# --- Utilities ---

def sanitize_for_markdown(text):
    try:
        safe_text = text.encode("utf-8", "replace").decode("utf-8", "replace")
        safe_text = ''.join(c for c in safe_text if unicodedata.category(c)[0] != 'C')
        return safe_text
    except Exception:
        return "[Error displaying this content]"

def clean_for_gemini(text):
    try:
        cleaned = text.encode("utf-8", "replace").decode("utf-8", "replace")
        cleaned = ''.join(c for c in cleaned if unicodedata.category(c)[0] != 'C')
        return cleaned
    except Exception:
        return "[Unable to process this content due to encoding issues.]"

def clean_text(text):
    if isinstance(text, bytes):
        try:
            return text.decode("utf-8", "replace")
        except:
            return text.decode("latin1", "replace")
    return str(text).encode("utf-8", "replace").decode("utf-8", "replace")

# --- Email Fetching & Parsing ---

def fetch_last_emails(username, password, n=20):
    emails = []
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(username, password)
        imap.select("inbox")
        status, messages = imap.search(None, "ALL")
        email_ids = messages[0].split()
        if not email_ids:
            return []

        latest_ids = email_ids[-n:]

        for eid in reversed(latest_ids):
            res, msg = imap.fetch(eid, "(RFC822)")
            for response in msg:
                if isinstance(response, tuple):
                    msg = email.message_from_bytes(response[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    subject = clean_text(subject)
                    from_ = msg.get("From")
                    date_ = msg.get("Date")

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                                try:
                                    body = part.get_payload(decode=True).decode()
                                    break
                                except:
                                    pass
                    else:
                        body = msg.get_payload(decode=True).decode()

                    emails.append({
                        "rank": 0,
                        "from": from_,
                        "subject": subject,
                        "date": date_,
                        "body": body.strip()
                    })
        imap.logout()
    except Exception as e:
        st.error(f"Error fetching emails: {e}")
    return emails

# --- Simplification for Ranking ---

def simplify_email_data(email_list, max_chars=300):
    simplified = []
    for e in email_list:
        simplified.append({
            "rank": 0,
            "from": e["from"],
            "subject": e["subject"],
            "date": e["date"],
            "body": e["body"][:max_chars] + "..." if len(e["body"]) > max_chars else e["body"]
        })
    return simplified

# --- Gemini Integration ---

def rank_emails_with_gemini(email_list, sort_option="Default"):
    emails_str = json.dumps(email_list, indent=2)

    if sort_option == "Urgency":
        criteria = "Rank emails by urgency based on tone, keywords, and deadlines mentioned. Prioritize high-stakes language and time-sensitive instructions."
    elif sort_option == "Time":
        criteria = "Rank emails by how close the deadline is. Emails with immediate or near-term deadlines come first."
    elif sort_option == "Sender":
        criteria = "Rank emails by sender importance (e.g., executives > directors > team leads > peers > interns)."
    else:
        criteria = """
Please update the 'rank' field in each dictionary so that:
- The most relevant or important emails get the lowest rank (1 = highest importance).
- The least relevant emails get the highest rank (n = lowest importance), where n is the number of emails.
- No two emails should share the same rank.

Use contextual information to determine importance. For example:
- Security alerts or account setup emails from Google are more important than casual test emails.
- Emails with only "hola", "prueba", etc., are less important.
- Password or verification-related emails are important.
"""

    prompt = f"""
You will receive a list of email dictionaries in the format:

[
  {{"rank": 0, "from": "...", "subject": "...", "date": "...", "body": "..."}},
  ...
]

Your task: {criteria}
Return only the modified list with updated ranks and preserve all other fields as-is. Do not add any explanation or comments.

Here is the input list:

{emails_str}
"""

    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(prompt)

    match = re.search(r"\[.*\]", response.text, re.DOTALL)
    if match:
        try:
            ranked_list = ast.literal_eval(match.group(0))
            return sorted(ranked_list, key=lambda x: x["rank"])
        except Exception as e:
            st.error(f"Failed to parse Gemini response: {e}")
            return []
    else:
        st.error("No list found in Gemini response.")
        return []


def summarize_email_with_gemini(email_body, max_words=300):
    email_body = clean_for_gemini(email_body)
    prompt = f"""
Summarize the following email in up to {max_words} words. Focus only on what is explicitly written. Do not assume, speculate, or include generalizations.

Email:
\"\"\"
{email_body}
\"\"\"

Summary:
"""
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(prompt)
    return response.text.strip()

def answer_question_about_email(email_body, question):
    email_body = clean_for_gemini(email_body)
    prompt = f"""
You are an email assistant. Answer the user's question **only using information that is present in the email**. If the email doesn't contain the answer, say "The email doesn't specify that."

Email content:
\"\"\"
{email_body}
\"\"\"

User question: "{question}"

Answer:
"""
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(prompt)
    return response.text.strip()

# --- Caching ---

@st.cache_data(show_spinner="📬 Fetching and ranking emails...", ttl=300)
def fetch_and_rank_emails(username, password, n=20, sort_option="Default"):
    raw_emails = fetch_last_emails(username, password, n)
    simplified = simplify_email_data(raw_emails)
    ranked = rank_emails_with_gemini(simplified, sort_option=sort_option)
    return ranked, raw_emails
# --- Reply Handler ---

def send_email_reply(to_email, subject, body, username, password):
    try:
        msg = EmailMessage()
        msg["From"] = username
        msg["To"] = to_email
        msg["Subject"] = f"Re: {subject}"
        msg.set_content(body)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(username, password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

def call_gemini(prompt):
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}]
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return f"Error {response.status_code}: {response.text}"

def email_response_assistant(email_dict, selected_index):
    st.subheader("🤖 AI Reply Assistant")

    # Clear previous reply when switching emails
    if st.session_state.get("last_reply_index") != selected_index:
        st.session_state.ai_response = ""
        st.session_state.chat_input = ""
        st.session_state.show_response = False
        st.session_state.last_reply_index = selected_index

    subject = email_dict.get("subject", "No Subject")
    sender = email_dict.get("from", "Unknown")
    body = email_dict.get("body", "No Body")
    st.session_state.email_context = f"From: {sender}\nSubject: {subject}\n\n{body.strip()}"

    # Tone selection
    st.subheader("Select Formality Level")
    tone = st.select_slider(
        "Tone",
        options=["Casual", "Neutral", "Formal"],
        value=st.session_state.get("tone", "Neutral"),
        key=f"tone_selector_{selected_index}"
    )
    st.session_state.tone = tone

    # Generate AI reply
    if st.button("✍️ Generate AI Reply", key=f"generate_{selected_index}"):
        st.session_state.show_response = True
        st.session_state.ai_response = ""

    if st.session_state.show_response and not st.session_state.ai_response:
        prompt = f"{st.session_state.email_context}\n\nInstruction: Write a professional email reply.\n\nWrite in a {tone.lower()} tone."
        with st.spinner("Generating response..."):
            st.session_state.ai_response = call_gemini(prompt)

    # Show and refine
    if st.session_state.show_response and st.session_state.ai_response:
        st.subheader("💬 AI-Generated Reply")
        st.text(st.session_state.ai_response)

        st.subheader("🔧 Refine Your Reply")
        with st.form(key=f"refine_form_{selected_index}"):
            chat_input = st.text_input("Ask to revise or update the reply:", value=st.session_state.get("chat_input", ""), label_visibility="collapsed")
            submitted = st.form_submit_button("Apply")
            if submitted and chat_input.strip():
                followup_prompt = (
                    f"Original Email:\n{st.session_state.email_context}\n\n"
                    f"Current AI Reply:\n{st.session_state.ai_response}\n\n"
                    f"Instruction: {chat_input}\n\nWrite in a {tone.lower()} tone."
                )
                with st.spinner("Updating reply..."):
                    st.session_state.ai_response = call_gemini(followup_prompt)
                    st.session_state.chat_input = ""
                st.rerun()
            else:
                st.session_state.chat_input = chat_input  # persist input while typing

        # Send reply
        st.subheader("📤 Send This Reply")
        if st.button("Send Reply", key=f"send_{selected_index}"):
            to_email = email_dict["from"].split("<")[-1].replace(">", "").strip()
            success = send_email_reply(to_email, subject, st.session_state.ai_response, USERNAME, PASSWORD)
            if success:
                st.success("✅ Reply sent!")



# --- Streamlit UI ---

#st.set_page_config(layout="wide")
#st.title("📬 Email Viewer with Gemini Assistant")

st.set_page_config(layout="wide")

col1, col2 = st.columns([0.2, 0.8])
with col1:
    st.image("kawaii_mailbox_bot_transparent_clean.png", width=200)
with col2:
    st.markdown("""
    <h1 style='font-size: 90px; margin-bottom: 0;'>InboxIE</h1>
    <p style='font-size: 18px; color: gray;'>Powered by Gemini + Streamlit</p>
""", unsafe_allow_html=True)

    #st.title("ImboxIE")
    #st.caption("Powered by Gemini + Streamlit")


if st.button("🔄 Refresh Inbox"):
    st.cache_data.clear()

ranked_emails, full_emails = fetch_and_rank_emails(USERNAME, PASSWORD)

if ranked_emails:
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.subheader("📥 Inbox")

        sort_option = st.selectbox(
            "Sort emails by:",
            options=["Default (Smart Rank)", "Time", "Urgency", "Sender"],
            index=0
        )

        selected_index = st.radio(
            "Select an email:",
            options=list(range(len(ranked_emails))),
            format_func=lambda i: f"{ranked_emails[i]['subject'][:60]}",
            label_visibility="collapsed"
        )

    with right_col:
        selected_email = ranked_emails[selected_index]

        # ✅ Match full email by subject + from + date
        selected_full_email = next(
            (e for e in full_emails if
             e["subject"] == selected_email["subject"] and
             e["from"] == selected_email["from"] and
             e["date"] == selected_email["date"]),
            selected_email  # fallback if not found
        )

        st.subheader("📧 Email Preview")
        st.markdown(f"**From**: {selected_email['from']}")
        st.markdown(f"**Subject**: {selected_email['subject']}")
        st.markdown(f"**Date**: {selected_email['date']}")

        with st.expander("📖 Click to show full email content"):
            st.markdown(sanitize_for_markdown(selected_full_email["body"]))


        # 📜 Summary
        if "email_summary" not in st.session_state or st.session_state.get("last_index") != selected_index:
            with st.spinner("Generating summary..."):
                st.session_state.email_summary = summarize_email_with_gemini(selected_full_email["body"])
                st.session_state.last_index = selected_index

        st.subheader("Summary")
        st.markdown(st.session_state.email_summary)

        # ❓ Q&A
        st.subheader("❓ Ask a question about this email")
        question = st.text_input("Your question", key=f"question_input_{selected_index}")

        if question:
            if f"last_question_{selected_index}" not in st.session_state or st.session_state[f"last_question_{selected_index}"] != question:
                with st.spinner("Getting answer..."):
                    st.session_state[f"last_question_{selected_index}"] = question
                    st.session_state[f"answer_{selected_index}"] = answer_question_about_email(selected_full_email["body"], question)

        if st.session_state.get(f"answer_{selected_index}"):
            st.markdown("**Answer:**")
            st.success(st.session_state[f"answer_{selected_index}"])

        # ✍️ Reply
        # 👉 Run the assistant with selected full email
        email_response_assistant(selected_full_email, selected_index)
else:
    st.info("No emails found.")

#gols