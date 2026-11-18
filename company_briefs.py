"""Curated company facts and lightweight PDF research briefs.

Author: Namira Mujawar | Project date: 2026-11-18
"""

import textwrap
import unicodedata
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
SNAPSHOT_DATE = "18 November 2026"
FETCHED_AT = "2026-11-18T00:00:00+00:00"

CURATED_RESEARCH_RECORDS = (
    {
        "url": (
            "https://darglobal.co.uk/press/"
            "darglobal-five-years-global-expansion-23bn-development-portfolio-future-vision"
        ),
        "title": "DarGlobal portfolio update: seven markets (15 June 2026)",
        "source": "DarGlobal official statements",
        "body": (
            "DarGlobal's official 15 June 2026 press release described a USD "
            "23 billion development portfolio across seven markets: the United "
            "Arab Emirates, Saudi Arabia, Oman, Qatar, Spain, Greece, and the "
            "United Kingdom. This is the company's stated development-portfolio "
            "footprint on that date, not a count of offices or only completed "
            "projects. The official announcement is linked below."
        ),
        "fetched_at": FETCHED_AT,
    },
    {
        "url": "https://darglobal.co.uk/about",
        "title": "DarGlobal approach and vision (official About page)",
        "source": "DarGlobal official statements",
        "body": (
            "DarGlobal's official About page describes its aim as creating "
            "homes, communities, and destinations with lasting meaning and "
            "value, working with trusted global partners. Its official vision "
            "blog also describes pioneering luxury real estate through "
            "innovation, brand collaborations, and sustainable "
            "technology. The official About page and vision blog are linked below."
        ),
        "fetched_at": FETCHED_AT,
    },
    {
        "url": (
            "https://darglobal.co.uk/blog/"
            "Our-Vision-for-the-future-Whats-Next-for-Real-Estate-Development"
        ),
        "title": "DarGlobal vision: innovation and luxury real estate",
        "source": "DarGlobal official statements",
        "body": (
            "DarGlobal's official vision blog describes using innovation, "
            "strategic brand partnerships, "
            "and sustainable technology to create distinctive luxury spaces. "
            "It references AIDA and The Astera as examples. "
            "The original blog post is linked below."
        ),
        "fetched_at": FETCHED_AT,
    },
    {
        "url": (
            "https://www.zawya.com/en/press-release/companies-news/"
            "dar-global-expands-saudi-arabia-portfolio-with-new-jeddah-development-valued-at-sar-1bln-2283558"
        ),
        "title": "DarGlobal announces planned Jeddah mixed-use development (16 November 2026)",
        "source": "Zawya",
        "body": (
            "A DarGlobal press release republished by Zawya on 16 November "
            "2026 announced plans for a new mixed-use development in Jeddah, "
            "Saudi Arabia, with an estimated gross development value of about "
            "SAR 1 billion (USD 267 million). The project name, design, and "
            "official launch date had not yet been disclosed. The announcement "
            "said the project forms part of a Saudi portfolio expansion "
            "programme. This is a reported plan, not a completed development."
        ),
        "fetched_at": FETCHED_AT,
    },
)

BRIEFS = {
    "DarGlobal_Research_Brief.pdf": (
        "DarGlobal | Company Research Brief",
        (
            "Company at a glance",
            "DarGlobal is a real-estate developer headquartered in Riyadh and listed on the London Stock Exchange, according to its Wikipedia overview. It was established in 2017 as a real-estate subsidiary of Dar Al Arkan.",
            "Reported geographic reach",
            "A DarGlobal press release dated 15 June 2026 described a USD 23 billion development portfolio across seven markets: the United Arab Emirates, Saudi Arabia, Oman, Qatar, Spain, Greece, and the United Kingdom. This is the company's reported portfolio footprint at that date; it is not necessarily a count of offices or completed projects.",
            "Vision and approach",
            "DarGlobal's official About page describes creating homes, communities, and destinations with lasting value in partnership with trusted global partners. Its official vision blog emphasizes innovation, brand collaborations, and sustainable technology in luxury real estate.",
            "Recent reported project",
            "On 16 November 2026, DarGlobal announced plans for a new mixed-use Jeddah development with an estimated value of about SAR 1 billion (USD 267 million). The project name and launch date were not yet announced. Earlier reports covered planned developments in Diriyah and a Dubai tower. Plans and announcements do not establish that construction is complete.",
            "Sources",
            "DarGlobal portfolio press release (15 Jun 2026): https://darglobal.co.uk/press/darglobal-five-years-global-expansion-23bn-development-portfolio-future-vision",
            "DarGlobal About page: https://darglobal.co.uk/about",
            "DarGlobal vision blog: https://darglobal.co.uk/blog/Our-Vision-for-the-future-Whats-Next-for-Real-Estate-Development",
            "DarGlobal Wikipedia overview (CC BY-SA): https://en.wikipedia.org/wiki/DarGlobal",
            "Jeddah project press release via Zawya (16 Nov 2026): https://www.zawya.com/en/press-release/companies-news/dar-global-expands-saudi-arabia-portfolio-with-new-jeddah-development-valued-at-sar-1bln-2283558",
            "Other selected project reports: https://www.thenationalnews.com/business/property/",
            "Prepared by Namira Mujawar | Research snapshot: 18 November 2026",
        ),
    ),
    "Wasalt_Research_Brief.pdf": (
        "Wasalt | Company Research Brief",
        (
            "Platform overview",
            "Wasalt describes itself as a Saudi-based, AI-backed real-estate platform for discovering verified properties and connecting with trusted brokers and property experts.",
            "What people can do",
            "Its public pages cover buying, selling, and renting homes; browsing projects and masterplans; daily rentals; and participating in online or hybrid real-estate auctions. The site also describes tools for brokers and property owners.",
            "How Wasalt describes its platform",
            "Wasalt presents its service as a way to make property discovery and connections easier across Saudi Arabia, with verified listings and technology-supported search.",
            "Sources",
            "Wasalt public homepage: https://wasalt.sa/en",
            "Wasalt corporate and product overview: https://wasalt.sa/en/corporate",
            "Prepared by Namira Mujawar | Research snapshot: 18 November 2026",
        ),
    ),
}


def _ascii_text(value):
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2022": "-",
        "\u00a0": " ",
    }
    for original, replacement in replacements.items():
        value = value.replace(original, replacement)
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def _wrap_content(title, paragraphs, width=84):
    lines = [title, "Research snapshot: " + SNAPSHOT_DATE, ""]
    for paragraph in paragraphs:
        if paragraph in {"Company at a glance", "Reported geographic reach",
                         "Vision and approach", "Recent reported project",
                         "Platform overview", "What people can do",
                         "How Wasalt describes its platform", "Sources"}:
            lines.extend([paragraph.upper(), ""])
        else:
            lines.extend(textwrap.wrap(_ascii_text(paragraph), width=width) or [""])
            lines.append("")
    return lines


def _pdf_escape(value):
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _page_stream(lines):
    commands = ["BT", "/F1 18 Tf", "50 790 Td", "({0}) Tj".format(_pdf_escape(lines[0]))]
    commands.extend(["/F1 10 Tf", "0 -26 Td"])
    for index, line in enumerate(lines[1:]):
        if index:
            commands.append("0 -14 Td")
        commands.append("({0}) Tj".format(_pdf_escape(line)))
    commands.append("ET")
    return ("\n".join(commands) + "\n").encode("ascii")


def _make_pdf(title, paragraphs):
    lines = _wrap_content(title, paragraphs)
    lines_per_page = 51
    page_lines = [
        [lines[0]] + lines[start : start + lines_per_page]
        for start in range(1, len(lines), lines_per_page)
    ]
    page_ids = [4 + index * 2 for index in range(len(page_lines))]
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            "<< /Type /Pages /Kids [{0}] /Count {1} >>".format(
                " ".join("{0} 0 R".format(page_id) for page_id in page_ids),
                len(page_ids),
            )
        ).encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]

    for index, content_lines in enumerate(page_lines):
        page_id = page_ids[index]
        content_id = page_id + 1
        stream = _page_stream(content_lines)
        objects.extend(
            [
                (
                    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                    "/Resources << /Font << /F1 3 0 R >> >> "
                    "/Contents {0} 0 R >>".format(content_id)
                ).encode("ascii"),
                (
                    "<< /Length {0} >>\nstream\n".format(len(stream)).encode("ascii")
                    + stream
                    + b"endstream"
                ),
            ]
        )

    info_id = len(objects) + 1
    objects.append(
        b"<< /Title (" + _pdf_escape(_ascii_text(title)).encode("ascii")
        + b") /Author (Namira Mujawar) /Creator (DarGlobal research brief) >>"
    )
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend("{0} 0 obj\n".format(index).encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend("xref\n0 {0}\n".format(len(objects) + 1).encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend("{0:010d} 00000 n \n".format(offset).encode("ascii"))
    pdf.extend(
        (
            "trailer\n<< /Size {0} /Root 1 0 R /Info {1} 0 R >>\n"
            "startxref\n{2}\n%%EOF\n"
        ).format(len(objects) + 1, info_id, xref_offset).encode("ascii")
    )
    return bytes(pdf)


def generate_pdfs(output_dir=None):
    destination = Path(output_dir) if output_dir else APP_DIR / "knowledge_packs"
    destination.mkdir(parents=True, exist_ok=True)
    written = []
    for filename, (title, paragraphs) in BRIEFS.items():
        path = destination / filename
        path.write_bytes(_make_pdf(title, paragraphs))
        written.append(path)
    return written


if __name__ == "__main__":
    for output_path in generate_pdfs():
        print("Created {0}".format(output_path))
