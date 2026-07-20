"""
preprocess.py
--------------
This module contains all text-cleaning (NLP preprocessing) functions
used by the FAQ chatbot.

Why does this file exist separately?
- Both the FAQ dataset and every incoming user question must be cleaned
  in EXACTLY the same way before comparison. Keeping this logic in one
  place avoids duplication and bugs (e.g., forgetting a step somewhere).
- It keeps app.py focused on routing/orchestration, not text-processing
  details. This is a common "separation of concerns" practice.

Pipeline order for each piece of text:
    1. Lowercase
    2. Remove punctuation
    3. Tokenize (split into words)
    4. Remove stopwords (common filler words)
    5. Lemmatize (reduce words to their dictionary base form)
"""

import string
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer


def download_nltk_resources():
    """
    Downloads the NLTK data packages required for preprocessing,
    but only if they are not already present on this machine.

    Why check first? Downloading every time the app starts would be
    slow and unnecessary. NLTK stores downloaded data locally (usually
    in a folder like C:\\Users\\<you>\\AppData\\Roaming\\nltk_data on
    Windows), so after the first successful run, this function will
    find everything already there and skip re-downloading.
    """
    resources = {
        "tokenizers/punkt": "punkt",
        "tokenizers/punkt_tab": "punkt_tab",
        "corpora/stopwords": "stopwords",
        "corpora/wordnet": "wordnet",
        "corpora/omw-1.4": "omw-1.4",
    }

    for resource_path, package_name in resources.items():
        try:
            nltk.data.find(resource_path)
        except LookupError:
            print(f"Downloading NLTK resource: {package_name} ...")
            nltk.download(package_name, quiet=True)


# Run the resource check once, when this module is first imported,
# so app.py doesn't need to remember to do it separately.
download_nltk_resources()

# Load English stopwords once at import time (not inside the function),
# because reloading the stopword list on every single function call
# would be wasteful. This set is reused for every FAQ and every query.
STOPWORDS = set(stopwords.words("english"))

# Create ONE lemmatizer instance and reuse it. Creating a new
# WordNetLemmatizer object every time we lemmatize a word is
# unnecessary overhead.
lemmatizer = WordNetLemmatizer()


def clean_text(text: str) -> str:
    """
    Runs the full preprocessing pipeline on a single piece of text
    and returns a cleaned string ready for TF-IDF vectorization.

    Args:
        text (str): raw input text (a user question or an FAQ question)

    Returns:
        str: cleaned text, e.g. "reset password" from "How do I RESET my Password?!"
    """
    # Guard clause: handle empty or non-string input gracefully instead
    # of letting the function crash further down the pipeline.
    if not text or not isinstance(text, str):
        return ""

    # Step 1: Lowercase
    # "How do I Reset my Password?" -> "how do i reset my password?"
    text = text.lower()

    # Step 2: Remove punctuation
    # str.maketrans('', '', string.punctuation) builds a translation
    # table that maps every punctuation character to None (i.e. deletes it).
    # string.punctuation = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
    text = text.translate(str.maketrans("", "", string.punctuation))

    # Step 3: Tokenization
    # Splits the sentence into a list of individual words (tokens).
    # "how do i reset my password" -> ["how", "do", "i", "reset", "my", "password"]
    tokens = word_tokenize(text)

    # Step 4: Remove stopwords
    # Stopwords are extremely common words ("i", "do", "my", "the", "is")
    # that carry little meaning for matching intent. Removing them lets
    # TF-IDF focus on the words that actually distinguish one FAQ from another.
    tokens = [word for word in tokens if word not in STOPWORDS]

    # Step 5: Lemmatization
    # Reduces each word to its dictionary base form.
    # "resetting" -> "reset", "passwords" -> "password"
    tokens = [lemmatizer.lemmatize(word) for word in tokens]

    # Join the cleaned tokens back into a single string, because
    # scikit-learn's TfidfVectorizer expects a string per document,
    # not a list of tokens.
    return " ".join(tokens)


def clean_texts(text_list: list) -> list:
    """
    Convenience helper to clean a list of texts at once
    (used when preprocessing all FAQ questions in bulk).

    Args:
        text_list (list): list of raw strings

    Returns:
        list: list of cleaned strings, same order as input
    """
    return [clean_text(text) for text in text_list]


# ---------------------------------------------------------------
# Quick manual test — only runs if you execute this file directly
# with: python utils/preprocess.py
# This is NOT part of the Flask app; it's just for us to sanity-check
# the pipeline works before wiring it into app.py.
# ---------------------------------------------------------------
if __name__ == "__main__":
    sample = "How do I RESET my Password?! It's not working."
    print("Original:", sample)
    print("Cleaned :", clean_text(sample))