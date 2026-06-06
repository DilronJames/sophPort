# Dilpreet Singh — Portfolio

A Flask portfolio for the CIS Academy *Portfolio Website* assignment. It showcases
project case studies plus two working tools you can use live in the browser:

- **Stock Strategy Backtester** — `/backtest` (Python + Flask + pandas + matplotlib + yfinance)
- **Password Strength Checker** — `/password` (Python logic mirrored in client-side JavaScript)

Both tools also run as standalone command-line programs (`backtest.py`, `password.py`).

---

## Run it locally

```powershell
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5000**. (Or double-click `run.bat`.)

> Open it through the server, not by double-clicking the `.html` files — the templates
> only render through Flask.

---

## Publish a live URL (required for the assignment)

GitHub Pages cannot host this (the backtester needs a live Python server). Use **Render**
(free), which deploys straight from GitHub:

1. Put the code on GitHub:
   ```powershell
   git init
   git add .
   git commit -m "Portfolio site"
   git branch -M main
   git remote add origin https://github.com/DilronJames/portfolio.git
   git push -u origin main
   ```
2. Go to **render.com** → sign up with GitHub → **New + → Web Service** → pick the repo.
3. Render auto-detects `render.yaml` (build: `pip install -r requirements.txt`, start:
   `gunicorn app:app`). Click **Deploy**.
4. You get a public URL like `https://dilpreet-portfolio.onrender.com`.
5. **Test it in an incognito window** before submitting (the assignment requires this).

Note: Render's free tier sleeps after 15 min idle; the first visit after sleeping takes
~30 seconds to wake.

---

## Customize (everything lives in `data.py`)

- `BIO` — name, school, professional summary, career track, interests, skills.
- `CONTACT` — **add your school email and LinkedIn here** (they appear in the Contact
  section and footer automatically once filled in). GitHub is already set.
- `PROJECTS` — the case-study projects (title, problem, stack, process, challenges, repo, demo).
- `TOOLS` — the two live tools (each already has problem / process / challenges / source link).

### Add screenshots (visual proof — worth rubric points)
Drop image files into `static/images/` and set the `image` field on each project in
`data.py`, e.g. `"image": "images/p5js.png"`. The project page shows it automatically.
The two tools are their own live demos (the backtester renders a real chart), so they
already have visual proof.

### Add your résumé (optional)
Drop `resume.pdf` into `static/files/resume.pdf`. A **Résumé** link then appears in the
Contact section and it's served at `/resume`.

### Point "View source" at the exact repo
The tools' source links and `CONTACT["github"]` currently point at your GitHub profile.
After you push, you can change `source_url` in `TOOLS` (data.py) to the exact file, e.g.
`https://github.com/DilronJames/portfolio/blob/main/backtest.py`.

---

## File layout

```
app.py            Flask routes
data.py           ALL your content
backtest.py       backtester engine (also a CLI)
password.py       password analyzer (also a CLI)
requirements.txt
render.yaml       Render deploy config
templates/        base, index, project, backtest, password, 404
static/
  css/style.css
  js/main.js, password.js
  files/          drop resume.pdf here
  images/         drop project screenshots here
```

---

## A note on code authenticity
Be ready to explain any line you present. The Python is intentionally small, commented,
and built from clear functions (data fetch → signals → simulation → metrics for the
backtester; entropy + pattern checks for the password tool). Read through `backtest.py`
and `password.py` so you can defend the logic.
