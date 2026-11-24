# The UPSC Newsroom — UPSC Current Affairs

A small full-stack newspaper-style site for UPSC aspirants. It uses Python and Flask for the server, SQLite for storage, and HTML, CSS and JavaScript for the pages.

## Run it

1. Install Python 3.10 or newer.
2. Open PowerShell in this folder and run:

   ```bash
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe app.py
   ```

3. Open `http://127.0.0.1:5000` in your browser.
4. Select **Refresh news** to fetch recent stories from The Hindu and The Indian Express RSS feeds. If the feeds are unavailable, the page explains how to retry.

## Daily news refresh

The home page checks when the feeds were last refreshed. If 24 hours have passed, it starts a background refresh when someone visits and reloads the page after the check. The **Refresh news** button is still available for an immediate manual update. This is a first-visit daily refresh, not a fixed-time schedule: if nobody opens the site, the refresh waits until the next visit. A fixed-time Render Cron Job needs a separate service (currently at least $1/month) and cannot share this app's local SQLite disk, so it would also require a shared database.

## Publish a shareable link

For a public demo, push this project to a GitHub repository and create a Blueprint on Render connected to that repository. The included `render.yaml` supplies the Python build and start commands and asks Render to generate a private `SECRET_KEY`. The local SQLite database is excluded from Git; use a persistent hosted database if you need accounts and saved stories to survive server restarts.

## What it does

- Fetches RSS headlines and descriptions from two newspaper feeds.
- Starts an automatic background feed refresh when the site is visited after 24 hours.
- Saves stories in a local SQLite database (`current_affairs.db`).
- Creates short extractive summaries from each feed description and assigns a broad topic using simple keywords.
- Maps each headline and feed description to likely UPSC syllabus papers and micro-topics from the supplied 2026 guide; filter by subject, paper, or micro-topic.
- Lets you search, filter by topic, open the source story and save articles to a reading list.
- Includes sign-in and login pages; each account has its own saved reading list.
- Provides a short UPSC-oriented study prompt on each story.

## Project files

- `app.py` — Flask routes, RSS fetching, keyword topics and summary logic.
- `syllabus.py` — UPSC paper/micro-topic taxonomy and transparent keyword matching.
- `schema.sql` — SQLite table definition (also created by the app on startup).
- `templates/` — Jinja HTML pages.
- `static/style.css` and `static/app.js` — page styling and small browser interactions.
- `static/brief-illustration.svg` — custom newspaper and study-notes hero illustration.
- `render.yaml` — Render Blueprint configuration for a public demo.

## Notes

The feed endpoints and availability are controlled by the publishers and may change. Summaries and topic labels are intentionally simple student-project features; they are not expert analysis. Always read the original linked reporting and check facts before using them in an answer.

For a public deployment, keep `SECRET_KEY` private and use the included Render Blueprint. The app creates a random secret for local development if no environment variable is set. Render's default filesystem is temporary, so use a persistent hosted database for accounts and saved stories that must survive restarts.
