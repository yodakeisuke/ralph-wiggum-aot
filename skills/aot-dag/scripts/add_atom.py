#!/usr/bin/env python3
"""
Add a new Atom to the DAG.
Usage: python add_atom.py <id> --description "..." [--depends-on "A1,A2"] [--or-group NAME]
"""

import sys
import json
import argparse
from pathlib import Path


def parse_existing_ids(content: str) -> set:
    """Parse existing atom IDs from state file."""
    ids = set()
    for line in content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('- id:'):
            atom_id = stripped.split(':', 1)[1].strip().strip('"').strip("'")
            ids.add(atom_id)
    return ids


def add_atom(content: str, atom_id: str, description: str, depends_on: list, or_group: str = None) -> str:
    """Add a new atom to the atoms section."""
    lines = content.split('\n')

    # Build the new atom YAML
    atom_lines = [f'  - id: {atom_id}']
    atom_lines.append(f'    description: "{description}"')
    atom_lines.append('    status: pending')

    if depends_on:
        deps_str = ', '.join(depends_on)
        atom_lines.append(f'    depends_on: [{deps_str}]')
    else:
        atom_lines.append('    depends_on: []')

    if or_group:
        atom_lines.append(f'    or_group: {or_group}')

    # Find where to insert (end of atoms section)
    atoms_section_end = -1
    in_atoms = False

    for i, line in enumerate(lines):
        if line.startswith('atoms:'):
            in_atoms = True
            continue

        if in_atoms:
            # Check for next top-level section
            if line and not line.startswith(' ') and ':' in line:
                atoms_section_end = i
                break

    if atoms_section_end < 0:
        # No next section, append at end
        atoms_section_end = len(lines)

    # Insert before the next section
    result = lines[:atoms_section_end] + atom_lines + lines[atoms_section_end:]

    return '\n'.join(result)


def main():
    parser = argparse.ArgumentParser(description='Add new Atom to DAG')
    parser.add_argument('atom_id', help='Atom ID (e.g., A9)')
    parser.add_argument('--description', required=True, help='Atom description')
    parser.add_argument('--depends-on', default='', help='Comma-separated list of dependency IDs')
    parser.add_argument('--or-group', default=None, help='OR group name')
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

    # Check for duplicate ID
    existing_ids = parse_existing_ids(content)
    if args.atom_id in existing_ids:
        print(json.dumps({
            'error': f'Atom ID already exists: {args.atom_id}',
            'success': False
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    # Parse depends_on
    depends_on = [d.strip() for d in args.depends_on.split(',') if d.strip()]

    # Check that dependencies exist
    for dep in depends_on:
        if dep not in existing_ids:
            print(json.dumps({
                'error': f'Dependency not found: {dep}',
                'success': False
            }, ensure_ascii=False, indent=2))
            sys.exit(1)

    new_content = add_atom(content, args.atom_id, args.description, depends_on, args.or_group)
    state_file.write_text(new_content)

    result = {
        'success': True,
        'atom_id': args.atom_id,
        'depends_on': depends_on
    }
    if args.or_group:
        result['or_group'] = args.or_group

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
