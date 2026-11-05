#!/usr/bin/env python3
"""
Offline unittest for issue_reporter.py

Mocks swytchcode_runtime.exec with REAL envelope shapes from logs:
- 01_read.txt: 200 with empty list (data=[])
- 02_create.txt: 201 with data.number=1
- 03_close.txt: 200 with data.number=1
- 404 envelope for --fail-demo (close #999999)

Run with: ./venv/bin/python -m unittest tests/test_issue_reporter.py -v
"""

import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from typing import Any, Dict

# Import the module under test
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import issue_reporter


# Real envelope shapes from logs/
READ_ENVELOPE_200 = {
    "data": [],
    "request": {
        "method": "GET",
        "url": "https://api.github.com/repos/TaperBubbles04/swytchcode-ppi-project/issues?direction=desc&page=1&per_page=30&sort=created&state=open"
    },
    "status_code": 200
}

CREATE_ENVELOPE_201 = {
    "data": {
        "number": 1,
        "id": 6199033314,
        "title": "Swytchcode PPI test",
        "body": "Created via swy exec",
        "state": "open",
        "html_url": "https://github.com/TaperBubbles04/swytchcode-ppi-project/issues/1"
    },
    "request": {
        "method": "POST",
        "url": "https://api.github.com/repos/TaperBubbles04/swytchcode-ppi-project/issues"
    },
    "status_code": 201
}

CLOSE_ENVELOPE_200 = {
    "data": {
        "number": 1,
        "id": 6199033314,
        "title": "Swytchcode PPI test",
        "body": "Created via swy exec",
        "state": "closed",
        "html_url": "https://github.com/TaperBubbles04/swytchcode-ppi-project/issues/1"
    },
    "request": {
        "method": "PATCH",
        "url": "https://api.github.com/repos/TaperBubbles04/swytchcode-ppi-project/issues/1"
    },
    "status_code": 200
}

# Real 404 envelope from logs/05_fail_demo.txt
CLOSE_ENVELOPE_404 = {
    "data": {
        "documentation_url": "https://docs.github.com/rest/issues/issues#update-an-issue",
        "message": "Not Found",
        "status": "404"
    },
    "error_category": "not_found",
    "request": {
        "method": "PATCH",
        "url": "https://api.github.com/repos/TaperBubbles04/swytchcode-ppi-project/issues/999999"
    },
    "retryable": False,
    "status_code": 404,
    "suggested_action": "the target resource does not exist; check the ids and the endpoint"
}


class MockExec:
    """Mock for swytchcode_runtime.exec that returns predefined envelopes."""

    def __init__(self):
        self.calls = []
        self.return_values = {}

    def __call__(self, canonical_id: str, input: Dict[str, Any], dry_run: bool = False) -> Any:
        self.calls.append({
            "canonical_id": canonical_id,
            "input": input,
            "dry_run": dry_run
        })
        key = (canonical_id, input.get("issue_number"))
        if key in self.return_values:
            return self.return_values[key]
        # Default returns based on canonical_id
        if canonical_id == "github.issue.get1":
            return READ_ENVELOPE_200
        elif canonical_id == "github.issue.create":
            return CREATE_ENVELOPE_201
        elif canonical_id == "github.issue.update":
            issue_num = input.get("issue_number")
            if issue_num == 999999:
                return CLOSE_ENVELOPE_404
            return CLOSE_ENVELOPE_200
        return {"data": {}, "status_code": 200}


class TestIssueReporter(unittest.TestCase):

    def test_extract_issue_number_from_envelope(self):
        """Test extract_issue_number handles the full envelope."""
        num = issue_reporter.extract_issue_number(CREATE_ENVELOPE_201)
        self.assertEqual(num, 1)

    def test_extract_issue_number_from_unwrapped(self):
        """Test extract_issue_number handles already-unwrapped dict."""
        unwrapped = CREATE_ENVELOPE_201["data"]
        num = issue_reporter.extract_issue_number(unwrapped)
        self.assertEqual(num, 1)

    def test_extract_issue_number_from_list_returns_none(self):
        """Test extract_issue_number returns None for list response."""
        num = issue_reporter.extract_issue_number(READ_ENVELOPE_200)
        self.assertIsNone(num)

    def test_is_provider_error_200_ok(self):
        """Test is_provider_error returns False for 200."""
        is_err, _, _, _, _ = issue_reporter.is_provider_error(READ_ENVELOPE_200)
        self.assertFalse(is_err)

    def test_is_provider_error_201_ok(self):
        """Test is_provider_error returns False for 201."""
        is_err, _, _, _, _ = issue_reporter.is_provider_error(CREATE_ENVELOPE_201)
        self.assertFalse(is_err)

    def test_is_provider_error_404_error(self):
        """Test is_provider_error returns True for 404 with retryable and suggested_action."""
        is_err, status, cat, retryable, action = issue_reporter.is_provider_error(CLOSE_ENVELOPE_404)
        self.assertTrue(is_err)
        self.assertEqual(status, "404")
        self.assertEqual(cat, "not_found")
        self.assertEqual(retryable, False)
        self.assertEqual(action, "the target resource does not exist; check the ids and the endpoint")

    def test_is_provider_error_500_error(self):
        """Test is_provider_error returns True for 500."""
        envelope = {"status_code": 500, "error_category": "server_error"}
        is_err, status, cat, retryable, action = issue_reporter.is_provider_error(envelope)
        self.assertTrue(is_err)
        self.assertEqual(status, "500")
        self.assertEqual(cat, "server_error")
        self.assertIsNone(retryable)
        self.assertIsNone(action)

    @patch("issue_reporter.swy_exec")
    def test_list_issues_returns_envelope(self, mock_exec):
        """Test list_issues returns the envelope from exec."""
        mock_exec.return_value = READ_ENVELOPE_200
        result = issue_reporter.list_issues("owner", "repo", dry_run=False)
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], READ_ENVELOPE_200)
        mock_exec.assert_called_once()
        call = mock_exec.call_args
        self.assertEqual(call[1]["canonical_id"], "github.issue.get1")
        self.assertEqual(call[1]["input"], {"owner": "owner", "repo": "repo"})

    @patch("issue_reporter.swy_exec")
    def test_create_issue_returns_envelope(self, mock_exec):
        """Test create_issue returns the envelope from exec."""
        mock_exec.return_value = CREATE_ENVELOPE_201
        result = issue_reporter.create_issue("owner", "repo", "title", "body", dry_run=False)
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], CREATE_ENVELOPE_201)
        call = mock_exec.call_args
        self.assertEqual(call[1]["canonical_id"], "github.issue.create")
        self.assertEqual(call[1]["input"]["owner"], "owner")
        self.assertEqual(call[1]["input"]["repo"], "repo")
        self.assertEqual(call[1]["input"]["body"]["title"], "title")

    @patch("issue_reporter.swy_exec")
    def test_close_issue_returns_envelope(self, mock_exec):
        """Test close_issue returns the envelope from exec."""
        mock_exec.return_value = CLOSE_ENVELOPE_200
        result = issue_reporter.close_issue("owner", "repo", 1, dry_run=False)
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], CLOSE_ENVELOPE_200)
        call = mock_exec.call_args
        self.assertEqual(call[1]["canonical_id"], "github.issue.update")
        self.assertEqual(call[1]["input"]["issue_number"], 1)
        self.assertEqual(call[1]["input"]["body"]["state"], "closed")

    @patch("issue_reporter.swy_exec")
    def test_main_create_then_close_uses_extracted_number(self, mock_exec):
        """Test main flow: create extracts number=1, close called with that number."""
        # First call (create) returns 201 with number=1, second (close) returns 200
        call_count = [0]

        def side_effect(canonical_id, input, dry_run):
            call_count[0] += 1
            if canonical_id == "github.issue.create":
                return CREATE_ENVELOPE_201
            elif canonical_id == "github.issue.update":
                return CLOSE_ENVELOPE_200
            return READ_ENVELOPE_200

        mock_exec.side_effect = side_effect

        # Capture stdout
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            # Simulate: python issue_reporter.py --owner o --repo r --title t --body b
            sys.argv = ["issue_reporter.py", "--owner", "owner", "--repo", "repo", "--title", "Test", "--body", "Body"]
            try:
                issue_reporter.main()
            except SystemExit as e:
                self.assertEqual(e.code, 0)

        output = f.getvalue()

        # Verify create was called
        create_calls = [c for c in mock_exec.call_args_list if c[1]["canonical_id"] == "github.issue.create"]
        self.assertEqual(len(create_calls), 1)

        # Verify close was called with issue_number=1 (extracted from create response)
        close_calls = [c for c in mock_exec.call_args_list if c[1]["canonical_id"] == "github.issue.update"]
        self.assertEqual(len(close_calls), 1)
        self.assertEqual(close_calls[0][1]["input"]["issue_number"], 1)

        # Verify output mentions issue #1
        self.assertIn("#1", output)

    @patch("issue_reporter.swy_exec")
    def test_main_fail_demo_closes_999999_gets_404_exits_1(self, mock_exec):
        """Test --fail-demo: close #999999 returns 404 envelope, exits 1."""
        def side_effect(canonical_id, input, dry_run):
            if canonical_id == "github.issue.update" and input.get("issue_number") == 999999:
                return CLOSE_ENVELOPE_404
            return {"data": {}, "status_code": 200}

        mock_exec.side_effect = side_effect

        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            sys.argv = ["issue_reporter.py", "--owner", "owner", "--repo", "repo", "--fail-demo"]
            try:
                issue_reporter.main()
                self.fail("Expected SystemExit with code 1")
            except SystemExit as e:
                self.assertEqual(e.code, 1)

        output = f.getvalue()
        # Verify close was called with 999999
        close_calls = [c for c in mock_exec.call_args_list if c[1]["canonical_id"] == "github.issue.update"]
        self.assertEqual(len(close_calls), 1)
        self.assertEqual(close_calls[0][1]["input"]["issue_number"], 999999)

        # Verify 404 error reported
        self.assertIn("404", output)
        self.assertIn("PROVIDER ERROR", output)

    def test_extract_summary(self):
        """Test extract_summary produces short summary from envelope."""
        # Test create envelope
        summary = issue_reporter.extract_summary(CREATE_ENVELOPE_201)
        self.assertIn("status=201", summary)
        self.assertIn("#1", summary)
        self.assertIn("open", summary)
        self.assertIn("github.com", summary)

        # Test close envelope
        summary = issue_reporter.extract_summary(CLOSE_ENVELOPE_200)
        self.assertIn("status=200", summary)
        self.assertIn("#1", summary)
        self.assertIn("closed", summary)

        # Test list envelope (empty data)
        summary = issue_reporter.extract_summary(READ_ENVELOPE_200)
        self.assertIn("status=200", summary)


if __name__ == "__main__":
    unittest.main()