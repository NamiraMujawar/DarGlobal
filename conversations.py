"""Owner-isolated SQLite conversation history.

Author: Namira Mujawar | Project date: 2026-11-18
"""

import json
import re
import uuid
from datetime import datetime, timezone

from guardrails import PUBLIC_CONTACT_EMAILS, redact_pii
from knowledge import connect


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_conversation(owner_id):
    conversation = {
        "id": str(uuid.uuid4()),
        "owner_id": owner_id,
        "title": "New conversation",
        "created_at": _now(),
        "updated_at": _now(),
    }
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO conversations(id, owner_id, title, created_at, updated_at)
            VALUES (:id, :owner_id, :title, :created_at, :updated_at)
            """,
            conversation,
        )
    return conversation


def list_conversations(owner_id):
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   COUNT(m.id) AS message_count
            FROM conversations AS c
            LEFT JOIN messages AS m ON m.conversation_id = c.id
            WHERE c.owner_id = ?
            GROUP BY c.id
            ORDER BY c.updated_at DESC, c.id
            """,
            (owner_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_conversation(owner_id, conversation_id):
    with connect() as connection:
        conversation = connection.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM conversations
            WHERE id = ? AND owner_id = ?
            """,
            (conversation_id, owner_id),
        ).fetchone()
        if conversation is None:
            return None
        rows = connection.execute(
            """
            SELECT id, role, content, sources_json, mode, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id
            """,
            (conversation_id,),
        ).fetchall()
    result = dict(conversation)
    result["messages"] = []
    for row in rows:
        message = dict(row)
        message["sources"] = json.loads(message.pop("sources_json"))
        result["messages"].append(message)
    return result


def recent_context(owner_id, conversation_id, limit=8):
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT m.role, m.content
            FROM messages AS m
            JOIN conversations AS c ON c.id = m.conversation_id
            WHERE c.id = ? AND c.owner_id = ?
            ORDER BY m.id DESC
            LIMIT ?
            """,
            (conversation_id, owner_id, max(1, min(int(limit), 12))),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def save_message(owner_id, conversation_id, role, content, sources=None, mode="local"):
    if role not in ("user", "assistant"):
        raise ValueError("Unsupported conversation message role.")
    content_text = str(content)
    preserved_contacts = {}
    if role == "assistant":
        for index, email in enumerate(PUBLIC_CONTACT_EMAILS):
            marker = "PUBLICCONTACTEMAIL{0}TOKEN".format(index)
            content_text, count = re.subn(
                re.escape(email), marker, content_text, flags=re.IGNORECASE
            )
            if count:
                preserved_contacts[marker] = email
    safe_content = redact_pii(content_text)[:8_000]
    for marker, email in preserved_contacts.items():
        safe_content = safe_content.replace(marker, email)
    source_data = sources if isinstance(sources, list) else []
    serialized_sources = json.dumps(source_data, ensure_ascii=False)
    created_at = _now()
    with connect() as connection:
        conversation = connection.execute(
            """
            SELECT title FROM conversations
            WHERE id = ? AND owner_id = ?
            """,
            (conversation_id, owner_id),
        ).fetchone()
        if conversation is None:
            return False
        connection.execute(
            """
            INSERT INTO messages(
                conversation_id, role, content, sources_json, mode, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                conversation_id,
                role,
                safe_content,
                serialized_sources,
                str(mode)[:32],
                created_at,
            ),
        )
        title = conversation["title"]
        if role == "user" and title == "New conversation":
            title = safe_content.replace("\n", " ").strip()[:60] or title
        connection.execute(
            """
            UPDATE conversations
            SET title = ?, updated_at = ?
            WHERE id = ? AND owner_id = ?
            """,
            (title, created_at, conversation_id, owner_id),
        )
    return True


def delete_conversation(owner_id, conversation_id):
    with connect() as connection:
        cursor = connection.execute(
            "DELETE FROM conversations WHERE id = ? AND owner_id = ?",
            (conversation_id, owner_id),
        )
    return cursor.rowcount == 1
