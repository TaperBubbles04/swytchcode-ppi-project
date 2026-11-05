#!/usr/bin/env python3
"""
Issue Reporter - Creates, lists, and closes GitHub issues using Swytchcode runtime.

This script demonstrates the Swytchcode runtime integration:
- Uses only `from swytchcode_runtime import exec` (no HTTP client, no token, no env-var credentials)
- Owner and repo are REQUIRED argparse arguments (no hardcoded account)
- Creates an issue via github.issue.create, then closes it via github.issue.update
- Lists issues via github.issue.get1 (read op)
- Handles structured error JSON (category, retryable, suggested_action) via SwytchcodeError.details
- Treats provider 4xx/5xx as an error (exits 0 with status_code/error_category in result)
- Supports --dry-run (verified via signature)
- One deliberate-failure option for demo (--fail-demo skips creation, attempts to close #999999)
"""

import argparse
import json
import sys
from typing import Any, Optional

from swytchcode_runtime import exec as swy_exec
from swytchcode_runtime.errors import SwytchcodeError


def extract_issue_number(result: Any) -> Optional[int]:
    """
    Extract issue number from swy exec result.
    Handles both the full envelope {"data": {...}, "status_code": N} and already-unwrapped dict.
    """
    if not isinstance(result, dict):
        return None
    # Try envelope first: result["data"]["number"]
    data = result.get("data", result)
    if isinstance(data, dict):
        return data.get("number")
    return None


def list_issues(owner: str, repo: str, dry_run: bool = False) -> dict:
    """List GitHub issues using github.issue.get1."""
    try:
        result = swy_exec(
            canonical_id="github.issue.get1",
            input={"owner": owner, "repo": repo},
            dry_run=dry_run,
        )
        return {"success": True, "result": result}
    except SwytchcodeError as e:
        return {"success": False, "error": str(e), "details": e.details}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}", "details": None}


def create_issue(owner: str, repo: str, title: str, body: str, dry_run: bool = False) -> dict:
    """Create a GitHub issue using github.issue.create."""
    payload = {
        "title": title,
        "body": body,
    }
    try:
        result = swy_exec(
            canonical_id="github.issue.create",
            input={"owner": owner, "repo": repo, "body": payload},
            dry_run=dry_run,
        )
        return {"success": True, "result": result}
    except SwytchcodeError as e:
        return {"success": False, "error": str(e), "details": e.details}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}", "details": None}


def close_issue(owner: str, repo: str, issue_number: int, dry_run: bool = False) -> dict:
    """Close a GitHub issue using github.issue.update with state=closed."""
    payload = {"state": "closed"}
    try:
        result = swy_exec(
            canonical_id="github.issue.update",
            input={"owner": owner, "repo": repo, "issue_number": issue_number, "body": payload},
            dry_run=dry_run,
        )
        return {"success": True, "result": result}
    except SwytchcodeError as e:
        return {"success": False, "error": str(e), "details": e.details}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}", "details": None}


def is_provider_error(result: Any) -> tuple[bool, Optional[str], Optional[str], Optional[bool], Optional[str]]:
    """
    Check if result contains a provider 4xx/5xx error.
    Handles both the full envelope {"status_code": N, "error_category": "..."} and unwrapped.
    Returns: (is_error, status_code, error_category, retryable, suggested_action)
    """
    if isinstance(result, dict):
        # Check top-level status_code (envelope)
        status_code = result.get("status_code")
        error_category = result.get("error_category")
        retryable = result.get("retryable")
        suggested_action = result.get("suggested_action")
        if status_code and isinstance(status_code, int) and status_code >= 400:
            return True, str(status_code), error_category, retryable, suggested_action
        # Also check nested data if present (some providers might wrap differently)
        data = result.get("data")
        if isinstance(data, dict):
            status_code = data.get("status_code")
            error_category = data.get("error_category")
            retryable = data.get("retryable")
            suggested_action = data.get("suggested_action")
            if status_code and isinstance(status_code, int) and status_code >= 400:
                return True, str(status_code), error_category, retryable, suggested_action
    return False, None, None, None, None


def extract_summary(result: dict) -> str:
    """Extract a short summary from the result envelope."""
    if not isinstance(result, dict):
        return "unknown"
    data = result.get("data", result)
    # If data is a list (e.g., empty list from list issues), just use the envelope
    if isinstance(data, list):
        status_code = result.get("status_code")
        return f"status={status_code}" if status_code is not None else "ok"
    if not isinstance(data, dict):
        status_code = result.get("status_code")
        return f"status={status_code}" if status_code is not None else "unknown"
    number = data.get("number")
    html_url = data.get("html_url")
    state = data.get("state")
    status_code = result.get("status_code")
    parts = []
    if status_code is not None:
        parts.append(f"status={status_code}")
    if number is not None:
        parts.append(f"#{number}")
    if html_url:
        parts.append(html_url)
    if state:
        parts.append(state)
    return " ".join(parts) if parts else "ok"


def print_result(operation: str, result: dict, verbose: bool = False) -> int:
    """Print result and return exit code."""
    if verbose:
        print(f"\n=== {operation} ===")
        print(json.dumps(result, indent=2, default=str))
    else:
        # Short summary
        summary = extract_summary(result.get("result", {}))
        print(f"{operation}: {summary}")

    if not result.get("success", False):
        if not verbose:
            print(f"  ❌ FAILED")
        details = result.get("details")
        if details:
            if verbose:
                print(f"Error details: {json.dumps(details, indent=2)}")
            if isinstance(details, dict):
                category = details.get("category")
                retryable = details.get("retryable")
                suggested_action = details.get("suggested_action")
                if category or retryable is not None or suggested_action:
                    if verbose:
                        print(f"  category: {category}")
                        print(f"  retryable: {retryable}")
                        print(f"  suggested_action: {suggested_action}")
                    else:
                        print(f"  category={category} retryable={retryable} action={suggested_action}")
        return 1

    is_err, status_code, error_category, retryable, suggested_action = is_provider_error(result.get("result"))
    if is_err:
        if verbose:
            print(f"\n❌ {operation} PROVIDER ERROR")
            print(f"  status_code: {status_code}")
            print(f"  error_category: {error_category}")
            if retryable is not None:
                print(f"  retryable: {retryable}")
            if suggested_action:
                print(f"  suggested_action: {suggested_action}")
        else:
            print(f"  ❌ PROVIDER ERROR status={status_code} category={error_category} retryable={retryable} action={suggested_action}")
        return 1

    if verbose:
        print(f"\n✅ {operation} SUCCESS")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="List, create, and close GitHub issues using Swytchcode runtime",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --owner myuser --repo myrepo --list
  %(prog)s --owner myuser --repo myrepo --title "Test" --body "Test body"
  %(prog)s --owner myuser --repo myrepo --title "Test" --body "Test body" --dry-run
  %(prog)s --owner myuser --repo myrepo --fail-demo
  %(prog)s --owner myuser --repo myrepo --list --dry-run
""",
    )
    parser.add_argument("--owner", required=True, help="GitHub repository owner (required)")
    parser.add_argument("--repo", required=True, help="GitHub repository name (required)")
    parser.add_argument("--title", default="Test issue from Swytchcode", help="Issue title")
    parser.add_argument("--body", default="Created by issue_reporter.py demo", help="Issue body")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode (no live API call)")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List issues in the repository (read operation via github.issue.get1)",
    )
    parser.add_argument(
        "--fail-demo",
        action="store_true",
        help="Deliberate failure demo: skip creation, attempt to close non-existent issue #999999",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print full JSON response instead of summary",
    )

    args = parser.parse_args()

    print(f"Owner: {args.owner}")
    print(f"Repo: {args.repo}")
    print(f"Dry-run: {args.dry_run}")
    print(f"List mode: {args.list}")
    print(f"Fail demo: {args.fail_demo}")

    exit_codes = []

    # Step 0: List issues if requested
    if args.list:
        print("\n📋 Listing issues...")
        list_result = list_issues(args.owner, args.repo, args.dry_run)
        exit_codes.append(print_result("LIST ISSUES", list_result, args.verbose))

    # Step 1: Create issue (unless fail-demo or list-only)
    if not args.fail_demo and not args.list:
        print("\n📝 Creating issue...")
        create_result = create_issue(args.owner, args.repo, args.title, args.body, args.dry_run)
        exit_codes.append(print_result("CREATE ISSUE", create_result, args.verbose))

        issue_number = None
        if create_result.get("success") and not args.dry_run:
            result = create_result.get("result")
            issue_number = extract_issue_number(result)

        # Step 2: Close issue
        if issue_number is not None:
            print(f"\n🔒 Closing issue #{issue_number}...")
            close_result = close_issue(args.owner, args.repo, issue_number, args.dry_run)
        else:
            print("\n⚠️  No issue number available to close (dry-run or creation failed)")
            close_result = {"success": True, "result": {"skipped": True, "reason": "no issue number"}}
        exit_codes.append(print_result("CLOSE ISSUE", close_result, args.verbose))

    # Fail demo: skip creation, only attempt to close #999999
    if args.fail_demo:
        print("\n💥 Fail demo: attempting to close non-existent issue #999999...")
        close_result = close_issue(args.owner, args.repo, 999999, args.dry_run)
        exit_codes.append(print_result("CLOSE ISSUE (fail demo)", close_result, args.verbose))

    # Overall exit code
    if any(code != 0 for code in exit_codes):
        sys.exit(1)

    print("\n✅ All operations completed successfully")


if __name__ == "__main__":
    main()