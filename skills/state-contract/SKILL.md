---
description: "This skill should be used when you need to read, write, or manipulate the AoT Loop state file (.claude/aot-loop-state.md). Use it when implementing commands like /align-goal, /enter-recursion, /exit-recursion, /redirect, or when agents need to update Atom status, Bindings, or control flags."
allowed-tools: Bash(python3:*)
---

# State Contract v1.3

State management schema and operation methods for AoT Loop.

**v1.3 Changes**: Supports checklist format for base_case, negative conditions (not_command, not_file), and qualitative quality assessment (quality).

## File Format

State file: `.claude/aot-loop-state.md`

YAML frontmatter + Markdown body structure:

```
---
(YAML frontmatter: structured data)
---

# Original Prompt

(Markdown body: user's original request)
```

## Section List

| Section | Required | Empty Allowed | Description |
|-----------|:----:|:------:|------|
| objective | Yes | No | Goal, completion criteria, constraints |
| control | Yes | No | Execution control flags |
| atoms | Yes | No | Work Graph (at least 1) |
| decompositions | No | Yes | Atom decomposition relationships |
| or_groups | No | Yes | OR branch definitions |
| bindings | Yes | Yes | Resolved Atom summaries |
| trail | Yes | Yes | OR selection history |
| corrections | Yes | Yes | Redirect history |

## Field Details

### objective

```yaml
objective:
  goal: "Implement authentication feature"
  base_case:
    checklist:
      - item: "Functional Requirements"
        group:
          - item: "Tests pass"
            check:
              type: command
              value: "npm test"
          - item: "No vulnerabilities"
            check:
              type: not_command
              value: "npm audit --audit-level=high"
      - item: "Code Quality"
        check:
          type: quality
          criteria: "Code is readable and well designed"
          pass_threshold: 3
  background_intent: "Enable existing users to log in"
  deliverables: "Login API with JWT authentication"
  definition_of_done: "All auth tests pass"
  constraints:
    max_iterations: 20
    max_parallel_agents: 3
    max_stall_count: 3
```

**Verification method by check.type:**

| type | Verification Method | PASS Condition | Autonomy |
|------|---------|-----------|--------|
| `command` | Execute command | exit code = 0 | High |
| `file` | Check existence | File exists | High |
| `not_command` | Execute command | exit code ≠ 0 | High |
| `not_file` | Check existence | File doesn't exist | High |
| `assertion` | Agent judgment | Judgment result | Low |
| `quality` | LLM as a Judge | weighted avg >= threshold | High |

### control

```yaml
control:
  status: running          # pending | running | stopped | completed
  iteration: 5
  stall_count: 0
  prev_pending_count: 3
  stop_requested: false
  stop_reason: null
  redirect_requested: false
```

### atoms

```yaml
atoms:
  - id: A1
    description: "User model definition"
    status: resolved       # pending | in_progress | resolved
    depends_on: []
    or_group: null         # Optional: OR group membership
```

### bindings

```yaml
bindings:
  A1:
    summary: "Created User model"
    artifacts: ["src/models/user.ts"]
```

### trail

```yaml
trail:
  - or_group: token_method
    selected: A4
    reason: "JWT is stateless"
    timestamp: "2025-01-15T10:00:00Z"
```

## Invariants

- `atoms.length >= 1`: At least 1 Atom after /align-goal
- `atoms[].id` is unique
- No circular dependencies in `depends_on`
- Atom: `pending → in_progress → resolved`
- Control: `pending → running → {stopped, completed}`

## Operation Examples

### Atom Status Update

```yaml
# Before
- id: A2
  status: pending

# After
- id: A2
  status: in_progress
```

### Adding Bindings

```yaml
bindings:
  A2:
    summary: "Implemented auth middleware"
    artifacts: ["src/middleware/auth.ts"]
```

---

# Deterministic Operations (Python Scripts)

For reliable state updates, use the Python scripts in `scripts/`. These execute deterministically without LLM interpretation.

**IMPORTANT**: Always use these scripts instead of manually editing the state file.

## Available Scripts

### 1. Read State

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/read_state.py
```

Returns JSON with current state including:
- `status`, `iteration`, `stall_count`
- `atoms` (all atoms with status)
- `executable_atoms` (pending with deps resolved)
- `bindings`

### 2. Update Atom Status

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/update_atom.py <atom_id> <status>
```

**Arguments:**
- `atom_id`: e.g., "A1", "A2"
- `status`: "pending", "in_progress", or "resolved"

**Examples:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/update_atom.py A1 in_progress
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/update_atom.py A1 resolved
```

### 3. Add Binding

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/add_binding.py <atom_id> --summary "..." --artifacts "file1,file2"
```

**Arguments:**
- `atom_id`: Atom ID (e.g., "A1")
- `--summary`: Summary of what was accomplished
- `--artifacts`: Comma-separated list of files (optional)

**Example:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/add_binding.py A1 \
  --summary "Fetched source text and identified structure" \
  --artifacts "./source/original.md,./source/structure.md"
```

### 4. Set Loop Status

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/set_status.py <status> [--reason "..."]
```

**Arguments:**
- `status`: "running", "stopped", or "completed"
- `--reason`: Optional reason (for stopped status)

**Examples:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/set_status.py completed
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/set_status.py stopped --reason "All OR branches exhausted"
```

### 5. Verify Command

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/verify_command.py "<command>" [--expect-fail] [--timeout 120]
```

**Arguments:**
- `command`: Command to execute
- `--expect-fail`: For `not_command` type - PASS when exit code ≠ 0
- `--timeout`: Timeout in seconds (default: 120)

**Examples:**
```bash
# command type (PASS when exit = 0)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/verify_command.py "npm test"

# not_command type (PASS when exit ≠ 0)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/verify_command.py "npm audit --audit-level=high" --expect-fail
```

### 6. Verify File

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/verify_file.py <path> [--expect-missing]
```

**Arguments:**
- `path`: File or directory path to check
- `--expect-missing`: For `not_file` type - PASS when file does NOT exist

**Examples:**
```bash
# file type (PASS when exists)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/verify_file.py "./dist/bundle.js"

# not_file type (PASS when missing)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/verify_file.py "./dist/*.map" --expect-missing
```

### 7. Verify Checklist

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/verify_checklist.py [--state-file PATH]
```

Evaluates the entire `base_case.checklist` from the state file. Returns JSON with:
- `passed`: Overall pass/fail
- `checklist`: Detailed results for each item
- `skipped`: Items that require LLM judgment (type: quality)

**Note:** Quality checks are skipped and must be evaluated by the Verifier agent using LLM-as-a-Judge.

### 8. Validate State

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/validate_state.py [--state-file PATH]
```

Validates state file structure:
- YAML frontmatter syntax
- Required sections exist (objective, control, atoms)
- At least 1 atom
- No duplicate atom IDs
- No circular dependencies

Returns: `{"valid": bool, "errors": [...], "warnings": [...]}`

### 9. Check Gate

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/check_gate.py [--state-file PATH]
```

Checks `/enter-recursion` preconditions:
- State file exists
- objective.goal, base_case, background_intent, deliverables, definition_of_done set
- At least 1 atom
- control.status is "pending" or "stopped"

Returns: `{"ready": bool, "missing": [...], "status": "..."}`

## Workflow Example

**Coordinator iteration flow:**

```bash
# 1. Read current state
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/read_state.py

# 2. Mark atom as in_progress before spawning worker
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/update_atom.py A1 in_progress

# 3. After worker completes, mark resolved and add binding
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/update_atom.py A1 resolved
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/add_binding.py A1 \
  --summary "Completed task successfully" \
  --artifacts "./output/file.md"

# 4. When all atoms resolved and verified
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/set_status.py completed
```

**Verifier workflow:**

```bash
# Run full checklist verification
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/verify_checklist.py

# Or verify individual items
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/verify_command.py "npm test"
python3 ${CLAUDE_PLUGIN_ROOT}/skills/state-contract/scripts/verify_file.py "./dist/"
```
