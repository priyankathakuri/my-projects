from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import re
import sqlite3
import os
import urllib.request
import xml.etree.ElementTree as ET

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)
DATABASE = "current_affairs.db"

FEEDS = {
    "The Hindu": "https://www.thehindu.com/news/national/feeder/default.rss",
    "Indian Express": "https://indianexpress.com/section/india/feed/",
}

CATEGORY_KEYWORDS = {
    "Polity": ("parliament", "court", "election", "government", "constitution", "bill", "minister", "policy"),
    "Economy": ("economy", "bank", "inflation", "gdp", "trade", "tax", "budget", "rupee", "market"),
    "Environment": ("climate", "forest", "wildlife", "environment", "pollution", "energy", "rainfall", "tiger"),
    "Science & Tech": ("science", "technology", "space", "research", "ai", "digital", "satellite", "isro"),
    "International": ("india", "world", "international", "border", "foreign", "summit", "china", "pakistan"),
}


def connect_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
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
            category TEXT NOT NULL DEFAULT 'General',
            saved INTEGER NOT NULL DEFAULT 0
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


def add_demo_articles(db):
    """A small starter set keeps the site useful before the first feed refresh."""
    samples = [
        ("India's monsoon outlook and the rural economy", "UPSC Daily Desk", "https://example.com/monsoon-rural-economy", "Today", "Seasonal rainfall can affect farm output, rural demand and food prices. The outlook is useful context for questions on agriculture and the economy.", "Economy"),
        ("New conservation steps put biodiversity in focus", "UPSC Daily Desk", "https://example.com/biodiversity-conservation", "Today", "Conservation policy connects habitat protection with local livelihoods. Consider the role of communities, protected areas and coordination between levels of government.", "Environment"),
        ("Parliamentary committees: why their scrutiny matters", "UPSC Daily Desk", "https://example.com/parliamentary-committees", "Yesterday", "Committee review gives members time to examine proposed laws and hear evidence. It is an important part of legislative accountability and informed debate.", "Polity"),
        ("India's digital public infrastructure draws global interest", "UPSC Daily Desk", "https://example.com/digital-public-infrastructure", "Yesterday", "Digital public infrastructure can widen access to services, while raising questions about privacy, inclusion and data security. These are useful angles for balanced answers.", "Science & Tech"),
    ]
    db.executemany("INSERT OR IGNORE INTO articles (title, source, url, published, description, summary, category) VALUES (?, ?, ?, ?, ?, ?, ?)", samples)


def clean_text(value):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def category_for(text):
    content = text.lower()
    for category, words in CATEGORY_KEYWORDS.items():
        if sum(1 for word in words if word in content) >= 1:
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
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date.isoformat()
    except (TypeError, ValueError, OverflowError):
        return datetime.now(timezone.utc).isoformat()


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
        desc_node = next((node for node in (field("description"), field("summary"), field("content")) if node is not None), None)
        pub_node = next((node for node in (field("pubDate"), field("published"), field("updated")) if node is not None), None)
        title = clean_text(title_node.text)
        description = clean_text(desc_node.text if desc_node is not None else "")
        if link.startswith("http"):
            collected.append((title, source, link, parse_date(pub_node.text if pub_node is not None else ""), description, summarize(title, description), category_for(title + " " + description)))
    return collected


@app.route("/")
def index():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
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
    if category:
        query += " AND category = ?"
        params.append(category)
    if saved_only:
        query += " AND EXISTS(SELECT 1 FROM saved_articles WHERE saved_articles.article_id = articles.id AND saved_articles.user_id = ?)"
        params.append(user_id)
    query += " ORDER BY published DESC, id DESC"
    with connect_db() as db:
        articles = db.execute(query, params).fetchall()
        counts = db.execute("SELECT COUNT(*) AS total, COUNT(DISTINCT category) AS topics FROM articles").fetchone()
    return render_template("index.html", articles=articles, search=search, category=category, saved_only=saved_only, counts=counts, categories=list(CATEGORY_KEYWORDS))


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
        return redirect(url_for("login", next=request.referrer or url_for("index")))
    with connect_db() as db:
        exists = db.execute("SELECT 1 FROM saved_articles WHERE user_id = ? AND article_id = ?", (user_id, article_id)).fetchone()
        if exists:
            db.execute("DELETE FROM saved_articles WHERE user_id = ? AND article_id = ?", (user_id, article_id))
        else:
            db.execute("INSERT OR IGNORE INTO saved_articles (user_id, article_id) VALUES (?, ?)", (user_id, article_id))
    return redirect(request.referrer or url_for("index"))


@app.route("/article/<int:article_id>")
def article_detail(article_id):
    with connect_db() as db:
        article = db.execute("SELECT articles.*, EXISTS(SELECT 1 FROM saved_articles WHERE saved_articles.article_id = articles.id AND saved_articles.user_id = ?) AS is_saved FROM articles WHERE id = ?", (session.get("user_id") or -1, article_id)).fetchone()
    if article is None:
        return render_template("404.html"), 404
    return render_template("article.html", article=article)


@app.route("/about")
def about():
    return render_template("about.html")


def safe_next_url(value):
    if value and value.startswith("/") and not value.startswith("//"):
        return value
    return url_for("index")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if session.get("user_id"):
        return redirect(url_for("index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Add your name and email, and choose a password with at least 8 characters.", "error")
        else:
            try:
                with connect_db() as db:
                    cursor = db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)", (name, email, generate_password_hash(password)))
                    session["user_id"] = cursor.lastrowid
                    session["user_name"] = name
                flash("Your account is ready. Welcome to The Daily Brief!", "success")
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
        if user and check_password_hash(user["password_hash"], password):
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
