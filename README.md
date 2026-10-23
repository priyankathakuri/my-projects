# The Daily Brief — UPSC Current Affairs

A small full-stack newspaper-style site for UPSC aspirants. It uses Python and Flask for the server, SQLite for storage, and HTML, CSS and JavaScript for the pages.

## Run it

1. Install Python 3.10 or newer.
2. Open a terminal in this folder and run:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```

3. Open `http://127.0.0.1:5000` in your browser.
4. Select **Refresh news** to fetch recent stories from The Hindu and The Indian Express RSS feeds. The site has a few clearly marked starter stories if the feeds cannot be reached.

## Publish a shareable link

For a public demo, push this project to a GitHub repository and create a Python Web Service on Render connected to that repository. Use `pip install -r requirements.txt` as the build command and `gunicorn app:app` as the start command. Set a private `SECRET_KEY` environment variable in the hosting dashboard. The local SQLite database is excluded from Git; use a persistent hosted database if you need accounts and saved stories to survive server restarts.

## What it does

- Fetches RSS headlines and descriptions from two newspaper feeds.
- Saves stories in a local SQLite database (`current_affairs.db`).
- Creates short extractive summaries from each feed description and assigns a broad topic using simple keywords.
- Lets you search, filter by topic, open the source story and save articles to a reading list.
- Includes sign-in and login pages; each account has its own saved reading list.
- Provides a short UPSC-oriented study prompt on each story.

## Project files

- `app.py` — Flask routes, RSS fetching, keyword topics and summary logic.
- `schema.sql` — SQLite table definition (also created by the app on startup).
- `templates/` — Jinja HTML pages.
- `static/style.css` and `static/app.js` — page styling and small browser interactions.
- `static/brief-illustration.svg` — custom newspaper and study-notes hero illustration.

## Notes

The feed endpoints and availability are controlled by the publishers and may change. Summaries and topic labels are intentionally simple student-project features; they are not expert analysis. Always read the original linked reporting and check facts before using them in an answer.

For a public deployment, set a strong `SECRET_KEY` environment variable and use a production-ready server. The default secret key is only for local development.
