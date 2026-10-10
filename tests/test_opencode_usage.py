from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from providers.opencode import read_opencode_usage


class OpencodeUsageTest(unittest.TestCase):
    def test_recursive_session_usage_respects_window_with_live_wal(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            db_path = Path(raw_tmp) / "opencode.db"
            db = sqlite3.connect(db_path)
            self.assertEqual(db.execute("PRAGMA journal_mode=WAL").fetchone()[0], "wal")
            db.executescript(
                """
                CREATE TABLE session (
                    id TEXT PRIMARY KEY,
                    parent_id TEXT
                );
                CREATE TABLE part (
                    id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    time_created INTEGER NOT NULL,
                    data TEXT NOT NULL
                );
                """
            )
            db.executemany(
                "INSERT INTO session (id, parent_id) VALUES (?, ?)",
                [("root", None), ("child", "root"), ("other", None)],
            )

            def step(
                part_id: str,
                session_id: str,
                created: int,
                input_tokens: int,
                output_tokens: int,
                reasoning_tokens: int,
                cache_read: int,
                cache_write: int,
            ) -> tuple[str, str, str, int, str]:
                return (
                    part_id,
                    f"message-{part_id}",
                    session_id,
                    created,
                    json.dumps(
                        {
                            "type": "step-finish",
                            "tokens": {
                                "input": input_tokens,
                                "output": output_tokens,
                                "reasoning": reasoning_tokens,
                                "cache": {"read": cache_read, "write": cache_write},
                            },
                        }
                    ),
                )

            db.executemany(
                "INSERT INTO part VALUES (?, ?, ?, ?, ?)",
                [
                    step("before", "root", 99, 100, 100, 100, 100, 100),
                    step("root-step", "root", 100, 10, 3, 2, 20, 1),
                    step("child-step", "child", 150, 30, 5, 4, 40, 2),
                    step("after", "child", 201, 100, 100, 100, 100, 100),
                    step("other-step", "other", 150, 100, 100, 100, 100, 100),
                ],
            )
            db.commit()
            self.assertTrue(db_path.with_name("opencode.db-wal").is_file())

            usage = read_opencode_usage(db_path, "root", 100, 200)

            self.assertEqual(usage.input_tokens, 43)
            self.assertEqual(usage.cached_input_tokens, 60)
            self.assertEqual(usage.output_tokens, 8)
            self.assertEqual(usage.reasoning_tokens, 6)
            self.assertEqual(usage.total_tokens, 117)
            db.close()


if __name__ == "__main__":
    unittest.main()
