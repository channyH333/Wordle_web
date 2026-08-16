# Channy's WORDLE 🎮

A simple Wordle-style web game built with Python and Flask.

Choose how you want to play:

---

## 🎮 Classic Mode

Just enjoy Wordle.

No score.  
No time pressure.  
You have **6 tries** to guess the five-letter word.

👉 **Play Classic Mode**

https://channy-wordle-world.onrender.com

---

## ⚡ Score Mode

Want a little more competition?

Score Mode adds a **100-point scoring system** based on both accuracy and speed.

👉 **Play Score Mode**

https://channy-wordle-score.onrender.com

### Scoring

You start each game with **100 points**.

- Wrong guess: **-5 points**
- Every 3 seconds: **-1 point**
- Faster answers = higher score
- Fewer attempts = higher score
- If you fail to guess the word within 6 tries: **0 points**

Your score decreases while you play, so think fast! ⏱️

---

## 🟩 How to Play

Guess the hidden **five-letter English word** in six tries.

After each guess:

- 🟩 **Green** — correct letter, correct position
- 🟨 **Yellow** — correct letter, wrong position
- ⬜ **Gray** — letter is not in the word

You can use either your physical keyboard or the keyboard on the screen.

---

## ✨ Features

- Random five-letter English words
- 6 attempts per game
- Wordle-style color feedback
- Physical keyboard support
- On-screen keyboard
- Mobile-friendly design
- Light / Dark mode
- Player name input
- Personalized messages
- Game history
- Restart / Play Again
- Score Mode with time-based scoring
- Animated score decrease
- Final score display

---

## 🛠 Built With

- Python
- Flask
- JavaScript
- HTML / CSS
- wordfreq
- Gunicorn
- Render

---

## 💻 Run Locally

Clone the repository and install the requirements:

```bash
pip install -r requirements.txt
