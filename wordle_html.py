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
        "Run: py -m pip install flask wordfreq"
    ) from exc


# =========================
# Game settings
# =========================

WORD_LENGTH = 5
MAX_ATTEMPTS = 6
ANSWER_POOL_SIZE = 100

WRONG_MESSAGES = [
    "HMM you sure? 👀",
    "One more guess! 🧐",
    "You can do better {name} 🤨",
    "Is this all you've got, {name}? 😏",
    "No way... 😵",
    "BAHAHAHAHAHAHA 😂",
]

WIN_MESSAGE = "Way to go Shawty 🎉"


# =========================
# Word list
# =========================

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


# =========================
# Wordle logic
# =========================

def evaluate_guess(answer, guess):
    result = ["absent"] * WORD_LENGTH
    remaining = {}

    # Exact matches first
    for i in range(WORD_LENGTH):
        if guess[i] == answer[i]:
            result[i] = "correct"
        else:
            letter = answer[i]
            remaining[letter] = remaining.get(letter, 0) + 1

    # Correct letter, wrong position
    for i in range(WORD_LENGTH):
        if result[i] == "correct":
            continue

        letter = guess[i]

        if remaining.get(letter, 0) > 0:
            result[i] = "present"
            remaining[letter] -= 1

    return result


# =========================
# Flask
# =========================

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

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
    return games.get(session.get("game_id"))


# =========================
# Web page
# =========================

HTML = r"""
<!DOCTYPE html>
<html lang="en">

<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Channy's Wordle World</title>

<style>

:root {
    --bg: #10122B;
    --text: #FFFFFF;
    --subtext: #C7D2FE;
    --alert: #FF5C7A;

    --tile: #202450;
    --tile-border: #8B5CF6;
    --filled-border: #F472B6;

    --correct: #22C55E;
    --present: #F59E0B;
    --absent: #64748B;

    --key: #A5B4FC;
    --key-hover: #C4B5FD;
    --key-text: #1E1B4B;

    --button: #EC4899;
    --button-hover: #F472B6;
}

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    min-height: 100dvh;

    background:
        radial-gradient(
            circle at top,
            #292D69 0%,
            var(--bg) 43%
        );

    color: var(--text);

    font-family:
        "Segoe UI",
        Arial,
        sans-serif;
}

button,
input {
    font: inherit;
}


/* Main game */

.game {
    width: min(94vw, 520px);
    min-height: 100dvh;

    margin: auto;
    padding: 18px 12px 14px;

    display: flex;
    flex-direction: column;
    align-items: center;

    gap: 10px;
}

header {
    text-align: center;
}

h1 {
    margin: 0;

    font-size:
        clamp(
            1.7rem,
            6vw,
            2.3rem
        );

    font-weight: 900;
}

.subtitle {
    margin: 5px 0 0;

    color: var(--subtext);

    font-size:
        clamp(
            0.82rem,
            3vw,
            1rem
        );

    font-weight: 700;
}


/* Board */

.board {
    width: min(72vw, 310px);

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
        3px solid
        var(--tile-border);

    border-radius: 7px;

    background: var(--tile);
    color: var(--text);

    font-size:
        clamp(
            1.25rem,
            6vw,
            2rem
        );

    font-weight: 900;
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
}

.tile.present {
    background:
        var(--present);

    border-color:
        var(--present);
}

.tile.absent {
    background:
        var(--absent);

    border-color:
        var(--absent);
}


/* Status */

.status {
    min-height: 55px;
    margin: 0;

    display: grid;
    place-items: center;

    text-align: center;
    white-space: pre-line;

    font-weight: 800;
}

.status.big {
    color: var(--alert);

    font-size:
        clamp(
            1.15rem,
            4.5vw,
            1.55rem
        );

    font-weight: 900;
}


/* Keyboard */

.keyboard {
    width: 100%;

    display: grid;

    gap: 4px;
}

.keyboard-row {
    display: flex;
    justify-content: center;

    gap: 3px;
}

.keyboard-row.middle {
    padding: 0 5%;
}

.key {
    flex: 1;

    min-width: 0;

    height:
        clamp(
            42px,
            10vw,
            53px
        );

    padding: 0;

    border: 0;
    border-radius: 7px;

    background: var(--key);
    color: var(--key-text);

    font-size:
        clamp(
            0.8rem,
            3vw,
            1rem
        );

    font-weight: 900;

    cursor: pointer;
}

.key:hover {
    background:
        var(--key-hover);
}

.key:active {
    transform:
        scale(0.94);
}

.key.wide {
    flex: 1.6;

    font-size:
        clamp(
            0.65rem,
            2.4vw,
            0.8rem
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


/* Buttons */

.again,
.play {
    border: 0;
    border-radius: 8px;

    background:
        var(--button);

    color: white;

    font-weight: 900;

    cursor: pointer;
}

.again {
    margin-top: 3px;

    padding:
        9px
        31px;
}

.play {
    width: 100%;

    padding:
        11px
        16px;
}

.again:hover,
.play:hover {
    background:
        var(--button-hover);
}


/* Name screen */

.name-screen {
    position: fixed;

    inset: 0;

    z-index: 10;

    display: grid;
    place-items: center;

    padding: 20px;

    background:
        radial-gradient(
            circle at top,
            #343879,
            var(--bg) 65%
        );
}

.name-screen.hidden {
    display: none;
}

.name-box {
    width:
        min(
            92vw,
            380px
        );

    padding: 30px;

    border:
        2px solid
        var(--tile-border);

    border-radius: 20px;

    background:
        var(--tile);

    text-align: center;

    box-shadow:
        0
        25px
        70px
        rgba(
            0,
            0,
            0,
            0.4
        );
}

.name-box h2 {
    margin:
        0
        0
        8px;

    font-size: 1.8rem;
}

.name-description {
    margin:
        0
        0
        18px;

    color:
        var(--subtext);

    font-weight: 700;
}

.name-input {
    width: 100%;

    padding:
        11px
        12px;

    border:
        3px solid
        transparent;

    border-radius: 8px;

    outline: 0;

    background: white;

    color:
        var(--key-text);

    font-size: 1.1rem;

    font-weight: 800;

    text-align: center;
}

.name-input:focus {
    border-color:
        var(--filled-border);
}

.name-error {
    min-height: 22px;

    margin:
        5px
        0;

    color:
        var(--alert);

    font-size: 0.8rem;

    font-weight: 800;
}


/* Small screens */

@media (max-height: 730px) {

    .game {
        padding-top: 8px;
        gap: 5px;
    }

    .board {
        width:
            min(
                56vh,
                290px
            );
    }

    .status {
        min-height: 42px;
    }

    .key {
        height: 40px;
    }
}

</style>
</head>


<body>


<!-- Name screen -->

<div
    id="nameScreen"
    class="name-screen"
>

    <div class="name-box">

        <h2>
            Type your name
        </h2>

        <p class="name-description">
            Your name will appear in the game.
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
        >
            LET'S PLAY
        </button>

    </div>

</div>


<!-- Game -->

<main class="game">

    <header>

        <h1>
            Channy's WORDLE WORLD
        </h1>

        <p class="subtitle">
            Guess the five-letter word in six tries.
        </p>

    </header>


    <div
        id="board"
        class="board"
    ></div>


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
    >
        again?
    </button>

</main>


<script>

const WORD_LENGTH = 5;
const MAX_ATTEMPTS = 6;

const board =
    document.getElementById(
        "board"
    );

const keyboard =
    document.getElementById(
        "keyboard"
    );

const statusLabel =
    document.getElementById(
        "status"
    );

const nameScreen =
    document.getElementById(
        "nameScreen"
    );

const nameInput =
    document.getElementById(
        "nameInput"
    );

const nameError =
    document.getElementById(
        "nameError"
    );


const keyboardRows = [
    [..."QWERTYUIOP"],
    [..."ASDFGHJKL"],
    [
        "ENTER",
        ..."ZXCVBNM",
        "⌫"
    ]
];


const priority = {
    unused: 0,
    absent: 1,
    present: 2,
    correct: 3
};


let currentRow = 0;
let currentGuess = [];

let gameOver = false;
let submitting = false;


/* Build board */

function buildBoard() {

    board.innerHTML = "";

    for (
        let i = 0;
        i < WORD_LENGTH * MAX_ATTEMPTS;
        i++
    ) {

        const tile =
            document.createElement(
                "div"
            );

        tile.className =
            "tile";

        board.appendChild(
            tile
        );
    }
}


/* Build keyboard */

function buildKeyboard() {

    keyboard.innerHTML = "";

    keyboardRows.forEach(
        (keys, rowIndex) => {

            const row =
                document.createElement(
                    "div"
                );

            row.className =
                "keyboard-row";

            if (rowIndex === 1) {
                row.classList.add(
                    "middle"
                );
            }

            keys.forEach(
                key => {

                    const button =
                        document.createElement(
                            "button"
                        );

                    button.className =
                        "key";

                    button.textContent =
                        key;

                    button.dataset.key =
                        key;

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

                    row.appendChild(
                        button
                    );
                }
            );

            keyboard.appendChild(
                row
            );
        }
    );
}


/* Helpers */

function tileAt(
    row,
    column
) {

    return board.children[
        row * WORD_LENGTH
        + column
    ];
}


function setStatus(
    message,
    big = false
) {

    statusLabel.textContent =
        message;

    statusLabel.classList.toggle(
        "big",
        big
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
        "Take your first guess."
    );
}


/* Letter input */

function addLetter(
    letter
) {

    if (
        gameOver
        ||
        currentGuess.length
        >= WORD_LENGTH
    ) {
        return;
    }

    currentGuess.push(
        letter
    );

    const tile =
        tileAt(
            currentRow,
            currentGuess.length - 1
        );

    tile.textContent =
        letter;

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


/* Apply tile colors */

function applyResult(
    result
) {

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


/* Keyboard colors */

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
                priority[newState]
                <=
                priority[oldState]
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


/* Submit guess */

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
                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            {
                                guess:
                                    currentGuess.join(
                                        ""
                                    )
                            }
                        )
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

            currentRow++;

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


/* Name input */

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
                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            {name}
                        )
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


/* Restart */

async function restartGame() {

    try {

        const response =
            await fetch(
                "/restart",
                {
                    method:
                        "POST"
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


/* Keyboard handler */

function handleKey(
    key
) {

    if (
        !nameScreen
        .classList
        .contains(
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

    if (
        /^[A-Z]$/.test(
            key
        )
    ) {

        addLetter(
            key
        );
    }
}


/* Buttons */

document
    .getElementById(
        "playButton"
    )
    .addEventListener(
        "click",
        submitName
    );


document
    .getElementById(
        "againButton"
    )
    .addEventListener(
        "click",
        restartGame
    );


/* Physical keyboard */

document.addEventListener(
    "keydown",
    event => {

        if (
            !nameScreen
            .classList
            .contains(
                "hidden"
            )
        ) {

            if (
                event.key
                === "Enter"
            ) {
                submitName();
            }

            return;
        }

        if (
            event.key
            === "Enter"
        ) {

            handleKey(
                "ENTER"
            );

            return;
        }

        if (
            event.key
            === "Backspace"
        ) {

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

            handleKey(
                key
            );
        }
    }
);


/* Initial page */

buildBoard();
buildKeyboard();

nameInput.focus();

</script>

</body>
</html>
"""


# =========================
# Routes
# =========================

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
    entered = str(data.get("guess", "")).strip().lower()

    if len(entered) != WORD_LENGTH:
        return jsonify(
            error="Five letters, please."
        ), 400

    if not entered.isascii() or not entered.isalpha():
        return jsonify(
            error="English letters only."
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

    # Sixth attempt
    if game["attempt"] >= MAX_ATTEMPTS:

        game["finished"] = True

        message += (
            f"\nThe word was "
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


# =========================
# Start browser
# =========================

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
