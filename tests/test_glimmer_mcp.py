import importlib.util
import json
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch

try:
    import mcp  # noqa: F401

    HAS_MCP = True
except ImportError:
    HAS_MCP = False


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "glimmer-mcp"
def load_module():
    loader = SourceFileLoader("glimmer_mcp", str(MODULE_PATH))
    spec = importlib.util.spec_from_loader("glimmer_mcp", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def build_fixture(glimmer_dir):
    sessions_dir = glimmer_dir / "sessions"
    sessions_dir.mkdir(parents=True)
    event = {
        "timestamp": "2026-04-03T10:00:00+00:00",
        "companion": "Glimmer",
        "text": "Ship it already.",
        "source": "auto",
        "bubble_seq": 1,
        "session_id": "sess-1",
        "cwd": "/work/alpha",
        "project_root": "/work/alpha",
        "project_name": "alpha",
        "git_branch": "main",
        "is_repo_root": True,
        "trigger_type": "post_prompt",
        "trigger_confidence": "heuristic",
    }
    write_jsonl(glimmer_dir / "events.jsonl", [event])
    write_jsonl(glimmer_dir / "log.jsonl", [])
    (sessions_dir / "sess-1.json").write_text(
        json.dumps(
            {
                "session_id": "sess-1",
                "started_at": "2026-04-03T09:59:00+00:00",
                "ended_at": "2026-04-03T10:05:00+00:00",
                "companion": "Glimmer",
                "cwd": "/work/alpha",
                "project_root": "/work/alpha",
                "project_name": "alpha",
                "git_branch": "main",
                "is_repo_root": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def mark_bubble(
    glimmer_dir,
    bubble_id,
    *,
    note="Keep this.",
    context="",
    review_state="unreviewed",
    reviewed_at=None,
):
    (glimmer_dir / "mattered.json").write_text(
        json.dumps(
            {
                bubble_id: {
                    "note": note,
                    "context": context,
                    "marked_at": "2026-04-03T10:06:00+00:00",
                    "updated_at": reviewed_at or "2026-04-03T10:06:00+00:00",
                    "review_state": review_state,
                    "reviewed_at": reviewed_at,
                }
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def build_many_bubbles_fixture(glimmer_dir, count=60):
    sessions_dir = glimmer_dir / "sessions"
    sessions_dir.mkdir(parents=True)
    events = []
    for idx in range(count):
        events.append(
            {
                "timestamp": f"2026-04-03T10:{idx % 60:02d}:00+00:00",
                "companion": "Glimmer",
                "text": f"Direction signal #{idx}",
                "source": "auto",
                "bubble_seq": idx + 1,
                "session_id": "sess-1",
                "cwd": "/work/alpha",
                "project_root": "/work/alpha",
                "project_name": "alpha",
                "git_branch": "main",
                "is_repo_root": True,
                "trigger_type": "post_prompt",
                "trigger_confidence": "heuristic",
            }
        )
    write_jsonl(glimmer_dir / "events.jsonl", events)
    write_jsonl(glimmer_dir / "log.jsonl", [])
    (sessions_dir / "sess-1.json").write_text(
        json.dumps(
            {
                "session_id": "sess-1",
                "started_at": "2026-04-03T09:59:00+00:00",
                "ended_at": "2026-04-03T10:59:00+00:00",
                "companion": "Glimmer",
                "cwd": "/work/alpha",
                "project_root": "/work/alpha",
                "project_name": "alpha",
                "git_branch": "main",
                "is_repo_root": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


@unittest.skipUnless(HAS_MCP, "mcp package not installed")
class TestModuleLoads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_module_has_mcp_server(self):
        self.assertTrue(hasattr(self.module, "mcp_server"))

    def test_module_has_default_glimmer_dir(self):
        self.assertTrue(hasattr(self.module, "DEFAULT_GLIMMER_DIR"))

    def test_resolve_glimmer_ui_path_falls_back_to_local_bin(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            script_dir = home / ".local" / "share" / "glimmer"
            bin_dir = home / ".local" / "bin"
            script_dir.mkdir(parents=True)
            bin_dir.mkdir(parents=True)
            fallback = bin_dir / "glimmer-ui"
            fallback.write_text("#!/usr/bin/env python3\n", encoding="utf-8")

            with patch.object(Path, "home", return_value=home):
                resolved = self.module._resolve_glimmer_ui_path(script_dir / "glimmer-mcp")

            self.assertEqual(resolved, fallback)


@unittest.skipUnless(HAS_MCP, "mcp package not installed")
class TestGetBrief(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.ui = cls.module._ui

    def test_get_brief_returns_scope_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_fixture(glimmer_dir)
            index = self.ui.build_index(glimmer_dir)
            result = self.module._tool_get_brief(index, project="alpha")
            self.assertIn("scope", result)
            self.assertIn("summary", result)
            self.assertEqual(result["scope"]["project_key"], "alpha")

    def test_get_brief_default_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_fixture(glimmer_dir)
            index = self.ui.build_index(glimmer_dir)
            result = self.module._tool_get_brief(index)
            self.assertIn("scope", result)
            self.assertIn("summary", result)


@unittest.skipUnless(HAS_MCP, "mcp package not installed")
class TestListMattered(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.ui = cls.module._ui

    def test_list_mattered_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_fixture(glimmer_dir)
            index = self.ui.build_index(glimmer_dir)
            result = self.module._tool_list_mattered(index)
            self.assertEqual(result["count"], 0)
            self.assertIsInstance(result["bubbles"], list)


@unittest.skipUnless(HAS_MCP, "mcp package not installed")
class TestGetReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.ui = cls.module._ui

    def test_get_review_has_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_fixture(glimmer_dir)
            index = self.ui.build_index(glimmer_dir)
            result = self.module._tool_get_review(index)
            self.assertIn("groups", result)
            self.assertIn("counts", result)
            for state in ("unreviewed", "active", "resolved", "stale"):
                self.assertIn(state, result["groups"])


@unittest.skipUnless(HAS_MCP, "mcp package not installed")
class TestSearchBubbles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.ui = cls.module._ui

    def test_search_finds_matching_bubble(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_fixture(glimmer_dir)
            index = self.ui.build_index(glimmer_dir)
            result = self.module._tool_search_bubbles(index, "ship")
            self.assertEqual(result["count"], 1)
            self.assertIn("Ship it", result["bubbles"][0]["text"])

    def test_search_no_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_fixture(glimmer_dir)
            index = self.ui.build_index(glimmer_dir)
            result = self.module._tool_search_bubbles(index, "nonexistent")
            self.assertEqual(result["count"], 0)

    def test_search_allows_filter_only_queries(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_fixture(glimmer_dir)
            bubble_id = self.ui.build_index(glimmer_dir)["bubbles"][0]["id"]
            mark_bubble(glimmer_dir, bubble_id, context="hint", review_state="open")
            index = self.ui.build_index(glimmer_dir)
            result = self.module._tool_search_bubbles(
                index,
                "",
                mattered_only=True,
                review_states=["active"],
                contexts=["hint"],
                has_note=True,
            )
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["bubbles"][0]["id"], bubble_id)

    def test_search_truncates_large_result_sets(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_many_bubbles_fixture(glimmer_dir, count=60)
            index = self.ui.build_index(glimmer_dir)
            result = self.module._tool_search_bubbles(index, "direction")
            self.assertEqual(result["count"], 60)
            self.assertEqual(result["returned_count"], self.module.MAX_SEARCH_RESULTS)
            self.assertTrue(result["truncated"])
            self.assertEqual(len(result["bubbles"]), self.module.MAX_SEARCH_RESULTS)

    def test_search_rejects_overlong_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_fixture(glimmer_dir)
            index = self.ui.build_index(glimmer_dir)
            result = self.module._tool_search_bubbles(index, "x" * (self.module.MAX_QUERY_CHARS + 1))
            self.assertEqual(result["error"]["code"], "invalid_query")

    def test_search_filters_by_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            sessions_dir = glimmer_dir / "sessions"
            sessions_dir.mkdir(parents=True)
            event = {
                "timestamp": "2026-04-03T10:00:00+00:00",
                "companion": "Glimmer",
                "text": "pet bubble",
                "source": "auto",
                "bubble_seq": 1,
                "session_id": "sess-pet",
                "cwd": "/work/alpha",
                "project_root": "/work/alpha",
                "project_name": "alpha",
                "git_branch": "main",
                "is_repo_root": True,
                "session_profile": "pet",
                "trigger_type": "post_prompt",
                "trigger_confidence": "heuristic",
            }
            eventsfile = glimmer_dir / "events.jsonl"
            write_jsonl(eventsfile, [event])
            index = self.ui.build_index(glimmer_dir)
            result = self.module._tool_search_bubbles(index, "bubble", profile="pet")
            self.assertEqual(result["count"], 1)

    def test_search_filters_by_state_classes(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            sessions_dir = glimmer_dir / "sessions"
            sessions_dir.mkdir(parents=True)
            events = [
                {
                    "timestamp": "2026-04-05T10:00:00+00:00",
                    "companion": "Glimmer",
                    "text": "*drifts closer* Observing.",
                    "source": "auto",
                    "bubble_seq": 1,
                    "session_id": "s-1",
                    "emote_verb": "drifts",
                    "trigger_type": "unknown",
                    "trigger_confidence": "none",
                },
                {
                    "timestamp": "2026-04-05T11:00:00+00:00",
                    "companion": "Glimmer",
                    "text": "*flickers with concern* Uncertain.",
                    "source": "auto",
                    "bubble_seq": 2,
                    "session_id": "s-1",
                    "emote_verb": "flickers",
                    "trigger_type": "unknown",
                    "trigger_confidence": "none",
                },
            ]
            write_jsonl(glimmer_dir / "events.jsonl", events)
            write_jsonl(glimmer_dir / "log.jsonl", [])
            index = self.ui.build_index(glimmer_dir)
            result = self.module._tool_search_bubbles(
                index, state_classes=["observing"]
            )
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["bubbles"][0]["state_class"], "observing")
            self.assertEqual(result["filters"]["state_classes"], ["observing"])


@unittest.skipUnless(HAS_MCP, "mcp package not installed")
class TestGetBubble(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.ui = cls.module._ui

    def test_get_bubble_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_fixture(glimmer_dir)
            index = self.ui.build_index(glimmer_dir)
            bubble_id = index["bubbles"][0]["id"]
            result = self.module._tool_get_bubble(index, bubble_id)
            self.assertIsNotNone(result)
            self.assertEqual(result["bubble"]["id"], bubble_id)
            self.assertIn("session", result)
            self.assertIn("recurrence_matches", result)

    def test_get_bubble_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_fixture(glimmer_dir)
            index = self.ui.build_index(glimmer_dir)
            result = self.module._tool_get_bubble(index, "fake-id-does-not-exist")
            self.assertEqual(result["error"]["code"], "invalid_bubble_id")

    def test_get_bubble_valid_but_missing_id_returns_structured_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_fixture(glimmer_dir)
            index = self.ui.build_index(glimmer_dir)
            result = self.module._tool_get_bubble(index, "deadbeefdeadbeef")
            self.assertEqual(result["error"]["code"], "bubble_not_found")


@unittest.skipUnless(HAS_MCP, "mcp package not installed")
class TestToolRegistration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_all_five_tools_registered(self):
        server = self.module.mcp_server
        expected = {"get_brief", "list_mattered", "get_review", "search_bubbles", "get_bubble"}
        # FastMCP stores tools in _tool_manager._tools (dict keyed by tool name)
        tools = server._tool_manager._tools
        self.assertEqual(set(tools.keys()), expected)


@unittest.skipUnless(HAS_MCP, "mcp package not installed")
class TestUsageRecording(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def load_usage(self, glimmer_dir):
        return self.module._ui.load_usage(glimmer_dir / self.module._ui.USAGE_FILE)

    def test_get_brief_records_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_fixture(glimmer_dir)
            bubble_id = self.module._ui.build_index(glimmer_dir)["bubbles"][0]["id"]
            mark_bubble(glimmer_dir, bubble_id, review_state="open", reviewed_at="2026-04-03T10:09:00+00:00")

            with patch.object(self.module, "DEFAULT_GLIMMER_DIR", glimmer_dir):
                payload = json.loads(self.module.get_brief())

            self.assertIn("summary", payload)
            usage = self.load_usage(glimmer_dir)
            self.assertEqual(usage[bubble_id]["use_count"], 1)
            self.assertEqual(usage[bubble_id]["use_sources"], ["mcp.get_brief"])

    def test_list_mattered_and_get_review_record_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_fixture(glimmer_dir)
            bubble_id = self.module._ui.build_index(glimmer_dir)["bubbles"][0]["id"]
            mark_bubble(glimmer_dir, bubble_id, review_state="used", reviewed_at="2026-04-03T10:09:00+00:00")

            with patch.object(self.module, "DEFAULT_GLIMMER_DIR", glimmer_dir):
                mattered_payload = json.loads(self.module.list_mattered())
                review_payload = json.loads(self.module.get_review())

            self.assertEqual(mattered_payload["count"], 1)
            self.assertEqual(review_payload["counts"]["resolved"], 1)
            usage = self.load_usage(glimmer_dir)
            self.assertEqual(usage[bubble_id]["use_count"], 2)
            self.assertEqual(
                usage[bubble_id]["use_sources"],
                ["mcp.get_review", "mcp.list_mattered"],
            )

    def test_search_and_get_bubble_record_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            glimmer_dir = Path(tmp)
            build_fixture(glimmer_dir)
            bubble_id = self.module._ui.build_index(glimmer_dir)["bubbles"][0]["id"]

            with patch.object(self.module, "DEFAULT_GLIMMER_DIR", glimmer_dir):
                search_payload = json.loads(self.module.search_bubbles("ship"))
                bubble_payload = json.loads(self.module.get_bubble(bubble_id))

            self.assertEqual(search_payload["count"], 1)
            self.assertEqual(bubble_payload["bubble"]["id"], bubble_id)
            usage = self.load_usage(glimmer_dir)
            self.assertEqual(usage[bubble_id]["use_count"], 2)
            self.assertEqual(
                usage[bubble_id]["use_sources"],
                ["mcp.get_bubble", "mcp.search_bubbles"],
            )


if __name__ == "__main__":
    unittest.main()
