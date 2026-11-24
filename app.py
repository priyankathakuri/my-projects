from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import hmac
import re
from pathlib import Path
import secrets
import sqlite3
import os
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from syllabus import PAPER_ORDER, SYLLABUS, match_syllabus

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER_EXTERNAL_HOSTNAME")),
)
DATABASE = os.environ.get(
    "DATABASE_PATH", str(Path(__file__).resolve().parent / "current_affairs.db")
)

FEEDS = {
    "The Hindu": "https://www.thehindu.com/news/national/feeder/default.rss",
    "Indian Express": "https://indianexpress.com/section/india/feed/",
}

CATEGORY_KEYWORDS = {
    "Polity": ("parliament", "court", "election", "government", "constitution", "bill", "minister", "policy", "governance"),
    "Economy": ("economy", "economic", "bank", "banking", "inflation", "gdp", "trade", "tax", "budget", "rupee", "market", "finance"),
    "Environment": ("climate", "forest", "wildlife", "environment", "pollution", "energy", "rainfall", "tiger", "biodiversity", "emissions"),
    "Science & Tech": ("science", "technology", "tech", "space", "research", "ai", "digital", "satellite", "isro", "cyber"),
    "International": ("international", "border", "foreign", "summit", "china", "pakistan", "diplomacy", "bilateral", "treaty"),
}

UPSC_STUDY_GUIDES = {
    "Polity": {
        "paper": "GS Paper II · Polity and Governance",
        "focus": "Identify the constitutional provision or institution involved, the stakeholders affected, and the accountability or implementation question.",
        "question": "Examine the governance implications of this issue. Suggest measures to improve accountability and implementation.",
    },
    "Economy": {
        "paper": "GS Paper III · Indian Economy",
        "focus": "Consider the effects on households, workers, businesses and public finances. Note both short-term effects and long-term trade-offs.",
        "question": "Discuss the economic effects of this issue and suggest policy measures that balance growth with inclusion.",
    },
    "Environment": {
        "paper": "GS Paper III · Environment and Ecology",
        "focus": "Connect the issue to biodiversity, climate resilience, livelihoods and the balance between conservation and development.",
        "question": "Examine the environmental and livelihood dimensions of this issue. What measures could support sustainable outcomes?",
    },
    "Science & Tech": {
        "paper": "GS Paper III · Science and Technology",
        "focus": "Separate the scientific development from its applications. Consider access, safety, ethics, regulation and possible unintended effects.",
        "question": "Discuss the opportunities and concerns associated with this development, and suggest an appropriate policy approach.",
    },
    "International": {
        "paper": "GS Paper II · International Relations",
        "focus": "Map India’s interests, the other parties involved, regional implications and the diplomatic options available.",
        "question": "Analyse the implications of this issue for India’s interests and suggest a way forward.",
    },
    "History": {
        "paper": "GS Paper I · Indian and World History",
        "focus": "Place the event in its historical context. Consider causes, major actors, social change and the longer-term effects visible today.",
        "question": "Explain the historical background of this issue and assess its continuing significance.",
    },
    "Indian Culture": {
        "paper": "GS Paper I · Indian Heritage and Culture",
        "focus": "Consider the tradition’s historical setting, regional diversity, continuity and the ways it is preserved or adapted today.",
        "question": "Discuss the cultural significance of this issue and the need to preserve the heritage involved.",
    },
    "Geography": {
        "paper": "GS Paper I · Geography",
        "focus": "Locate the places involved and connect the story to physical processes, people, resources and regional differences.",
        "question": "Analyse the geographical factors behind this issue and their effects on people and development.",
    },
    "Polity and Governance": {
        "paper": "GS Paper II · Polity and Governance",
        "focus": "Identify the constitutional provision or institution involved, the stakeholders affected, and the accountability or implementation question.",
        "question": "Examine the governance implications of this issue. Suggest measures to improve accountability and implementation.",
    },
    "Economy and Agriculture": {
        "paper": "GS Paper III · Economy and Agriculture",
        "focus": "Consider effects on households, workers, farmers, businesses and public finances. Note short-term effects and long-term trade-offs.",
        "question": "Discuss the economic and livelihood effects of this issue and suggest inclusive policy measures.",
    },
    "Science and Technology": {
        "paper": "GS Paper III · Science and Technology",
        "focus": "Separate the scientific development from its applications. Consider access, safety, ethics, regulation and unintended effects.",
        "question": "Discuss the opportunities and concerns associated with this development and suggest an appropriate policy approach.",
    },
    "Environment and Ecology": {
        "paper": "GS Paper III · Environment and Ecology",
        "focus": "Connect the issue to ecosystems, biodiversity, climate resilience, livelihoods and the balance between conservation and development.",
        "question": "Examine the environmental and livelihood dimensions of this issue. What measures could support sustainable outcomes?",
    },
    "International Relations": {
        "paper": "GS Paper II · International Relations",
        "focus": "Map India’s interests, the other parties involved, regional implications and the diplomatic options available.",
        "question": "Analyse the implications of this issue for India’s interests and suggest a way forward.",
    },
    "Internal Security and Disaster Management": {
        "paper": "GS Paper III · Internal Security and Disaster Management",
        "focus": "Identify the risks, vulnerable groups and institutional responsibilities. Consider preparedness, coordination, prevention and recovery.",
        "question": "Assess the challenges raised by this issue and suggest coordinated measures to reduce risk and improve resilience.",
    },
    "Ethics, Integrity and Aptitude": {
        "paper": "GS Paper IV · Ethics, Integrity and Aptitude",
        "focus": "Identify the values, stakeholders and competing duties involved. Consider transparency, impartiality, empathy and public interest.",
        "question": "Identify the ethical issues in this situation and justify a course of action in the public interest.",
    },
    "General": {
        "paper": "Connect to the relevant GS paper",
        "focus": "Identify the issue, the people and institutions affected, and the available policy choices. Support your notes with the original report.",
        "question": "Explain the significance of this issue and suggest practical measures to address it.",
    },
}


def connect_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    with connect_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            published TEXT,
            description TEXT,
            summary TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'General'
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS saved_articles (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
            PRIMARY KEY (user_id, article_id)
        )""")
        db.execute(
            """
            DELETE FROM saved_articles
            WHERE article_id IN (
                SELECT id FROM articles
                WHERE url LIKE 'https://example.com/%'
            )
            """
        )
        db.execute(
            "DELETE FROM articles WHERE url LIKE 'https://example.com/%'"
        )


def clean_text(value):
    decoded = unescape(value or "")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", decoded)).strip()


def category_for(text):
    content = text.lower()
    for category, words in CATEGORY_KEYWORDS.items():
        if any(re.search(rf"(?<!\w){re.escape(word)}(?!\w)", content) for word in words):
            return category
    return "General"


def summarize(title, description):
    """Pick the most informative sentence from the publisher's RSS description."""
    text = clean_text(description)
    if not text or text.lower() == clean_text(title).lower():
        return "Read the source report for the full story. Use the issue, its causes and its impact as starting points for your UPSC notes."
    sentences = re.split(r"(?<=[.!?])\s+", text)
    title_words = set(re.findall(r"[a-z]{4,}", title.lower()))
    scored = []
    for sentence in sentences:
        words = re.findall(r"[a-z]{4,}", sentence.lower())
        if words:
            overlap = len(set(words) & title_words)
            scored.append((len(words) + overlap * 2, sentence.strip()))
    best = max(scored, default=(0, text), key=lambda item: item[0])[1]
    return best[:360].rsplit(" ", 1)[0] + ("…" if len(best) > 360 else "")


def parse_date(value):
    try:
        date = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            date = datetime.fromisoformat((value or "").replace("Z", "+00:00"))
        except (TypeError, ValueError, OverflowError):
            date = datetime.now(timezone.utc)
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return date.isoformat()


def fetch_feed(source, feed_url):
    request_obj = urllib.request.Request(feed_url, headers={"User-Agent": "UPSC-Current-Affairs-Student-Project/1.0"})
    with urllib.request.urlopen(request_obj, timeout=12) as response:
        root = ET.fromstring(response.read())
    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{*}entry")
    collected = []
    for item in items[:30]:
        def field(name):
            child = item.find(name)
            if child is None:
                child = item.find("{*}" + name)
            return child

        title_node, link_node = field("title"), field("link")
        if title_node is None or not title_node.text:
            continue
        link = (link_node.text if link_node is not None else "") or ""
        if not link and link_node is not None:
            link = link_node.attrib.get("href", "")
        if link_node is not None and link_node.attrib.get("rel") not in (None, "", "alternate"):
            alternate = next(
                (node for node in item.findall("{*}link") if node.attrib.get("rel") == "alternate"),
                None,
            )
            if alternate is not None:
                link = alternate.attrib.get("href", link)
        desc_node = next((node for node in (field("description"), field("summary"), field("content")) if node is not None), None)
        pub_node = next((node for node in (field("pubDate"), field("published"), field("updated")) if node is not None), None)
        title = clean_text(" ".join(title_node.itertext()))
        description = clean_text(" ".join(desc_node.itertext()) if desc_node is not None else "")
        parsed_link = urlsplit(link)
        if parsed_link.scheme in ("http", "https") and parsed_link.netloc:
            collected.append((title, source, link, parse_date(pub_node.text if pub_node is not None else ""), description, summarize(title, description), category_for(title + " " + description)))
    return collected


@app.before_request
def protect_post_forms():
    if request.method == "POST":
        expected = session.get("_csrf_token", "")
        provided = request.form.get("_csrf_token", "")
        if not expected or not provided or not hmac.compare_digest(expected, provided):
            abort(400)


@app.context_processor
def inject_csrf_token():
    def csrf_token():
        if "_csrf_token" not in session:
            session["_csrf_token"] = secrets.token_urlsafe(32)
        return session["_csrf_token"]

    return {"csrf_token": csrf_token}


@app.route("/")
def index():
    search = request.args.get("q", "").strip()
    subject = request.args.get("subject", request.args.get("category", "")).strip()
    legacy_subjects = {
        "Polity": "Polity and Governance",
        "Economy": "Economy and Agriculture",
        "Science & Tech": "Science and Technology",
        "Environment": "Environment and Ecology",
        "International": "International Relations",
    }
    subject = legacy_subjects.get(subject, subject)
    if subject not in SYLLABUS:
        subject = ""
    paper = request.args.get("paper", "").strip()
    if paper not in PAPER_ORDER:
        paper = ""
    topic = request.args.get("topic", "").strip()
    known_topics = {topic_name for section in SYLLABUS.values() for topic_name in section["topics"]}
    if topic not in known_topics:
        topic = ""
    saved_only = request.args.get("saved") == "1"
    user_id = session.get("user_id")
    if saved_only and not user_id:
        flash("Log in to see your personal reading list.", "error")
        return redirect(url_for("login", next=url_for("index", saved=1)))
    query = "SELECT articles.*, EXISTS(SELECT 1 FROM saved_articles WHERE saved_articles.article_id = articles.id AND saved_articles.user_id = ?) AS is_saved FROM articles WHERE 1=1"
    params = [user_id or -1]
    if search:
        query += " AND (title LIKE ? OR description LIKE ? OR summary LIKE ?)"
        params.extend([f"%{search}%"] * 3)
    if saved_only:
        query += " AND EXISTS(SELECT 1 FROM saved_articles WHERE saved_articles.article_id = articles.id AND saved_articles.user_id = ?)"
        params.append(user_id)
    query += " ORDER BY published DESC, id DESC"
    with connect_db() as db:
        rows = db.execute(query, params).fetchall()
        counts = db.execute("SELECT COUNT(*) AS total, COUNT(DISTINCT category) AS topics FROM articles").fetchone()
    articles = []
    for row in rows:
        article = dict(row)
        article["syllabus_matches"] = match_syllabus(article["title"], article["description"])
        matches = article["syllabus_matches"]
        if subject or paper or topic:
            matching_tags = [
                match for match in matches
                if (not subject or match["subject"] == subject)
                and (not paper or paper in match["papers"])
                and (not topic or match["topic"] == topic)
            ]
            if not matching_tags:
                continue
        articles.append(article)
    return render_template(
        "index.html",
        articles=articles,
        search=search,
        subject=subject,
        paper=paper,
        topic=topic,
        saved_only=saved_only,
        counts=counts,
        syllabus=SYLLABUS,
        syllabus_subjects=list(SYLLABUS),
        papers=PAPER_ORDER,
    )


@app.post("/refresh")
def refresh():
    new_count = 0
    errors = []
    with connect_db() as db:
        for source, feed_url in FEEDS.items():
            try:
                entries = fetch_feed(source, feed_url)
                before = db.total_changes
                db.executemany("INSERT OR IGNORE INTO articles (title, source, url, published, description, summary, category) VALUES (?, ?, ?, ?, ?, ?, ?)", entries)
                new_count += db.total_changes - before
            except Exception as error:
                errors.append(source)
                app.logger.warning("Could not refresh %s: %s", source, error)
    if new_count:
        flash(f"Added {new_count} new article{'s' if new_count != 1 else ''} to your briefing.", "success")
    elif errors:
        flash("News feeds could not be reached right now. Your saved briefing is still here.", "error")
    else:
        flash("You're up to date. No new articles were found.", "success")
    return redirect(url_for("index"))


@app.post("/save/<int:article_id>")
def save_article(article_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Log in to save stories to your reading list.", "error")
        return redirect(url_for("login", next=safe_next_url(request.referrer)))
    with connect_db() as db:
        if not db.execute("SELECT 1 FROM articles WHERE id = ?", (article_id,)).fetchone():
            return render_template("404.html"), 404
        exists = db.execute("SELECT 1 FROM saved_articles WHERE user_id = ? AND article_id = ?", (user_id, article_id)).fetchone()
        if exists:
            db.execute("DELETE FROM saved_articles WHERE user_id = ? AND article_id = ?", (user_id, article_id))
        else:
            db.execute("INSERT OR IGNORE INTO saved_articles (user_id, article_id) VALUES (?, ?)", (user_id, article_id))
    return redirect(safe_next_url(request.referrer))


@app.route("/article/<int:article_id>")
def article_detail(article_id):
    with connect_db() as db:
        article = db.execute("SELECT articles.*, EXISTS(SELECT 1 FROM saved_articles WHERE saved_articles.article_id = articles.id AND saved_articles.user_id = ?) AS is_saved FROM articles WHERE id = ?", (session.get("user_id") or -1, article_id)).fetchone()
    if article is None:
        return render_template("404.html"), 404
    syllabus_matches = match_syllabus(article["title"], article["description"])
    if syllabus_matches:
        guide_key = syllabus_matches[0]["subject"]
        study_guide = dict(UPSC_STUDY_GUIDES.get(guide_key, UPSC_STUDY_GUIDES["General"]))
        study_guide["paper"] = syllabus_matches[0]["paper"]
    else:
        study_guide = UPSC_STUDY_GUIDES.get(article["category"], UPSC_STUDY_GUIDES["General"])
    return render_template("article.html", article=article, study_guide=study_guide, syllabus_matches=syllabus_matches)


@app.route("/about")
def about():
    return render_template("about.html")


def safe_next_url(value):
    if not value:
        return url_for("index")
    parsed = urlsplit(value)
    if not parsed.netloc and value.startswith("/") and not value.startswith("//"):
        return value
    if parsed.netloc == request.host and parsed.scheme in ("http", "https"):
        return parsed.path + (("?" + parsed.query) if parsed.query else "")
    return url_for("index")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_id"):
        return redirect(url_for("index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        valid_email = re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
        if not name or len(name) > 80 or not valid_email or len(email) > 254 or not 8 <= len(password) <= 128:
            flash("Add your name and email, and choose a password with at least 8 characters.", "error")
        else:
            try:
                with connect_db() as db:
                    cursor = db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", (name, email, generate_password_hash(password)))
                    session.clear()
                    session["user_id"] = cursor.lastrowid
                    session["user_name"] = name
                flash("Your account is ready. Welcome to The UPSC Newsroom!", "success")
                return redirect(url_for("index"))
            except sqlite3.IntegrityError:
                flash("An account with that email already exists. Please log in.", "error")
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("index"))
    next_url = safe_next_url(request.args.get("next") or request.form.get("next"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with connect_db() as db:
            user = db.execute("SELECT id, name, password_hash FROM users WHERE email = ?", (email,)).fetchone()
        if user and len(password) <= 128 and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash(f"Welcome back, {user['name']}.", "success")
            return redirect(safe_next_url(request.form.get("next")))
        flash("We couldn't match that email and password. Please try again.", "error")
    return render_template("login.html", next_url=next_url)


@app.post("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
