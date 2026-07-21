# 🤖 FAQ Chatbot using NLP

A web-based chatbot that answers Frequently Asked Questions using Natural
Language Processing. Built with Flask, NLTK, and scikit-learn on the
backend, and a responsive vanilla HTML/CSS/JavaScript frontend.

Given a user's question, the chatbot cleans and vectorizes the text using
**TF-IDF**, compares it against a dataset of known FAQs using **Cosine
Similarity**, and returns the best-matching answer — or a polite fallback
message if no FAQ is a good enough match.

---

## ✨ Features

### Core (NLP / Backend)
- Loads FAQs from a JSON file (`faq.json`)
- Text preprocessing pipeline using NLTK:
  - Lowercasing
  - Punctuation removal
  - Tokenization
  - Stopword removal
  - Lemmatization
- TF-IDF vectorization of FAQ questions
- Cosine similarity matching against user queries
- Confidence threshold with graceful fallback response

### Chat UI
- Modern, responsive chat interface
- User & bot avatars with chat bubbles
- Message timestamps
- Typing indicator ("bot is thinking...") animation
- Auto-scroll to the latest message
- Scrollable chat history
- Enter-key support to send messages

### Extra Features
- 🌙 Dark / Light mode toggle (persists across reloads)
- 🗑️ Clear chat (with confirmation)
- ⬇️ Download entire conversation as a `.txt` file
- 📋 Copy-to-clipboard button on every bot answer
- 🔊 Text-to-Speech playback of bot answers (Web SpeechSynthesis API)
- ⏹️ Stop-speaking control
- 💡 Suggested FAQ chips shown on page load
- Smooth entrance animations for new messages

---

## 🛠️ Technologies Used

**Backend:** Python, Flask, NLTK, scikit-learn
**Frontend:** HTML5, CSS3, Vanilla JavaScript
**Version Control:** Git, GitHub

---

## 📁 Project Structure

```
FAQ-Chatbot/
│
├── app.py                  # Main Flask application (routes + matching logic)
├── requirements.txt         # Python dependencies
├── README.md                 # Project documentation
├── faq.json                  # FAQ dataset (questions + answers)
├── .gitignore
│
├── static/
│   ├── css/
│   │   └── style.css         # Chat UI styling (light/dark themes, animations)
│   ├── js/
│   │   └── script.js         # Frontend logic (chat, TTS, dark mode, etc.)
│   └── images/                # Avatar/icon assets
│
├── templates/
│   └── index.html            # Chat UI markup
│
└── utils/
    ├── __init__.py
    └── preprocess.py          # NLP text-cleaning pipeline
```

---

## ⚙️ Installation

**Prerequisites:** Python 3.9+ installed on your machine.

1. **Clone the repository**
   ```bash
   git clone https://github.com/<your-username>/FAQ-Chatbot.git
   cd FAQ-Chatbot
   ```

2. **(Recommended) Create a virtual environment**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   > NLTK's required data (stopwords, wordnet, punkt) will download
   > automatically the first time you run the app.

---

## ▶️ Running Locally

```bash
python app.py
```

Then open your browser and go to:
```
http://127.0.0.1:5000/
```

---

## 📸 Screenshots

> _Add screenshots of your chatbot here once styled and running, e.g.:_
> - Light mode chat view
> - Dark mode chat view
> - Mobile responsive view

```
![Light Mode](static/images/screenshot-light.png)
![Dark Mode](static/images/screenshot-dark.png)
```

---

## 🚀 Future Improvements

- Support multiple phrasings per FAQ (e.g. a `patterns` list) to improve
  match accuracy for differently-worded questions
- Add spell-correction before matching to handle typos
- Replace TF-IDF with sentence embeddings (e.g. Sentence-BERT) for more
  semantic (meaning-based) matching instead of pure keyword overlap
- Add a feedback mechanism ("Was this helpful?") to flag poorly-answered
  questions for review
- Persist chat history server-side (e.g. with a database) instead of
  only in-browser memory
- Add authentication and per-user chat history
- Deploy to a cloud platform (Render, Railway, PythonAnywhere) with a
  production WSGI server (e.g. Gunicorn) instead of Flask's dev server
- Add unit tests for the preprocessing and matching logic

---

## 📄 License

This project was built for educational/internship purposes.