# 📬 AI Email Assistant with Gemini

This project is a **Streamlit web app** that connects to your Gmail inbox, fetches and ranks recent emails, summarizes them, answers questions about them, and helps you **generate and send AI-powered replies** — all powered by **Google's Gemini 1.5 API**.

> ✨ Ideal for busy professionals or students who want to manage and respond to emails faster and smarter.

---

## 🚀 Features

- **Secure IMAP integration** to fetch Gmail inbox.
- **Email importance ranking** using Gemini 1.5 Flash.
- **Smart summaries** of email content.
- **Contextual Q&A** about email content.
- **AI-generated replies** with selectable tone (Casual, Neutral, Formal).
- **Refinement loop** for rewording or customizing the reply.
- **Send replies directly** from the app via SMTP.

---

## 🧠 Powered by Gemini

This app uses the **Google Generative AI (Gemini)** API for:
- Ranking emails based on importance.
- Summarizing email bodies.
- Answering questions grounded only in the email context.
- Writing and refining email replies in a chosen tone.

---

## 🛠️ Requirements

- Python 3.8+
- A Gmail account (with an **App Password** for IMAP/SMTP access)
- A **Gemini API key** from Google AI Studio
- Dependencies listed in `requirements.txt`

---

## 🧪 Setup

1. **Clone the repo**  
   ```bash
   git clone https://github.com/yourusername/email-gemini-assistant.git
   cd email-gemini-assistant
   ```

2. **Create a virtual environment (optional but recommended)**  
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**  
   Create a `.env` file (or use `variables.env`) and add your Gemini API key:
   ```env
   GEMINI_API_KEY=your_google_gemini_api_key
   ```

5. **Add your Gmail credentials**  
   Update the `USERNAME` and `PASSWORD` fields in the script.  
   > ⚠️ Use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular Gmail password.

---

## 🖥️ Running the App

```bash
streamlit run app.py
```

The app will open in your browser. You can:
- Refresh and fetch recent emails.
- View summaries, ask questions, and draft AI replies.
- Edit and send responses directly.

---

## 📌 Notes

- Email data is cached for 5 minutes to reduce unnecessary API calls.
- Gemini responses are parsed and validated. Errors are handled with helpful messages.
- All Gemini prompts are carefully designed to **ensure grounded, safe, and concise outputs**.

---

## 📄 License

MIT License. Feel free to use, modify, and share.

---

## 🙌 Acknowledgments

- [Google Generative AI](https://makersuite.google.com/)
- [Streamlit](https://streamlit.io/)
- [OpenAI / LangChain inspirations](https://www.langchain.com/)
