import os
import random
import secrets
import threading
import webbrowser

from flask import Flask, jsonify, render_template_string, request, session
from wordfreq import iter_wordlist


# =========================================================
# SETTINGS
# =========================================================

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


# =========================================================
# WORDS
# =========================================================

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

    return words


ANSWER_WORDS = load_common_words()


# =========================================================
# WORDLE LOGIC
# =========================================================

def evaluate_guess(answer, guess):
    result = ["absent"] * WORD_LENGTH
    remaining = {}

    # Correct letter + correct position
    for i in range(WORD_LENGTH):
        if guess[i] == answer[i]:
            result[i] = "correct"
        else:
            letter = answer[i]
            remaining[letter] = remaining.get(letter, 0) + 1

    # Correct letter + wrong position
    for i in range(WORD_LENGTH):
        if result[i] == "correct":
            continue

        letter = guess[i]

        if remaining.get(letter, 0) > 0:
            result[i] = "present"
            remaining[letter] -= 1

    return result


# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "channy-wordle-secret-key"
)

games = {}


def create_game(name):
    game_id = secrets.token_hex(16)

    games[game_id] = {
        "name": name,
        "answer": random.choice(ANSWER_WORDS),
        "attempt": 0,
        "finished": False,
    }

    session["game_id"] = game_id


def get_game():
    game_id = session.get("game_id")

    if not game_id:
        return None

    return games.get(game_id)


# =========================================================
# WEB PAGE
# =========================================================

HTML = r"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Channy's Wordle</title>

<style>

:root {
    --background: #ffffff;
    --text: #000000;
    --subtext: #787c7e;

    --border: #d3d6da;
    --filled-border: #878a8c;

    --correct: #6aaa64;
    --present: #c9b458;
    --absent: #787c7e;

    --key: #d3d6da;
    --key-hover: #b8babc;

    --button: #000000;
    --button-hover: #333333;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    min-height: 100dvh;

    background: var(--background);
    color: var(--text);

    font-family:
        "Helvetica Neue",
        Arial,
        sans-serif;
}

button,
input {
    font: inherit;
}


/* =========================
   MAIN
   ========================= */

.game {
    width: min(96vw, 520px);
    min-height: 100dvh;

    margin: 0 auto;
    padding-bottom: 14px;

    display: flex;
    flex-direction: column;
    align-items: center;
}


/* =========================
   HEADER
   ========================= */

.header {
    width: 100%;

    padding: 12px 10px 10px;

    border-bottom:
        1px solid
        var(--border);

    text-align: center;
}

.title {
    margin: 0;

    font-family:
        "Arial Black",
        "Helvetica Neue",
        Arial,
        sans-serif;

    font-size:
        clamp(
            1.65rem,
            6vw,
            2.1rem
        );

    font-weight: 900;

    letter-spacing: 0.08em;
}

.subtitle {
    margin: 5px 0 0;

    color: var(--subtext);

    font-size:
        clamp(
            0.76rem,
            2.8vw,
            0.9rem
        );
}


/* =========================
   BOARD
   ========================= */

.board-area {
    flex: 1;

    width: 100%;

    display: flex;
    align-items: center;
    justify-content: center;

    padding: 12px 0 7px;
}

.board {
    width: min(68vw, 300px);

    display: grid;

    grid-template-columns:
        repeat(5, 1fr);

    gap: 5px;
}

.tile {
    aspect-ratio: 1;

    display: grid;
    place-items: center;

    border:
        2px solid
        var(--border);

    background: white;
    color: black;

    font-family:
        "Arial Black",
        Arial,
        sans-serif;

    font-size:
        clamp(
            1.35rem,
            6vw,
            2rem
        );

    font-weight: 900;

    user-select: none;
}

.tile.filled {
    border-color:
        var(--filled-border);
}

.tile.correct {
    background:
        var(--correct);

    border-color:
        var(--correct);

    color: white;
}

.tile.present {
    background:
        var(--present);

    border-color:
        var(--present);

    color: white;
}

.tile.absent {
    background:
        var(--absent);

    border-color:
        var(--absent);

    color: white;
}


/* =========================
   MESSAGE
   ========================= */

.status {
    width: 100%;
    min-height: 56px;

    margin: 0;
    padding: 4px 10px;

    display: grid;
    place-items: center;

    text-align: center;
    white-space: pre-line;

    font-size:
        clamp(
            0.9rem,
            3vw,
            1rem
        );

    font-weight: 600;
}

.status.big {
    font-size:
        clamp(
            1.1rem,
            4.5vw,
            1.45rem
        );

    font-weight: 800;
}


/* =========================
   KEYBOARD
   ========================= */

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

.keyboard-row.middle {
    padding: 0 5%;
}

.key {
    flex: 1;

    min-width: 0;

    height:
        clamp(
            45px,
            10vw,
            56px
        );

    padding: 0;

    border: 0;
    border-radius: 4px;

    background: var(--key);
    color: black;

    font-size:
        clamp(
            0.78rem,
            3vw,
            0.95rem
        );

    font-weight: 700;

    cursor: pointer;
}

.key:hover {
    background:
        var(--key-hover);
}

.key:active {
    transform:
        scale(0.95);
}

.key.wide {
    flex: 1.55;

    font-size:
        clamp(
            0.62rem,
            2.4vw,
            0.76rem
        );
}

.key.correct {
    background:
        var(--correct);

    color: white;
}

.key.present {
    background:
        var(--present);

    color: white;
}

.key.absent {
    background:
        var(--absent);

    color: white;
}


/* =========================
   AGAIN
   ========================= */

.again {
    margin-top: 12px;

    padding: 9px 28px;

    border: 0;
    border-radius: 4px;

    background: var(--button);
    color: white;

    font-weight: 700;

    cursor: pointer;
}

.again:hover {
    background:
        var(--button-hover);
}


/* =========================
   NAME SCREEN
   ========================= */

.name-screen {
    position: fixed;
    inset: 0;

    z-index: 100;

    display: grid;
    place-items: center;

    padding: 20px;

    background: white;
}

.name-screen.hidden {
    display: none;
}

.name-box {
    width: min(90vw, 360px);

    padding: 30px 26px;

    border:
        1px solid
        var(--border);

    background: white;

    text-align: center;
}

.name-title {
    margin: 0 0 7px;

    font-family:
        "Arial Black",
        Arial,
        sans-serif;

    font-size: 1.6rem;
    font-weight: 900;
}

.name-description {
    margin: 0 0 18px;

    color: var(--subtext);

    font-size: 0.85rem;
}

.name-input {
    width: 100%;

    padding: 11px;

    border:
        2px solid
        var(--border);

    border-radius: 0;

    outline: 0;

    background: white;
    color: black;

    font-size: 1rem;
    font-weight: 600;

    text-align: center;
}

.name-input:focus {
    border-color:
        var(--filled-border);
}

.name-error {
    min-height: 21px;

    margin: 6px 0;

    color: #b00020;

    font-size: 0.78rem;
    font-weight: 600;
}

.play {
    width: 100%;

    padding: 11px;

    border: 0;
    border-radius: 4px;

    background: var(--button);
    color: white;

    font-weight: 700;

    cursor: pointer;
}

.play:hover {
    background:
        var(--button-hover);
}


/* =========================
   SMALL SCREEN
   ========================= */

@media (max-height: 740px) {

    .header {
        padding:
            7px
            10px;
    }

    .board-area {
        padding:
            6px
            0
            4px;
    }

    .board {
        width:
            min(
                53vh,
                275px
            );
    }

    .status {
        min-height: 42px;
    }

    .key {
        height: 40px;
    }

    .again {
        margin-top: 7px;
    }
}

</style>

</head>


<body>


<!-- =========================
     NAME SCREEN
     ========================= -->

<div
    id="nameScreen"
    class="name-screen"
>

    <div class="name-box">

        <h2 class="name-title">
            Type your name
        </h2>

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

        <p
            id="nameError"
            class="name-error"
        ></p>

        <button
            id="playButton"
            class="play"
            type="button"
        >
            PLAY
        </button>

    </div>

</div>


<!-- =========================
     GAME
     ========================= -->

<main class="game">

    <header class="header">

        <h1 class="title">
            CHANNY'S WORDLE
        </h1>

        <p class="subtitle">
            Guess the five-letter word in six tries.
        </p>

    </header>


    <div class="board-area">

        <div
            id="board"
            class="board"
        ></div>

    </div>


    <p
        id="status"
        class="status"
    >
        Take your first guess.
    </p>


    <div
        id="keyboard"
        class="keyboard"
    ></div>


    <button
        id="againButton"
        class="again"
        type="button"
    >
        again?
    </button>

</main>


<script>

const WORD_LENGTH = 5;
const MAX_ATTEMPTS = 6;

let currentRow = 0;
let currentGuess = [];

let gameOver = false;
let submitting = false;


const board =
    document.getElementById("board");

const keyboard =
    document.getElementById("keyboard");

const statusLabel =
    document.getElementById("status");

const nameScreen =
    document.getElementById("nameScreen");

const nameInput =
    document.getElementById("nameInput");

const nameError =
    document.getElementById("nameError");

const playButton =
    document.getElementById("playButton");

const againButton =
    document.getElementById("againButton");


const keyboardRows = [
    [..."QWERTYUIOP"],
    [..."ASDFGHJKL"],
    [
        "ENTER",
        ..."ZXCVBNM",
        "⌫"
    ]
];


const statePriority = {
    unused: 0,
    absent: 1,
    present: 2,
    correct: 3
};


/* =========================
   BUILD BOARD
   ========================= */

function buildBoard() {

    board.innerHTML = "";

    for (
        let i = 0;
        i < WORD_LENGTH * MAX_ATTEMPTS;
        i++
    ) {

        const tile =
            document.createElement("div");

        tile.className = "tile";

        board.appendChild(tile);
    }
}


/* =========================
   BUILD KEYBOARD
   ========================= */

function buildKeyboard() {

    keyboard.innerHTML = "";

    keyboardRows.forEach(
        (keys, rowIndex) => {

            const row =
                document.createElement("div");

            row.className =
                "keyboard-row";

            if (rowIndex === 1) {
                row.classList.add(
                    "middle"
                );
            }

            keys.forEach(key => {

                const button =
                    document.createElement(
                        "button"
                    );

                button.type = "button";

                button.className = "key";

                button.textContent = key;

                button.dataset.key = key;

                button.dataset.state =
                    "unused";

                if (
                    key === "ENTER"
                    ||
                    key === "⌫"
                ) {

                    button.classList.add(
                        "wide"
                    );
                }

                button.addEventListener(
                    "click",
                    () => handleKey(key)
                );

                row.appendChild(button);
            });

            keyboard.appendChild(row);
        }
    );
}


/* =========================
   HELPERS
   ========================= */

function tileAt(row, column) {

    return board.children[
        row * WORD_LENGTH
        + column
    ];
}


function setStatus(
    message,
    emphasized = false
) {

    statusLabel.textContent =
        message;

    statusLabel.classList.toggle(
        "big",
        emphasized
    );
}


function resetUI() {

    currentRow = 0;
    currentGuess = [];

    gameOver = false;
    submitting = false;

    buildBoard();
    buildKeyboard();

    setStatus(
        "Take your first guess.",
        false
    );
}


/* =========================
   LETTERS
   ========================= */

function addLetter(letter) {

    if (
        gameOver
        ||
        currentGuess.length
        >= WORD_LENGTH
    ) {
        return;
    }

    currentGuess.push(letter);

    const tile =
        tileAt(
            currentRow,
            currentGuess.length - 1
        );

    tile.textContent = letter;

    tile.classList.add(
        "filled"
    );

    if (
        currentRow === 0
        &&
        statusLabel.textContent
        === "Take your first guess."
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

    const tile =
        tileAt(
            currentRow,
            currentGuess.length - 1
        );

    currentGuess.pop();

    tile.textContent = "";

    tile.classList.remove(
        "filled"
    );
}


/* =========================
   COLORS
   ========================= */

function applyResult(result) {

    result.forEach(
        (state, column) => {

            const tile =
                tileAt(
                    currentRow,
                    column
                );

            tile.classList.remove(
                "filled"
            );

            tile.classList.add(
                state
            );
        }
    );
}


function updateKeyboard(
    letters,
    result
) {

    letters.forEach(
        (letter, index) => {

            const button =
                keyboard.querySelector(
                    `[data-key="${letter}"]`
                );

            if (!button) {
                return;
            }

            const oldState =
                button.dataset.state;

            const newState =
                result[index];

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

            button.classList.add(
                newState
            );

            button.dataset.state =
                newState;
        }
    );
}


/* =========================
   SUBMIT GUESS
   ========================= */

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

        const response =
            await fetch(
                "/guess",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            guess:
                                currentGuess.join("")
                        })
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            setStatus(
                data.error
                ||
                "Something went wrong.",
                true
            );

            return;
        }

        applyResult(
            data.result
        );

        updateKeyboard(
            currentGuess,
            data.result
        );

        setStatus(
            data.message,
            true
        );

        gameOver =
            data.game_over;

        if (!gameOver) {

            currentRow += 1;

            currentGuess = [];
        }

    } catch (error) {

        setStatus(
            "Server error.",
            true
        );

    } finally {

        submitting = false;
    }
}


/* =========================
   NAME
   ========================= */

async function submitName() {

    const name =
        nameInput.value.trim();

    if (!name) {

        nameError.textContent =
            "Please enter your name.";

        nameInput.focus();

        return;
    }

    try {

        const response =
            await fetch(
                "/start",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            name: name
                        })
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            nameError.textContent =
                data.error
                ||
                "Something went wrong.";

            return;
        }

        nameError.textContent = "";

        nameScreen.classList.add(
            "hidden"
        );

        resetUI();

    } catch (error) {

        nameError.textContent =
            "Server error.";
    }
}


/* =========================
   RESTART
   ========================= */

async function restartGame() {

    try {

        const response =
            await fetch(
                "/restart",
                {
                    method: "POST"
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            setStatus(
                data.error
                ||
                "Something went wrong.",
                true
            );

            return;
        }

        resetUI();

    } catch (error) {

        setStatus(
            "Server error.",
            true
        );
    }
}


/* =========================
   INPUT HANDLER
   ========================= */

function handleKey(key) {

    if (
        !nameScreen
            .classList
            .contains("hidden")
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


/* =========================
   BUTTONS
   ========================= */

playButton.addEventListener(
    "click",
    submitName
);


againButton.addEventListener(
    "click",
    restartGame
);


/* =========================
   PHYSICAL KEYBOARD
   ========================= */

document.addEventListener(
    "keydown",
    event => {

        if (
            !nameScreen
                .classList
                .contains("hidden")
        ) {

            if (event.key === "Enter") {
                submitName();
            }

            return;
        }

        if (event.key === "Enter") {

            handleKey("ENTER");

            return;
        }

        if (event.key === "Backspace") {

            handleKey("⌫");

            return;
        }

        const key =
            event.key.toUpperCase();

        if (/^[A-Z]$/.test(key)) {

            handleKey(key);
        }
    }
);


/* =========================
   START PAGE
   ========================= */

buildBoard();
buildKeyboard();

nameInput.focus();

</script>

</body>
</html>
"""


# =========================================================
# ROUTES
# =========================================================

@app.get("/")
def home():
    return render_template_string(HTML)


@app.post("/start")
def start():

    data = request.get_json(silent=True) or {}

    name = str(
        data.get("name", "")
    ).strip()

    if not name:
        return jsonify(
            error="Please enter your name."
        ), 400

    if len(name) > 16:
        return jsonify(
            error="Please use 16 characters or fewer."
        ), 400

    create_game(name)

    return jsonify(
        success=True
    )


@app.post("/guess")
def guess():

    game = get_game()

    if not game:
        return jsonify(
            error="Please start the game first."
        ), 400

    if game["finished"]:
        return jsonify(
            error="The game is already over."
        ), 400

    data = request.get_json(silent=True) or {}

    entered = str(
        data.get("guess", "")
    ).strip().lower()

    if (
        len(entered) != WORD_LENGTH
        or
        not entered.isascii()
        or
        not entered.isalpha()
    ):

        return jsonify(
            error="Five English letters, please."
        ), 400

    result = evaluate_guess(
        game["answer"],
        entered
    )

    game["attempt"] += 1


    # Correct answer
    if entered == game["answer"]:

        game["finished"] = True

        return jsonify(
            result=result,
            message=WIN_MESSAGE,
            game_over=True
        )


    # Wrong answer
    message = WRONG_MESSAGES[
        game["attempt"] - 1
    ].format(
        name=game["name"]
    )


    # Sixth wrong answer
    if game["attempt"] >= MAX_ATTEMPTS:

        game["finished"] = True

        message += (
            "\nThe word was "
            f"{game['answer'].upper()}."
        )


    return jsonify(
        result=result,
        message=message,
        game_over=game["finished"]
    )


@app.post("/restart")
def restart():

    game = get_game()

    if not game:
        return jsonify(
            error="Please enter your name first."
        ), 400

    game["answer"] = random.choice(
        ANSWER_WORDS
    )

    game["attempt"] = 0
    game["finished"] = False

    return jsonify(
        success=True
    )


# =========================================================
# LOCAL RUN
# =========================================================

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
