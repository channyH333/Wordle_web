
import os
import random
import threading
import webbrowser

from flask import Flask, jsonify, render_template_string, request, session
from wordfreq import iter_wordlist

WORD_LENGTH = 5
MAX_ATTEMPTS = 6
ANSWER_POOL_SIZE = 100

WRONG_MESSAGES = [
    "HMM you sure? 👀",
    "Okay {name}, stay calm 🧐",
    "I might be judging now 🤨",
    "Is this all you've got, {name}? 😏",
    "You've got one last chance {name} 😵",
    "BAHAHAHAHAHAHA 😂",
]

WIN_MESSAGE = "Way to go Shawty 🎉"


def load_common_words(limit=ANSWER_POOL_SIZE):
    words = []
    seen = set()

    for candidate in iter_wordlist("en"):
        word = candidate.lower()
        if (
            len(word) == WORD_LENGTH
            and word.isascii()
            and word.isalpha()
            and word not in seen
        ):
            seen.add(word)
            words.append(word)
        if len(words) >= limit:
            break

    if len(words) < limit:
        raise RuntimeError("Not enough five-letter words were found.")

    return words


ANSWER_WORDS = load_common_words()


def evaluate_guess(answer, guess):
    result = ["absent"] * WORD_LENGTH
    remaining = {}

    for i in range(WORD_LENGTH):
        if guess[i] == answer[i]:
            result[i] = "correct"
        else:
            remaining[answer[i]] = remaining.get(answer[i], 0) + 1

    for i in range(WORD_LENGTH):
        if result[i] == "correct":
            continue
        letter = guess[i]
        if remaining.get(letter, 0) > 0:
            result[i] = "present"
            remaining[letter] -= 1

    return result


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "channy-wordle-secret")


def reset_game():
    session["answer"] = random.choice(ANSWER_WORDS)
    session["attempt"] = 0
    session["finished"] = False


HTML = r"""
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Channy's Wordle</title>

<style>
:root {
    color-scheme: light;
    --bg: #ffffff;
    --surface: #ffffff;
    --text: #000000;
    --muted: #787c7e;
    --border: #d3d6da;
    --filled-border: #878a8c;
    --correct: #6aaa64;
    --present: #c9b458;
    --absent: #787c7e;
    --key: #d3d6da;
    --key-hover: #bfc2c5;
    --key-text: #000000;
    --button-bg: #000000;
    --button-text: #ffffff;
    --button-hover: #333333;
    --control-hover: #f2f2f2;
    --overlay: rgba(0, 0, 0, 0.35);
    --error: #b00020;

    --score-accent: #6aaa64;
    --score-danger: #d9534f;
    --score-track: #e7e7e7;
}

:root[data-theme="dark"] {
    color-scheme: dark;
    --bg: #121213;
    --surface: #121213;
    --text: #f8f8f8;
    --muted: #a6a6a6;
    --border: #3a3a3c;
    --filled-border: #565758;
    --correct: #538d4e;
    --present: #b59f3b;
    --absent: #3a3a3c;
    --key: #818384;
    --key-hover: #9a9a9c;
    --key-text: #ffffff;
    --button-bg: #f8f8f8;
    --button-text: #121213;
    --button-hover: #d8d8d8;
    --control-hover: #2a2a2c;
    --overlay: rgba(0, 0, 0, 0.68);
    --error: #ff6b6b;

    --score-accent: #6aaa64;
    --score-danger: #ff7373;
    --score-track: #2f2f31;
}

* { box-sizing: border-box; }

body {
    margin: 0;
    min-height: 100dvh;
    background: var(--bg);
    color: var(--text);
    font-family: "Helvetica Neue", Arial, sans-serif;
}

button, input { font: inherit; }
.hidden { display: none !important; }

.top-left {
    position: fixed;
    top: 14px;
    left: 14px;
    z-index: 10001;
    display: flex;
    gap: 8px;
}

.top-right {
    position: fixed;
    top: 14px;
    right: 14px;
    z-index: 10001;
    display: flex;
    gap: 8px;
}

.icon-button,
.stats-button,
.restart-button {
    height: 42px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text);
    cursor: pointer;
    font-weight: 700;
}

.icon-button {
    width: 42px;
    padding: 0;
    border-radius: 50%;
    display: grid;
    place-items: center;
    font-size: 1.2rem;
}

.stats-button,
.restart-button {
    padding: 0 14px;
    border-radius: 6px;
}

.restart-button {
    border-color: var(--button-bg);
    background: var(--button-bg);
    color: var(--button-text);
}

.icon-button:hover,
.stats-button:hover {
    background: var(--control-hover);
}

.restart-button:hover {
    background: var(--button-hover);
}

.icon-button:active,
.stats-button:active,
.restart-button:active {
    transform: scale(0.95);
}

.game {
    width: min(96vw, 520px);
    min-height: 100dvh;
    margin: 0 auto;
    padding-bottom: 14px;
    display: flex;
    flex-direction: column;
    align-items: center;
}

.header {
    width: 100%;
    padding: 12px 70px 10px;
    border-bottom: 1px solid var(--border);
    text-align: center;
}

.title {
    margin: 0;
    font-family: "Trebuchet MS", Arial, sans-serif;
    font-size: clamp(1.55rem, 6vw, 2.05rem);
    font-weight: 900;
    letter-spacing: 0.08em;
}

.subtitle {
    margin: 5px 0 0;
    color: var(--muted);
    font-size: clamp(0.76rem, 2.8vw, 0.9rem);
}

.board-area {
    flex: 1;
    width: 100%;
    padding: 12px 0 7px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.board {
    width: min(68vw, 300px);
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 5px;
}

.tile {
    aspect-ratio: 1;
    display: grid;
    place-items: center;
    border: 2px solid var(--border);
    background: var(--surface);
    color: var(--text);
    font-family: "Arial Black", Arial, sans-serif;
    font-size: clamp(1.35rem, 6vw, 2rem);
    font-weight: 900;
    user-select: none;
}

.tile.filled { border-color: var(--filled-border); }
.tile.correct { background: var(--correct); border-color: var(--correct); color: #fff; }
.tile.present { background: var(--present); border-color: var(--present); color: #fff; }
.tile.absent { background: var(--absent); border-color: var(--absent); color: #fff; }

/* =========================
   LIVE SCORE
   ========================= */

.score-area {
    position: relative;
    width: min(72vw, 230px);
    margin: 8px auto 0;
    padding: 7px 12px 9px;
    text-align: center;
}

.score-label {
    color: var(--muted);
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 0.12em;
}

.score-value {
    margin-top: 1px;
    color: var(--text);
    font-family: "Trebuchet MS", Arial, sans-serif;
    font-size: clamp(1.35rem, 5vw, 1.8rem);
    font-weight: 900;
    line-height: 1.05;
}

.score-meter {
    width: 100%;
    height: 5px;
    margin-top: 7px;
    overflow: hidden;
    border-radius: 999px;
    background: var(--score-track);
}

.score-meter-fill {
    width: 100%;
    height: 100%;
    border-radius: inherit;
    background: var(--score-accent);
    transform-origin: left center;
    transition: width 0.12s linear;
}

.score-effects {
    position: absolute;
    inset: 0;
    pointer-events: none;
    overflow: visible;
}

.score-drop {
    position: absolute;
    top: 0;
    left: 50%;
    z-index: 5;
    color: var(--score-danger);
    font-size: 0.95rem;
    font-weight: 900;
    opacity: 0;
    text-shadow: 0 1px 0 var(--surface);
    animation: scoreFall 900ms ease-out forwards;
}

.score-drop.big {
    font-size: 1.1rem;
}

.score-area.hit .score-value {
    animation: scoreHit 320ms ease;
}

.score-area.final {
    width: min(86vw, 330px);
    margin-top: 12px;
    padding: 16px 18px 18px;
    border: 2px solid var(--score-accent);
    border-radius: 14px;
    background: var(--control-hover);
    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.14);
    animation: finalCardPop 650ms cubic-bezier(.2,.9,.25,1.15);
}

.score-area.final .score-label {
    color: var(--score-accent);
    font-size: 0.82rem;
    letter-spacing: 0.18em;
}

.score-area.final .score-value {
    margin-top: 5px;
    font-size: clamp(2.7rem, 12vw, 4.2rem);
    line-height: 0.95;
    animation: finalScorePop 800ms cubic-bezier(.2,.9,.25,1.25);
}

.score-area.final .score-meter {
    height: 7px;
    margin-top: 12px;
}

@keyframes scoreFall {
    0% {
        opacity: 0;
        transform: translate(-50%, -14px) scale(0.85);
    }
    18% {
        opacity: 1;
    }
    100% {
        opacity: 0;
        transform: translate(-50%, 34px) scale(1.08);
    }
}

@keyframes scoreHit {
    0% { transform: scale(1); }
    45% { transform: scale(1.12); }
    100% { transform: scale(1); }
}

@keyframes finalCardPop {
    0% {
        opacity: 0;
        transform: translateY(-8px) scale(0.9);
    }
    100% {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

@keyframes finalScorePop {
    0% {
        opacity: 0.2;
        transform: scale(0.72);
    }
    70% {
        opacity: 1;
        transform: scale(1.12);
    }
    100% {
        transform: scale(1);
    }
}

.status {
    width: 100%;
    min-height: 56px;
    margin: 0;
    padding: 4px 10px;
    display: grid;
    place-items: center;
    text-align: center;
    white-space: pre-line;
    font-size: clamp(0.9rem, 3vw, 1rem);
    font-weight: 600;
}

.status.big {
    font-size: clamp(1.1rem, 4.5vw, 1.45rem);
    font-weight: 800;
}

.keyboard {
    width: 100%;
    padding: 0 7px;
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.keyboard-row {
    display: flex;
    justify-content: center;
    gap: 5px;
}

.keyboard-row.middle { padding: 0 3%; }
.keyboard-row.bottom { padding: 0 12%; }

.key {
    flex: 1;
    min-width: 0;
    height: clamp(45px, 10vw, 56px);
    padding: 0;
    border: 0;
    border-radius: 4px;
    background: var(--key);
    color: var(--key-text);
    font-size: clamp(0.78rem, 3vw, 0.95rem);
    font-weight: 700;
    cursor: pointer;
    user-select: none;
}

.key:hover { background: var(--key-hover); }
.key:active { transform: scale(0.95); }
.key.wide { flex: 1.55; font-size: clamp(0.62rem, 2.4vw, 0.76rem); }
.key.correct { background: var(--correct); color: #fff; }
.key.present { background: var(--present); color: #fff; }
.key.absent { background: var(--absent); color: #fff; }

.again,
.play {
    border: 0;
    border-radius: 4px;
    background: var(--button-bg);
    color: var(--button-text);
    font-weight: 700;
    cursor: pointer;
}

.again {
    margin-top: 12px;
    padding: 9px 28px;
}

.play {
    width: 100%;
    padding: 11px;
}

.again:hover,
.play:hover {
    background: var(--button-hover);
}

.name-screen {
    position: fixed;
    inset: 0;
    z-index: 9000;
    display: grid;
    place-items: center;
    padding: 20px;
    background: var(--bg);
}

.name-box {
    width: min(90vw, 360px);
    padding: 30px 26px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text);
    text-align: center;
}

.name-title {
    margin: 0 0 7px;
    font-family: "Arial Black", Arial, sans-serif;
    font-size: 1.6rem;
    font-weight: 900;
}

.name-description {
    margin: 0 0 18px;
    color: var(--muted);
    font-size: 0.85rem;
}

.name-input {
    width: 100%;
    padding: 11px;
    border: 2px solid var(--border);
    border-radius: 0;
    outline: 0;
    background: var(--surface);
    color: var(--text);
    font-size: 1rem;
    font-weight: 600;
    text-align: center;
}

.name-input:focus { border-color: var(--filled-border); }
.name-input::placeholder { color: var(--muted); }

.name-error {
    min-height: 21px;
    margin: 6px 0;
    color: var(--error);
    font-size: 0.78rem;
    font-weight: 600;
}


.how-to-play {
    width: 100%;
    margin-top: 10px;
    padding: 10px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--surface);
    color: var(--text);
    font-weight: 800;
    cursor: pointer;
}

.how-to-play:hover {
    background: var(--control-hover);
}

.rules-overlay {
    position: fixed;
    inset: 0;
    z-index: 25000;
    display: grid;
    place-items: center;
    padding: 18px;
    background: var(--overlay);
}

.rules-panel {
    width: min(94vw, 540px);
    max-height: min(86dvh, 760px);
    overflow: auto;
    padding: 24px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--surface);
    color: var(--text);
}

.rules-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
}

.rules-title {
    margin: 0;
    font-family: "Trebuchet MS", Arial, sans-serif;
    font-size: 1.65rem;
    font-weight: 900;
}

.rules-panel h3 {
    margin: 20px 0 8px;
    font-size: 1rem;
}

.rules-panel p,
.rules-panel li {
    line-height: 1.5;
}

.rules-panel ul {
    margin: 8px 0 0;
    padding-left: 20px;
}

.rule-colors {
    display: grid;
    gap: 8px;
    margin-top: 12px;
}

.rule-color-row {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.9rem;
}

.rule-tile {
    width: 34px;
    height: 34px;
    display: grid;
    place-items: center;
    flex: 0 0 34px;
    color: #fff;
    font-weight: 900;
}

.rule-tile.correct { background: var(--correct); }
.rule-tile.present { background: var(--present); }
.rule-tile.absent { background: var(--absent); }

.score-rules {
    margin-top: 10px;
    padding: 14px 15px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--control-hover);
}

.base-score-line {
    margin-top: 10px;
    color: var(--muted);
    font-size: 0.82rem;
    font-weight: 700;
    line-height: 1.5;
}

.stats-overlay {
    position: fixed;
    inset: 0;
    z-index: 20000;
    display: grid;
    place-items: center;
    padding: 20px;
    background: var(--overlay);
}

.stats-panel {
    width: min(96vw, 800px);
    max-height: 78dvh;
    overflow: auto;
    padding: 22px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text);
}

.stats-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;
}

.stats-title {
    margin: 0;
    font-size: 1.35rem;
    font-weight: 900;
}

.close-button {
    width: 36px;
    height: 36px;
    border: 1px solid var(--border);
    border-radius: 50%;
    background: var(--surface);
    color: var(--text);
    cursor: pointer;
    font-size: 1.15rem;
}

.stats-table {
    width: 100%;
    min-width: 720px;
    border-collapse: collapse;
    font-size: 0.9rem;
}

.stats-score {
    font-weight: 900;
    font-size: 1rem;
}

.stats-table th,
.stats-table td {
    padding: 10px 8px;
    border-bottom: 1px solid var(--border);
    text-align: center;
}

.stats-table th {
    color: var(--muted);
    font-size: 0.76rem;
    text-transform: uppercase;
}

.empty-history {
    margin: 24px 0 8px;
    color: var(--muted);
    text-align: center;
}

@media (max-width: 640px) {
    /* Reserve a real top toolbar area on phones so fixed buttons never cover the title. */
    .top-left,
    .top-right {
        top: calc(env(safe-area-inset-top, 0px) + 10px);
    }

    .top-left {
        left: 10px;
    }

    .top-right {
        right: 10px;
    }

    .icon-button,
    .stats-button,
    .restart-button {
        height: 40px;
    }

    .icon-button {
        width: 40px;
    }

    .stats-button,
    .restart-button {
        padding: 0 11px;
        font-size: 0.88rem;
    }

    .header {
        padding:
            calc(env(safe-area-inset-top, 0px) + 66px)
            12px
            10px;
    }

    .title {
        font-size: clamp(1.55rem, 8vw, 2rem);
        letter-spacing: 0.04em;
        white-space: nowrap;
    }

    .subtitle {
        font-size: clamp(0.75rem, 3.5vw, 0.9rem);
    }

    .stats-label { display: none; }
    .stats-panel { padding: 16px 10px; }
    .stats-table { font-size: 0.75rem; }
    .stats-table th, .stats-table td { padding: 8px 3px; }

    .rules-overlay {
        padding: 12px;
    }

    .rules-panel {
        width: 100%;
        max-height: 88dvh;
        padding: 20px 18px;
    }

    .rules-title {
        font-size: 1.45rem;
    }
}

@media (max-width: 390px) {
    .top-left,
    .top-right {
        gap: 6px;
    }

    .stats-button,
    .restart-button {
        padding: 0 9px;
        font-size: 0.82rem;
    }

    .header {
        padding-top: calc(env(safe-area-inset-top, 0px) + 64px);
    }

    .title {
        font-size: clamp(1.45rem, 7.6vw, 1.85rem);
    }
}

@media (max-height: 740px) {
    .header { padding-top: 7px; padding-bottom: 7px; }
    .board-area { padding: 6px 0 4px; }
    .board { width: min(53vh, 275px); }
    .status { min-height: 42px; }
    .key { height: 40px; }
    .again { margin-top: 7px; }
}

/* ==================================================
   MOBILE KEYBOARD - BIGGER KEYS
   ================================================== */

@media (max-width: 640px) {
    .keyboard {
        padding: 0 8px;
        gap: 8px;
    }

    .keyboard-row {
        gap: 6px;
    }

    .key {
        height: clamp(54px, 13vw, 62px);
        font-size: clamp(0.95rem, 4vw, 1.1rem);
        border-radius: 6px;
    }

    .key.wide {
        font-size: clamp(0.72rem, 3.2vw, 0.9rem);
    }

    .score-area {
        width: min(66vw, 210px);
        margin-top: 5px;
        padding-top: 5px;
        padding-bottom: 6px;
    }
}

</style>
</head>

<body>

<div class="top-left">
    <button
        id="themeToggle"
        class="icon-button"
        type="button"
        title="Switch to dark mode"
        aria-label="Switch to dark mode"
    >
        ☾
    </button>

    <button
        id="backButton"
        class="icon-button hidden"
        type="button"
        title="Back to name"
        aria-label="Back to name"
    >
        ←
    </button>
</div>

<div class="top-right">
    <button
        id="statsButton"
        class="stats-button"
        type="button"
        title="Game statistics"
    >
        ▦ <span class="stats-label">Stats</span>
    </button>

    <button
        id="restartButton"
        class="restart-button hidden"
        type="button"
        title="Restart current game"
        aria-label="Restart current game"
    >
        ↻ Restart
    </button>
</div>

<div id="nameScreen" class="name-screen">
    <div class="name-box">
        <h2 class="name-title">Type your name</h2>

        <p class="name-description">
            Your name may appear during the game.
        </p>

        <input
            id="nameInput"
            class="name-input"
            type="text"
            maxlength="16"
            placeholder="Your name"
            autocomplete="name"
        >

        <p id="nameError" class="name-error"></p>

        <button
            id="playButton"
            class="play"
            type="button"
        >
            PLAY
        </button>

        <button
            id="howToPlayButton"
            class="how-to-play"
            type="button"
        >
            How to Play
        </button>
    </div>
</div>

<div id="rulesOverlay" class="rules-overlay hidden">
    <section
        class="rules-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="rulesTitle"
    >
        <div class="rules-header">
            <h2 id="rulesTitle" class="rules-title">How to Play</h2>

            <button
                id="closeRulesButton"
                class="close-button"
                type="button"
                aria-label="Close game rules"
            >
                ×
            </button>
        </div>

        <p>
            Guess the hidden five-letter word in six tries.
            Type a word and press ENTER to submit it.
        </p>

        <div class="rule-colors">
            <div class="rule-color-row">
                <span class="rule-tile correct">A</span>
                <span>Green: the letter is correct and in the correct spot.</span>
            </div>

            <div class="rule-color-row">
                <span class="rule-tile present">B</span>
                <span>Yellow: the letter is in the word, but in a different spot.</span>
            </div>

            <div class="rule-color-row">
                <span class="rule-tile absent">C</span>
                <span>Gray: the letter is not in the word.</span>
            </div>
        </div>

        <h3>Scoring</h3>

        <div class="score-rules">
            <ul>
                <li>Every game starts at <strong>100 points</strong>.</li>
                <li>Each wrong submitted try costs <strong>5 points</strong>.</li>
                <li>Time costs <strong>1 point every 3 seconds</strong> (about 0.33 point per second on average).</li>
                <li>The score bar drains continuously, while the displayed score drops in 1-point steps every 3 seconds.</li>
                <li>Time can deduct up to <strong>30 points</strong> total. If all six tries are used without solving the word, the final score is <strong>0</strong>.</li>
            </ul>

            <div class="base-score-line">
                Before time penalties: 1st try 100 · 2nd 95 · 3rd 90 · 4th 85 · 5th 80 · 6th 75
            </div>
        </div>
    </section>
</div>

<main class="game">
    <header class="header">
        <h1 class="title">Channy's WORDLE</h1>
        <p class="subtitle">Guess the five-letter word in six tries.</p>
    </header>

    <div id="scoreArea" class="score-area hidden" aria-live="polite">
        <div id="scoreLabel" class="score-label">SCORE</div>
        <div id="scoreValue" class="score-value">100</div>

        <div class="score-meter" aria-hidden="true">
            <div id="scoreMeterFill" class="score-meter-fill"></div>
        </div>

        <div id="scoreEffects" class="score-effects" aria-hidden="true"></div>
    </div>

    <div class="board-area">
        <div id="board" class="board"></div>
    </div>

    <p id="status" class="status" aria-live="polite">
        Take your first guess.
    </p>

    <div id="keyboard" class="keyboard"></div>

    <button
        id="againButton"
        class="again hidden"
        type="button"
    >
        again?
    </button>
</main>

<div id="statsOverlay" class="stats-overlay hidden">
    <section class="stats-panel">
        <div class="stats-header">
            <h2 class="stats-title">Game History</h2>

            <button
                id="closeStatsButton"
                class="close-button"
                type="button"
                aria-label="Close statistics"
            >
                ×
            </button>
        </div>

        <div id="statsContent"></div>
    </section>
</div>

<script>
const WORD_LENGTH = 5;
const MAX_ATTEMPTS = 6;

const board = document.getElementById("board");
const keyboard = document.getElementById("keyboard");
const statusLabel = document.getElementById("status");
const nameScreen = document.getElementById("nameScreen");
const nameInput = document.getElementById("nameInput");
const nameError = document.getElementById("nameError");
const themeToggle = document.getElementById("themeToggle");
const backButton = document.getElementById("backButton");
const statsButton = document.getElementById("statsButton");
const restartButton = document.getElementById("restartButton");
const playButton = document.getElementById("playButton");
const againButton = document.getElementById("againButton");
const statsOverlay = document.getElementById("statsOverlay");
const statsContent = document.getElementById("statsContent");
const closeStatsButton = document.getElementById("closeStatsButton");
const howToPlayButton = document.getElementById("howToPlayButton");
const rulesOverlay = document.getElementById("rulesOverlay");
const closeRulesButton = document.getElementById("closeRulesButton");

const scoreArea = document.getElementById("scoreArea");
const scoreLabel = document.getElementById("scoreLabel");
const scoreValue = document.getElementById("scoreValue");
const scoreMeterFill = document.getElementById("scoreMeterFill");
const scoreEffects = document.getElementById("scoreEffects");

const keyboardRows = [
    [..."QWERTYUIOP", "⌫"],
    [..."ASDFGHJKL", "ENTER"],
    [..."ZXCVBNM"]
];

const statePriority = {
    unused: 0,
    absent: 1,
    present: 2,
    correct: 3
};

/*
Scoring:
- Start at 100
- Each failed submitted try: -5
- Every 3 seconds: -1 (about 0.33 point/second on average)
- The meter drains continuously between score ticks
- Time penalty is capped at -30
- Failed game: final score 0
*/
const START_SCORE = 100;
const TRY_PENALTY = 5;
const TIME_STEP_MS = 3000;
const TIME_STEP_PENALTY = 1;
const MAX_TIME_PENALTY = 30;
const MAX_TIME_STEPS = Math.floor(MAX_TIME_PENALTY / TIME_STEP_PENALTY);

let currentRow = 0;
let currentGuess = [];
let submittedAttempts = 0;
let gameOver = false;
let submitting = false;
let gameLogged = false;
let gameStartedAt = null;

let currentScore = START_SCORE;
let appliedTimeSteps = 0;
let scoreTimer = null;
let finalScore = null;

let playerName = "";
let gameHistory = [];


function normalizePlayerName(name) {
    return name.trim().toLowerCase();
}


function getHistoryKey(name) {
    return "channyWordleHistory_" + normalizePlayerName(name);
}


function loadHistoryForPlayer(name) {
    if (!name) {
        return [];
    }

    try {
        const saved = sessionStorage.getItem(getHistoryKey(name));
        return saved ? JSON.parse(saved) : [];
    } catch {
        return [];
    }
}


function saveHistory() {
    if (!playerName) {
        return;
    }

    sessionStorage.setItem(
        getHistoryKey(playerName),
        JSON.stringify(gameHistory)
    );
}


function setTheme(theme) {
    const dark = theme === "dark";

    document.documentElement.setAttribute(
        "data-theme",
        dark ? "dark" : "light"
    );

    themeToggle.textContent = dark ? "☀" : "☾";

    const label = dark
        ? "Switch to light mode"
        : "Switch to dark mode";

    themeToggle.title = label;
    themeToggle.setAttribute("aria-label", label);

    localStorage.setItem(
        "channyWordleTheme",
        dark ? "dark" : "light"
    );
}


function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme");
    setTheme(current === "dark" ? "light" : "dark");
}


function buildBoard() {
    board.innerHTML = "";

    for (let i = 0; i < WORD_LENGTH * MAX_ATTEMPTS; i++) {
        const tile = document.createElement("div");
        tile.className = "tile";
        board.appendChild(tile);
    }
}


function buildKeyboard() {
    keyboard.innerHTML = "";

    keyboardRows.forEach((keys, rowIndex) => {
        const row = document.createElement("div");
        row.className = "keyboard-row";

        if (rowIndex === 1) {
            row.classList.add("middle");
        }

        if (rowIndex === 2) {
            row.classList.add("bottom");
        }

        keys.forEach(key => {
            const button = document.createElement("button");

            button.type = "button";
            button.className = "key";
            button.textContent = key;
            button.dataset.key = key;
            button.dataset.state = "unused";

            if (key === "ENTER" || key === "⌫") {
                button.classList.add("wide");
            }

            button.addEventListener(
                "click",
                () => handleKey(key)
            );

            row.appendChild(button);
        });

        keyboard.appendChild(row);
    });
}


function tileAt(row, column) {
    return board.children[
        row * WORD_LENGTH + column
    ];
}


function setStatus(message, emphasized = false) {
    statusLabel.textContent = message;

    statusLabel.classList.toggle(
        "big",
        emphasized
    );
}


function clampScore(value) {
    return Math.max(
        0,
        Math.min(START_SCORE, value)
    );
}


function getContinuousVisualScore() {
    if (
        gameStartedAt === null
        ||
        gameOver
    ) {
        return clampScore(currentScore);
    }

    const elapsed =
        Math.max(0, Date.now() - gameStartedAt);

    const rawTimeSteps =
        Math.floor(elapsed / TIME_STEP_MS);

    const cappedTimeSteps =
        Math.min(rawTimeSteps, MAX_TIME_STEPS);

    const unappliedSteps =
        Math.max(
            0,
            cappedTimeSteps - appliedTimeSteps
        );

    const fractionOfCurrentStep =
        rawTimeSteps < MAX_TIME_STEPS
            ? (elapsed % TIME_STEP_MS) / TIME_STEP_MS
            : 0;

    const pendingTimePenalty =
        (unappliedSteps * TIME_STEP_PENALTY)
        +
        (fractionOfCurrentStep * TIME_STEP_PENALTY);

    return clampScore(
        currentScore - pendingTimePenalty
    );
}


function updateContinuousMeter() {
    const visualScore =
        getContinuousVisualScore();

    scoreMeterFill.style.width =
        `${visualScore}%`;
}


function renderScore() {
    currentScore =
        Math.round(
            clampScore(currentScore)
        );

    scoreValue.textContent =
        String(currentScore);

    updateContinuousMeter();
}


function animateScoreDrop(amount, big = false) {
    const drop = document.createElement("div");

    drop.className =
        big
            ? "score-drop big"
            : "score-drop";

    drop.textContent =
        `−${Math.round(Number(amount))}`;

    scoreEffects.appendChild(drop);

    scoreArea.classList.remove("hit");

    void scoreArea.offsetWidth;

    scoreArea.classList.add("hit");

    window.setTimeout(
        () => {
            drop.remove();
            scoreArea.classList.remove("hit");
        },
        950
    );
}


function applyScorePenalty(
    amount,
    big = false
) {
    if (
        gameOver
        ||
        currentScore <= 0
    ) {
        return;
    }

    const before = currentScore;

    currentScore =
        Math.max(
            0,
            currentScore - amount
        );

    const actualPenalty =
        before - currentScore;

    renderScore();

    if (actualPenalty > 0) {
        animateScoreDrop(
            actualPenalty,
            big
        );
    }
}


function updateScoreFromClock() {
    if (
        gameOver
        ||
        gameStartedAt === null
    ) {
        return;
    }

    const elapsed =
        Date.now() - gameStartedAt;

    const targetSteps =
        Math.min(
            Math.floor(
                elapsed / TIME_STEP_MS
            ),
            MAX_TIME_STEPS
        );

    while (
        appliedTimeSteps < targetSteps
        &&
        currentScore > 0
    ) {
        appliedTimeSteps += 1;

        applyScorePenalty(
            TIME_STEP_PENALTY
        );
    }

    updateContinuousMeter();
}


function startScoreTimer() {
    stopScoreTimer();

    scoreTimer =
        window.setInterval(
            () => {
                updateScoreFromClock();
                updateContinuousMeter();
            },
            100
        );
}


function stopScoreTimer() {
    if (
        scoreTimer !== null
    ) {
        window.clearInterval(
            scoreTimer
        );

        scoreTimer = null;
    }
}


function finishScore(won) {
    updateScoreFromClock();

    stopScoreTimer();

    if (!won) {
        currentScore = 0;
    }

    currentScore =
        Math.round(
            clampScore(currentScore)
        );

    finalScore = currentScore;

    scoreValue.textContent =
        String(finalScore);

    scoreMeterFill.style.width =
        `${finalScore}%`;

    scoreLabel.textContent =
        "FINAL SCORE";

    scoreArea.classList.add(
        "final"
    );

    return finalScore;
}


function resetUI() {
    currentRow = 0;
    currentGuess = [];
    submittedAttempts = 0;
    gameOver = false;
    submitting = false;
    gameLogged = false;
    gameStartedAt = Date.now();

    currentScore = START_SCORE;
    appliedTimeSteps = 0;
    finalScore = null;

    scoreLabel.textContent = "SCORE";
    scoreArea.classList.remove("final");
    scoreArea.classList.remove("hidden");
    scoreEffects.innerHTML = "";

    renderScore();

    buildBoard();
    buildKeyboard();

    setStatus("Take your first guess.");

    startScoreTimer();

    backButton.classList.remove("hidden");
    restartButton.classList.remove("hidden");
    againButton.classList.add("hidden");
}


function addLetter(letter) {
    if (
        gameOver
        ||
        currentGuess.length >= WORD_LENGTH
    ) {
        return;
    }

    currentGuess.push(letter);

    const tile = tileAt(
        currentRow,
        currentGuess.length - 1
    );

    tile.textContent = letter;
    tile.classList.add("filled");

    if (
        currentRow === 0
        &&
        statusLabel.textContent === "Take your first guess."
    ) {
        setStatus("");
    }
}


function removeLetter() {
    if (
        gameOver
        ||
        currentGuess.length === 0
    ) {
        return;
    }

    const tile = tileAt(
        currentRow,
        currentGuess.length - 1
    );

    currentGuess.pop();

    tile.textContent = "";
    tile.classList.remove("filled");
}


function applyResult(result) {
    result.forEach((state, column) => {
        const tile = tileAt(
            currentRow,
            column
        );

        tile.classList.remove("filled");
        tile.classList.add(state);
    });
}


function updateKeyboard(letters, result) {
    letters.forEach((letter, index) => {
        const button = keyboard.querySelector(
            `[data-key="${letter}"]`
        );

        if (!button) {
            return;
        }

        const oldState = button.dataset.state;
        const newState = result[index];

        if (
            statePriority[newState]
            <=
            statePriority[oldState]
        ) {
            return;
        }

        button.classList.remove(
            "absent",
            "present",
            "correct"
        );

        button.classList.add(newState);
        button.dataset.state = newState;
    });
}


async function postJSON(url, payload = null) {
    const options = {
        method: "POST"
    };

    if (payload !== null) {
        options.headers = {
            "Content-Type": "application/json"
        };

        options.body = JSON.stringify(payload);
    }

    const response = await fetch(
        url,
        options
    );

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            data.error
            ||
            "Something went wrong."
        );
    }

    return data;
}


function formatDuration(milliseconds) {
    const totalSeconds = Math.max(
        0,
        Math.round(milliseconds / 1000)
    );

    const minutes = Math.floor(
        totalSeconds / 60
    );

    const seconds = totalSeconds % 60;

    if (minutes === 0) {
        return `${seconds}s`;
    }

    return `${minutes}m ${seconds}s`;
}


function addGameLog(won, attempts, score = null) {
    if (
        gameLogged
        ||
        gameStartedAt === null
        ||
        !playerName
    ) {
        return;
    }

    const started = new Date(gameStartedAt);

    gameHistory.push({
        userName: playerName,

        started: started.toLocaleTimeString(
            [],
            {
                hour: "2-digit",
                minute: "2-digit"
            }
        ),

        duration: formatDuration(
            Date.now() - gameStartedAt
        ),

        won: won,

        attempts: attempts,

        score: score
    });

    gameLogged = true;

    saveHistory();
}


function logUnfinishedGameIfNeeded() {
    if (
        !gameLogged
        &&
        gameStartedAt !== null
        &&
        submittedAttempts > 0
    ) {
        addGameLog(
            false,
            submittedAttempts,
            0
        );
    }
}


function escapeHTML(value) {
    const element = document.createElement("div");
    element.textContent = String(value);
    return element.innerHTML;
}


function renderStats() {
    if (!playerName) {
        statsContent.innerHTML =
            '<p class="empty-history">Enter your name first.</p>';
        return;
    }

    if (gameHistory.length === 0) {
        statsContent.innerHTML =
            `<p class="empty-history">
                No games yet for ${escapeHTML(playerName)}.
            </p>`;
        return;
    }

    const rows = gameHistory.map(
        (game, index) => {

            const result = game.won
                ? "✅ Correct"
                : "❌ Not solved";

            return `
                <tr>
                    <td>${escapeHTML(game.userName)}</td>
                    <td>${index + 1}</td>
                    <td>${escapeHTML(game.started)}</td>
                    <td>${escapeHTML(game.duration)}</td>
                    <td>${result}</td>
                    <td>${game.attempts}</td>
                    <td class="stats-score">${game.score ?? "—"}</td>
                </tr>
            `;
        }
    ).join("");

    statsContent.innerHTML = `
        <table class="stats-table">
            <thead>
                <tr>
                    <th>User Name</th>
                    <th>Game</th>
                    <th>Start Time</th>
                    <th>Play Time</th>
                    <th>Result</th>
                    <th>Attempts</th>
                    <th>Score</th>
                </tr>
            </thead>

            <tbody>
                ${rows}
            </tbody>
        </table>
    `;
}


function openStats() {
    renderStats();
    statsOverlay.classList.remove("hidden");
}


function closeStats() {
    statsOverlay.classList.add("hidden");
}


function openRules() {
    rulesOverlay.classList.remove("hidden");
}


function closeRules() {
    rulesOverlay.classList.add("hidden");
}


async function submitGuess() {
    if (
        gameOver
        ||
        submitting
    ) {
        return;
    }

    if (
        currentGuess.length
        !== WORD_LENGTH
    ) {
        setStatus(
            "Five letters, please.",
            true
        );

        return;
    }

    submitting = true;

    try {
        const data = await postJSON(
            "/guess",
            {
                guess: currentGuess.join("")
            }
        );

        submittedAttempts = data.attempt;

        applyResult(data.result);

        updateKeyboard(
            currentGuess,
            data.result
        );

        setStatus(
            data.message,
            true
        );

        const ended =
            data.game_over;

        if (ended) {
            const finishedScore =
                finishScore(
                    data.won
                );

            gameOver = true;

            setStatus(
                `${data.message}\nFinal Score: ${finishedScore}`,
                true
            );

            restartButton.classList.add("hidden");
            againButton.classList.remove("hidden");

            addGameLog(
                data.won,
                data.attempt,
                finishedScore
            );

            return;
        }

        /*
        A wrong submitted guess costs 5 points.
        At the current time rate, -5 points is equivalent
        to 15 seconds of time penalty.
        */
        applyScorePenalty(
            TRY_PENALTY,
            true
        );

        currentRow += 1;
        currentGuess = [];

    } catch (error) {
        setStatus(
            error.message,
            true
        );

    } finally {
        submitting = false;
    }
}


async function submitName() {
    const name = nameInput.value.trim();

    if (!name) {
        nameError.textContent =
            "Please enter your name.";

        nameInput.focus();

        return;
    }

    try {
        await postJSON(
            "/start",
            {
                name: name
            }
        );

        playerName = name;

        gameHistory =
            loadHistoryForPlayer(
                playerName
            );

        nameError.textContent = "";

        nameScreen.classList.add(
            "hidden"
        );

        resetUI();

    } catch (error) {
        nameError.textContent =
            error.message;
    }
}


async function restartGame() {
    stopScoreTimer();

    try {
        logUnfinishedGameIfNeeded();

        await postJSON(
            "/restart"
        );

        resetUI();

    } catch (error) {
        setStatus(
            error.message,
            true
        );

        if (!gameOver) {
            startScoreTimer();
        }
    }
}


async function backToName() {
    stopScoreTimer();

    logUnfinishedGameIfNeeded();

    try {
        await postJSON(
            "/leave"
        );
    } catch {
        // Return to name screen anyway.
    }

    nameInput.value = playerName;

    nameScreen.classList.remove(
        "hidden"
    );

    backButton.classList.add(
        "hidden"
    );

    restartButton.classList.add("hidden");
    againButton.classList.add("hidden");
    scoreArea.classList.add("hidden");

    nameInput.focus();
}


function handleKey(key) {
    if (
        !nameScreen.classList.contains(
            "hidden"
        )
    ) {
        return;
    }

    if (key === "ENTER") {
        submitGuess();
        return;
    }

    if (key === "⌫") {
        removeLetter();
        return;
    }

    if (/^[A-Z]$/.test(key)) {
        addLetter(key);
    }
}


themeToggle.addEventListener(
    "click",
    toggleTheme
);


backButton.addEventListener(
    "click",
    backToName
);


statsButton.addEventListener(
    "click",
    openStats
);


closeStatsButton.addEventListener(
    "click",
    closeStats
);


howToPlayButton.addEventListener(
    "click",
    openRules
);


closeRulesButton.addEventListener(
    "click",
    closeRules
);


rulesOverlay.addEventListener(
    "click",
    event => {
        if (event.target === rulesOverlay) {
            closeRules();
        }
    }
);


playButton.addEventListener(
    "click",
    submitName
);


restartButton.addEventListener(
    "click",
    restartGame
);


againButton.addEventListener(
    "click",
    restartGame
);


statsOverlay.addEventListener(
    "click",
    event => {
        if (
            event.target
            ===
            statsOverlay
        ) {
            closeStats();
        }
    }
);


document.addEventListener(
    "keydown",
    event => {

        if (
            event.key === "Escape"
            &&
            !rulesOverlay.classList.contains(
                "hidden"
            )
        ) {
            closeRules();
            return;
        }

        if (
            event.key === "Escape"
            &&
            !statsOverlay.classList.contains(
                "hidden"
            )
        ) {
            closeStats();
            return;
        }

        if (
            !statsOverlay.classList.contains(
                "hidden"
            )
        ) {
            return;
        }

        if (
            !nameScreen.classList.contains(
                "hidden"
            )
        ) {
            if (
                event.key === "Enter"
            ) {
                submitName();
            }

            return;
        }

        if (
            event.key === "Enter"
        ) {
            event.preventDefault();

            handleKey(
                "ENTER"
            );

            return;
        }

        if (
            event.key === "Backspace"
        ) {
            event.preventDefault();

            handleKey(
                "⌫"
            );

            return;
        }

        const key =
            event.key.toUpperCase();

        if (
            /^[A-Z]$/.test(
                key
            )
        ) {
            handleKey(key);
        }
    }
);


const savedTheme =
    localStorage.getItem(
        "channyWordleTheme"
    )
    ||
    "light";


setTheme(savedTheme);

buildBoard();

buildKeyboard();

nameInput.focus();

</script>

</body>
</html>
"""


@app.get("/")
def home():
    return render_template_string(HTML)


@app.post("/start")
def start():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()

    if not name:
        return jsonify(
            error="Please enter your name."
        ), 400

    if len(name) > 16:
        return jsonify(
            error="Please use 16 characters or fewer."
        ), 400

    session.clear()
    session["name"] = name

    reset_game()

    return jsonify(
        success=True
    )


@app.post("/guess")
def guess():
    if (
        "name" not in session
        or
        "answer" not in session
    ):
        return jsonify(
            error="Please start the game first."
        ), 400

    if session.get("finished"):
        return jsonify(
            error="The game is already over."
        ), 400

    data = request.get_json(silent=True) or {}

    entered = str(
        data.get("guess", "")
    ).strip().lower()

    if (
        len(entered) != WORD_LENGTH
        or not entered.isascii()
        or not entered.isalpha()
    ):
        return jsonify(
            error="Five English letters, please."
        ), 400

    answer = session["answer"]

    result = evaluate_guess(
        answer,
        entered
    )

    attempt = session["attempt"] + 1
    session["attempt"] = attempt

    if entered == answer:
        session["finished"] = True

        return jsonify(
            result=result,
            message=WIN_MESSAGE,
            game_over=True,
            won=True,
            attempt=attempt
        )

    message = WRONG_MESSAGES[
        attempt - 1
    ].format(
        name=session["name"]
    )

    if attempt >= MAX_ATTEMPTS:
        session["finished"] = True

        message += (
            "\nThe word was "
            f"{answer.upper()}."
        )

    return jsonify(
        result=result,
        message=message,
        game_over=session["finished"],
        won=False,
        attempt=attempt
    )


@app.post("/restart")
def restart():
    if "name" not in session:
        return jsonify(
            error="Please enter your name first."
        ), 400

    reset_game()

    return jsonify(
        success=True
    )


@app.post("/leave")
def leave():
    session.clear()

    return jsonify(
        success=True
    )


def open_browser():
    webbrowser.open(
        "http://127.0.0.1:5000"
    )


if __name__ == "__main__":
    threading.Timer(
        1.0,
        open_browser
    ).start()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )
