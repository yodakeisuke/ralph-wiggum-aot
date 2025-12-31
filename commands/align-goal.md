---
description: "Goal alignment - Interactive agreement formation for AoT Loop (background, deliverables, completion criteria)"
argument-hint: "[initial request or task description]"
allowed-tools: ["Read", "Write", "Edit", "Glob", "Grep", "AskUserQuestion"]
---

# Align Goal Command

Interactively form agreement and generate the AoT Loop state file.

## Responsibility

Establish agreement equivalent to "alignment with manager" as the Objective, and form the initial Work Graph (DAG).

## Agreement Items to Establish

The following 3 points must be confirmed:

1. **Background purpose (background_intent)**: Why do it
2. **Deliverables (deliverables)**: What should be produced
3. **Completion criteria (definition_of_done)**: Externally verifiable completion criteria

## Important: Interactive Questions

**All questions to the user MUST use the `AskUserQuestion` tool (interactive question).** Do not ask questions in plain text output. This ensures structured user interaction and proper response handling.

## Dialogue Flow

### Step 1: Understanding Requirements

Deep-dive into user requirements. Ask questions about ambiguous points using `AskUserQuestion` tool.

**Acceptable ambiguity**: "How to do it" (implementation approach) → Resolved through loop exploration
**Unacceptable ambiguity**: "What to achieve" "When is it complete"

### Step 2: Extraction/Structuring

Organize understood content and present in the following format:

```
## Agreement Confirmation

**Background purpose**: [Why this work is needed]

**Deliverables**: [What will be produced specifically]

**Completion criteria** (Checklist format):
- [ ] Functional requirements
  - [ ] Tests pass (`npm test`)
  - [ ] Build succeeds (`npm run build`)
- [ ] Quality requirements
  - [ ] No lint errors (`npm run lint`)
  - [ ] No vulnerabilities (`npm audit` fails)
- [ ] Code quality
  - [ ] Readable and well designed (LLM as a Judge)

**Initial tasks**:
1. [First thing to work on]
2. [Next thing to work on]
...
```

**Note**: Express completion criteria as nested checklists. Each item is defined in verifiable format (command/file/not_command/not_file/quality).

### Step 3: Agreement Confirmation

When user OKs:

1. Generate state file `.claude/aot-loop-state.md`
2. Add initial Atoms to Work Graph
3. Display completion message

## base_case Format

### Format 1: Legacy format (simple single condition)

| type | Verification Method | Example | Confirmation at completion |
|------|----------|-----|-----------|
| `command` | exit code = 0 | `npm test` | Not required |
| `file` | Existence check | `./dist/bundle.js` | Not required |
| `assertion` | Agent judgment | "Auth API operates normally" | User confirmation required |

### Format 2: Checklist format (v1.3+ recommended)

Express multiple conditions as nested checklists:

| type | Verification Method | PASS Condition | Autonomy |
|------|----------|-----------|--------|
| `command` | exit code check | = 0 | High |
| `file` | Existence check | File exists | High |
| `not_command` | exit code check | ≠ 0 | High |
| `not_file` | Existence check | File doesn't exist | High |
| `assertion` | Agent judgment | Judgment result | Low (confirmation required) |
| `quality` | LLM as a Judge + Rubric | weighted average >= threshold | High |

**Checklist structure**:
- `group`: AND group (all must pass)
- `any_of`: OR group (any one passes)

**quality type (qualitative evaluation)**:

```yaml
check:
  type: quality
  rubric:                    # Rubric format
    - criterion: "Readability"
      weight: 0.5
      levels:
        1: "Hard to read"
        3: "Mostly readable"
        5: "Very readable"
  pass_threshold: 3.5

  # Or simple format
  # criteria: "Code is readable and well designed"
  # pass_threshold: 3
```

## State File Generation

After agreement confirmation, generate `.claude/aot-loop-state.md` with the following content:

### Checklist format (v1.3+ recommended)

```yaml
---
objective:
  goal: "[minimal goal summary]"
  base_case:
    checklist:
      - item: "Functional Requirements"
        group:
          - item: "Tests pass"
            check:
              type: command
              value: "npm test"
          - item: "Build succeeds"
            check:
              type: command
              value: "npm run build"
      - item: "Quality Requirements"
        group:
          - item: "No lint errors"
            check:
              type: command
              value: "npm run lint"
          - item: "No vulnerabilities"
            check:
              type: not_command
              value: "npm audit --audit-level=high"
      - item: "Code Quality"
        check:
          type: quality
          criteria: "Code is readable and well designed"
          pass_threshold: 3
  background_intent: "[background purpose]"
  deliverables: "[deliverables summary]"
  definition_of_done: "[human-readable completion criteria summary]"
  constraints:
    max_iterations: 20
    max_parallel_agents: 3
    max_stall_count: 3

control:
  status: pending
  iteration: 0
  stall_count: 0
  prev_pending_count: -1
  stop_requested: false
  stop_reason: null
  redirect_requested: false

atoms:
  - id: A1
    description: "[first task]"
    status: pending
    depends_on: []
  # Add more as needed

decompositions: []
or_groups: {}
bindings: {}
trail: []
corrections: []
---

# Original Prompt

[Record user's original request here]
```

### Legacy format (backward compatible)

```yaml
---
objective:
  goal: "[minimal goal summary]"
  base_case:
    type: command        # or file, assertion
    value: "[verification command or file path or condition]"
  # ... same as above
---
```

## Error Cases

- Executed without arguments: Prompt for request input
- State file already exists: Confirm overwrite

## Completion Message

```
Objective confirmed and saved to .claude/aot-loop-state.md

To start the autonomous loop, run:
  /enter-recursion

To modify the objective, run:
  /align-goal [new requirements]
```
