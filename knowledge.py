"""SQLite storage and lightweight lexical retrieval for crawled pages.

Author: Namira Mujawar | Project date: 2026-11-18
"""

import math
import os
import re
import sqlite3
import unicodedata
from pathlib import Path

from company_briefs import CURATED_RESEARCH_RECORDS


APP_DIR = Path(__file__).resolve().parent
TOKEN_PATTERN = re.compile(r"[\w'-]{2,}", flags=re.UNICODE)
ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
SOURCE_CATALOG = {
    "DarGlobal": "https://www.darglobal.co.uk/",
    "Companies House": "https://find-and-update.company-information.service.gov.uk/company/14388348",
    "Wasalt": "https://wasalt.sa/",
    "Wikipedia": "https://en.wikipedia.org/wiki/DarGlobal",
    "The National": "https://www.thenationalnews.com/business/property/",
    "DarGlobal official statements": "https://darglobal.co.uk/press/",
    "Zawya": (
        "https://www.zawya.com/en/press-release/companies-news/"
        "dar-global-expands-saudi-arabia-portfolio-with-new-jeddah-development-valued-at-sar-1bln-2283558"
    ),
}
SOURCE_LICENSES = {
    "Wikipedia": "CC BY-SA; attribution required",
    "The National": "Brief paraphrased facts only; link to publisher",
    "DarGlobal official statements": (
        "Paraphrased facts from official company statements; source links provided"
    ),
    "Zawya": "Press release summary only; link to publisher",
}
CURATED_COMPANY_RECORD = {
    "url": SOURCE_CATALOG["Companies House"],
    "title": "DAR GLOBAL PLC - Companies House company overview",
    "source": "Companies House",
    "body": (
        "DarGlobal PLC (registered as DAR GLOBAL PLC) is an active UK public "
        "limited company, company number 14388348, incorporated on 30 September "
        "2022. Companies House lists its "
        "registered nature of business as SIC 64209 (activities of other holding "
        "companies not elsewhere classified) and SIC 68100 (buying and selling "
        "of own real estate). This official register supports legal identity and "
        "registered activities only; it does not verify particular developments, "
        "brands, locations, current prices, or investment claims. "
        "Source reviewed 18 November 2026."
    ),
    "fetched_at": "2026-11-18T00:00:00+00:00",
}
STOP_WORDS = {
    "a",
    "about",
    "an",
    "and",
    "are",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "or",
    "tell",
    "that",
    "the",
    "to",
    "was",
    "what",
    "when",
    "where",
    "which",
    "who",
    "with",
    "you",
}


def get_database_path():
    configured = os.environ.get("DATA_DIR", "").strip()
    data_dir = Path(configured) if configured else APP_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "assistant.sqlite3"


def connect():
    connection = sqlite3.connect(str(get_database_path()), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def initialize_database():
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pages (
                url TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                body TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS pages_source_idx ON pages(source)")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS conversations_owner_updated_idx "
            "ON conversations(owner_id, updated_at DESC)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                sources_json TEXT NOT NULL DEFAULT '[]',
                mode TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS messages_conversation_idx "
            "ON messages(conversation_id, id)"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS source_status (
                source TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                message TEXT NOT NULL,
                checked_at TEXT
            )
            """
        )
        for source in SOURCE_CATALOG:
            status_messages = {
                "Companies House": (
                    "curated",
                    "Manually verified official company-register reference.",
                ),
                "DarGlobal official statements": (
                    "curated",
                    "Paraphrased facts from official company statements.",
                ),
                "Wasalt": (
                    "curated",
                    "Paraphrased facts from Wasalt's public company overview.",
                ),
                "Zawya": (
                    "curated",
                    "Paraphrased facts from a DarGlobal press release republished by Zawya.",
                ),
            }
            initial_status, initial_message = status_messages.get(
                source, ("not_checked", "Source has not been crawled yet.")
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO source_status(source, status, message)
                VALUES (?, ?, ?)
                """,
                (source, initial_status, initial_message),
            )
        connection.execute(
            """
            INSERT INTO pages(url, title, source, body, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title = excluded.title,
                source = excluded.source,
                body = excluded.body,
                fetched_at = excluded.fetched_at
            """,
            (
                CURATED_COMPANY_RECORD["url"],
                CURATED_COMPANY_RECORD["title"],
                CURATED_COMPANY_RECORD["source"],
                CURATED_COMPANY_RECORD["body"],
                CURATED_COMPANY_RECORD["fetched_at"],
            ),
        )
        for record in CURATED_RESEARCH_RECORDS:
            connection.execute(
                """
                INSERT INTO pages(url, title, source, body, fetched_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title = excluded.title,
                    source = excluded.source,
                    body = excluded.body,
                    fetched_at = excluded.fetched_at
                """,
                (
                    record["url"],
                    record["title"],
                    record["source"],
                    record["body"],
                    record["fetched_at"],
                ),
            )


def save_page(url, title, source, body, fetched_at):
    cleaned_body = re.sub(r"\s+", " ", body).strip()[:20_000]
    if not cleaned_body:
        return False
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO pages(url, title, source, body, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                title = excluded.title,
                source = excluded.source,
                body = excluded.body,
                fetched_at = excluded.fetched_at
            """,
            (url, title[:300] or url, source, cleaned_body, fetched_at),
        )
    return True


def list_pages():
    with connect() as connection:
        rows = connection.execute(
            "SELECT url, title, source, body, fetched_at FROM pages ORDER BY source, title"
        ).fetchall()
    return [dict(row) for row in rows]


def retain_source_pages(source, urls):
    keep = list(dict.fromkeys(urls))
    if not keep:
        return
    placeholders = ", ".join("?" for _ in keep)
    with connect() as connection:
        connection.execute(
            "DELETE FROM pages WHERE source = ? AND url NOT IN ({0})".format(
                placeholders
            ),
            [source] + keep,
        )


def source_list():
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT s.source, s.status, s.message, s.checked_at,
                   COALESCE(p.page_count, 0) AS page_count,
                   p.last_updated
            FROM source_status AS s
            LEFT JOIN (
                SELECT source, COUNT(*) AS page_count, MAX(fetched_at) AS last_updated
                FROM pages
                GROUP BY source
            ) AS p ON p.source = s.source
            ORDER BY s.source
            """
        ).fetchall()
    return [
        dict(
            row,
            homepage=SOURCE_CATALOG[row["source"]],
            license=SOURCE_LICENSES.get(row["source"], "Public reference"),
        )
        for row in rows
    ]


def public_source_list():
    """Return indexed content sources without internal crawl-status diagnostics."""
    public_statuses = {"available", "curated"}
    return [
        {
            "source": item["source"],
            "status": item["status"],
            "page_count": item["page_count"],
            "homepage": item["homepage"],
            "license": item["license"],
            "last_updated": item["last_updated"],
        }
        for item in source_list()
        if item["status"] in public_statuses and item["page_count"] > 0
    ]


def record_source_status(source, status, message, checked_at):
    if source not in SOURCE_CATALOG:
        raise ValueError("Unknown source: {0}".format(source))
    allowed_statuses = {
        "checking",
        "available",
        "blocked",
        "unavailable",
        "not_checked",
        "curated",
        "metadata_only",
    }
    if status not in allowed_statuses:
        raise ValueError("Invalid source status: {0}".format(status))
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO source_status(source, status, message, checked_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                status = excluded.status,
                message = excluded.message,
                checked_at = excluded.checked_at
            """,
            (source, status, message[:400], checked_at),
        )


def normalized_tokens(text):
    text = unicodedata.normalize("NFKC", text).lower()
    text = ARABIC_DIACRITICS.sub("", text)
    return TOKEN_PATTERN.findall(text)


def make_snippet(body, query_terms, max_length=460):
    normalized_body = body.lower()
    positions = [normalized_body.find(term) for term in query_terms if term]
    positions = [position for position in positions if position >= 0]
    start = max(0, min(positions) - 100) if positions else 0
    if start:
        start = normalized_body.find(" ", start)
        if start < 0:
            start = 0
    snippet = body[start : start + max_length].strip()
    if start:
        snippet = "..." + snippet
    if start + max_length < len(body):
        snippet += "..."
    return snippet


def search_documents(query, limit=4):
    query_terms = [
        term
        for term in dict.fromkeys(normalized_tokens(query))
        if term not in STOP_WORDS
    ]
    if not query_terms:
        return []
    pages = list_pages()
    if not pages:
        return []

    document_terms = [
        normalized_tokens(page["title"] + " " + page["body"]) for page in pages
    ]
    document_frequency = {
        term: sum(1 for terms in document_terms if term in set(terms))
        for term in query_terms
    }
    ranked = []
    for page, terms in zip(pages, document_terms):
        frequencies = {}
        for term in terms:
            frequencies[term] = frequencies.get(term, 0) + 1
        title_terms = set(normalized_tokens(page["title"]))
        score = 0.0
        for term in query_terms:
            frequency = frequencies.get(term, 0)
            if not frequency:
                continue
            inverse_frequency = math.log(
                1 + len(pages) / (1 + document_frequency[term])
            )
            score += (
                (frequency / (frequency + 1.2))
                * inverse_frequency
                * (2.0 if term in title_terms else 1.0)
            )
        if score:
            page["snippet"] = make_snippet(page["body"], query_terms)
            page["score"] = score
            ranked.append(page)
    ranked.sort(key=lambda page: (-page["score"], page["title"].lower()))
    return ranked[: max(1, min(int(limit), 8))]
