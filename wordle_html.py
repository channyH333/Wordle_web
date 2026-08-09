import os
import random
import secrets
import threading
import webbrowser

from flask import Flask, jsonify, render_template_string, request, session

try:
    from wordfreq import iter_wordlist
except ImportError as exc:
    raise SystemExit(
        "Required packages are missing.\n"
        "Run: pip install -r requirements.txt"
    ) from exc


# ==================================================
# Game settings
# ==================================================

WORD_LENGTH = 5
MAX_ATTEMPTS = 6
ANSWER_POOL_SIZE = 100

WRONG_MESSAGES = [
    "HMM you sure? 👀",
    "Okay stay calm 🧐",
    "I just can't believe this 🤨",
    "Is this all you've got, {name}? 😏",
    "No way... 😵",
    "BAHAHAHAHAHAHA 😂",
]

WIN_MESSAGE = "Way to go Shawty 🎉"


# ==================================================
# Word source
# ==================================================

def load_common_words(limit=ANSWER_POOL_SIZE):
    words = []
    seen = set()

    for candidate in iter_wordlist("en"):
        word = candidate.lower()

        if len(word) != WORD_LENGTH:
            continue

        if not word.isascii() or not word.isalpha():
            continue

        if word in seen:
            continue

        seen.add(word)
        words.append(word)

        if len(words) >= limit:
            break

    return words


ANSWER_WORDS = load_common_words()


# ==================================================
# Wordle evaluation
# ==================================================

def evaluate_guess(answer, guess):
    result = ["absent"] * WORD_LENGTH
    remaining = {}

    # First pass: correct letter + correct position
    for i in range(WORD_LENGTH):
        if guess[i] == answer[i]:
            result[i] = "correct"
        else:
            letter = answer[i]
            remaining[letter] = remaining.get(letter, 0) + 1

    # Second pass: correct letter + wrong position
    for i in range(WORD_LENGTH):
        if result[i] == "correct":
            continue

        letter = guess[i]
