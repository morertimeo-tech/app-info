"""Récupération des articles depuis les flux RSS."""
from __future__ import annotations

import calendar
import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone

import feedparser
import requests

log = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; InfoDuJour/1.0; +https://github.com)"
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


@dataclass
class Article:
    id: str
    title: str
    link: str
    source: str
    published: datetime
    summary: str = ""
    category: str = ""
    extra: dict = field(default_factory=dict)


def clean_text(raw: str) -> str:
    text = TAG_RE.sub(" ", raw or "")
    text = html.unescape(text)
    return SPACE_RE.sub(" ", text).strip()


def _entry_date(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime.fromtimestamp(calendar.timegm(value), tz=timezone.utc)
    return None


def fetch_feed(source: str, url: str, since: datetime) -> list[Article]:
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("Flux inaccessible %s (%s): %s", source, url, exc)
        return []

    parsed = feedparser.parse(resp.content)
    articles = []
    for entry in parsed.entries:
        published = _entry_date(entry)
        if published is None or published < since:
            continue
        title = clean_text(entry.get("title", ""))
        link = entry.get("link", "")
        if not title or not link:
            continue
        real_source = source
        # Google News : le vrai journal est dans <source>, et le titre finit par " - Journal"
        src = entry.get("source")
        if src and src.get("title"):
            real_source = src["title"]
            suffix = f" - {real_source}"
            if title.endswith(suffix):
                title = title[: -len(suffix)]
        summary = clean_text(entry.get("summary", ""))
        if summary.startswith(title):  # Google News répète souvent le titre
            summary = ""
        articles.append(
            Article(
                id="",
                title=title,
                link=link,
                source=real_source,
                published=published,
                summary=summary[:800],
            )
        )
    log.info("%-15s %3d article(s) récents", source, len(articles))
    return articles


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9àâäéèêëîïôöùûüç ]", "", title.lower()).strip()


def matches_keywords(article: Article, keywords: list[str] | None) -> bool:
    if not keywords:
        return True
    haystack = f" {article.title} {article.summary} ".lower()
    return any(k in haystack for k in keywords)


def fetch_category(category: dict, since: datetime) -> list[Article]:
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = pool.map(lambda f: fetch_feed(f[0], f[1], since), category["feeds"])
    seen: set[str] = set()
    articles: list[Article] = []
    for batch in results:
        for art in batch:
            key = normalize_title(art.title)
            if key in seen or not matches_keywords(art, category.get("keywords")):
                continue
            seen.add(key)
            art.category = category["id"]
            articles.append(art)
    articles.sort(key=lambda a: a.published, reverse=True)
    for i, art in enumerate(articles):
        art.id = f"{category['id']}-{i}"
    return articles
