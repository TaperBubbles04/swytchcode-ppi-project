<!-- swytchcode:contract:start -->
# Swytchcode Agent Contract

When writing or changing code that calls an external API or runs a workflow, use
Swytchcode rather than direct HTTP or SDK calls. Read the project-root `skills.md`
before writing integration code. If it is missing, restore it with `swytchcode init`.

- `.swytchcode/tooling.json` lists trusted, enabled tools and the execution mode.
  Confirm the exact canonical ID with `swytchcode list tooling` before generating a call.
  Do not invent IDs or execute tools that are not enabled.
- `.swytchcode/integrations/manifest.json` supplies provider endpoints for the selected
  mode. Use `swytchcode info` and `swytchcode doctor` to inspect the setup. Do not
  bypass the configured endpoint with a direct request.
- `.swytchcode/integrations/policies.json` contains guard policies evaluated before
  execution. Check them with `swytchcode policy list` when relevant. Honor blocks and
  required approvals; surface the policy instruction instead of bypassing it.

Use Swytchcode CLI or MCP tools to inspect project state and tool contracts. Keep
provider bundle internals behind those interfaces.
<!-- swytchcode:contract:end -->

# Internship Task Rules (Hard Rules)

**These rules override any default behavior and MUST be followed exactly as written.**

## Rule 1: Git Commands
NEVER run `git add`, `git commit`, `git push`, `git rebase`, `git reset` or any git command that changes history/staging/remotes. Instead, give me the exact commands in a "RUN THESE YOURSELF" block and explain what each does. Read-only git (`status`, `diff`, `log`) is fine.

## Rule 2: Secrets
Never print, log, or write secrets (API keys, tokens, passwords). Use environment variables and a gitignored `.env`. If a command output might contain a secret, warn me before showing it.

## Rule 3: Explain Everything
Explain everything in simple terms BEFORE doing it: every command, every file you create, every concept (Wrekenfile, canonical ID, tooling.json, sandbox mode, policy, dry-run). I must be able to explain all of it in an interview.

## Rule 4: No Hidden Tasks
Never leave important things for me to remember. At the end of EVERY reply include two blocks:
- **FOR YOU TO CHECK**: the specific files/outputs I should open and look at, and what to look for.
- **RUN THESE YOURSELF**: commands I must run myself (git, account/key creation, anything needing my login), or "none".
Flag anything risky, surprising or irreversible clearly and early, in a "HEADS UP" line.

## Rule 5: Log Failures
Don't hide failures. Any confusing or failing step goes into FRICTION.md immediately, and you tell me when you've added an entry.

## Rule 6: Log AI Usage
Log AI usage in AI_USAGE.md as we go (prompt + whether the answer worked), and tell me when you add to it.

## Rule 7: Don't Overwrite
Don't overwrite existing files (e.g. CLAUDE.md); append to them and tell me.

## Rule 8: No Global Changes
Don't install global packages or change system config without asking me first.

## Rule 9: No Live Exec
NEVER run a LIVE `swy exec` (or the swytchcode MCP exec tool) yourself. You may only run exec with `--explain`, `--dry-run` or `--demo`. Any live call, `swy auth connect`, or `swy login` is for ME to run; give me the exact command in RUN THESE YOURSELF. Provider: GitHub only (already fetched: GitHub@github:1.1.4). Don't fetch any other provider. Don't create accounts, keys or OAuth apps.
