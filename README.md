# Swytchcode PPI Project— Reference Implementation

## Overview

**Goal**: Build a working Python CLI (`issue_reporter.py`) that:
- Uses only `from swytchcode_runtime import exec` (no HTTP client, no token, no env-var credentials)
- Lists, creates, and closes GitHub issues via Swytchcode-enabled methods
- Handles the structured error envelope returned by Swytchcode
- Works in both dry-run and live modes
- Includes offline unit tests using real response envelopes from live runs

**Provider**: GitHub (`GitHub@github:1.1.4`)
- 1,026 methods, 0 workflows
- Auth: OAuth2 (managed by Swytchcode CLI)
- Production endpoint: `https://api.github.com`
- Sandbox endpoint: empty (must use production mode)

---

## Project Structure

```
swyproject/
├── .claude/
│   ├── CLAUDE.md           # Agent contract + 9 hard rules
│   ├── RTK.md              # Rust Token Killer usage
│   └── settings.json       # Deny rules for git writes, swy exec live
├── .swytchcode/
│   ├── tooling.json        # Enabled methods + execution mode
│   ├── tooling.json.lock
│   ├── integrations/
│   │   └── GitHub/github/1.1.4/
│   │       ├── wrekenfile.yaml    # 3.1 MB, 1026 methods
│   │       ├── manifest.json
│   │       └── methods.json
│   └── mcp.pid
├── docs/
│   ├── providers.txt       # Full swy search --all output (1329 lines)
│   └── PROJECT_STATE.md    # Live results, decisions, corrections
├── logs/
│   ├── 01_read.txt         # List issues (200, empty list)
│   ├── 02_create.txt       # Create issue #1 (201)
│   ├── 03_close.txt        # Close issue #1 (200)
│   ├── 04_script_run.txt   # Script create #2 + close #2
│   ├── 05_fail_demo.txt    # Fail demo close #999999 (404)
│   └── 06_summary_run.txt  # Summary run
├── tests/
│   └── test_issue_reporter.py  # 13 unittest cases, offline, mocked exec
├── venv/                   # Python virtual env (gitignored)
├── issue_reporter.py       # Main CLI script
├── FRICTION.md             # 19 friction entries (F1-F19)
├── AI_USAGE.md             # 8 AI interaction rows
├── skills.md               # Swytchcode integration skill (detailed workflow)
└── .gitignore
```

---

## Quick Start

### Prerequisites
- Python 3.10+
- `swytchcode` CLI installed and authenticated
- GitHub account for OAuth connection

### 1. Clone and Setup
```bash
git clone https://github.com/TaperBubbles04/swytchcode-ppi-project
cd swyproject

# Create venv (Ubuntu 22.04 workaround for ensurepip)
python3 -m venv venv --without-pip
curl -sS https://bootstrap.pypa.io/get-pip.py | ./venv/bin/python
./venv/bin/pip install swytchcode-runtime
```

### 2. Initialize Swytchcode Project
```bash
swy init                    # Choose "production" mode (not sandbox)
swy get GitHub@github:1.1.4 # Fetches provider bundle, creates Wrekenfile
swy add method github.issue.get1
swy add method github.issue.create
swy add method github.issue.update
swy add method github.issue.list
```

### 3. Connect GitHub (run yourself)
```bash
swy auth connect Github     # Interactive - opens browser for OAuth consent
# Note: --json connect gives 403; use interactive command
```

### 4. Set Production Mode (required for GitHub)
```bash
# GitHub's sandbox_endpoint is empty — must use production
# Edit .swytchcode/tooling.json: "mode": "production"
# Or run:
jq '.mode = "production"' .swytchcode/tooling.json > tmp && mv tmp .swytchcode/tooling.json
```

### 5. Run the CLI

**List issues:**
```bash
./venv/bin/python issue_reporter.py --owner TaperBubbles04 --repo swytchcode-ppi-project --list
```

**Create + close an issue:**
```bash
./venv/bin/python issue_reporter.py --owner TaperBubbles04 --repo swytchcode-ppi-project \
  --title "Test issue" --body "Created via Swytchcode"
```

**Dry-run (no live API call):**
```bash
./venv/bin/python issue_reporter.py --owner TaperBubbles04 --repo swytchcode-ppi-project \
  --title "Test" --body "Test" --dry-run
```

**Deliberate failure demo (404):**
```bash
./venv/bin/python issue_reporter.py --owner TaperBubbles04 --repo swytchcode-ppi-project --fail-demo
```

**Verbose output (full JSON):**
```bash
./venv/bin/python issue_reporter.py --owner TaperBubbles04 --repo swytchcode-ppi-project --list --verbose
```

### 6. Run Tests (offline, no network)
```bash
./venv/bin/python -m unittest tests.test_issue_reporter -v
# All 13 tests should pass
```

---

## Key Files Explained

### `issue_reporter.py` — Main CLI

**Pattern**: Uses only `from swytchcode_runtime import exec`

```python
from swytchcode_runtime import exec as swy_exec
from swytchcode_runtime.errors import SwytchcodeError

result = swy_exec(
    canonical_id="github.issue.create",
    input={"owner": owner, "repo": repo, "body": {"title": title, "body": body}},
    dry_run=dry_run
)
```

**Handles the Swytchcode response envelope**:
```json
{
  "data": { "number": 1, "title": "...", "state": "open", "html_url": "..." },
  "request": { "method": "POST", "url": "https://api.github.com/..." },
  "status_code": 201,
  "error_category": "",
  "retryable": false,
  "suggested_action": ""
}
```

**Extracts issue number** from `result.get("data", result).get("number")`

**Provider error detection**: checks `status_code >= 400` in envelope

**CLI flags**:
- `--owner` / `--repo` — required
- `--list` — list issues (read via `github.issue.get1`)
- `--title` / `--body` — create issue
- `--dry-run` — preview without calling API
- `--fail-demo` — attempt to close #999999 (shows 404 handling)
- `--verbose` — print full JSON

---

### `tests/test_issue_reporter.py` — Offline Unit Tests

**13 tests** mocking `swytchcode_runtime.exec` with **real envelopes from `logs/`**:

| Test | What it verifies |
|------|------------------|
| `test_extract_issue_number_from_envelope` | Extracts `#1` from 201 create envelope |
| `test_extract_issue_number_from_unwrapped` | Handles already-unwrapped dict |
| `test_extract_issue_number_from_list_returns_none` | List returns empty list → None |
| `test_is_provider_error_200_ok` | 200 → not an error |
| `test_is_provider_error_201_ok` | 201 → not an error |
| `test_is_provider_error_404_error` | 404 → error, retryable=false, action="check ids" |
| `test_is_provider_error_500_error` | 500 → error |
| `test_list_issues_returns_envelope` | Calls `github.issue.get1` with owner/repo |
| `test_create_issue_returns_envelope` | Calls `github.issue.create` with title/body |
| `test_close_issue_returns_envelope` | Calls `github.issue.update` with state=closed |
| `test_main_create_then_close_uses_extracted_number` | Full flow: create → extract #1 → close #1 |
| `test_main_fail_demo_closes_999999_gets_404_exits_1` | Fail demo returns 404, exits 1 |
| `test_extract_summary` | Short summary: "status=201 #1 open https://github.com/..." |

Run: `./venv/bin/python -m unittest tests.test_issue_reporter -v`

---

### `docs/PROJECT_STATE.md` — Live Results & Decisions

Contains **exact commands and outputs** from live runs against `TaperBubbles04/swytchcode-ppi-project`:

| Operation | Command | Result |
|-----------|---------|--------|
| List issues | `swy exec github.issue.get1 --input owner=... --input repo=...` | `200`, `data: []` |
| Create issue #1 | `swy exec github.issue.create --input owner=... --body '{"title":"..."}'` | `201`, `data.number: 1` |
| Close issue #1 | `swy exec github.issue.update --input issue_number=1 --body '{"state":"closed"}'` | `200`, `state: closed` |
| Script run (#2) | `issue_reporter.py` live | Create `201` #2, Close `200` #2 |
| Fail demo | `swy exec github.issue.update --input issue_number=999999` | `404`, `not_found`, `retryable=false` |

Also documents:
- **Verified canonical IDs** (with HTTP method/path)
- **Tooling.json changes** (before/after `swy add method`)
- **Corrections** (e.g., no `--mode` flag on exec — mode is in tooling.json only)
- **Docs excerpts** (what is/isn't documented about GitHub auth)

---

### `FRICTION.md` — 19 Real Friction Entries

Every failure, confusion, and workaround documented with exact commands:

| ID | Issue | Resolution |
|----|-------|------------|
| F1 | `swy auth status` = "No connected accounts" after login | `swy login` ≠ `swy auth connect`; provider auth is separate |
| F2 | PostHog shutdown warnings after every command | Unresolved (harmless) |
| F3 | `swy init` asks for mode with no explanation | Mode selects manifest endpoint (prod vs sandbox) |
| F4 | `swy init` edits `~/.claude.json` without asking | Unresolved |
| F5 | `swy search --all` = 1329 lines, no pager | Workaround: save to file, grep |
| F6 | Wrekenfile comes from `swy get`, not `swy init` | Verified |
| F7 | Three `swy get` formats: search=`lib.prov@ver`, get=`prov@lib:ver`, docs=`prov` | Use `provider@library:version` |
| F8 | `swy get` fails with SWY-ERR-7F2B06, works after `swy search` | Cache/registry sync issue |
| F9 | `swy get` auto-creates workspace without prompt | Understood |
| F10 | `--explain` warns empty sandbox URL | Set `"mode": "production"` in tooling.json |
| F11 | `--dry-run` needs credentials (exit 3), `--explain` doesn't | Use `--explain` for previews |
| F12 | `--demo` only for Stripe | Understood |
| F13 | `--explain` validates required inputs | Provide `--input` flags for preview |
| F14 | `swy info` = 500-1100 lines, no summary | Pipe to `head`/`grep` |
| F15 | `--json` connect doesn't show GitHub scopes | Only visible on GitHub consent screen |
| F16 | `--json` connect link gives 403, interactive works | Use interactive `swy auth connect Github` |
| F17 | OAuth token storage unclear (WorkOS redirect) | Unresolved (docs say `~/.swytchcode/credentials.db`) |
| F18 | `python3 -m venv` fails on Ubuntu 22.04 | Workaround: `--without-pip` + `get-pip.py` |
| F19 | Canonical IDs hard to distinguish (`get1` vs `list`) | Read `swy info` for each; `get1` = repo-scoped |

---

### `AI_USAGE.md` — 8 AI Interaction Sessions

Honest log of all AI prompts, what worked, what needed correction:

| Session | Task | Worked? |
|---------|------|---------|
| 1 | Safe setup: deny rules, .gitignore, CLAUDE.md, templates | Yes (caught .gitignore excluding Wrekenfile) |
| 2 | Explore registry, fetch GitHub@github:1.1.4 | Yes (after F7/F8 format issues) |
| 3 | Choose/enable methods, test --explain/--dry-run/--demo | Mostly (had wrong facts, corrected) |
| 4 | Read auth docs, extract 5 excerpts | Yes (showed undocumented scopes, WorkOS) |
| 5 | Review GitHub consent screen (screenshot) | Yes (listed broad permissions, chose main account) |
| 6 | Build issue_reporter.py with swytchcode_runtime | Partly (guessed response shape, fixed later) |
| 7 | Fix script against real logs, add offline tests | Yes (tests pass offline) |
| 8 | Readable output, real 404 envelope in tests | Yes (13 tests pass) |

---

### `skills.md` — Swytchcode Integration Skill

The **golden path** for any Swytchcode integration:

1. **Check local state** — `swytchcode list`
2. **Ensure provider present** — `swytchcode get <provider@lib:ver>`
3. **Ensure tool enabled** — `swytchcode add method <canonical_id>` + verify via `swytchcode list tooling`
4. **Inspect contract** — `swytchcode info <canonical_id>`
5. **Generate code** — Only after steps 1-4 complete

**Runtime pattern** (Python):
```python
from swytchcode_runtime import exec
result = exec("canonical.id", { /* args */ })
```

**Auth model**: Check `swytchcode info` for `Auth` section
- `oauth2`/`api_key`/`basic_auth`/`api_key_header` → MANAGED (CLI injects credentials, **don't** read from env)
- No `Auth` or `bearer_token` → UNMANAGED (read from env var, load `.env`)

---

## Verified Canonical IDs (GitHub)

| Operation | Canonical ID | HTTP Method | Path |
|-----------|--------------|-------------|------|
| List issues in ONE repo (SAFE) | `github.issue.get1` | GET | `/repos/{owner}/{repo}/issues` |
| List issues across all repos | `github.issue.list` | GET | `/user/issues` (exposes private) |
| Create issue | `github.issue.create` | POST | `/repos/{owner}/{repo}/issues` |
| Close issue | `github.issue.update` | PATCH | `/repos/{owner}/{repo}/issues/{issue_number}` |
| Comment on issue | `github.issue.comments.create` | POST | `/repos/{owner}/{repo}/issues/{issue_number}/comments` |

**Use `github.issue.get1` for demos** — repo-scoped, requires owner/repo, doesn't expose private repos.

---

## Execution Modes

| Flag | Effect | Credentials Needed? |
|------|--------|---------------------|
| `--explain` | Preview resolved request (method, URL, headers, body) | **No** |
| `--dry-run` | Validate request without calling API | **Yes** (exit 3 if not connected) |
| `--demo` | Mock response (Stripe only) | No (but GitHub not supported) |
| (none) | Live call to production endpoint | Yes |

**Critical**: GitHub's `sandbox_endpoint` is empty. You **must** set `"mode": "production"` in `.swytchcode/tooling.json` for live calls. There is **no `--mode` flag** on `swy exec`.

---

## Swytchcode Response Envelope

Every `swy exec` call returns this shape:

```json
{
  "data": { ... },           // API response body (or error object on 4xx/5xx)
  "request": {               // What was sent
    "method": "POST",
    "url": "https://api.github.com/repos/.../issues"
  },
  "status_code": 201,        // HTTP status
  "error_category": "",      // Empty on success; e.g., "not_found", "validation", "auth"
  "retryable": false,        // True for transient errors (rate_limit, network)
  "suggested_action": ""     // Human-readable guidance
}
```

**On provider 4xx/5xx**: `data` contains GitHub's error object, `error_category` is set, `retryable` indicates if retry is safe.

---

## Key Learnings

1. **Never guess canonical IDs** — always verify with `swytchcode info`
2. **Tooling.json is NOT an execution gate** — `swy exec` works for methods not in tooling.json (e.g., `github.repo.get` worked live despite not being added)
3. **Auth is managed by CLI** — for OAuth providers (GitHub), never read tokens from env; `swy exec` injects `Authorization` header automatically
4. **Production mode only for GitHub** — sandbox endpoint is empty; edit tooling.json
5. **Real envelopes differ from guesses** — issue number at `data.number`, not `result["number"]`
6. **Offline tests are essential** — mock `exec` with real envelopes from `logs/`
7. **`swy search` output is unwieldy** — save to file and grep
8. **Interactive auth works; `--json` connect gives 403** — use `swy auth connect Github` (prompts for library)

---

## Commands Reference

### Swytchcode CLI (run yourself for live operations)
```bash
swy login                          # Sign in to Swytchcode
swy auth connect Github            # Connect GitHub (interactive, opens browser)
swy auth status                    # Check connected providers
swy auth disconnect Github         # Disconnect (revokes backend grant by default)
swy get GitHub@github:1.1.4        # Fetch provider bundle
swy add method github.issue.get1   # Enable method in tooling.json
swy list tooling                   # Show enabled methods
swy info github.issue.get1         # Show method contract (500+ lines)
swy exec github.issue.get1 --explain --input owner=X --input repo=Y  # Preview
swy exec github.issue.create --input owner=X --input repo=Y --body '{"title":"T"}'  # Live
swy doctor                         # Diagnose project setup
swy doctor --network               # Network routing check
swy audit network -n 10            # Last 10 network calls
```

### Project Commands
```bash
# Run script
./venv/bin/python issue_reporter.py --owner OWNER --repo REPO [options]

# Run tests (offline)
./venv/bin/python -m unittest tests.test_issue_reporter -v

# View live results
cat logs/02_create.txt
cat docs/PROJECT_STATE.md

# View friction
cat FRICTION.md

# View AI usage
cat AI_USAGE.md
```

---
