import streamlit as st
import requests
from dotenv import load_dotenv
import os

# === Load API Key from .env ===
load_dotenv("variables.env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

# === Gemini API Call ===
def call_gemini(prompt):
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(API_URL, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return f"Error {response.status_code}: {response.text}"

# === Email Response App Function ===
def email_response_assistant(email_dict):
    if "ai_response" not in st.session_state:
        st.session_state.ai_response = ""
    if "tone" not in st.session_state:
        st.session_state.tone = "Neutral"
    if "show_response" not in st.session_state:
        st.session_state.show_response = False
    if "chat_input" not in st.session_state:
        st.session_state.chat_input = ""

    subject = email_dict.get("subject", "No Subject")
    sender = email_dict.get("from", "Unknown")
    body = email_dict.get("body", "No Body")
    st.session_state.email_context = f"From: {sender}\nSubject: {subject}\n\n{body.strip()}"

    st.subheader("Select Formality Level")
    st.session_state.tone = st.select_slider(
        "Tone",
        options=["Casual", "Neutral", "Formal"],
        value=st.session_state.tone
    )

    if st.button("Set and Generate Reply"):
        st.session_state.show_response = True
        st.session_state.ai_response = ""

    if st.session_state.show_response and not st.session_state.ai_response:
        prompt = f"{st.session_state.email_context}\n\nInstruction: Write a professional email reply.\n\nWrite in a {st.session_state.tone.lower()} tone."
        with st.spinner("Generating response..."):
            st.session_state.ai_response = call_gemini(prompt)

    if st.session_state.show_response and st.session_state.ai_response:
        st.subheader("AI-Generated Reply")
        st.text(st.session_state.ai_response)

        st.subheader("Refine Your Reply")
        col1, col2 = st.columns([6, 1])
        with col1:
            st.session_state.chat_input = st.text_input("Ask to revise or update the reply:", value=st.session_state.chat_input, label_visibility="collapsed")
        with col2:
            if st.button("Send") and st.session_state.chat_input.strip():
                followup_prompt = f"Original Email:\n{st.session_state.email_context}\n\nCurrent AI Reply:\n{st.session_state.ai_response}\n\nInstruction: {st.session_state.chat_input}\n\nWrite in a {st.session_state.tone.lower()} tone."
                with st.spinner("Updating reply..."):
                    st.session_state.ai_response = call_gemini(followup_prompt)
                    st.session_state.chat_input = ""
                st.experimental_rerun()

# === Run Example ===
example_email = {
    'rank': 8,
    'from': 'ml_project <ml.project.ie@gmail.com>',
    'subject': 'prueba',
    'date': 'Mon, 31 Mar 2025 17:46:22 +0200',
    'body': 'hola'
}

email_response_assistant(example_email)