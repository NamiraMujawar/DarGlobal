# DarGlobal × Wasalt Property Intelligence

**Author:** Namira Mujawar  
**Project date:** 2026-11-18

A source-grounded research chatbot with a Python standard-library server, SQLite storage, a bounded public-site crawler, modular AI/PII guardrails, and optional OpenRouter integration. The app can be explored locally without an API key; common company questions receive concise, user-friendly answers, and linked sources appear separately below each answer. Configure an OpenRouter key for model-generated answers.

## Run locally (Windows / VS Code)

Python 3.9 or newer is required. No Python packages need to be installed.

Open the **DarGlobal** folder in VS Code and run these commands in its integrated **PowerShell** terminal. On this computer use `py` (the Python launcher), not `python`:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe scraper.py
.\.venv\Scripts\python.exe app.py
```

The first command creates an isolated Python environment. The second refreshes the source index (obeys `robots.txt`; up to eight pages per site). The third starts the website. Leave that terminal open, then visit **http://localhost:8000** in your browser. Press `Ctrl+C` in the server terminal to stop it. After creating `.venv` once, skip the first command on future runs.

The local `.env` file is already set up and is excluded from Git. If `OPENROUTER_API_KEY` is blank, the app uses **Source preview** mode and answers common DarGlobal and Wasalt questions from its curated knowledge base without calling an AI provider. No key, package install, or account is required for the local demo. Never share or commit your key.

To recreate the printable company briefs, run:

```powershell
.\.venv\Scripts\python.exe company_briefs.py
```

The generated PDFs are saved in `knowledge_packs/`.

For safe TypeScript and cURL request templates, see [OPENROUTER_API.md](./OPENROUTER_API.md).
The AI and privacy policy implementation is documented in [GUARDRAILS.md](./GUARDRAILS.md).

Tests are not the website. Run them separately, in a second terminal:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Every push or pull request to `main` also runs the test suite, validates the
Compose configuration, builds the Docker image, and smoke-tests its health
endpoint through GitHub Actions.

## Docker

The container includes the Python standard-library app and does not install from
`requirements.txt`. `.env` is not copied into the image and is not required.
Without an OpenRouter key the chatbot runs in its local demo mode; set
`OPENROUTER_API_KEY` in the host environment only when model-generated answers
are needed. Docker Desktop (or a compatible Docker Engine with Compose v2) is
required to build and run containers.

```powershell
docker compose build
docker compose --profile index run --rm indexer
docker compose up -d assistant
```

The one-shot indexer refreshes the public source index and stores it in the
named `assistant_data` volume shared with the app. Then open
[http://localhost:8000](http://localhost:8000). Use `docker compose logs -f assistant`
to inspect startup and `docker compose down` to stop it. The named volume keeps
the source index and chat history across container restarts. `docker compose down
-v` deletes that data.

To enable OpenRouter for the container, set the key in the same PowerShell
session before starting the assistant:

```powershell
$env:OPENROUTER_API_KEY = "YOUR_REPLACEMENT_KEY"
docker compose up -d assistant
```

Never put a real key in the Dockerfile, Compose file, source code, or a built
image. The free `openrouter/free` model is the default; model availability and
provider limits can change.

## Assignment readiness

- **Public data:** the bounded crawler indexes accessible Wasalt and other
  public pages. DarGlobal's site may return an automated verification page, so
  the chatbot also uses concise linked company summaries and secondary reports.
- **AI:** OpenRouter integration is present and defaults to `openrouter/free`;
  a valid server-side API key is required to activate model-generated answers.
- **Container:** Docker builds the app without installing Python packages or
  requiring a local `.env`. The source index and chat history use a named volume.
- **Public deployment / URL:** this project has not been deployed to a public
  host, so there is no public test URL yet. Deployment requires a hosting
  account and its credentials; a local Docker URL is not publicly reachable.

## Project layout

```text
app.py                 HTTP server, chat API, OpenRouter integration
knowledge.py           SQLite schema, storage, and lexical retrieval
scraper.py             robots-aware, bounded public-page crawler
company_briefs.py      Curated facts and printable company research briefs
guardrails.py          Input validation, PII redaction, source injection and citation checks
static/                Responsive chat UI (plain HTML, CSS, JavaScript)
knowledge_packs/       Printable, attributed DarGlobal and Wasalt research briefs
tests/                 Offline unit tests
.github/workflows/     Automated tests and Docker build checks
GUARDRAILS.md          AI safety and PII behavior, guarantees, and limitations
Dockerfile             Small, non-root Python container
docker-compose.yml     Local container configuration
requirements.txt       Documents that no third-party packages are needed
.env                   Local settings; OpenRouter key is intentionally blank
```

## API

- `GET /api/health` — server status and whether an OpenRouter key is configured.
- `GET /api/sources` — indexed source counts and last refresh times.
- `POST /api/chat/stream` — `{ "message": "...", "conversation_id": "..." }`, returning a Server-Sent Events stream with incremental text and a final answer/citations event.
- `GET /api/conversations` and `GET /api/conversations/{id}` — list or restore conversations for this browser.
- `POST /api/conversations` and `DELETE /api/conversations/{id}` — create or delete a conversation.

## Data handling and limitations

- Crawling is limited to allowlisted public HTTPS pages. It obeys each site's `robots.txt`, uses request delays and page/response caps, and does not access authenticated content.
- DarGlobal's crawler may not retrieve full page content in every environment. The knowledge base includes its public page listings, concise linked summaries of company statements, and secondary reports. A June 2026 official portfolio update described a $23 billion development portfolio across seven markets: the UAE, Saudi Arabia, Oman, Qatar, Spain, Greece, and the UK. This is the company's reported portfolio footprint, not a count of offices or completed developments.
- The index also includes the public DarGlobal Wikipedia article (CC BY-SA attribution), official Wasalt pages, selected *The National* reports, and a short summary of a DarGlobal press release republished by Zawya on 16 November 2026 about a planned Jeddah project. Full publisher articles are not copied.
- The `knowledge_packs/` PDFs are concise, original research summaries with source links, not copies of entire website pages. The briefs and chatbot present summaries as summaries and link to their references; they do not claim to contain full copies of company pages.
- DarGlobal and Wasalt answers are kept separate when the conversation changes topics. Visible source links appear below answers without inline `[S1]`-style markers. Without an OpenRouter key, the app can answer common profile, vision, project, and footprint questions from the curated index.
- Fee, refund, and cancellation details are answered only when matching public-source evidence is indexed. Otherwise, the assistant explains that the information is not available in its current sources and directs users to the relevant company or booking terms rather than guessing.
- For those questions, the assistant also links to the listed company contact channels: DarGlobal customer relations (`crm@darglobal.co.uk`, [Get in Touch](https://darglobal.co.uk/get-in-touch)) and Wasalt Support (`support@wasalt.com`, [Wasalt Support](https://support.wasalt.com/)). Verify current contact details on the official pages before sending sensitive information.
- News reports and Wikipedia can be outdated or incomplete; they are cited as secondary sources, not proof of current construction status, availability, or prices. A manually verified Companies House record supports narrow legal-registration facts.
- Conversations are retained in the local SQLite database. The application stores a hashed browser-session identifier in its conversation owner field and uses a random HttpOnly cookie to isolate browser histories. It is not an account system; clearing cookies loses access to that browser's saved history.
- User and assistant messages are PII-redacted before they are stored. When a key is configured, recent conversation context and retrieved public excerpts are sent to OpenRouter. The database is not encrypted at rest.
- Guardrails redact common emails, phone numbers, Saudi national IDs, and payment-card patterns from model-bound text. Pattern-based detection is not perfect and is not a substitute for avoiding sensitive information.
- The app is for research, not a source of guaranteed property availability, pricing, investment advice, or legal advice.
- Public content is not scraped without limits. Each source is allowlisted and bounded; copyrighted articles are reduced to short attributed fact summaries.
- This package is ready for local evaluation and container builds, not a claim of production certification. Public deployment additionally needs TLS, hosting credentials, operational monitoring, a deployment-grade WSGI server/reverse proxy, rate limiting, legal/data-governance review, and verification of source-content reuse rights.
