---
description: "This skill should be used when you need to manipulate the AoT DAG (Work Graph) structure. Use it when decomposing Atoms into sub-tasks, resolving Atoms, managing AND/OR dependencies, performing backtracking on OR branches, or shrinking the DAG by replacing resolved Atoms with summaries in Bindings."
allowed-tools: Bash(python3:*)
---

# AoT DAG (Atom of Thoughts)

Decompose problems into Atoms and manage them as a DAG with dependencies (AND/OR).

## DAG Structure

### Atom

The smallest unit of a task:

| status | Description |
|--------|------|
| `pending` | Not started, waiting for dependencies |
| `in_progress` | In execution |
| `resolved` | Complete, summary in Bindings |

### Dependencies

**AND dependency**: Specified via `depends_on`. Cannot execute until all resolved.

**OR dependency**: Defined in `or_groups`. Select and execute one from choices.

## Atom Operations

### Decomposition

```yaml
# Before
atoms:
  - id: A2
    description: "Implement auth logic"
    status: pending
    depends_on: [A1]

# After
atoms:
  - id: A2
    status: pending              # Parent stays pending
    depends_on: [A1]
  - id: A3
    description: "Password hashing"
    depends_on: [A1]             # Copy dependencies
  - id: A4
    description: "JWT generation"
    depends_on: [A1]

decompositions:
  - parent: A2
    children: [A3, A4]
    reason: "Split auth logic into hashing and token"
```

### Resolution

```yaml
atoms:
  - id: A1
    status: resolved
bindings:
  A1:
    summary: "Created User model"
    artifacts: ["src/models/user.ts"]
```

## Auto-Backtracking

On OR branch failure, automatically switch to alternative.

```yaml
# After A4_jwt fails
or_groups:
  auth_method:
    choices: [A4_jwt, A4_session]
    selected: A4_session      # Auto-switched
    failed: [A4_jwt]          # Failure tracking
trail:
  - or_group: auth_method
    selected: A4_session
    reason: "Auto-backtrack: A4_jwt failed"
```

## Executable Atom Determination

```python
def get_executable_atoms(state):
    ready = []
    for atom in state.atoms:
        if atom.status != 'pending':
            continue
        if atom.or_group:
            if state.or_groups[atom.or_group].selected != atom.id:
                continue
        if all(get_atom(dep).status == 'resolved' for dep in atom.depends_on):
            ready.append(atom)
    return ready
```

---

# Deterministic Operations (Python Scripts)

For reliable DAG manipulation, use the Python scripts in `scripts/`. These execute deterministically without LLM interpretation.

## Available Scripts

### 1. Add Atom

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/aot-dag/scripts/add_atom.py <id> --description "..." [--depends-on "A1,A2"] [--or-group NAME]
```

**Arguments:**
- `id`: New atom ID (e.g., "A9")
- `--description`: Atom description (required)
- `--depends-on`: Comma-separated dependency IDs (optional)
- `--or-group`: OR group name (optional)

**Example:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/aot-dag/scripts/add_atom.py A9 \
  --description "Implement new feature" \
  --depends-on "A1,A2"
```

Returns: `{"success": true, "atom_id": "A9", "depends_on": ["A1", "A2"]}`

### 2. Decompose Atom

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/aot-dag/scripts/decompose_atom.py <parent_id> \
  --children "A3,A4" \
  --descriptions "desc1|||desc2" \
  --reason "..."
```

**Arguments:**
- `parent_id`: Parent atom ID
- `--children`: Comma-separated child IDs
- `--descriptions`: Pipe-separated descriptions (use `|||` as separator)
- `--reason`: Reason for decomposition

**Notes:**
- Child atoms inherit parent's `depends_on`
- Records decomposition in `decompositions` section
- Use `|||` to separate descriptions (allows commas within descriptions)

**Example:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/aot-dag/scripts/decompose_atom.py A2 \
  --children "A2a,A2b" \
  --descriptions "Password hashing implementation|||JWT token generation" \
  --reason "Split auth logic into separate concerns"
```

Returns: `{"success": true, "parent": "A2", "children": ["A2a", "A2b"], "inherited_deps": ["A1"]}`

### 3. Switch OR Branch

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/aot-dag/scripts/switch_or_branch.py <group_name> <new_selection> --reason "..."
```

**Arguments:**
- `group_name`: OR group name
- `new_selection`: New selected atom ID
- `--reason`: Reason for switch (required)

**Example:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/aot-dag/scripts/switch_or_branch.py auth_method A4_session \
  --reason "JWT implementation failed, switching to session-based auth"
```

Returns: `{"success": true, "or_group": "auth_method", "selected": "A4_session"}`

**Notes:**
- Updates `or_groups[group].selected`
- Automatically records in `trail` with timestamp

## Workflow Examples

**Adding new work during iteration:**

```bash
# When you discover additional work needed
python3 ${CLAUDE_PLUGIN_ROOT}/skills/aot-dag/scripts/add_atom.py A9 \
  --description "Handle edge case discovered during A3" \
  --depends-on "A3"
```

**Decomposing complex atom:**

```bash
# When an atom is too large to complete in one step
python3 ${CLAUDE_PLUGIN_ROOT}/skills/aot-dag/scripts/decompose_atom.py A5 \
  --children "A5a,A5b,A5c" \
  --descriptions "Parse input|||Validate format|||Transform output" \
  --reason "Task too complex for single worker"
```

**Backtracking on OR branch failure:**

```bash
# When current OR branch fails, switch to alternative
python3 ${CLAUDE_PLUGIN_ROOT}/skills/aot-dag/scripts/switch_or_branch.py storage_method A6_postgres \
  --reason "SQLite doesn't support concurrent writes needed for this use case"
```
