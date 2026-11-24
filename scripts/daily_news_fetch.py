"""Fetch public UPSC current-affairs metadata and send it to the website."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import json
import os
import re
import sys
import time
from urllib.parse import urljoin, urlsplit
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


USER_AGENT = "UPSC-Newsroom-Student-Project/1.0 (public article metadata; contact via website)"
MAX_PER_SITE = 12
TIMEOUT_SECONDS = 18
SITES = {
    "Vision IAS": "https://visionias.in/current-affairs/",
    "Drishti IAS": "https://www.drishtiias.com/rss.rss",
    "Vajiram & Ravi": "https://vajiramandravi.com/current-affairs/",
}
SKIP_VAJIRAM_PATHS = {
    "daily-editorial-analysis", "daily-quiz", "prelims-pointers",
    "mains-articles", "upsc-prelims-current-affairs",
    "upsc-mains-current-affairs", "current-affairs",
}


def fetch_text(url):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read(2_000_000).decode(
            response.headers.get_content_charset() or "utf-8", errors="replace"
        )


def plain_text(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", value or "")).strip()


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.anchors = []
        self.active_anchor = None
        self.meta = {}
        self.times = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.active_anchor = [values["href"], []]
        if tag == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            content = values.get("content", "").strip()
            if key and content:
                self.meta[key] = content
        if tag == "time" and values.get("datetime"):
            self.times.append(values["datetime"])

    def handle_data(self, data):
        if self.active_anchor is not None:
            self.active_anchor[1].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.active_anchor is not None:
            href, chunks = self.active_anchor
            label = plain_text(" ".join(chunks))
            if label:
                self.anchors.append((href, label))
            self.active_anchor = None


def parse_date(value):
    if not value:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            result = parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            for pattern in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"):
                try:
                    result = datetime.strptime(value, pattern)
                    break
                except ValueError:
                    continue
            else:
                return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.isoformat()


def meta_details(url):
    try:
        parser = PageParser()
        parser.feed(fetch_text(url))
        date = next((parse_date(value) for value in parser.times if parse_date(value)), None)
        date = date or next(
            (parse_date(parser.meta.get(key)) for key in (
                "article:published_time", "datepublished", "date", "pubdate"
            ) if parse_date(parser.meta.get(key))),
            None,
        )
        description = next((parser.meta[key] for key in (
            "og:description", "description", "twitter:description"
        ) if parser.meta.get(key)), "")
        return date, plain_text(description)[:1200]
    except Exception as error:
        print(f"Could not read article details {url}: {error}", file=sys.stderr)
        return None, ""


def fetch_drishti():
    root = ET.fromstring(fetch_text(SITES["Drishti IAS"]))
    items = root.findall(".//item") or root.findall(".//{*}entry")
    results = []
    for item in items[:MAX_PER_SITE]:
        def value(name):
            child = item.find(name)
            return child if child is not None else item.find("{*}" + name)

        title_node = value("title")
        link_node = value("link")
        if title_node is None:
            continue
        link = (link_node.text or "").strip() if link_node is not None else ""
        if link_node is not None and not link:
            link = link_node.attrib.get("href", "")
        description_node = value("description")
        if description_node is None:
            description_node = value("summary")
        date_node = value("pubDate")
        if date_node is None:
            date_node = value("published")
        if date_node is None:
            date_node = value("updated")
        title = plain_text("".join(title_node.itertext()))
        if urlsplit(link).hostname not in {"drishtiias.com", "www.drishtiias.com"}:
            continue
        results.append({
            "source": "Drishti IAS",
            "title": title,
            "url": link,
            "published": parse_date(date_node.text if date_node is not None else ""),
            "description": plain_text("".join(description_node.itertext()) if description_node is not None else "")[:1200],
        })
    return results


def is_candidate(source, url):
    parsed = urlsplit(url)
    path = parsed.path.strip("/")
    if source == "Vision IAS":
        return (
            parsed.scheme == "https"
            and parsed.hostname in {"visionias.in", "www.visionias.in"}
            and "/current-affairs/" in parsed.path
            and "/article/" in parsed.path
        )
    if source == "Vajiram & Ravi":
        if parsed.scheme != "https" or parsed.hostname not in {"vajiramandravi.com", "www.vajiramandravi.com"}:
            return False
        parts = path.split("/")
        if len(parts) < 2 or parts[0] != "current-affairs":
            return False
        slug = parts[1].lower()
        return slug not in SKIP_VAJIRAM_PATHS and not re.fullmatch(r"[a-z]+-\d{1,2}-\d{4}", slug)
    return False


def fetch_listing(source, page_url):
    parser = PageParser()
    parser.feed(fetch_text(page_url))
    unique = {}
    for href, title in parser.anchors:
        article_url = urljoin(page_url, href).split("#", 1)[0]
        if is_candidate(source, article_url):
            unique.setdefault(article_url, title)

    rows = []
    for article_url, title in list(unique.items())[:MAX_PER_SITE]:
        published, description = meta_details(article_url)
        # Vision embeds publication dates in its public article URL.
        if not published and source == "Vision IAS":
            match = re.search(r"/article/(\d{4}-\d{2}-\d{2})/", article_url)
            if match:
                published = parse_date(match.group(1))
        rows.append({
            "source": source,
            "title": title[:500],
            "url": article_url,
            "published": published,
            "description": description,
        })
        time.sleep(0.15)
    return rows


def fetch_everything():
    articles = []
    for source in ("Vision IAS", "Vajiram & Ravi"):
        try:
            articles.extend(fetch_listing(source, SITES[source]))
            print(f"Fetched public listing metadata from {source}.")
        except Exception as error:
            print(f"Could not fetch {source}: {error}", file=sys.stderr)
    try:
        articles.extend(fetch_drishti())
        print("Fetched Drishti IAS public RSS items.")
    except Exception as error:
        print(f"Could not fetch Drishti IAS: {error}", file=sys.stderr)
    return articles


def send_to_website(articles):
    base_url = os.environ.get("PUBLIC_SITE_URL", "").rstrip("/")
    token = os.environ.get("NEWS_REFRESH_TOKEN", "")
    if not base_url.startswith("https://") or not token:
        raise RuntimeError("Set PUBLIC_SITE_URL and NEWS_REFRESH_TOKEN in the scheduled service environment.")
    body = json.dumps({"articles": articles}).encode("utf-8")
    request = Request(
        f"{base_url}/internal/news-ingest",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
        method="POST",
    )
    for attempt, wait_seconds in enumerate((0, 20, 35), start=1):
        if wait_seconds:
            print(f"Retrying the website after {wait_seconds} seconds (attempt {attempt}/3).")
            time.sleep(wait_seconds)
        try:
            with urlopen(request, timeout=90) as response:
                result = json.loads(response.read().decode("utf-8"))
            print(f"Website accepted {result.get('inserted', 0)} new stories from {result.get('received', 0)} collected items.")
            return
        except (HTTPError, URLError, TimeoutError) as error:
            if attempt == 3:
                raise RuntimeError(f"Could not deliver the daily update to the website: {error}") from error


if __name__ == "__main__":
    collected = fetch_everything()
    if not collected:
        raise SystemExit("No publisher metadata was collected; the website was not updated.")
    send_to_website(collected)
