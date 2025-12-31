#!/usr/bin/env python3
"""
Decompose an Atom into child Atoms.
Usage: python decompose_atom.py <parent_id> --children "A3,A4" --descriptions "desc1|||desc2" --reason "..."

Note: Descriptions are separated by "|||" to allow commas within descriptions.
"""

import sys
import json
import argparse
import re
from pathlib import Path
from datetime import datetime


def parse_atom_info(content: str, atom_id: str) -> dict:
    """Get atom info including depends_on."""
    lines = content.split('\n')
    current_atom = None
    in_atoms = False

    for line in lines:
        stripped = line.strip()

        if line.startswith('atoms:'):
            in_atoms = True
            continue

        if in_atoms:
            if line and not line.startswith(' ') and ':' in line:
                break

            if stripped.startswith('- id:'):
                if current_atom and current_atom.get('id') == atom_id:
                    return current_atom
                aid = stripped.split(':', 1)[1].strip().strip('"').strip("'")
                current_atom = {'id': aid, 'depends_on': []}
            elif current_atom and ':' in stripped:
                key, _, value = stripped.partition(':')
                key = key.strip()
                value = value.strip()

                if key == 'depends_on':
                    if value.startswith('['):
                        deps = value[1:-1].split(',')
                        current_atom[key] = [d.strip().strip('"').strip("'") for d in deps if d.strip()]
                    else:
                        current_atom[key] = []

    if current_atom and current_atom.get('id') == atom_id:
        return current_atom

    return None


def parse_existing_ids(content: str) -> set:
    """Parse existing atom IDs."""
    ids = set()
    for line in content.split('\n'):
        stripped = line.strip()
        if stripped.startswith('- id:'):
            atom_id = stripped.split(':', 1)[1].strip().strip('"').strip("'")
            ids.add(atom_id)
    return ids


def add_decomposition_record(content: str, parent_id: str, children: list, reason: str) -> str:
    """Add a record to decompositions section."""
    lines = content.split('\n')

    # Build decomposition entry
    timestamp = datetime.now().isoformat()
    children_str = ', '.join(children)
    decomp_lines = [
        f'  - parent: {parent_id}',
        f'    children: [{children_str}]',
        f'    reason: "{reason}"',
        f'    timestamp: "{timestamp}"'
    ]

    # Find decompositions section
    decomp_idx = -1
    next_section_idx = -1

    for i, line in enumerate(lines):
        if line.startswith('decompositions:'):
            decomp_idx = i
            # Check if empty list
            if '[]' in line:
                lines[i] = 'decompositions:'
        elif decomp_idx >= 0 and line and not line.startswith(' ') and ':' in line:
            next_section_idx = i
            break

    if decomp_idx >= 0:
        insert_idx = next_section_idx if next_section_idx >= 0 else len(lines)
        result = lines[:insert_idx] + decomp_lines + lines[insert_idx:]
    else:
        result = lines

    return '\n'.join(result)


def add_child_atoms(content: str, parent_depends_on: list, children: list, descriptions: list, parent_id: str) -> str:
    """Add child atoms to the atoms section."""
    lines = content.split('\n')

    # Build child atoms
    atom_lines = []
    deps_str = ', '.join(parent_depends_on) if parent_depends_on else ''

    for child_id, desc in zip(children, descriptions):
        atom_lines.append(f'  - id: {child_id}')
        atom_lines.append(f'    description: "{desc}"')
        atom_lines.append('    status: pending')
        atom_lines.append(f'    depends_on: [{deps_str}]')
        atom_lines.append(f'    decomposed_from: {parent_id}')

    # Find end of atoms section
    atoms_section_end = -1
    in_atoms = False

    for i, line in enumerate(lines):
        if line.startswith('atoms:'):
            in_atoms = True
            continue

        if in_atoms:
            if line and not line.startswith(' ') and ':' in line:
                atoms_section_end = i
                break

    if atoms_section_end < 0:
        atoms_section_end = len(lines)

    result = lines[:atoms_section_end] + atom_lines + lines[atoms_section_end:]

    return '\n'.join(result)


def main():
    parser = argparse.ArgumentParser(description='Decompose Atom into children')
    parser.add_argument('parent_id', help='Parent Atom ID')
    parser.add_argument('--children', required=True, help='Comma-separated child IDs')
    parser.add_argument('--descriptions', required=True, help='Pipe-separated descriptions (use ||| as separator)')
    parser.add_argument('--reason', required=True, help='Reason for decomposition')
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

    # Get parent info
    parent = parse_atom_info(content, args.parent_id)
    if not parent:
        print(json.dumps({
            'error': f'Parent atom not found: {args.parent_id}',
            'success': False
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    # Parse children and descriptions
    children = [c.strip() for c in args.children.split(',')]
    descriptions = [d.strip() for d in args.descriptions.split('|||')]

    if len(children) != len(descriptions):
        print(json.dumps({
            'error': f'Number of children ({len(children)}) does not match descriptions ({len(descriptions)})',
            'success': False
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    # Check for duplicate IDs
    existing_ids = parse_existing_ids(content)
    for child_id in children:
        if child_id in existing_ids:
            print(json.dumps({
                'error': f'Child atom ID already exists: {child_id}',
                'success': False
            }, ensure_ascii=False, indent=2))
            sys.exit(1)

    # Add child atoms (inherit parent's depends_on)
    content = add_child_atoms(content, parent.get('depends_on', []), children, descriptions, args.parent_id)

    # Add decomposition record
    content = add_decomposition_record(content, args.parent_id, children, args.reason)

    state_file.write_text(content)

    print(json.dumps({
        'success': True,
        'parent': args.parent_id,
        'children': children,
        'inherited_deps': parent.get('depends_on', [])
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
