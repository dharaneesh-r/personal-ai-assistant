import unittest
import os
from app import database

class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Swap out the DB path for testing
        self.original_db_path = database.DB_PATH
        database.DB_PATH = "data/test_history.db"
        database.init_db()

    def tearDown(self):
        # Remove the test database file
        if os.path.exists(database.DB_PATH):
            os.remove(database.DB_PATH)
        database.DB_PATH = self.original_db_path

    def test_session_lifecycle(self):
        # Create session
        database.save_session("session1", "Title 1", "chat", "model-1", "2026-07-15")
        
        # Verify exists
        sess = database.get_session("session1")
        self.assertIsNotNone(sess)
        self.assertEqual(sess["title"], "Title 1")
        self.assertEqual(sess["mode"], "chat")
        
        # List all
        all_sessions = database.get_all_sessions()
        self.assertEqual(len(all_sessions), 1)
        self.assertEqual(all_sessions[0]["id"], "session1")
        
        # Delete session
        database.delete_session("session1")
        self.assertIsNone(database.get_session("session1"))

    def test_message_persistence(self):
        database.save_session("session1", "Title 1", "chat", "model-1", "2026-07-15")
        
        database.save_message(
            msg_id="msg1",
            session_id="session1",
            role="user",
            content="Hello world",
            mode="chat",
            timestamp="2026-07-15T12:00:00",
            sources=["doc1.txt"],
            chunks_used=1,
            rewritten_query="hello rewritten",
            tool_calls=[{"tool": "calculator", "args": {}, "result": {}}],
            iterations=1,
            model="model-1"
        )
        
        messages = database.get_session_messages("session1")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["content"], "Hello world")
        self.assertEqual(messages[0]["sources"], ["doc1.txt"])
        self.assertEqual(messages[0]["tool_calls"], [{"tool": "calculator", "args": {}, "result": {}}])

    def test_evaluation_persistence(self):
        database.save_evaluation(
            eval_id="eval1",
            question="What is 2+2?",
            answer="4",
            context="Simple arithmetic context",
            overall=1.0,
            faithfulness_score=5,
            faithfulness_reason="perfect",
            relevance_score=5,
            relevance_reason="great",
            groundedness_score=5,
            groundedness_reason="grounded",
            model="model-1",
            timestamp="2026-07-15T12:05:00"
        )
        
        evals = database.get_all_evaluations()
        self.assertEqual(len(evals), 1)
        self.assertEqual(evals[0]["id"], "eval1")
        self.assertEqual(evals[0]["overall"], 1.0)
