import streamlit as st
import imaplib
import smtplib
import email
from email.message import EmailMessage
from email.header import decode_header

USERNAME = "ml.project.ie@gmail.com"
PASSWORD = "ucjeravgzupoqyra"

def clean_text(text):
    if isinstance(text, bytes):
        try:
            return text.decode("utf-8")
        except:
            return text.decode("latin1")
    return text

@st.cache_data(show_spinner="Fetching unread emails...")
def fetch_last_emails(username, password, n=20):
    emails = []
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com")
        imap.login(username, password)
        imap.select("inbox")
        status, messages = imap.search(None, "ALL")  # Only unread

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
                        "from": from_,
                        "subject": subject,
                        "date": date_,
                        "body": body.strip()
                    })
        imap.logout()
    except Exception as e:
        st.error(f"Error fetching emails: {e}")
    return emails

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

# Layout setup
st.set_page_config(layout="wide")
st.title("📬 Email Viewer with Reply")

emails = fetch_last_emails(USERNAME, PASSWORD)

if emails:
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.subheader("📥 Inbox")
        selected_index = st.radio(
            "Select an email:",
            options=list(range(len(emails))),
            format_func=lambda i: f"{emails[i]['subject'][:60]}",
            label_visibility="collapsed"
        )

    with right_col:
        selected_email = emails[selected_index]

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
