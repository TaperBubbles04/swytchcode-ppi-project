# Swytchcode PPI Project — Reference Implementation

**Demo Video**: https://youtu.be/N30U2W8G2hw

---

## Problem and Intended User

**Problem**: Calling external APIs requires writing and maintaining HTTP clients, handling auth, parsing responses, and dealing with errors — boilerplate that repeats for every integration.

**Intended User**: Developers exploring Swytchcode who want a minimal, working example of using the runtime (`from swytchcode_runtime import exec`) to call GitHub issue operations without writing raw HTTP code.

**What This Project Does**: A small Python CLI (`issue_reporter.py`) that lists, creates, and closes GitHub issues using Swytchcode-enabled methods (`github.issue.get1`, `github.issue.create`, `github.issue.update`). It handles the structured response envelope Swytchcode returns and includes offline tests using real response shapes from live runs.

---

## API/Integration Explored

**Provider**: GitHub (`GitHub@github:1.1.4`)
- **Source**: `swy get GitHub@github:1.1.4` (fetches provider bundle from Swytchcode registry)
- **Wrekenfile**: 3.1 MB YAML at `.swytchcode/integrations/GitHub/github/1.1.4/wrekenfile.yaml`
- **Methods**: 1,026 methods, 0 workflows
- **Auth**: OAuth2 (managed by Swytchcode CLI — tokens stored in `~/.swytchcode/credentials.db`, injected automatically)
- **Endpoints**:
  - Production: `https://api.github.com` (used for all live calls)
  - Sandbox: empty (not usable for GitHub)

**Methods Used** (enabled via `swy add method`):

| Operation | Canonical ID | HTTP Method | Path |
|-----------|--------------|-------------|------|
| List issues in ONE repo (SAFE read) | `github.issue.get1` | GET | `/repos/{owner}/{repo}/issues` |
| List issues across all repos | `github.issue.list` | GET | `/user/issues` (exposes private repos) |
| Create issue | `github.issue.create` | POST | `/repos/{owner}/{repo}/issues` |
| Close issue | `github.issue.update` | PATCH | `/repos/{owner}/{repo}/issues/{issue_number}` |

---

## Setup and Commands

### Prerequisites
- Python 3.10+
- `swytchcode` CLI installed (`pip install swytchcode` or download from https://swytchcode.com)
- GitHub account for OAuth connection

### 1. Clone and Create Virtual Environment
```bash
git clone https://github.com/TaperBubbles04/swytchcode-ppi-project
cd swyproject

# Ubuntu 22.04 workaround for ensurepip (F18)
python3 -m venv venv --without-pip
curl -sS https://bootstrap.pypa.io/get-pip.py | ./venv/bin/python
./venv/bin/pip install swytchcode-runtime
```

### 2. Initialize Swytchcode Project
```bash
swy init                              # Choose "production" mode (not sandbox — F3)
swy get GitHub@github:1.1.4           # Fetches bundle, creates Wrekenfile + workspace (F6, F9)
swy add method github.issue.get1      # Enable repo-scoped list
swy add method github.issue.create    # Enable create
swy add method github.issue.update    # Enable close
swy add method github.issue.list      # Enable cross-repo list (for comparison)
```

### 3. Connect GitHub (run yourself — live auth)
```bash
swy auth connect Github               # Interactive: prompts for library, opens browser
# Note: `swy auth connect GitHub --json` returns 403 on the auth link (F16) — use interactive
```

### 4. Set Production Mode (required — GitHub sandbox is empty)
```bash
# Edit .swytchcode/tooling.json: "mode": "production"
jq '.mode = "production"' .swytchcode/tooling.json > tmp && mv tmp .swytchcode/tooling.json
```

### 5. Run the CLI (issue_reporter.py)
```bash
# List issues (read)
./venv/bin/python issue_reporter.py --owner TaperBubbles04 --repo swytchcode-ppi-project --list

# Create + close an issue (write + write)
./venv/bin/python issue_reporter.py --owner TaperBubbles04 --repo swytchcode-ppi-project \
  --title "Test issue" --body "Created via Swytchcode"

# Dry-run (preview, no live call)
./venv/bin/python issue_reporter.py --owner TaperBubbles04 --repo swytchcode-ppi-project \
  --title "Test" --body "Test" --dry-run

# Fail demo: attempt to close non-existent issue #999999 (shows 404 handling)
./venv/bin/python issue_reporter.py --owner TaperBubbles04 --repo swytchcode-ppi-project --fail-demo

# Verbose: full JSON response
./venv/bin/python issue_reporter.py --owner TaperBubbles04 --repo swytchcode-ppi-project --list --verbose
```

### 6. Run Offline Tests (no network)
```bash
./venv/bin/python -m unittest tests.test_issue_reporter -v
# 13 tests pass — mocks exec with real envelopes from logs/
```

### 7. Useful Swytchcode CLI Commands (for exploration)
```bash
swy search GitHub                     # Find provider (28 lines; --all = 1329 lines, F5)
swy list tooling                      # Show enabled methods
swy info github.issue.get1            # Contract (500-1100 lines, F14 — pipe to head/grep)
swy exec github.issue.get1 --explain --input owner=X --input repo=Y  # Preview request
swy doctor                            # Diagnose setup (warns about empty sandbox_endpoint)
swy doctor --network                  # Network routing check
```

---

## What Worked

| Operation | Command | Result |
|-----------|---------|--------|
| List issues | `swy exec github.issue.get1 --input owner=TaperBubbles04 --input repo=swytchcode-ppi-project` | `status_code: 200`, `data: []` (empty list) |
| Create issue #1 | `swy exec github.issue.create --input owner=... --body '{"title":"Swytchcode PPI test","body":"..."}'` | `status_code: 201`, `data.number: 1` |
| Close issue #1 | `swy exec github.issue.update --input issue_number=1 --body '{"state":"closed"}'` | `status_code: 200`, `data.state: "closed"` |
| Script run (create #2 + close #2) | `./venv/bin/python issue_reporter.py ...` | Create `201` #2, Close `200` #2 |
| Fail demo (close #999999) | `swy exec github.issue.update --input issue_number=999999 ...` | `status_code: 404`, `error_category: not_found`, `retryable: false` |
| Offline tests | `./venv/bin/python -m unittest tests.test_issue_reporter -v` | **13/13 pass** |

**Swytchcode Response Envelope** (all responses follow this shape):
```json
{
  "data": { "number": 1, "title": "...", "state": "open", "html_url": "..." },
  "request": { "method": "POST", "url": "https://api.github.com/repos/.../issues" },
  "status_code": 201,
  "error_category": "",
  "retryable": false,
  "suggested_action": ""
}
```
On 4xx/5xx: `data` contains provider error, `error_category` set (e.g., `not_found`), `retryable` indicates if retry is safe.

**Key Working Patterns**:
- `swy exec --explain` works **without credentials** (F11) — use for previews
- `swy exec` (live) injects OAuth `Authorization` header automatically — no env vars needed
- Production mode set in `tooling.json` (no `--mode` flag on exec — corrected in PROJECT_STATE.md)
- Offline tests mock `swytchcode_runtime.exec` with real envelopes from `logs/`

---

## What Did Not Work and Errors Encountered

**19 friction entries documented in `FRICTION.md`** — each records: step, command, expected, actual (exact error), tried next, resolved.

| ID | Issue | Resolution |
|----|-------|------------|
| **F1** | `swy auth status` = "No connected accounts" after `swy login` | `swy login` ≠ `swy auth connect`; provider auth is separate |
| **F2** | PostHog shutdown warnings after every command | Unresolved (harmless telemetry noise) |
| **F3** | `swy init` asks for mode with no explanation | Mode selects manifest endpoint (production vs sandbox) |
| **F4** | `swy init` edits `~/.claude.json` without asking | Unresolved |
| **F5** | `swy search --all` = 1329 lines, no pager | Workaround: save to `docs/providers.txt`, grep |
| **F6** | Wrekenfile not from `swy init` | Comes from `swy get` (verified) |
| **F7** | Three `swy get` formats | Use `provider@library:version` (e.g., `GitHub@github:1.1.4`) |
| **F8** | `swy get` fails SWY-ERR-7F2B06, works after `swy search` | Cache/registry sync issue |
| **F9** | `swy get` auto-creates workspace without prompt | Understood |
| **F10** | `--explain` warns empty sandbox URL | Set `"mode": "production"` in tooling.json |
| **F11** | `--dry-run` needs credentials (exit 3), `--explain` doesn't | Use `--explain` for previews |
| **F12** | `--demo` only for Stripe | Understood — not available for GitHub |
| **F13** | `--explain` validates required inputs | Provide `--input` flags for preview |
| **F14** | `swy info` = 500-1100 lines, no summary | Pipe to `head`/`grep` |
| **F15** | `--json` connect doesn't show GitHub scopes | Only visible on GitHub consent screen |
| **F16** | `--json` connect link gives 403, interactive works | Use `swy auth connect Github` (interactive) |
| **F17** | OAuth token storage unclear (WorkOS redirect) | Unresolved (docs say `~/.swytchcode/credentials.db`) |
| **F18** | `python3 -m venv` fails on Ubuntu 22.04 | Workaround: `--without-pip` + `get-pip.py` |
| **F19** | Canonical IDs hard to distinguish (`get1` vs `list`) | Read `swy info` for each; `get1` = repo-scoped |

---

## How to Reproduce

### From Scratch (Clean Environment)
```bash
# 1. Clone
git clone https://github.com/TaperBubbles04/swytchcode-ppi-project
cd swyproject

# 2. Python environment
python3 -m venv venv --without-pip
curl -sS https://bootstrap.pypa.io/get-pip.py | ./venv/bin/python
./venv/bin/pip install swytchcode-runtime

# 3. Swytchcode project (run these yourself)
swy init                              # Pick "production"
swy get GitHub@github:1.1.4
swy add method github.issue.get1
swy add method github.issue.create
swy add method github.issue.update
swy add method github.issue.list

# 4. Connect GitHub (run yourself — interactive)
swy auth connect Github

# 5. Set production mode
jq '.mode = "production"' .swytchcode/tooling.json > tmp && mv tmp .swytchcode/tooling.json

# 6. Run the CLI
./venv/bin/python issue_reporter.py --owner TaperBubbles04 --repo swytchcode-ppi-project --list
./venv/bin/python issue_reporter.py --owner TaperBubbles04 --repo swytchcode-ppi-project \
  --title "Test" --body "Test body"

# 7. Run tests (offline)
./venv/bin/python -m unittest tests.test_issue_reporter -v
```

### Verify Live Results
```bash
# View exact response envelopes from live runs
cat logs/01_read.txt      # List: 200, data: []
cat logs/02_create.txt    # Create #1: 201, data.number: 1
cat logs/03_close.txt     # Close #1: 200, state: closed
cat logs/04_script_run.txt # Script: create #2 (201), close #2 (200)
cat logs/05_fail_demo.txt # Fail demo: 404, not_found, retryable: false

# View aggregated live results
cat docs/PROJECT_STATE.md
```

### View Friction & AI Usage
```bash
cat FRICTION.md    # 19 entries with exact errors and resolutions
cat AI_USAGE.md    # 8 AI interaction sessions (honest log)
```

---

## Link to Demo

**Demo Video**: https://youtu.be/N30U2W8G2hw

Shows:
- Project structure and key files
- Swytchcode CLI commands (`swy get`, `swy add method`, `swy exec --explain`, live `swy exec`)
- Running `issue_reporter.py` (list, create, close, fail-demo, dry-run)
- Offline tests passing
- One key learning: the Swytchcode response envelope structure

---

## Notes on the Generated Wrekenfile

**Location**: `.swytchcode/integrations/GitHub/github/1.1.4/wrekenfile.yaml`

**Generated by**: `swy get GitHub@github:1.1.4` (NOT by `swy init` — see F6)

**Contents**:
- **1,026 method definitions** — each with canonical ID, HTTP method, path, input/output schemas, auth requirements
- **0 workflows** — GitHub provider has no multi-step workflows
- **Manifest reference** — points to `manifest.json` for endpoints and auth config
- **Method hashes** — each method has a content hash (e.g., `github.issue.get1` = `7eb35a7c4de1f83e2c52f1c4c68227d53c38737d55987343d09f3f23152639ba`) used in `tooling.json` for version pinning

**Key Observations**:
- The Wrekenfile is the **single source of truth** for all GitHub API operations Swytchcode supports
- Canonical IDs are auto-generated (e.g., `github.issue.get1`, `github.issue.list`) — not human-friendly; must inspect via `swy info` to understand scope (F19)
- `github.issue.get1` = GET `/repos/{owner}/{repo}/issues` (repo-scoped, safe)
- `github.issue.list` = GET `/user/issues` (cross-repo, exposes private repos)
- No `GET /user` method exists for authenticated user — confirmed via `swy search` and `swy info`
- The file is **read-only** — developers don't edit it; they enable methods via `swy add method` which updates `tooling.json`

**Related Files in Same Directory**:
- `manifest.json` — endpoints (`production_endpoint: "https://api.github.com"`, `sandbox_endpoint: ""`), auth type (`oauth2`), scopes
- `methods.json` — index of all 1,026 method canonical IDs

---

## Project Files Reference

| File | Purpose |
|------|---------|
| `issue_reporter.py` | Main CLI — uses `swytchcode_runtime.exec` only |
| `tests/test_issue_reporter.py` | 13 offline unit tests with real envelope mocks |
| `docs/PROJECT_STATE.md` | Live results, decisions, corrections, docs excerpts |
| `FRICTION.md` | 19 friction entries (step, command, expected, actual, tried, resolved) |
| `AI_USAGE.md` | 8 AI sessions (prompt, worked?, notes) |
| `skills.md` | Swytchcode integration golden path (5-step workflow) |
| `.swytchcode/tooling.json` | Enabled methods + execution mode |
| `.claude/CLAUDE.md` | Agent contract + 9 hard rules (no git writes, no secrets, explain everything, etc.) |
| `logs/*.txt` | Raw response envelopes from 5 live command runs |

---

## Key Learnings (Summary)

1. **Never guess canonical IDs** — verify with `swytchcode info`
2. **Tooling.json is NOT an execution gate** — `swy exec` works for methods not in tooling.json
3. **Auth is managed by CLI** — for OAuth, never read tokens from env; CLI injects header automatically
4. **Production mode only for GitHub** — sandbox endpoint empty; edit `tooling.json`
5. **Real envelopes differ from guesses** — issue number at `data.number`, not `result["number"]`
6. **Offline tests are essential** — mock `exec` with real envelopes from `logs/`
7. **`swy search` output is unwieldy** — save to file and grep
8. **Interactive auth works; `--json` connect gives 403** — use `swy auth connect Github`

---