#!/usr/bin/env python3
"""
Update an Atom's status in the AoT Loop state file.
Usage: python update_atom.py <atom_id> <status> [--state-file PATH]
"""

import sys
import re
import argparse
from pathlib import Path


def update_atom_status(content: str, atom_id: str, new_status: str) -> tuple[str, bool]:
    """Update atom status in content. Returns (new_content, success)."""
    valid_statuses = ('pending', 'in_progress', 'resolved')
    if new_status not in valid_statuses:
        return content, False

    # Find the atom and update its status
    lines = content.split('\n')
    result = []
    found = False
    in_target_atom = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Check if this is the start of our target atom
        if stripped.startswith('- id:'):
            current_id = stripped.split(':', 1)[1].strip().strip('"').strip("'")
            in_target_atom = (current_id == atom_id)

        # If we're in the target atom and find status line
        if in_target_atom and stripped.startswith('status:'):
            # Preserve indentation
            indent = len(line) - len(line.lstrip())
            result.append(' ' * indent + f'status: {new_status}')
            found = True
            in_target_atom = False  # Done with this atom
        else:
            result.append(line)

    return '\n'.join(result), found


def main():
    parser = argparse.ArgumentParser(description='Update Atom status')
    parser.add_argument('atom_id', help='Atom ID (e.g., A1, A2)')
    parser.add_argument('status', choices=['pending', 'in_progress', 'resolved'],
                        help='New status')
    parser.add_argument('--state-file', default='.claude/aot-loop-state.md')
    args = parser.parse_args()

    state_file = Path(args.state_file)

    if not state_file.exists():
        print(f'{{"error": "State file not found: {state_file}", "success": false}}')
        sys.exit(1)

    content = state_file.read_text()
    new_content, success = update_atom_status(content, args.atom_id, args.status)

    if not success:
        print(f'{{"error": "Atom {args.atom_id} not found", "success": false}}')
        sys.exit(1)

    state_file.write_text(new_content)
    print(f'{{"success": true, "atom_id": "{args.atom_id}", "status": "{args.status}"}}')


if __name__ == '__main__':
    main()
