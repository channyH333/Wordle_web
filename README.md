# Channy's Wordle World

A colorful Wordle-style web game built with Python and Flask.

## Play Online

Play here:  
**https://YOUR-RENDER-URL.onrender.com**

No installation is needed for players.  
Just open the link in your browser and start playing.

## Features

- Guess a five-letter word in six tries
- Enter your name before starting
- Personalized messages
- Physical and on-screen keyboard support
- Random common English words

## Local Run (Optional)

If you want to run the project locally:

```bash
pip install -r requirements.txt
python wordle_html.py
```

Then open:

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
