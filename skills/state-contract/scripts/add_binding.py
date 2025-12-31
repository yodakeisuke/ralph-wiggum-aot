#!/usr/bin/env python3
"""
Add a binding for a resolved Atom.
Usage: python add_binding.py <atom_id> --summary "..." [--artifacts "file1,file2"]
"""

import sys
import re
import argparse
from pathlib import Path


def add_binding(content: str, atom_id: str, summary: str, artifacts: list) -> str:
    """Add or update a binding for an atom."""
    lines = content.split('\n')

    # Build the new binding text
    binding_lines = [f'  {atom_id}:']

    # Handle multi-line summary
    summary_lines = summary.strip().split('\n')
    if len(summary_lines) == 1:
        binding_lines.append(f'    summary: "{summary_lines[0]}"')
    else:
        binding_lines.append('    summary: |')
        for sl in summary_lines:
            binding_lines.append(f'      {sl}')

    # Add artifacts
    if artifacts:
        binding_lines.append('    artifacts:')
        for artifact in artifacts:
            binding_lines.append(f'      - "{artifact}"')

    # Find bindings section and determine insertion strategy
    bindings_line_idx = -1
    existing_binding_start = -1
    existing_binding_end = -1
    next_section_idx = -1
    in_bindings = False

    for i, line in enumerate(lines):
        # Find bindings: line
        if line.startswith('bindings:'):
            bindings_line_idx = i
            in_bindings = True
            continue

        if in_bindings:
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())

            # End of bindings section (next top-level key)
            if line and not line.startswith(' ') and ':' in line:
                next_section_idx = i
                in_bindings = False
                break

            # Check for existing binding for this atom
            if indent == 2 and stripped == f'{atom_id}:':
                existing_binding_start = i
            elif existing_binding_start >= 0 and existing_binding_end < 0:
                # Find end of this binding (next atom at same indent level)
                if indent == 2 and stripped.endswith(':'):
                    existing_binding_end = i

    # If binding exists but no end found, it extends to next section
    if existing_binding_start >= 0 and existing_binding_end < 0:
        existing_binding_end = next_section_idx if next_section_idx >= 0 else len(lines)

    # Build result
    if existing_binding_start >= 0:
        # Replace existing binding
        result = lines[:existing_binding_start] + binding_lines + lines[existing_binding_end:]
    elif bindings_line_idx >= 0:
        # Add new binding to bindings section
        bindings_line = lines[bindings_line_idx]

        # Handle bindings: {} (empty dict notation)
        if '{}' in bindings_line:
            lines[bindings_line_idx] = 'bindings:'

        # Insert before next section or at end
        insert_idx = next_section_idx if next_section_idx >= 0 else len(lines)
        result = lines[:insert_idx] + binding_lines + lines[insert_idx:]
    else:
        # No bindings section found (shouldn't happen with valid state file)
        result = lines

    return '\n'.join(result)


def main():
    parser = argparse.ArgumentParser(description='Add binding for resolved Atom')
    parser.add_argument('atom_id', help='Atom ID (e.g., A1)')
    parser.add_argument('--summary', required=True, help='Summary of what was accomplished')
    parser.add_argument('--artifacts', default='', help='Comma-separated list of files')
    parser.add_argument('--state-file', default='.claude/aot-loop-state.md')
    args = parser.parse_args()

    state_file = Path(args.state_file)

    if not state_file.exists():
        print(f'{{"error": "State file not found: {state_file}", "success": false}}')
        sys.exit(1)

    artifacts = [a.strip() for a in args.artifacts.split(',') if a.strip()]

    content = state_file.read_text()
    new_content = add_binding(content, args.atom_id, args.summary, artifacts)

    state_file.write_text(new_content)
    print(f'{{"success": true, "atom_id": "{args.atom_id}", "artifacts_count": {len(artifacts)}}}')


if __name__ == '__main__':
    main()
