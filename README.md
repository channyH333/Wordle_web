# Channy's Wordle World

A colorful Wordle-style web game built with Python and Flask.

## Features

- Guess a five-letter word in six tries
- Enter your name before starting
- Personalized messages
- Physical and on-screen keyboard support
- Random common English words using `wordfreq`

## Installation

Install the required packages:

```bash
pip install -r requirements.txt
```

## Run Locally

```bash
python wordle_html.py
```

The game will open in your browser at:

```text
http://127.0.0.1:5000
```

## Render Deployment

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
gunicorn wordle_html:app
```

## Built With

- Python
- Flask
- HTML / CSS / JavaScript
- wordfreq
