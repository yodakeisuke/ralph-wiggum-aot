# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **AoT (Atom of Thoughts) Loop Plugin** for Claude Code - an autonomous agent system that decomposes complex goals into a DAG (Directed Acyclic Graph) of atomic tasks with convergence guarantees and backtracking support.

## Plugin Architecture

### Component Structure

```
.claude-plugin/plugin.json    # Plugin manifest (name: ralph-wiggum-aot)
commands/                     # Slash commands (entry points)
agents/                       # Sub-agent definitions
skills/                       # Knowledge/reference skills
hooks/                        # Event hooks (SubagentStop, PreToolUse)
templates/                    # State file templates
PRD/                          # Design documents
```

### Core Flow

1. **`/align-goal`** - Interactive goal alignment that creates `.claude/aot-loop-state.md`
2. **`/enter-recursion`** - Starts the autonomous loop by spawning the coordinator agent
3. **Coordinator** cycles: analyze DAG → spawn workers/probes/verifiers → integrate results
4. **SubagentStop hook** (`hooks/subagent-stop-hook.sh`) manages iteration continuation
5. **`/exit-recursion`** or **`/redirect`** - Manual control

### Agent Hierarchy

| Agent | Role | Model | Tools |
|-------|------|-------|-------|
| **coordinator** | Manages iterations, spawns sub-agents | opus | Read, Write, Edit, Task, Glob, Grep, Bash |
| **probe** | Read-only feasibility investigation | sonnet | Read, Glob, Grep, WebSearch, WebFetch |
| **worker** | Executes individual Atoms | opus | Full tool access |
| **verifier** | Checks base_case completion | opus | Bash, Read, Glob |

### State File (`./claude/aot-loop-state.md`)

YAML frontmatter containing:
- **objective**: goal, base_case (checklist or legacy format), constraints
- **control**: status, iteration, stall_count, stop flags
- **atoms**: Work Graph with dependencies (AND/OR)
- **bindings**: Resolved Atom results
- **trail**: OR branch selection history

### Hooks

- **SubagentStop**: Controls loop iteration (block to continue, approve to stop)
- **PreToolUse**: Permission handling for tool calls

## Development Commands

```bash
# Load plugin in development mode
claude --plugin-dir /path/to/this/repo

# Validate plugin structure
/plugin validate /path/to/this/repo
```

## Key Design Decisions

- **Atom statuses**: `pending` → `in_progress` → `resolved` (failure resets to pending)
- **Auto-backtracking**: Failed OR group choices automatically switch to alternatives
- **Progress tracking**: `prev_pending_count` enables stall detection via hook
- **Iteration management**: Hook increments iteration count, not coordinator
- **Convergence**: DAG must shrink each iteration or stall_count increases

## File Patterns

- Agent definitions: `agents/*.md` with YAML frontmatter (name, description, whenToUse, model, tools)
- Command definitions: `commands/*.md` with YAML frontmatter (description, argument-hint, allowed-tools)
- Skill definitions: `skills/*/SKILL.md` with knowledge content
- State schema: `PRD/state-schema.md` (v1.3 with checklist, quality evaluation)
