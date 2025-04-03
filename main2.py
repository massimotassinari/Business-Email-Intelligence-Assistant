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
import google.generativeai as genai

# --- Configuration ---
USERNAME = "ml.project.ie@gmail.com"
PASSWORD = "ucjeravgzupoqyra"
genai.configure(api_key="AIzaSyDcGbQEPqWiwrauiM96h7_uElQIlowUqmM")

# --- Helper Functions ---

def clean_text(text):
    if isinstance(text, bytes):
        try:
            return text.decode("utf-8")
        except:
            return text.decode("latin1")
    return text


def fetch_last_emails(username, password, n=20):
    emails = []
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(username, password)
        imap.select("inbox")
        status, messages = imap.search(None, "ALL")  # Use "UNSEEN" for unread only

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


def rank_emails_with_gemini(email_list):
    """
    Takes a list of email dictionaries and returns it with updated
    'rank' values based on contextual importance, sorted by rank ascending.
    """
    emails_str = json.dumps(email_list, indent=2)

    prompt = f"""
You will receive a list of email dictionaries in the format:

[
  {{"rank": 0, "from": "...", "subject": "...", "date": "...", "body": "..."}},
  ...
]

Please update the "rank" field in each dictionary so that:
- The most relevant or important emails get the lowest rank (1 = highest importance).
- The least relevant emails get the highest rank (n = lowest importance), where n is the number of emails.
- No two emails should share the same rank.

Use contextual information to determine importance. For example:
- Security alerts or account setup emails from Google are more important than casual test emails.
- Emails with only "hola", "prueba", etc., are less important.
- Password or verification-related emails are important.

Return only the modified list with updated ranks and preserve all other fields as-is. Do not add any explanation or comments.

Here is the input list:

{emails_str}
    """

    model = genai.GenerativeModel('gemini-1.5-flash-latest')
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


@st.cache_data(show_spinner="📬 Fetching and ranking emails...", ttl=300)
def fetch_and_rank_emails(username, password, n=20):
    emails = fetch_last_emails(username, password, n)
    if emails:
        return rank_emails_with_gemini(emails)
    return []


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


# --- Streamlit UI ---

st.set_page_config(layout="wide")
st.title("📬 Email Viewer with Gemini Ranking & Reply")

# Optional refresh button
if st.button("🔄 Refresh Inbox"):
    st.cache_data.clear()

# Load emails (cached unless refreshed)
ranked_emails = fetch_and_rank_emails(USERNAME, PASSWORD)

if ranked_emails:
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.subheader("📥 Inbox")
        selected_index = st.radio(
            "Select an email:",
            options=list(range(len(ranked_emails))),
            format_func=lambda i: f"{ranked_emails[i]['subject'][:60]}",
            label_visibility="collapsed"
        )

    with right_col:
        selected_email = ranked_emails[selected_index]

        # Top: Email Details
        st.subheader("📧 Email Content")
        st.markdown(f"**From**: {selected_email['from']}")
        st.markdown(f"**Subject**: {selected_email['subject']}")
        st.markdown(f"**Date**: {selected_email['date']}")
        st.markdown("---")
        st.markdown(selected_email["body"])

        # Bottom: Reply
        st.subheader("✍️ Reply to this Email")
        reply_content = st.text_area("Your reply message", height=150)
        if st.button("Send Reply"):
            to_email = selected_email["from"].split("<")[-1].replace(">", "").strip()
            success = send_email_reply(to_email, selected_email["subject"], reply_content, USERNAME, PASSWORD)
            if success:
                st.success("✅ Reply sent!")
else:
    st.info("No emails found.")
