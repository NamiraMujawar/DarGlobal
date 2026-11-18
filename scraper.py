"""Polite, bounded crawler for public DarGlobal and Wasalt pages.

Author: Namira Mujawar | Project date: 2026-11-18
"""

import gzip
import io
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.robotparser
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser

from knowledge import (
    initialize_database,
    record_source_status,
    retain_source_pages,
    save_page,
)


USER_AGENT = "DarGlobalWasaltResearchBot/1.0 (+local research assistant)"
MAX_PAGES_PER_SITE = 8
MAX_RESPONSE_BYTES = 2_000_000
MAX_DECOMPRESSED_BYTES = 5_000_000
MAX_SITEMAPS_PER_SITE = 6
MAX_SITEMAP_URLS = 500
MIN_REQUEST_INTERVAL = 1.0
SITES = (
    {
        "name": "DarGlobal",
        "origin": "https://darglobal.co.uk",
        "hosts": {"www.darglobal.co.uk", "darglobal.co.uk"},
        "seeds": ["https://darglobal.co.uk/"],
        "priority": ("project", "development", "destination", "about", "company", "news"),
        "sitemap_metadata": True,
        "blocked": (
            "login",
            "account",
            "search",
            "sale",
            "rent",
            "privacy",
            "policy",
            "terms",
            "legal",
        ),
    },
    {
        "name": "Wasalt",
        "origin": "https://wasalt.sa",
        "hosts": {"wasalt.sa", "www.wasalt.sa", "cdn.wasalt.sa"},
        "seeds": ["https://wasalt.sa/", "https://wasalt.sa/en/corporate"],
        "priority": (
            "about",
            "faq",
            "project",
            "service",
            "company",
            "corporate",
            "product",
            "business",
            "auction",
            "masterplan",
            "من نحن",
            "أسئلة",
            "مشاريع",
            "عن وصلت",
        ),
        "blocked": (
            "login",
            "account",
            "search",
            "sale/search",
            "rent/search",
            "sale",
            "rent",
            "للبيع",
            "للايجار",
            "للإيجار",
            "privacy",
            "policy",
            "terms",
            "legal",
        ),
        "sitemap_allow": ("static_sitemap", "product_sitemap", "category_sitemap"),
    },
    {
        "name": "Wikipedia",
        "origin": "https://en.wikipedia.org",
        "hosts": {"en.wikipedia.org"},
        "seeds": ["https://en.wikipedia.org/wiki/DarGlobal"],
        "priority": ("darglobal",),
        "blocked": ("special:", "category:", "talk:", "file:", "template:"),
        "fixed_pages_only": True,
    },
    {
        "name": "The National",
        "origin": "https://www.thenationalnews.com",
        "hosts": {"www.thenationalnews.com"},
        "seeds": [
            "https://www.thenationalnews.com/business/property/2026/08/06/dubais-1bn-trump-tower-moves-forward-as-key-contract-issued/",
            "https://www.thenationalnews.com/business/property/2026/01/11/dar-global-and-trump-organisation-launch-luxury-project-in-riyadhs-diriyah/",
            "https://www.thenationalnews.com/business/property/2025/09/30/trump-tower-to-be-launched-in-jeddah/",
        ],
        "priority": ("darglobal", "dar-global", "trump-tower"),
        "blocked": ("/article/", "/blogs/", "/signin", "/search"),
        "fixed_pages_only": True,
        "summary_only": True,
        "summaries": {
            "https://www.thenationalnews.com/business/property/2026/08/06/dubais-1bn-trump-tower-moves-forward-as-key-contract-issued": (
                "The National reported on 6 August 2026 that DarGlobal awarded "
                "Gulf Asia Contracting a contract for the podium of its planned "
                "Trump International Hotel and Tower on Sheikh Zayed Road, Dubai. "
                "The report describes an 80-floor tower with residences, a hotel "
                "and a private members' club. This is a reported project plan, "
                "not confirmation of completion."
            ),
            "https://www.thenationalnews.com/business/property/2026/01/11/dar-global-and-trump-organisation-launch-luxury-project-in-riyadhs-diriyah": (
                "The National reported on 11 January 2026 that DarGlobal and the "
                "Trump Organization announced a planned luxury development in "
                "Wadi Safar, Diriyah, Riyadh, with a golf course, hotel and "
                "residences. The article also describes Trump Plaza Jeddah and "
                "mentions projects in Oman, the UAE and Qatar. Check current "
                "company releases for project status."
            ),
            "https://www.thenationalnews.com/business/property/2025/09/30/trump-tower-to-be-launched-in-jeddah": (
                "The National reported on 30 September 2025 that DarGlobal "
                "announced Trump Plaza Jeddah, a planned mixed-use development "
                "with residences, serviced apartments and office space. The "
                "article said a project timeline had not been disclosed."
            ),
        },
    },
)
LAST_REQUEST_AT = {}


def log(message):
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    print(str(message).encode(encoding, errors="replace").decode(encoding))


def rate_limit(host):
    previous = LAST_REQUEST_AT.get(host, 0)
    wait = MIN_REQUEST_INTERVAL - (time.monotonic() - previous)
    if wait > 0:
        time.sleep(wait)
    LAST_REQUEST_AT[host] = time.monotonic()


def request_url(url, host_allowlist, timeout=12):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in host_allowlist:
        raise ValueError("Refusing non-HTTPS or off-site URL: {0}".format(url))
    rate_limit(parsed.hostname)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xml,text/plain;q=0.9,*/*;q=0.2",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        final_url = response.geturl()
        final_host = urllib.parse.urlparse(final_url).hostname
        if final_host not in host_allowlist or not final_url.startswith("https://"):
            raise ValueError("Stopped an off-site redirect to {0}".format(final_url))
        content_type = response.headers.get("Content-Type", "").lower()
        is_gzip = parsed.path.lower().endswith(".gz") or any(
            kind in content_type for kind in ("application/gzip", "application/x-gzip")
        )
        if not is_gzip and not any(
            kind in content_type for kind in ("text/html", "xml", "text/plain")
        ):
            raise ValueError("Skipped non-text response from {0}".format(final_url))
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Response exceeds the 2 MB crawl limit.")
        if is_gzip:
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as archive:
                raw = archive.read(MAX_DECOMPRESSED_BYTES + 1)
            if len(raw) > MAX_DECOMPRESSED_BYTES:
                raise ValueError("Uncompressed response exceeds the 5 MB crawl limit.")
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace"), final_url


def load_robots(site):
    robots_url = site["origin"].rstrip("/") + "/robots.txt"
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        content, _ = request_url(robots_url, site["hosts"])
    except urllib.error.HTTPError as error:
        if error.code == 404:
            parser.parse([])
            return parser, []
        raise RuntimeError("Could not read robots.txt (HTTP {0}); skipping site.".format(
            error.code
        )) from None
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise RuntimeError("Could not read robots.txt ({0}); skipping site.".format(
            error
        )) from None
    parser.parse(content.splitlines())
    return parser, content.splitlines()


class PageParser(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "svg", "header", "nav", "footer", "form"}
    BREAK_TAGS = {"h1", "h2", "h3", "h4", "p", "li", "article", "section", "br"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_stack = []
        self.parts = []
        self.links = []
        self.title_parts = []
        self.in_title = False
        self.active_link_index = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.links.append((attrs["href"], ""))
            self.active_link_index = len(self.links) - 1
        if self.skip_stack:
            self.skip_stack.append(tag)
            return
        if tag in self.SKIP_TAGS:
            self.skip_stack.append(tag)
            return
        if tag == "title":
            self.in_title = True
        if tag in self.BREAK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "a":
            self.active_link_index = None
        if self.skip_stack:
            for index in range(len(self.skip_stack) - 1, -1, -1):
                if self.skip_stack[index] == tag:
                    del self.skip_stack[index:]
                    break
            return
        if tag == "title":
            self.in_title = False
        if tag in self.BREAK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        cleaned = re.sub(r"\s+", " ", data).strip()
        if not cleaned:
            return
        if self.in_title:
            self.title_parts.append(cleaned)
        elif self.active_link_index is not None:
            href, label = self.links[self.active_link_index]
            self.links[self.active_link_index] = (
                href,
                (label + " " + cleaned).strip(),
            )
            if not self.skip_stack:
                self.parts.append(cleaned)
        elif not self.skip_stack:
            self.parts.append(cleaned)

    @property
    def title(self):
        return " ".join(self.title_parts).strip()

    @property
    def text(self):
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()


def canonical_url(candidate, current_url, site):
    absolute = urllib.parse.urljoin(current_url, candidate)
    parsed = urllib.parse.urlparse(absolute)
    if parsed.scheme != "https" or parsed.hostname not in site["hosts"]:
        return None
    if parsed.query or parsed.fragment:
        parsed = parsed._replace(query="", fragment="")
    path = urllib.parse.unquote(parsed.path or "/")
    if re.search(r"\.(?:jpg|jpeg|png|gif|webp|svg|pdf|zip|xml)$", path, re.I):
        return None
    path = urllib.parse.quote(path.rstrip("/") or "/", safe="/%:@!$&'()*+,;=-._~")
    return urllib.parse.urlunparse(parsed._replace(path=path))


def link_priority(url, site, label=""):
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path).lower()
    searchable = path + " " + label.lower()
    if any(fragment in path for fragment in site["blocked"]):
        return -1
    if path == "/":
        return 0
    for index, keyword in enumerate(site["priority"], start=1):
        if keyword in searchable:
            return index
    return 100


def read_sitemaps(robot_lines, site):
    urls = []
    sitemap_entries = []
    sitemap_count = 0
    for line in robot_lines:
        if line.lower().startswith("sitemap:"):
            sitemap_url = line.split(":", 1)[1].strip()
            sitemap_path = urllib.parse.urlparse(sitemap_url).path.lower()
            allowed_paths = site.get("sitemap_allow", ())
            if allowed_paths and not any(item in sitemap_path for item in allowed_paths):
                continue
            if not any(sitemap_path.endswith(ext) for ext in (".xml", ".xml.gz")):
                continue
            sitemap_count += 1
            if sitemap_count > MAX_SITEMAPS_PER_SITE:
                break
            try:
                xml_content, _ = request_url(sitemap_url, site["hosts"])
                root = ET.fromstring(xml_content)
                for element in root.iter():
                    if not element.tag.endswith("url"):
                        continue
                    fields = {}
                    for child in element:
                        if child.tag.endswith("loc") or child.tag.endswith("lastmod") or child.tag.endswith("priority"):
                            fields[child.tag.rsplit("}", 1)[-1]] = child.text or ""
                    canonical = canonical_url(fields.get("loc", "").strip(), sitemap_url, site)
                    if not canonical:
                        continue
                    try:
                        priority = float(fields.get("priority", "0"))
                    except ValueError:
                        priority = 0.0
                    path = urllib.parse.unquote(
                        urllib.parse.urlparse(canonical).path
                    ).lower()
                    if (
                        site.get("sitemap_metadata")
                        and priority >= 0.8
                        and link_priority(canonical, site) >= 0
                    ):
                        title = path.rstrip("/").rsplit("/", 1)[-1]
                        title = re.sub(r"[-_]+", " ", title).strip().title()
                        if title:
                            sitemap_entries.append(
                                (priority, title, canonical, fields.get("lastmod", ""))
                            )
                    if (
                        (link_priority(canonical, site) < 100 or priority >= 0.8)
                        and link_priority(canonical, site) >= 0
                        and canonical not in urls
                    ):
                        urls.append(canonical)
                        if len(urls) >= MAX_SITEMAP_URLS:
                            break
                if len(urls) >= MAX_SITEMAP_URLS:
                    break
            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                TimeoutError,
                ValueError,
                OSError,
                ET.ParseError,
            ):
                continue
    sitemap_entries.sort(key=lambda item: (-item[0], item[1].lower()))
    metadata = ""
    if sitemap_entries:
        rows = [
            "DarGlobal's public site lists these pages.",
            "A listing does not necessarily mean a project is currently available.",
        ]
        for _, title, url, lastmod in sitemap_entries[:60]:
            rows.append(
                "- {0} | URL: {1} | Sitemap last modified: {2}".format(
                    title, url, lastmod or "not provided"
                )
            )
        metadata = "\n".join(rows)
    return urls, metadata


def crawl_site(site):
    log("[{0}] Reading robots.txt...".format(site["name"]))
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record_source_status(
        site["name"], "checking", "Checking public crawl permissions.", checked_at
    )
    try:
        robots, robot_lines = load_robots(site)
    except RuntimeError as error:
        log("[{0}] {1}".format(site["name"], error))
        record_source_status(
            site["name"],
            "blocked",
            "Could not verify crawl permission; this source was skipped.",
            checked_at,
        )
        return 0

    sitemap_urls, sitemap_metadata = read_sitemaps(robot_lines, site)
    candidates = []
    for url in site["seeds"] + sitemap_urls:
        canonical = canonical_url(url, site["origin"], site)
        if (
            canonical
            and canonical not in candidates
            and link_priority(canonical, site) >= 0
        ):
            candidates.append(canonical)
    queue = sorted(candidates, key=lambda url: (link_priority(url, site), url))
    queued = set(queue)
    visited = set()
    saved = 0
    saved_urls = []
    html_saved = 0
    blocked_detected = False
    robots_disallowed = False

    if sitemap_metadata:
        sitemap_url = site["origin"].rstrip("/") + "/sitemap.xml"
        fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if save_page(
            sitemap_url,
            "{0} public pages".format(site["name"]),
            site["name"],
            sitemap_metadata,
            fetched_at,
        ):
            saved += 1
            saved_urls.append(sitemap_url)
            log("[{0}] Indexed public sitemap metadata.".format(site["name"]))

    while queue and len(visited) < MAX_PAGES_PER_SITE:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        if not robots.can_fetch(USER_AGENT, url):
            log("[{0}] Robots disallows {1}".format(site["name"], url))
            robots_disallowed = True
            continue
        try:
            html, final_url = request_url(url, site["hosts"])
        except urllib.error.HTTPError as error:
            log("[{0}] HTTP {1}: {2}".format(site["name"], error.code, url))
            continue
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            log("[{0}] Skipped {1}: {2}".format(site["name"], url, error))
            continue

        if "incapsula" in html.lower() or "noindex,nofollow" in html.lower():
            log("[{0}] Could not collect page: {1}".format(site["name"], url))
            blocked_detected = True
            break
        content_type = html.lstrip().lower()
        if content_type.startswith("<?xml") or "<html" not in content_type[:1000]:
            continue
        parser = PageParser()
        parser.feed(html)
        body = parser.text
        if len(body) < 80:
            continue
        title = parser.title or urllib.parse.urlparse(final_url).path or site["name"]
        if site.get("summary_only"):
            body = site.get("summaries", {}).get(final_url.rstrip("/"), "")
            if not body:
                continue
        fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if save_page(final_url, title, site["name"], body, fetched_at):
            saved += 1
            html_saved += 1
            saved_urls.append(final_url)
            log("[{0}] Indexed: {1}".format(site["name"], title[:90]))

        if site.get("fixed_pages_only"):
            continue
        links = []
        for href, label in parser.links:
            candidate = canonical_url(href, final_url, site)
            if (
                candidate
                and candidate not in queued
                and candidate not in visited
                and link_priority(candidate, site, label) >= 0
            ):
                priority = link_priority(candidate, site, label)
                links.append((priority, candidate))
                queued.add(candidate)
        links.sort(key=lambda item: (item[0], item[1]))
        for _, candidate in links:
            if len(queue) + len(visited) >= MAX_PAGES_PER_SITE:
                break
            queue.append(candidate)

    log("[{0}] Indexed {1} page(s).".format(site["name"], saved))
    retain_source_pages(site["name"], saved_urls)
    if html_saved:
        status = "available"
        message = "Public page content was indexed successfully."
    elif sitemap_metadata:
        status = "metadata_only"
        message = (
            "Public page listings are indexed; project summaries come from linked sources."
        )
    elif blocked_detected or robots_disallowed:
        status = "blocked"
        message = "No page content was available during this refresh."
    else:
        status = "unavailable"
        message = "No indexable public pages were retrieved."
    record_source_status(site["name"], status, message, checked_at)
    return saved


def main():
    initialize_database()
    total = sum(crawl_site(site) for site in SITES)
    log("Refresh complete: {0} source document(s) indexed.".format(total))


if __name__ == "__main__":
    main()
