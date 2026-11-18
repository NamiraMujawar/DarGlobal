"""Tests for locally persisted, owner-isolated chat history.

Author: Namira Mujawar | Project date: 2026-11-18
"""

import os
import tempfile
import unittest
from unittest.mock import patch

import conversations
import knowledge


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env_patch = patch.dict(os.environ, {"DATA_DIR": self.temp_dir.name})
        self.env_patch.start()
        knowledge.initialize_database()

    def tearDown(self):
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def test_history_is_persistent_and_isolated_by_owner(self):
        conversation = conversations.create_conversation("owner-a")
        conversation_id = conversation["id"]
        conversations.save_message(
            "owner-a",
            conversation_id,
            "user",
            "What is Wasalt? My email is me@example.com",
            mode="user",
        )
        conversations.save_message(
            "owner-a",
            conversation_id,
            "assistant",
            "Wasalt is a platform. Contact support@wasalt.com or "
            "crm@darglobal.co.uk. [S1]",
            [{"id": "S1", "url": "https://wasalt.sa/"}],
            mode="openrouter",
        )

        restored = conversations.get_conversation("owner-a", conversation_id)

        self.assertEqual(len(restored["messages"]), 2)
        self.assertIn("[REDACTED EMAIL]", restored["messages"][0]["content"])
        self.assertIn("support@wasalt.com", restored["messages"][1]["content"])
        self.assertIn("crm@darglobal.co.uk", restored["messages"][1]["content"])
        self.assertEqual(restored["messages"][1]["sources"][0]["id"], "S1")
        self.assertIsNone(conversations.get_conversation("owner-b", conversation_id))

    def test_recent_context_is_ordered_and_conversation_can_be_deleted(self):
        conversation = conversations.create_conversation("owner")
        conversation_id = conversation["id"]
        conversations.save_message("owner", conversation_id, "user", "First")
        conversations.save_message("owner", conversation_id, "assistant", "Second")
        conversations.save_message("owner", conversation_id, "user", "Third")

        context = conversations.recent_context("owner", conversation_id, limit=2)

        self.assertEqual([item["content"] for item in context], ["Second", "Third"])
        self.assertTrue(conversations.delete_conversation("owner", conversation_id))
        self.assertIsNone(conversations.get_conversation("owner", conversation_id))


if __name__ == "__main__":
    unittest.main()
