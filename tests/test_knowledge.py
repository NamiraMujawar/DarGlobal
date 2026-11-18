"""Tests for SQLite retrieval and public-source crawling.

Author: Namira Mujawar | Project date: 2026-11-18
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import knowledge
from scraper import (
    PageParser,
    SITES,
    canonical_url,
    crawl_site,
    link_priority,
    read_sitemaps,
)


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path_patch = patch.dict(os.environ, {"DATA_DIR": self.temp_dir.name})
        self.path_patch.start()
        knowledge.initialize_database()

    def tearDown(self):
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def test_search_ranks_title_match_and_returns_citation_fields(self):
        knowledge.save_page(
            "https://wasalt.sa/about-us",
            "About Wasalt",
            "Wasalt",
            "Wasalt is a Saudi real estate platform for property discovery and services.",
            "2026-01-01T00:00:00+00:00",
        )
        knowledge.save_page(
            "https://www.darglobal.co.uk/projects",
            "International developments",
            "DarGlobal",
            "A property developer with international real estate projects.",
            "2026-01-01T00:00:00+00:00",
        )

        results = knowledge.search_documents("Wasalt platform", limit=2)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "Wasalt")
        self.assertIn("snippet", results[0])

    def test_search_returns_no_unrelated_pages(self):
        knowledge.save_page(
            "https://wasalt.sa/about-us",
            "About Wasalt",
            "Wasalt",
            "A Saudi real estate platform.",
            "2026-01-01T00:00:00+00:00",
        )
        self.assertEqual(knowledge.search_documents("volcano astronomy"), [])

    def test_refresh_retains_only_current_pages_for_that_source(self):
        knowledge.save_page(
            "https://wasalt.sa/old",
            "Old page",
            "Wasalt",
            "Old public page.",
            "2026-01-01T00:00:00+00:00",
        )
        knowledge.save_page(
            "https://wasalt.sa/current",
            "Current page",
            "Wasalt",
            "Current public page.",
            "2026-01-02T00:00:00+00:00",
        )
        knowledge.save_page(
            "https://www.darglobal.co.uk/current",
            "DarGlobal page",
            "DarGlobal",
            "Separate source page.",
            "2026-01-02T00:00:00+00:00",
        )

        knowledge.retain_source_pages("Wasalt", ["https://wasalt.sa/current"])

        urls = {page["url"] for page in knowledge.list_pages()}
        self.assertIn("https://wasalt.sa/current", urls)
        self.assertNotIn("https://wasalt.sa/old", urls)
        self.assertIn("https://www.darglobal.co.uk/current", urls)

    def test_arabic_search_ignores_diacritics(self):
        knowledge.save_page(
            "https://wasalt.sa/ar",
            "وصلت",
            "Wasalt",
            "وصلت منصة عقارية سعودية لاكتشاف العقارات.",
            "2026-01-01T00:00:00+00:00",
        )
        self.assertEqual(len(knowledge.search_documents("مَنْصَّة عقارية")), 1)

    def test_search_ignores_question_filler_words(self):
        knowledge.save_page(
            "https://wasalt.sa/about-us",
            "About Wasalt",
            "Wasalt",
            "Wasalt offers property discovery and real estate services.",
            "2026-01-01T00:00:00+00:00",
        )
        self.assertEqual(
            knowledge.search_documents("What does Wasalt offer?")[0]["url"],
            "https://wasalt.sa/about-us",
        )

    def test_source_status_lists_blocked_and_available_sources(self):
        knowledge.record_source_status(
            "DarGlobal",
            "blocked",
            "Automated access blocked.",
            "2026-01-03T00:00:00+00:00",
        )
        knowledge.record_source_status(
            "Wasalt",
            "available",
            "Public pages indexed.",
            "2026-01-03T00:00:00+00:00",
        )

        sources = {item["source"]: item for item in knowledge.source_list()}

        self.assertEqual(sources["DarGlobal"]["status"], "blocked")
        self.assertEqual(sources["DarGlobal"]["page_count"], 0)
        self.assertEqual(sources["Wasalt"]["status"], "available")
        self.assertEqual(sources["Wasalt"]["homepage"], "https://wasalt.sa/")

    def test_public_source_list_omits_internal_crawl_diagnostics(self):
        knowledge.record_source_status(
            "DarGlobal",
            "blocked",
            "Automated access blocked.",
            "2026-01-03T00:00:00+00:00",
        )

        sources = knowledge.public_source_list()
        names = {item["source"] for item in sources}
        dar_global = next(
            item for item in sources
            if item["source"] == "DarGlobal official statements"
        )

        self.assertNotIn("DarGlobal", names)
        self.assertEqual(dar_global["status"], "curated")
        self.assertNotIn("message", dar_global)
        self.assertNotIn("blocked", repr(sources).lower())

    def test_darglobal_question_retrieves_curated_company_register_fact(self):
        knowledge.initialize_database()

        results = knowledge.search_documents("DarGlobal Companies House company number", limit=8)

        company_record = next(item for item in results if item["source"] == "Companies House")
        self.assertIn("public limited company", company_record["snippet"].lower())
        self.assertEqual(
            company_record["url"],
            "https://find-and-update.company-information.service.gov.uk/company/14388348",
        )

    def test_initialization_indexes_curated_darglobal_market_update(self):
        results = knowledge.search_documents(
            "DarGlobal portfolio across how many countries markets", limit=8
        )

        portfolio_record = next(
            item
            for item in results
            if item["source"] == "DarGlobal official statements"
            and "seven markets" in item["body"].lower()
        )
        self.assertIn("United Kingdom", portfolio_record["body"])
        statuses = {item["source"]: item for item in knowledge.source_list()}
        self.assertEqual(statuses["DarGlobal official statements"]["status"], "curated")


class ScraperTests(unittest.TestCase):
    def test_news_crawl_keeps_short_summaries_not_copied_article_text(self):
        class PermissiveRobots:
            @staticmethod
            def can_fetch(user_agent, url):
                return True

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {"DATA_DIR": temp_dir}):
                knowledge.initialize_database()
                site = next(site for site in SITES if site["name"] == "The National")
                article_html = (
                    "<html><head><title>DarGlobal project report</title></head>"
                    "<body><main><h1>Latest DarGlobal project</h1><p>"
                    + ("Copyrighted original article wording. " * 8)
                    + "</p></main></body></html>"
                )
                with patch("scraper.load_robots", return_value=(PermissiveRobots(), [])):
                    with patch("scraper.read_sitemaps", return_value=([], "")):
                        with patch("scraper.rate_limit"):
                            with patch(
                                "scraper.request_url",
                                side_effect=lambda url, hosts: (article_html, url),
                            ):
                                count = crawl_site(site)

                national_pages = [
                    page for page in knowledge.list_pages()
                    if page["source"] == "The National"
                ]

        self.assertEqual(count, 3)
        self.assertEqual(len(national_pages), 3)
        self.assertTrue(all("The National reported" in page["body"] for page in national_pages))
        self.assertTrue(
            all("Copyrighted original article wording" not in page["body"]
                for page in national_pages)
        )

    def test_parser_extracts_content_and_ignores_navigation_and_scripts(self):
        parser = PageParser()
        parser.feed(
            "<html><head><title>About Wasalt</title></head>"
            '<body><nav>Menu<a href="/about-us">About</a></nav><main><h1>Property services</h1>'
            "<p>Discover homes and trusted real estate experts.</p>"
            "<script>secret()</script></main></body></html>"
        )
        self.assertEqual(parser.title, "About Wasalt")
        self.assertIn("Property services", parser.text)
        self.assertNotIn("Menu", parser.text)
        self.assertNotIn("secret", parser.text)
        self.assertIn(("/about-us", "About"), parser.links)

    def test_canonical_url_rejects_external_hosts_and_query_parameters(self):
        site = {"hosts": {"wasalt.sa"}}
        self.assertEqual(
            canonical_url("/about-us?campaign=x", "https://wasalt.sa/", site),
            "https://wasalt.sa/about-us",
        )
        self.assertIsNone(
            canonical_url("https://example.com/", "https://wasalt.sa/", site)
        )

    def test_canonical_url_percent_encodes_arabic_paths(self):
        site = {"hosts": {"wasalt.sa"}}
        result = canonical_url("/من-نحن", "https://wasalt.sa/", site)
        self.assertIn("%D9", result)

    def test_link_priority_drops_listing_search_pages(self):
        site = {
            "priority": ("about", "project"),
            "blocked": ("sale/search", "sale", "rent", "للبيع"),
        }
        self.assertEqual(link_priority("https://wasalt.sa/about-us", site), 1)
        self.assertEqual(link_priority("https://wasalt.sa/sale/search", site), -1)
        self.assertEqual(
            link_priority("https://wasalt.sa/apartments-for-rent", site), -1
        )
        self.assertEqual(
            link_priority(
                "https://wasalt.sa/%D9%81%D9%84%D9%84-%D9%84%D9%84%D8%A8%D9%8A%D8%B9",
                site,
            ),
            -1,
        )

    def test_reads_allowed_darglobal_sitemap_metadata(self):
        site = {
            "hosts": {"darglobal.co.uk"},
            "priority": ("project",),
            "blocked": ("privacy",),
            "sitemap_metadata": True,
        }
        sitemap = (
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            "<url><loc>https://darglobal.co.uk/</loc>"
            "<lastmod>2026-11-10</lastmod><priority>0.7</priority></url>"
            "<url><loc>https://darglobal.co.uk/aida-coastal-villas</loc>"
            "<lastmod>2026-11-10</lastmod><priority>0.8</priority></url>"
            "<url><loc>https://darglobal.co.uk/privacy-policy</loc>"
            "<priority>0.9</priority></url></urlset>"
        )
        with patch(
            "scraper.request_url",
            return_value=(sitemap, "https://darglobal.co.uk/sitemap.xml"),
        ):
            urls, metadata = read_sitemaps(
                ["Sitemap: https://darglobal.co.uk/sitemap.xml"],
                site,
            )

        self.assertIn("https://darglobal.co.uk/aida-coastal-villas", urls)
        self.assertIn("Aida Coastal Villas", metadata)
        self.assertIn("does not necessarily mean", metadata)
        self.assertNotIn("retrieved", metadata.lower())
        self.assertNotIn("blocked", metadata.lower())
        self.assertNotIn("privacy-policy", metadata)


if __name__ == "__main__":
    unittest.main()
