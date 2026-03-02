# Tool Development Requirements
**Version:** 1.0
**Purpose:** Standards, security guardrails, and style requirements for all scripts and tools in this repo. An LLM building any tool over ~200 lines must read this file first and comply before delivering code.
**Scope:** All Python, Bash/Shell, and Node.js/JavaScript tools committed to this repo.
**Audience:** LLMs generating tools. Humans reviewing them.

---

## When to Build a Tool

Build a script or tool — and commit it to the repo — when any of the following are true:

- Logic exceeds ~200 lines
- The operation will be run more than once
- The operation reads or writes files, JSON, or external state
- The operation requires argument parsing, error handling, or logging
- The output needs to be consistent and reproducible across sessions

For anything under ~200 lines used once, inline code or a short LLM-executed block is sufficient. Do not create files for throwaway logic.

When in doubt: if you'd want to run it again next week, it's a tool.

---

## Before Writing Any Code

Produce a brief plan and present it for approval before writing code for any tool over ~200 lines:

```
TOOL PLAN

Name:         [filename and repo path]
Purpose:      [one sentence]
Language:     [Python | Bash | Node.js]
Style guide:  [declared standard — see below]
Inputs:       [args, files, stdin]
Outputs:      [files, stdout, exit codes]
Dependencies: [external packages required]
Security:     [any credentials, user data, or sensitive inputs handled?]
Estimated lines: [approximate]
Integration:  [which specs or scripts invoke this, if any]
```

Do not proceed to implementation until the plan is confirmed.

---

## Language Standards

### Python

**Default standard:** PEP 8
**Linter:** `flake8` or `ruff` (preferred)
**Formatter:** `black` (optional but encouraged)

Required conventions:
- Type hints on all function signatures
- Docstring on every module, class, and public function (Google style)
- `if __name__ == "__main__":` guard on all executable scripts
- `argparse` for CLI argument handling — no `sys.argv` indexing
- Standard library preferred over third-party where capability is equivalent
- Third-party dependencies declared in `requirements.txt` with pinned versions

```python
# Correct
def load_run(path: str) -> dict:
    """Load a pipeline run JSON from disk.

    Args:
        path: Absolute or relative path to the run JSON file.

    Returns:
        Parsed run dictionary.

    Raises:
        FileNotFoundError: If the path does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
```

### Bash / Shell

**Default standard:** Google Shell Style Guide
**Linter:** `shellcheck` (flag all warnings — do not suppress without justification)

Required conventions:
- `#!/usr/bin/env bash` shebang — not `/bin/sh` unless POSIX compliance is explicitly required
- `set -euo pipefail` at the top of every script
- Quote all variable expansions: `"${variable}"` not `$variable`
- Local variables in functions declared with `local`
- Constants in `UPPER_SNAKE_CASE`
- Meaningful exit codes — `exit 0` on success, non-zero on failure
- No parsing of `ls` output — use globs or `find`

```bash
#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

main() {
    local run_path="${1:?Usage: script.sh <run_path>}"
    # ...
}

main "$@"
```

### Node.js / JavaScript

**Default standard:** Airbnb JavaScript Style Guide
**Linter:** `eslint` with `eslint-config-airbnb-base`
**Formatter:** `prettier` (configure to match Airbnb defaults)

Required conventions:
- `"use strict"` or ES modules (`import`/`export`) — no mixed mode
- `const` by default, `let` when reassignment is necessary, never `var`
- Arrow functions for callbacks and short functions
- Async/await over raw Promise chains
- `package.json` with pinned dependency versions (`npm install --save-exact`)
- `.nvmrc` or `engines` field in `package.json` to declare Node version

```javascript
// Correct
const loadRun = async (filePath) => {
  const raw = await fs.readFile(filePath, 'utf8');
  return JSON.parse(raw);
};
```

---

## Declaring Your Standard

Every tool must include a standards declaration in its module-level docstring or header comment:

**Python:**
```python
"""
Tool Name
=========
[Purpose — one sentence]

Style: PEP 8
Deviations: [list any, with justification — or "None"]
"""
```

**Bash:**
```bash
# Tool Name
# Purpose: [one sentence]
# Style: Google Shell Style Guide
# Deviations: [list any, with justification — or "None"]
```

**Node.js:**
```javascript
/**
 * Tool Name
 * Purpose: [one sentence]
 * Style: Airbnb JavaScript Style Guide
 * Deviations: [list any, with justification — or "None"]
 */
```

A deviation is any intentional departure from the declared standard. It must be named and justified. An unjustified deviation is a defect.

---

## Security Requirements

These are non-negotiable. No tool is compliant without meeting all of them.

### No Secrets or Credentials in Code

- Never hardcode API keys, tokens, passwords, connection strings, or any credential
- Credentials are always read from environment variables or a secrets manager
- `.env` files are for local development only — never committed to the repo
- Add `.env` to `.gitignore` if it doesn't already exist

```python
# Correct
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set")

# Never
api_key = "sk-ant-..."
```

If a tool requires credentials, document required environment variables in the tool's docstring and in a `## Environment Variables` section of the README or tool header.

### Logging Without Sensitive Data

- Never log credentials, tokens, API keys, or PII
- Never log raw request/response bodies that may contain sensitive content unless explicitly scrubbed
- Log file paths, operation names, counts, and status — not content
- Use log levels correctly: `DEBUG` for development detail, `INFO` for normal operation, `WARNING` for recoverable issues, `ERROR` for failures

```python
# Correct
logger.info("Loaded run JSON: %s (%d events)", run_path, len(events))

# Never
logger.debug("API response: %s", response_body)  # may contain sensitive data
```

If a tool logs to a file, the log path must be configurable and must not default to a location outside the repo or user home directory.

---

## Error Handling

- All file operations wrapped in try/except (Python) or checked with `[[ -f ]]` (Bash)
- All external calls (HTTP, subprocess, file I/O) handle failure explicitly
- Errors produce a meaningful message to stderr and exit with a non-zero code
- Never silently swallow exceptions

```python
# Correct
try:
    run = load_run(args.run)
except FileNotFoundError:
    print(f"ERROR: Run file not found: {args.run}", file=sys.stderr)
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"ERROR: Invalid JSON in {args.run}: {e}", file=sys.stderr)
    sys.exit(1)
```

---

## Structure and Maintainability

### File Header

Every tool file begins with: name, purpose, usage examples, dependencies, and repo path. This is the minimum context needed for an LLM or human to understand the tool without reading the implementation.

### Function Size

Functions do one thing. If a function exceeds ~40 lines, it likely does more than one thing. Split it.

### Naming

- Variables and functions: descriptive, not abbreviated. `run_date` not `rd`. `load_events` not `le`.
- Constants: `UPPER_SNAKE_CASE`
- Files: `lower_snake_case.py`, `kebab-case.js`, `kebab-case.sh`

### Dependencies

- Prefer standard library over third-party where capability is equivalent
- Every third-party dependency must be justified in the tool plan
- Python: pin versions in `requirements.txt` (`package==1.2.3`)
- Node.js: pin versions in `package.json` (`"package": "1.2.3"`)
- Bash: document any non-standard tool dependencies (e.g. `jq`, `curl`) in the header comment

### CLI Interface

All tools with a command-line interface must:
- Accept `--help` and produce useful output
- Use long-form flags (`--run`, not `-r`) as the primary interface
- Validate required arguments and fail fast with a clear message if missing
- Exit 0 on success, non-zero on any failure

---

## Repo Integration

When a new tool is committed to the repo:

1. **Add to `/scripts/` directory** — all tools live here unless there is a specific reason for a subdirectory
2. **Update README** — add to the Script Reference section with usage examples
3. **Update provenance_log.py `OUTPUT_TYPES`** — if the tool produces a new deliverable type
4. **Update calling specs** — if any spec invokes this tool, add it to that spec's companion specs section
5. **Add to spec-creation-spec.md integration checklist** — if the tool type should be referenced in future spec builds

---

## Self-Check Before Delivery

Before presenting any tool, verify:

```
TOOL SELF-CHECK

Plan approved:
  □ Tool plan presented and confirmed before implementation

Standards:
  □ Standards declaration in file header
  □ Deviations listed and justified — or "None" stated explicitly
  □ Linter would pass (no obvious violations)

Security:
  □ No hardcoded credentials or secrets
  □ Credentials read from environment variables
  □ Logging contains no sensitive data

Structure:
  □ Module docstring or header comment present
  □ All public functions have docstrings
  □ Error handling on all file and external operations
  □ CLI uses argparse / flags with --help
  □ Exit codes meaningful

Repo integration:
  □ Correct filename convention for language
  □ README update identified
  □ Calling specs updated if applicable
  □ requirements.txt or package.json updated if new dependencies
```

If any box is unchecked, resolve before delivery.

---

## Suggested Repo Path

`/docs/tool-requirements.md`

## References
- Python: https://peps.python.org/pep-0008/
- Bash: https://google.github.io/styleguide/shellguide.html
- JavaScript: https://github.com/airbnb/javascript
- ShellCheck: https://www.shellcheck.net/
