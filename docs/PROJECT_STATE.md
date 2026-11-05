# Project State

**Last Updated**: 2026-11-04
**Stage**: Wrekenfile analyzed, canonical IDs verified, swy add done for 4 methods (github.issue.create, github.issue.get1, github.issue.list, github.issue.update), --explain/--dry-run/--demo tested, swy doctor run, demos explored, auth reconciled, tooling.json mode set to production, network diagnostics run, live commands executed, unittest written

---

## What Works / Exact Commands

### Provider Setup
```bash
swy get GitHub@github:1.1.4    # Fetches provider bundle, creates Wrekenfile + methods.json, auto-creates workspace "swyproject" in tooling.json
```

### Current tooling.json (trimmed by jq)
```json
{
  "editor": "claude",
  "integrations": {
    "GitHub.github": {
      "version": "1.1.4"
    }
  },
  "mode": "production",
  "tools": {
    "github.issue.create": {
      "integration": "GitHub.github@1.1.4",
      "method_hash": "fffa8d8a62b4ed9b172b323ee8dd6e972a3200f3701ae42679be5048ab1cbdab",
      "summary": "Create an issue",
      "type": "method"
    },
    "github.issue.get1": {
      "integration": "GitHub.github@1.1.4",
      "method_hash": "7eb35a7c4de1f83e2c52f1c4c68227d53c38737d55987343d09f3f23152639ba",
      "summary": "List repository issues",
      "type": "method"
    },
    "github.issue.list": {
      "integration": "GitHub.github@1.1.4",
      "method_hash": "2f4d5b0008ded72dc1374d9a0c5e9f50ccf8e74a4133525e6afbde7f6c50cb00",
      "summary": "List issues assigned to the authenticated user",
      "type": "method"
    },
    "github.issue.update": {
      "integration": "GitHub.github@1.1.4",
      "method_hash": "fc73fdc13d56d5135b17ae71f2ba456473de38cc12d4ed05c9ad07f99ac9d1c2",
      "summary": "Update an issue",
      "type": "method"
    }
  },
  "version": "2.25.1",
  "workspace": "swyproject"
}
```

**GitHub Repository for demo**: `TaperBubbles04/swytchcode-ppi-project` (owner=TaperBubbles04, repo=swytchcode-ppi-project)

### Verified Canonical IDs (via `swy info`)
| Operation | Canonical ID | Key Inputs |
|-----------|--------------|------------|
| List issues across all repos (read) | `github.issue.list` | filter, state, labels, sort, direction, since, per_page, page (all optional query) |
| **List issues in ONE repo (SAFE read)** | **`github.issue.get1`** | **owner (path, req), repo (path, req), milestone, state, assignee, type (all optional query)** |
| Create issue (write) | `github.issue.create` | owner (path, req), repo (path, req), body.title (req), body.body, body.assignee, body.milestone, body.labels, body.assignees |
| Comment on issue | `github.issue.comments.create` | owner, repo, issue_number (path), body.body (req) |
| Close issue | `github.issue.update` | owner, repo, issue_number (path), body.state="closed" |
| Get user by ID | `github.user.get` | account_id (path, req, INT) |
| Get user by username | `github.user.get1` | username (path, req, STRING) |
| **Get authenticated user** | **NONE EXISTS** | GitHub API `GET /user` not exposed as a method |

**Recommended for demo**: Read = `github.issue.get1` (repo-scoped, requires owner/repo, doesn't expose private repos), Write = `github.issue.create` (reversible via close with `github.issue.update` state=closed)

---

## HTTP Method/Path Summary (Task 3)

| Canonical ID | HTTP Method | Path |
|--------------|-------------|------|
| `github.issue.get1` | GET | `/repos/{owner}/{repo}/issues` |
| `github.issue.update` | PATCH | `/repos/{owner}/{repo}/issues/{issue_number}` |

---

## Tooling Changes (Task 4)

**Before `swy add method github.issue.update`:**
```
Enabled Methods (tooling.json):
  github.issue.create  GitHub.github@1.1.4
  github.issue.get1    GitHub.github@1.1.4
  github.issue.list    GitHub.github@1.1.4
```

**After `swy add method github.issue.update`:**
```
Enabled Methods (tooling.json):
  github.issue.create  GitHub.github@1.1.4
  github.issue.get1    GitHub.github@1.1.4
  github.issue.list    GitHub.github@1.1.4
  github.issue.update  GitHub.github@1.1.4
```

**Remove tool command**: No `swy remove` command exists. Tools must be removed by manually editing `tooling.json` (delete the entry from the `"tools"` object).

---

## Exact Error Messages Encountered

1. **F7**: `swy get GitHub.github@1.1.4` → `error: invalid get target "GitHub.github@1.1.4": expected provider@library:version`
2. **F8**: `swy get GitHub@github:1.1.4` → `× Failed to fetch provider bundles. Reference ID: SWY-ERR-7F2B06 ... hint: run 'swytchcode search GitHub'` (succeeded after `swy search GitHub`)
3. **F9**: `swy get GitHub@github:1.1.4` → `Created workspace "swyproject"` (auto, no prompt)
4. **--explain (sandbox)**: `⚠ base URL for GitHub.github@1.1.4 (sandbox) is not set: ""` — sandbox_endpoint is empty in manifest.json
5. **--dry-run**: `missing credentials for GitHub - run 'swytchcode auth connect GitHub'` (exit code 3, ref SWY-ERR-C17477)
6. **--demo**: `Demo unavailable for github.issue.list: no demo available — supported: stripe.create_payment` (exit code 4)
7. **swy doctor**: Warning about empty sandbox_endpoint, "All checks passed (no errors)"
8. **swy exec github.issue.get1 --explain (production)**: Mode: production, Endpoint: GET https://api.github.com/repos/{owner}/{repo}/issues — **no sandbox warning**
9. **swy doctor --network**: Shows DIRECT execution routing, telemetry/billing/update/registry endpoints, all checks passed
10. **swy audit network -n 10**: Shows network calls to api-v2.swytchcode.com (404 on github.issue.create/list) — likely provider bundle fetches

---

## Decisions Made

1. **Format for `swy get`**: Use `provider@library:version` (e.g., `GitHub@github:1.1.4`), not the `library.provider@version` from `swy search`.
2. **Sandbox mode for GitHub**: manifest.json has `"sandbox_endpoint": ""`, so sandbox mode uses a dummy URL. Live calls require `"mode": "production"` in tooling.json to hit `https://api.github.com`.
3. **Auth**: GitHub uses OAuth2. Credentials stored in `~/.swytchcode/credentials.db` (not in project). Run `swy auth connect GitHub` to connect (user must do this). **[UNVERIFIED - not tested live]**
4. **No demo for GitHub**: `--demo` only works for specific methods that have demo implementations (e.g., Stripe). Not available for GitHub.
5. **Workflows**: 0 workflows for GitHub (`swy list workflows` returns `{}`). Workflow = multi-step opaque tool combining methods.
6. **MCP tools exposed (7)**: add, discover, exec, info, list, policy, search (agent profile).
7. **swy exec input modes**: CLI flags (`--input`, `--param`, `--header`, `--body`) OR JSON on stdin. Both work; `--input` takes precedence.
8. **Run GitHub live**: Set `"mode": "production"` in tooling.json. **No `--mode` flag on exec exists** (verified via `swy exec --help`). No env var documented.
9. **Demo behavior**: `swy demo stripe` makes a REAL network call to Stripe demo account (creates payment). Not a local mock. **[UNVERIFIED - not tested]**
10. **Auth reconciliation**: Backend holds OAuth grant (authorization), NOT credentials. `credentials.db` never synced. `swy auth disconnect` revokes backend grant by default; `--local` only forgets local credential. **[UNVERIFIED - inferred from docs/behavior, not tested live]**

---

## Corrections (2026-11-04)

**Previous claim**: "Live calls REQUIRE `--mode production` to hit `https://api.github.com`" and "Set `"mode": "production"` in tooling.json, OR use `swy exec <method> --mode production` if supported (check docs)."

**Corrected**: `swy exec --help` shows **no `--mode` flag**. The execution mode is set **only** via the top-level `"mode"` field in `tooling.json` (values: `"production"` | `"sandbox"`). This is documented at https://docs.swytchcode.com/configuration/tooling-json/. GitHub's `sandbox_endpoint` is empty, so sandbox mode cannot work for GitHub; you must set `"mode": "production"` in `tooling.json` before live calls.

**Previous RUN THESE YOURSELF commands** used `--mode production` flag — those are incorrect. Correct approach: edit `tooling.json` to set `"mode": "production"`.

---

## Docs Excerpts (Task 7)

Fetched from https://docs.swytchcode.com/cli/authentication/ and https://docs.swytchcode.com/guides/authentication/

| Topic | Documented? | Verbatim Excerpt |
|-------|-------------|------------------|
| (a) Env var names/patterns for GitHub credential; env var for OAuth? | Not documented | "Environment variables have the highest priority. This is the recommended approach for: Production deployments, CI/CD pipelines, Secret management systems, Containerized applications" (guides/authentication/) — no GitHub-specific env var name or OAuth-via-env-var guidance |
| (b) GitHub scopes requested | Not documented | No mention of GitHub scopes in either page |
| (c) Where OAuth token is stored | Documented (partial) | "When you authenticate with an integration, the CLI writes the credential to `~/.swytchcode/credentials.db` - a local SQLite database in your home directory" (cli/authentication/) — does not mention WorkOS or backend storage |
| (d) What `swy auth disconnect` revokes | Documented | "Removing an integration revokes its local credentials and prevents future tool executions until it is connected again. By default this also revokes access on the Swytchcode backend. If you only want to forget the credential on this machine and keep the connection active elsewhere, pass `--local`" (cli/authentication/) |
| (e) Plan limits on managed OAuth or 403 on connect | Plan limits: documented (monthly live-command count); 403 on connect / OAuth-specific limits: not documented | "Every plan includes a monthly number of live commands. When you reach it, Swytchcode tells you how many you've used and how to upgrade. Your limit resets each month. Only live commands count. Dry runs, `--explain`, and demos are free. Agents and CI: commands run with an API key (`swy_key_...`) don't count toward your monthly limit." (cli/authentication/) — no mention of 403 on connect or OAuth-specific limits |

---

## Live Results (2026-11-04)

Three live commands run by user against `TaperBubbles04/swytchcode-ppi-project` (production mode, GitHub connected) using `--input` flags:

### 1. List issues (`swy exec github.issue.get1`)
```bash
swy exec github.issue.get1 --input owner=TaperBubbles04 --input repo=swytchcode-ppi-project
```
**Returned**: `status_code: 200`, `data: []` (empty list)

### 2. Create issue (`swy exec github.issue.create`)
```bash
swy exec github.issue.create --input owner=TaperBubbles04 --input repo=swytchcode-ppi-project --body '{"title":"Swytchcode PPI test","body":"Created via swy exec"}'
```
**Returned**: `status_code: 201`, `data.number: 1` (issue #1 created)

### 3. Close issue (`swy exec github.issue.update`)
```bash
swy exec github.issue.update --input owner=TaperBubbles04 --input repo=swytchcode-ppi-project --input issue_number=1 --body '{"state":"closed"}'
```
**Returned**: `status_code: 200`, `data.number: 1` (issue #1 closed, state=closed)

### 4. Script run: create + close issue #2 (`logs/04_script_run.txt`)
The script `issue_reporter.py` was run live (no `--dry-run`), creating issue #2 then closing it:
- **Create**: `status_code: 201`, `data.number: 2`, `state: open`
- **Close**: `status_code: 200`, `data.number: 2`, `state: closed`

### 5. Fail demo: close #999999 (`logs/05_fail_demo.txt`)
```bash
swy exec github.issue.update --input owner=TaperBubbles04 --input repo=swytchcode-ppi-project --input issue_number=999999 --body '{"state":"closed"}'
```
**Returned**: `status_code: 404`, `error_category: not_found`, `retryable: false`, `suggested_action: "the target resource does not exist; check the ids and the endpoint"`

### Response Envelope (all responses)
```json
{
  "data": {...},
  "request": {"method": "...", "url": "..."},
  "status_code": N,
  "error_category": "...",
  "retryable": true|false,
  "suggested_action": "..."
}
```
- List (01_read.txt): `data=[]`, `status_code=200`
- Create #1 (02_create.txt): `data={..., "number":1, ...}`, `status_code=201`
- Close #1 (03_close.txt): `data={..., "number":1, "state":"closed", ...}`, `status_code=200`, `state=closed`
- Create #2 (04_script_run.txt): `data={..., "number":2, "state":"open", ...}`, `status_code=201`
- Close #2 (04_script_run.txt): `data={..., "number":2, "state":"closed", ...}`, `status_code=200`
- Fail demo (05_fail_demo.txt): `data={documentation_url, message, status}`, `status_code=404`, `error_category=not_found`, `retryable=false`, `suggested_action="the target resource does not exist; check the ids and the endpoint"`

**Note**: `logs/03_close.txt` has `status_code: 200` and `state: closed` in the response data.