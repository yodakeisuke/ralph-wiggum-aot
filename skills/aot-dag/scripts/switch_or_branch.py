#!/usr/bin/env python3
"""
Switch OR branch selection and record in trail.
Usage: python switch_or_branch.py <group_name> <new_selection> --reason "..."
"""

import sys
import json
import argparse
import re
from pathlib import Path
from datetime import datetime


def update_or_group_selection(content: str, group_name: str, new_selection: str) -> str:
    """Update the selected choice in an OR group."""
    lines = content.split('\n')
    result = []
    in_or_groups = False
    in_target_group = False

    for line in lines:
        stripped = line.strip()

        if line.startswith('or_groups:'):
            in_or_groups = True
            # Handle empty dict
            if '{}' in line:
                result.append('or_groups:')
                result.append(f'  {group_name}:')
                result.append('    choices: []')
                result.append(f'    selected: {new_selection}')
                result.append('    failed: []')
                in_or_groups = False
                continue
            result.append(line)
            continue

        if in_or_groups:
            # Check for end of or_groups
            if line and not line.startswith(' ') and ':' in line:
                in_or_groups = False
                in_target_group = False

            # Check for target group
            indent = len(line) - len(line.lstrip())
            if indent == 2 and stripped == f'{group_name}:':
                in_target_group = True
                result.append(line)
                continue

            if in_target_group:
                if indent == 4 and stripped.startswith('selected:'):
                    result.append(f'    selected: {new_selection}')
                    continue
                elif indent == 2 and stripped.endswith(':'):
                    in_target_group = False

        result.append(line)

    return '\n'.join(result)


def add_trail_entry(content: str, group_name: str, new_selection: str, reason: str) -> str:
    """Add an entry to the trail section."""
    lines = content.split('\n')
    timestamp = datetime.now().isoformat()

    trail_entry = [
        f'  - or_group: {group_name}',
        f'    selected: {new_selection}',
        f'    reason: "{reason}"',
        f'    timestamp: "{timestamp}"'
    ]

    # Find trail section
    trail_idx = -1
    next_section_idx = -1

    for i, line in enumerate(lines):
        if line.startswith('trail:'):
            trail_idx = i
            # Handle empty list
            if '[]' in line:
                lines[i] = 'trail:'
        elif trail_idx >= 0 and line and not line.startswith(' ') and ':' in line:
            next_section_idx = i
            break

    if trail_idx >= 0:
        insert_idx = next_section_idx if next_section_idx >= 0 else len(lines)
        result = lines[:insert_idx] + trail_entry + lines[insert_idx:]
    else:
        result = lines

    return '\n'.join(result)


def main():
    parser = argparse.ArgumentParser(description='Switch OR branch selection')
    parser.add_argument('group_name', help='OR group name')
    parser.add_argument('new_selection', help='New selected atom ID')
    parser.add_argument('--reason', required=True, help='Reason for switch')
    parser.add_argument('--state-file', default='.claude/aot-loop-state.md')
    args = parser.parse_args()

    state_file = Path(args.state_file)

    if not state_file.exists():
        print(json.dumps({
            'error': f'State file not found: {state_file}',
            'success': False
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    content = state_file.read_text()

    # Update OR group selection
    content = update_or_group_selection(content, args.group_name, args.new_selection)

    # Add trail entry
    content = add_trail_entry(content, args.group_name, args.new_selection, args.reason)

    state_file.write_text(content)

    print(json.dumps({
        'success': True,
        'or_group': args.group_name,
        'selected': args.new_selection,
        'reason': args.reason
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
