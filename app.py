"""
app.py
------
Main Flask application for the FAQ Chatbot.

Responsibilities of this file:
1. Load the FAQ dataset from faq.json (once, at startup).
2. Preprocess and vectorize all FAQ questions using TF-IDF (once, at startup).
3. Expose two routes:
     GET  "/"            -> serves the chat UI (index.html)
     POST "/get_answer"  -> receives a user question, returns the best-matching answer

Why load and vectorize FAQs only once at startup (not per-request)?
Because it's a relatively expensive operation, and the FAQ data doesn't
change while the server is running. Doing it once and reusing the result
for every request is far more efficient than repeating it every time
a user sends a message.
"""

import json
import logging

from flask import Flask, render_template, request, jsonify
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from utils.preprocess import clean_text, clean_texts

# ---------------------------------------------------------------
# Basic logging setup.
# Why: print() statements are fine for tiny scripts, but a real
# application should use the `logging` module so we can control
# what gets logged, and it plays nicely with production servers.
# ---------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Initialize the Flask application.
# Flask automatically looks for templates in a "templates/" folder
# and static files (CSS/JS/images) in a "static/" folder, by convention.
app = Flask(__name__)

# Minimum cosine similarity score required to trust a match.
# Below this threshold, we assume no FAQ is a good enough match
# and return a fallback "I don't know" message instead of guessing.
# This value was chosen empirically -- feel free to tune it once you
# start testing with real questions.
CONFIDENCE_THRESHOLD = 0.2

FAQ_FILE_PATH = "faq.json"


def load_faqs(filepath: str) -> list:
    """
    Loads the FAQ dataset from a JSON file.

    Args:
        filepath (str): path to the faq.json file

    Returns:
        list: list of FAQ dictionaries, e.g.
              [{"id": 1, "category": "...", "question": "...", "answer": "..."}, ...]

    Why wrap this in try/except?
    If faq.json is missing, malformed, or has a typo in its path, we want
    the app to fail with a clear, understandable error message at startup
    rather than crashing later with a confusing traceback when a user
    sends a message.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            faqs = json.load(f)
        logger.info(f"Loaded {len(faqs)} FAQs from '{filepath}'")
        return faqs
    except FileNotFoundError:
        logger.error(f"FAQ file not found at '{filepath}'. Please check the path.")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"FAQ file '{filepath}' contains invalid JSON: {e}")
        raise


def build_vectorizer(faqs: list):
    """
    Cleans all FAQ questions and fits a TF-IDF vectorizer on them.

    This is done ONCE at startup. The fitted vectorizer "remembers"
    the vocabulary learned from our FAQ dataset, and will later be
    reused (via .transform()) to convert each new user question into
    a compatible vector -- without re-learning the vocabulary.

    Args:
        faqs (list): list of FAQ dictionaries

    Returns:
        tuple: (vectorizer, faq_vectors)
            vectorizer  -> the fitted TfidfVectorizer instance
            faq_vectors -> TF-IDF matrix representing all FAQ questions
    """
    raw_questions = [faq["question"] for faq in faqs]
    cleaned_questions = clean_texts(raw_questions)

    vectorizer = TfidfVectorizer()
    # fit_transform does two things at once:
    #   1. fit()       -> learns the vocabulary from cleaned_questions
    #   2. transform()  -> converts cleaned_questions into TF-IDF vectors
    faq_vectors = vectorizer.fit_transform(cleaned_questions)

    logger.info(f"TF-IDF vectorizer fitted on {len(cleaned_questions)} FAQ questions")
    return vectorizer, faq_vectors


def get_best_answer(user_question: str, faqs: list, vectorizer, faq_vectors) -> dict:
    """
    Finds the best-matching FAQ answer for a given user question.

    Args:
        user_question (str): the raw question typed by the user
        faqs (list): the full list of FAQ dictionaries
        vectorizer: the TF-IDF vectorizer fitted on FAQ questions
        faq_vectors: TF-IDF matrix of all FAQ questions

    Returns:
        dict: {
            "answer": str,          # the matched answer, or fallback message
            "matched_question": str or None,  # which FAQ question matched (for debugging/UI)
            "confidence": float     # similarity score between 0 and 1
        }
    """
    # Step 1: Clean the user's question using the SAME pipeline used for FAQs.
    # This consistency is essential -- if we skipped this step, the user's
    # raw text (with stopwords/punctuation) would not match well against
    # our cleaned FAQ vocabulary.
    cleaned_question = clean_text(user_question)

    # Edge case: if cleaning results in an empty string (e.g. user sent
    # only punctuation or only stopwords), there's nothing meaningful
    # to compare, so we return the fallback immediately.
    if not cleaned_question:
        return {
            "answer": "Sorry, I couldn't find an appropriate answer.",
            "matched_question": None,
            "confidence": 0.0,
        }

    # Step 2: Transform the cleaned user question into the SAME vector
    # space as the FAQ vectors, using the already-fitted vectorizer.
    # Note: transform() expects a list, so we wrap the string in [ ].
    user_vector = vectorizer.transform([cleaned_question])

    # Step 3: Compute cosine similarity between the user's vector and
    # every FAQ vector. cosine_similarity returns a 2D array; since we
    # only have ONE user vector, we take row [0] to get a 1D array of
    # similarity scores (one score per FAQ).
    similarity_scores = cosine_similarity(user_vector, faq_vectors)[0]

    # Step 4: Find the index of the highest similarity score.
    best_index = similarity_scores.argmax()
    best_score = float(similarity_scores[best_index])

    logger.info(f"User question: '{user_question}' | Best score: {best_score:.3f}")

    # Step 5: Apply the confidence threshold.
    if best_score < CONFIDENCE_THRESHOLD:
        return {
            "answer": "Sorry, I couldn't find an appropriate answer.",
            "matched_question": None,
            "confidence": best_score,
        }

    best_faq = faqs[best_index]
    return {
        "answer": best_faq["answer"],
        "matched_question": best_faq["question"],
        "confidence": best_score,
    }


# ---------------------------------------------------------------
# Load data and build the vectorizer ONCE when the app starts,
# not inside a route function (which would re-run on every request).
# ---------------------------------------------------------------
faqs = load_faqs(FAQ_FILE_PATH)
vectorizer, faq_vectors = build_vectorizer(faqs)


@app.route("/")
def index():
    """
    Serves the main chat UI page.
    Flask's render_template() looks inside the 'templates/' folder
    by default, so this returns templates/index.html.
    """
    return render_template("index.html")


@app.route("/get_answer", methods=["POST"])
def get_answer():
    """
    Main chatbot API endpoint.

    Expects a JSON body like:
        { "question": "How do I reset my password?" }

    Returns a JSON response like:
        {
            "answer": "Go to the login page...",
            "matched_question": "How can I reset my password?",
            "confidence": 0.83
        }
    """
    try:
        data = request.get_json(silent=True)

        # Defensive checks: never trust incoming data blindly.
        # This prevents crashes if the frontend sends malformed
        # or missing data (e.g. due to a bug or a bad network request).
        if not data or "question" not in data:
            return jsonify({"error": "Request must include a 'question' field."}), 400

        user_question = data["question"].strip()

        if not user_question:
            return jsonify({"error": "Question cannot be empty."}), 400

        result = get_best_answer(user_question, faqs, vectorizer, faq_vectors)
        return jsonify(result), 200

    except Exception as e:
        # Catch-all safety net: if anything unexpected goes wrong,
        # log it for debugging but return a clean, generic error to
        # the user instead of leaking a stack trace to the frontend.
        logger.exception("Unexpected error in /get_answer")
        return jsonify({"error": "Something went wrong on the server."}), 500


@app.route("/faqs", methods=["GET"])
def get_all_faqs():
    """
    Returns all FAQs (id, category, question) so the frontend can
    display "Suggested FAQs" when the page loads.
    We intentionally omit the raw 'answer' here since it's not needed
    until the user actually clicks/asks it -- keeping the payload small.
    """
    suggestions = [
        {"id": faq["id"], "category": faq["category"], "question": faq["question"]}
        for faq in faqs
    ]
    return jsonify(suggestions), 200


if __name__ == "__main__":
    # debug=True enables auto-reload on code changes and detailed
    # error pages -- extremely helpful during development.
    # IMPORTANT: this should be turned OFF (debug=False) in production,
    # since debug mode can expose sensitive information.
    app.run(debug=True)