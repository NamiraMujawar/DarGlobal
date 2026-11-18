# AI and PII guardrails

**Author:** Namira Mujawar · **Project date:** 2026-11-18

This project uses deterministic controls in [`guardrails.py`](./guardrails.py)
before and after optional OpenRouter calls.

## Request and privacy handling

- The API accepts a non-empty text question up to 2,000 characters, rejects
  unsupported control characters, and caps the complete JSON request body.
- Conversations are retained in a local SQLite database. User and assistant
  messages are PII-redacted before persistence; database files are not encrypted
  at rest. The app does not log request bodies.
- Before sending text to the model, pattern-based checks redact email addresses,
  phone-like numbers, Saudi national-ID-shaped numbers, and Luhn-valid payment
  card numbers, plus recognized OpenRouter API keys, from questions and retrieved
  excerpts.
- Requests to reveal API keys, credentials, or hidden prompts receive a
  deterministic refusal without being sent to the model. The OpenRouter key is
  read by the server, is never included in browser responses, and the health
  endpoint reports only whether a key is configured.
- The local source-preview mode also redacts common PII from excerpts.
- When a key is configured, the question and selected public excerpts are sent
  to OpenRouter. Review OpenRouter's current privacy, retention, and model
  provider terms before using real personal or confidential data.

## Retrieval and model behavior

- The system policy treats retrieved page text as untrusted data and instructs
  the model not to follow instructions contained in source pages.
- General-answer instructions also prohibit revealing credentials, environment
  values, or hidden instructions. Credential-request routing enforces this
  locally before any model call.
- The chatbot is instructed to answer only from retrieved text, avoid
  unsupported real-estate, pricing, investment, or legal claims, and cite the
  supplied source IDs internally. Source links are displayed below the answer
  without source-number markers in the conversational text.
- Output validation rejects empty/oversized answers and unknown or missing
  source citations. If that check fails, the app falls back to redacted source
  excerpts rather than showing the unchecked model output.
- OpenRouter output streams with a rolling redaction buffer. The completed
  answer is validated and redacted before it is saved; the final stream event
  replaces provisional text if validation or redaction changes it. Citation
  markers are removed from the user-facing answer after validation.
- If no relevant pages match, the app explains the source/index limitation and
  does not send an unsupported question to the model.
- Source links are restricted at crawl time to configured HTTPS hosts; crawl
  limits and `robots.txt` checks remain in force.

## Human review and limits

Regex-based PII detection is imperfect and can miss names, addresses, less common
identity formats, or context-sensitive sensitive information. Redaction is a
best-effort safeguard, not a guarantee or substitute for not entering sensitive
data. Model instructions and citation checks reduce risk but do not prove every
sentence is true. Verify cited records and consult qualified professionals for
legal, financial, and property decisions.

DarGlobal information is presented through linked company summaries and public
project reports. Sitemap entries, when available, are useful for discovering
public page paths but do not confirm a development's details or availability.
The crawler respects the site's published crawl rules and does not attempt to
bypass automated access controls. The included Companies House entry is a
manually reviewed, narrow official record for registration and SIC classifications.
Public visibility alone is not blanket permission to crawl or reuse content.
