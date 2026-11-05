# AI Usage

Swytchcode PPI task, 3-4 Nov 2026.

## Tools used and how

- **Claude (chat, claude.ai):** planning, reviewing command output, explaining concepts (for example the GitHub consent screen), and drafting the written parts (README, explanation, marketing asset).
- **Claude Code (terminal, in the project folder):** running read-only and `--explain` commands, reading docs, editing project files and writing the example script and tests.

## How I supervised it

- I ran every live command myself: `swy auth connect`, and every live `swy exec` or script run. Claude Code was told never to run live calls, and never to run `git add`, `git commit` or `git push` (enforced by deny rules in `.claude/settings.json` and by `CLAUDE.md`).
- Claude Code sometimes overstated its results (for example marking a guess as verified, writing a wrong command into notes, or editing a file when I had asked only for a proposal, and once attempting a system package install without asking). I checked its output against the raw command output and had it corrected. The files in this repository reflect the corrected state.
- This log lists the prompts needed to reproduce the work. Many short follow-up prompts, used to correct mistakes or re-run commands, are not listed individually.

## Prompts that produced the work

Prompts marked "shortened" are condensed; they keep the instructions that mattered.

### 1. Safe setup (Claude chat)

- **Prompt (summary):** Help me start the Swytchcode task safely: `.claude/settings.json` deny rules for `git add`, `git commit` and `git push`, a `.gitignore` that does not hide the Wrekenfile, `CLAUDE.md` rules (no git writes, no secrets, explain everything, log failures and AI use, no live exec), and templates for FRICTION.md and AI_USAGE.md.
- **Worked?** Yes. A first `.gitignore` also excluded `.swytchcode/integrations/` (where the Wrekenfile lives), which I caught and removed.

### 2. Explore the registry and fetch the integration (Claude Code)

- **Prompt (summary):** Run `swy search` and save the full list to `docs/providers.txt`. Fetch `GitHub@github:1.1.4` with `swy get`. Inspect the Wrekenfile and `manifest.json` and report the number of methods and workflows, the auth type and the endpoints.
- **Result:** 359 providers; a 3.1 MB Wrekenfile with 1,026 methods and 0 workflows; auth oauth2; `production_endpoint` https://api.github.com; empty `sandbox_endpoint`.
- **Worked?** Yes, after using the `provider@library:version` format (friction F7, F8).

### 3. Choose and enable methods; try the safe execution modes (Claude Code)

- **Prompt (summary):** Check canonical IDs with `swy info` for listing issues, creating an issue, updating an issue and commenting. Find a repository-scoped list method. Enable the ones needed with `swy add method`. Run `--explain`, `--dry-run` and `--demo` and report exit codes and exact errors. No live exec.
- **Result:** enabled `github.issue.get1`, `github.issue.create`, `github.issue.update` (and `github.issue.list`). `--explain` works without credentials; `--dry-run` exits 3; `--demo` exists only for Stripe.
- **Worked?** Mostly. Its first notes contained wrong facts that I had corrected (friction F10 to F13).

### 4. Read the authentication docs (Claude Code)

- **Prompt (shortened):** Fetch https://docs.swytchcode.com/cli/authentication/ and https://docs.swytchcode.com/guides/authentication/. Give 3-5 short verbatim excerpts: (a) environment variable names for a GitHub credential, and whether they work for an OAuth provider; (b) GitHub scopes requested; (c) where the OAuth token is stored; (d) what `swy auth disconnect` revokes; (e) plan limits or a 403 on connect. Mark each documented or not documented. Do not set any variable or create any token.
- **Worked?** Yes. It showed that scopes and the WorkOS role are not documented (friction F15, F17).

### 5. Review the GitHub consent screen (Claude chat)

- **Prompt (summary):** I shared a screenshot of the consent screen and asked what the scopes allow before I authorize.
- **Result:** It listed the broad permissions (delete repositories, admin on organizations and SSH keys, workflow files, all private repositories), noted that the app is not owned by GitHub, and laid out options including a throwaway account. I decided to authorize my main account for the demo, knowing the risk, and to disconnect and revoke afterwards.
- **Worked?** Yes.

### 6. Build the example script (Claude Code)

- **Prompt (shortened):** Create `./venv`, `pip install swytchcode-runtime`, and show `pip show swytchcode-runtime` and the signature of `swytchcode_runtime.exec`. Write `issue_reporter.py`: uses only `from swytchcode_runtime import exec` (no HTTP client, no token); `--owner` and `--repo` are required arguments; creates an issue with `github.issue.create`, then closes it with `github.issue.update`; handles the structured error JSON (category, retryable, suggested_action); treats a provider 4xx/5xx as an error; supports `--dry-run` only if the verified signature allows it; has one deliberate-failure option. Do NOT run it live.
- **Worked?** Partly. The structure was right, but it guessed the response shape (`result["number"]`), which the live output later disproved.

### 7. Fix the script against real output and add offline tests (Claude Code)

- **Prompt (shortened):** Real live logs are in `logs/`. Every response has the shape `{"data": ..., "request": ..., "status_code": N}` and the issue number is at `data.number`. Extract the number from `result.get("data", result)`. Keep the provider-error check on `status_code >= 400`. Write `tests/test_issue_reporter.py` that mocks `exec` using the real response shapes copied from the logs (200 empty list, 201 create, 200 close, 404 for the failure demo) and assert the number is extracted, close is called with it, and a 404 counts as an error. Run the tests and show the raw output. No network.
- **Worked?** Yes. The tests pass offline.

### 8. Readable output and the real 404 (Claude Code)

- **Prompt (shortened):** Default output is a short summary per step (operation, status code, issue number, URL, state); `--verbose` prints the full JSON. On a provider error print `status_code`, `error_category`, `retryable` and `suggested_action` from the envelope. In the tests, replace the inferred 404 envelope with the real one from `logs/05_fail_demo.txt`, use a path relative to the test file, add a summary test, and run `python -m unittest discover -s tests -v`.
- **Worked?** Yes. 13 tests pass. My live run of the script produced the short summary.

## Things I did myself

- Ran `swy login`, `swy auth connect Github`, all live `swy exec` commands and all script runs.
- Chose GitHub, chose which methods to enable, and decided how much access to grant.
- Recorded the demo video, and will run the git commands.
