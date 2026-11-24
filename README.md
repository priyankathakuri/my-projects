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

The GitHub Actions workflow in `.github/workflows/daily-news.yml` is scheduled for 6:00 pm India time (`30 12 * * *`, since GitHub schedules use UTC). It fetches public current-affairs metadata from Vision IAS, Drishti IAS, and Vajiram & Ravi, then sends headlines, dates, short public descriptions, and source links to the website. It does not copy complete publisher articles or bypass gated material.

GitHub Actions standard runners are free for public repositories. GitHub can delay a scheduled run when Actions is busy, so 6:00 pm is the target time rather than an exact-second guarantee. Scheduled workflows run only from the repository's default branch; GitHub may disable a public repository's schedule after 60 days without repository activity.

### Enable the scheduled update

1. On your computer, open PowerShell and make a private token:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

   Keep the token private. Do not put it in a project file or send it in a chat.
2. In the Render Dashboard, open the `daily-brief-upsc` web service, select **Environment**, add `NEWS_REFRESH_TOKEN`, paste the token, and save/deploy.
3. On GitHub, open this repository and go to **Settings → Secrets and variables → Actions → New repository secret**. Name it `NEWS_REFRESH_TOKEN` and paste the same token.
4. Add `.github/workflows/daily-news.yml` and `scripts/daily_news_fetch.py` to the repository's default branch (`main`). The schedule will then run daily. In GitHub, open **Actions → Daily UPSC publisher update → Run workflow** to trigger a manual run and see its logs.

For local development, **Refresh news** still fetches The Hindu and The Indian Express. The GitHub schedule runs in the cloud even when your computer is off. The Render free web service still uses temporary SQLite storage, so accounts and saved stories can be lost when the service is rebuilt or restarted.

## Publish a shareable link

For a public demo, push this project to a GitHub repository and create a Blueprint on Render connected to that repository. The included `render.yaml` supplies the Python build and start commands and asks Render to generate a private `SECRET_KEY`. The local SQLite database is excluded from Git; use a persistent hosted database if you need accounts and saved stories to survive server restarts.

## What it does

- Fetches RSS headlines and descriptions from two newspaper feeds.
- Includes a free GitHub Actions schedule for publisher metadata at 6:00 pm India time.
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
