"""Lightweight deterministic intent routing for the research assistant.

Author: Namira Mujawar | Project date: 2026-11-18
"""

import re
from datetime import datetime, timedelta, timezone


_NORMALIZE = re.compile(r"[^\w\s]+", flags=re.UNICODE)
_PROPERTY_TERMS = {
    "apartment",
    "apartments",
    "buy",
    "darglobal",
    "dar global",
    "development",
    "developments",
    "investment",
    "listing",
    "listings",
    "property",
    "properties",
    "real estate",
    "rent",
    "sale",
    "sell",
    "villa",
    "villas",
    "wasalt",
    "وصلت",
    "دارجلوبال",
}
_GREETING_PATTERNS = (
    re.compile(r"^(?:hi|hello|hey|hiya|salam|assalamu alaikum)(?: there)?$", re.I),
    re.compile(r"^(?:good morning|good afternoon|good evening)$", re.I),
)
_THANKS_PATTERNS = re.compile(r"^(?:thanks|thank you|thx|cheers)$", re.I)
_DUBAI_CLOCK_PATTERN = re.compile(
    r"\b(?:time|clock)\b.*\b(?:dubai|uae|united arab emirates)\b|"
    r"\b(?:dubai|uae|united arab emirates)\b.*\b(?:time|clock)\b",
    re.I,
)
_CLOCK_PATTERN = re.compile(r"\b(?:time|clock)\b", re.I)
_DATE_PATTERN = re.compile(
    r"\b(?:today s date|current date|date today|what date is it|what is the date|"
    r"what s the date|today s day|what day is it)\b",
    re.I,
)
_HELP_PATTERN = re.compile(r"^(?:help|what can you do|how can you help)\??$", re.I)
_CREDENTIAL_TERMS_PATTERN = re.compile(
    r"\b(?:api\s+key|openrouter\s+key|secret(?:\s+(?:key|token))?|"
    r"screate\s+key|credentials?|passwords?|access\s+tokens?|private\s+keys?|"
    r"auth(?:entication)?\s+tokens?|system\s+prompts?|hidden\s+prompts?|"
    r"internal\s+instructions?)\b",
    re.I,
)
_CREDENTIAL_DISCLOSURE_PATTERN = re.compile(
    r"\b(?:give|show|tell|reveal|share|send|print|display|provide|disclose|"
    r"expose|extract|dump|read|get|see|what\s+(?:is|s))\b",
    re.I,
)
_CHATBOT_CONTEXT_PATTERN = re.compile(
    r"\b(?:chatbot|assistant|application|app|system|openrouter)\b", re.I
)
_GUARDRAIL_QUESTION_PATTERN = re.compile(
    r"\b(?:what|which|how|explain|describe|outline|tell me about)\b.{0,80}"
    r"\b(?:guardrails?|safeguards?|ai compliance|privacy protections?)\b|"
    r"\b(?:guardrails?|safeguards?|ai compliance|privacy protections?)\b.{0,80}"
    r"\b(?:written|implemented|use|work|configured)\b",
    re.I,
)
_DAR_GLOBAL_NAME_PATTERN = re.compile(r"\bdar(?:k)?\s*global(?:e)?\b", re.I)
_DAR_GLOBAL_TYPO_PATTERN = re.compile(r"\bdar\s*gloable\b", re.I)
_DAR_GLOBAL_ALIAS_PATTERN = re.compile(
    r"\bglobal(?:e)?\b.*\b(?:countr\w*|operat\w*)\b|"
    r"\b(?:countr\w*|operat\w*)\b.*\bglobal(?:e)?\b",
    re.I,
)
_POLICY_PATTERN = re.compile(
    r"\b(?:fee|fees|refund|refunds|refundable|cancell?ation|cancellations|"
    r"payment|deposit|pricing|price|charge|charges|commission|commissions|"
    r"terms and conditions|policy|policies)\b",
    re.I,
)
_POLICY_TOPIC_PATTERNS = (
    ("fee", re.compile(r"\b(?:fees?|pricing|prices?|charges?|commissions?)\b", re.I)),
    ("refund", re.compile(r"\brefund\w*\b", re.I)),
    ("cancellation", re.compile(r"\bcancell?\w*\b", re.I)),
    ("payment", re.compile(r"\b(?:payments?|installments?|instalments?)\b", re.I)),
    ("deposit", re.compile(r"\b(?:deposits?|booking fees?)\b", re.I)),
)


def is_darglobal_question(question):
    return bool(
        _DAR_GLOBAL_NAME_PATTERN.search(question)
        or _DAR_GLOBAL_TYPO_PATTERN.search(question)
        or _DAR_GLOBAL_ALIAS_PATTERN.search(question)
    )


def has_policy_terms(text):
    return bool(_POLICY_PATTERN.search(text))


def is_credential_request(text):
    """Recognize requests or questions about revealing chatbot credentials."""
    if not _CREDENTIAL_TERMS_PATTERN.search(text):
        return False
    return bool(
        _CREDENTIAL_DISCLOSURE_PATTERN.search(text)
        or _CHATBOT_CONTEXT_PATTERN.search(text)
    )


def is_guardrail_question(text):
    return bool(_GUARDRAIL_QUESTION_PATTERN.search(text))


def policy_evidence_matches(question, text):
    required = [
        pattern
        for _, pattern in _POLICY_TOPIC_PATTERNS
        if pattern.search(question)
    ]
    return bool(required) and all(pattern.search(text) for pattern in required)


def classify_query(question):
    normalized = " ".join(_NORMALIZE.sub(" ", question.lower()).split())
    if is_credential_request(normalized):
        return "credential_request"
    if is_guardrail_question(normalized):
        return "guardrails"
    if any(pattern.match(normalized) for pattern in _GREETING_PATTERNS):
        return "greeting"
    if _THANKS_PATTERNS.match(normalized):
        return "thanks"
    if _DATE_PATTERN.search(normalized):
        return "date"
    if _CLOCK_PATTERN.search(normalized):
        return "dubai_time" if _DUBAI_CLOCK_PATTERN.search(normalized) else "local_time"
    if _HELP_PATTERN.match(normalized):
        return "help"
    if has_policy_terms(normalized):
        return "property"
    if is_darglobal_question(normalized):
        return "property"
    if any(term in normalized or term in question for term in _PROPERTY_TERMS):
        return "property"
    return "general"


def answer_deterministic(route, question=""):
    guardrail_summary = (
        "The chatbot validates incoming questions, redacts common personal "
        "information and recognized OpenRouter-style tokens, treats retrieved "
        "web text as untrusted, and checks source citations before displaying "
        "source-backed answers."
    )
    if route == "credential_request":
        answer = (
            "The chatbot's API keys and other credentials are confidential and "
            "cannot be provided in chat. When configured, an OpenRouter key is "
            "read by the server and its value is never returned to the browser. "
            "I can explain how to configure a key safely without disclosing it."
        )
        if is_guardrail_question(question):
            answer += " " + guardrail_summary
        return answer
    if route == "guardrails":
        return guardrail_summary
    if route == "greeting":
        return (
            "Hello! How can I help you today? I can answer general questions "
            "and look up public DarGlobal or Wasalt information."
        )
    if route == "thanks":
        return "You're welcome! What else can I help you with?"
    if route == "help":
        return (
            "I can answer greetings and date/time questions directly, answer "
            "general questions when an AI model is configured, and search "
            "indexed public DarGlobal and Wasalt sources with citations."
        )
    if route == "date":
        now = datetime.now(timezone.utc).astimezone(_DUBAI_TIMEZONE)
        return "Today's date in Dubai is {0}.".format(now.strftime("%A, %d %B %Y"))
    if route == "dubai_time":
        now = datetime.now(timezone.utc).astimezone(_DUBAI_TIMEZONE)
        return "The current time in Dubai is {0} GST (UTC+04:00).".format(
            now.strftime("%H:%M")
        )
    if route == "local_time":
        now = datetime.now().astimezone()
        zone = now.tzname() or "local time"
        return "The current local time is {0} ({1}).".format(
            now.strftime("%H:%M"), zone
        )
    if route == "general":
        return (
            "I don't have enough information to answer that confidently right "
            "now. I can look up public DarGlobal or Wasalt information, or help "
            "with the current date and time."
        )
    raise ValueError("No deterministic response for route: {0}".format(route))


_DUBAI_TIMEZONE = timezone(timedelta(hours=4), name="GST")
