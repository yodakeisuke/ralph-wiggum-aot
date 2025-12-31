#!/usr/bin/env python3
"""
Read AoT Loop state file and return structured JSON.
Usage: python read_state.py [--state-file PATH]
"""

import sys
import json
import re
from pathlib import Path


def parse_atoms(content: str) -> list:
    """Parse atoms section from state file."""
    atoms = []
    current_atom = None
    in_atoms = False

    for line in content.split('\n'):
        stripped = line.strip()

        if line.startswith('atoms:'):
            in_atoms = True
            continue

        if in_atoms:
            # End of atoms section (new top-level key)
            if line and not line.startswith(' ') and ':' in line:
                break

            if stripped.startswith('- id:'):
                if current_atom:
                    atoms.append(current_atom)
                atom_id = stripped.split(':', 1)[1].strip().strip('"').strip("'")
                current_atom = {'id': atom_id, 'depends_on': []}
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
                elif key in ('description', 'status', 'or_group'):
                    current_atom[key] = value.strip('"').strip("'")

    if current_atom:
        atoms.append(current_atom)

    return atoms


def parse_bindings(content: str) -> dict:
    """Parse bindings section from state file."""
    bindings = {}
    in_bindings = False
    current_id = None
    current_field = None
    field_lines = []

    for line in content.split('\n'):
        if line.startswith('bindings:'):
            in_bindings = True
            continue

        if not in_bindings:
            continue

        # End of bindings section
        if line and not line.startswith(' ') and ':' in line:
            break

        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        # Atom ID level (2 spaces)
        if indent == 2 and stripped.endswith(':'):
            # Save previous
            if current_id and current_field and field_lines:
                bindings.setdefault(current_id, {})[current_field] = '\n'.join(field_lines).strip()
            current_id = stripped[:-1]
            current_field = None
            field_lines = []

        # Field level (4 spaces)
        elif indent == 4 and ':' in stripped:
            if current_id and current_field and field_lines:
                bindings.setdefault(current_id, {})[current_field] = '\n'.join(field_lines).strip()

            key, _, val = stripped.partition(':')
            current_field = key.strip()
            field_lines = []
            val = val.strip()
            if val and val != '|':
                field_lines.append(val.strip('"').strip("'"))

        # Content level (6+ spaces or list items)
        elif indent >= 6 or (stripped.startswith('- ') and current_field):
            if stripped.startswith('- '):
                field_lines.append(stripped[2:].strip('"').strip("'"))
            else:
                field_lines.append(stripped)

    # Save last
    if current_id and current_field and field_lines:
        bindings.setdefault(current_id, {})[current_field] = '\n'.join(field_lines).strip()

    return bindings


def get_executable_atoms(atoms: list, bindings: dict) -> list:
    """Get atoms that are pending and have all dependencies resolved."""
    resolved_ids = set(bindings.keys())
    resolved_ids.update(a['id'] for a in atoms if a.get('status') == 'resolved')

    executable = []
    for atom in atoms:
        if atom.get('status') != 'pending':
            continue
        deps = atom.get('depends_on', [])
        if all(dep in resolved_ids for dep in deps):
            executable.append(atom)

    return executable


def extract_control_field(content: str, field: str, default=None):
    """Extract a control field value."""
    pattern = rf'\n  {field}: (.+)'
    match = re.search(pattern, content)
    if match:
        val = match.group(1).strip().strip('"').strip("'")
        if val.lower() == 'true':
            return True
        if val.lower() == 'false':
            return False
        if val.lower() in ('null', '~'):
            return None
        try:
            return int(val)
        except ValueError:
            return val
    return default


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Read AoT Loop state')
    parser.add_argument('--state-file', default='.claude/aot-loop-state.md')
    args = parser.parse_args()

    state_file = Path(args.state_file)

    if not state_file.exists():
        print(json.dumps({'error': f'State file not found: {state_file}', 'exists': False}))
        sys.exit(1)

    content = state_file.read_text()

    atoms = parse_atoms(content)
    bindings = parse_bindings(content)
    executable = get_executable_atoms(atoms, bindings)

    result = {
        'exists': True,
        'status': extract_control_field(content, 'status', 'unknown'),
        'iteration': extract_control_field(content, 'iteration', 0),
        'stall_count': extract_control_field(content, 'stall_count', 0),
        'stop_requested': extract_control_field(content, 'stop_requested', False),
        'redirect_requested': extract_control_field(content, 'redirect_requested', False),
        'stop_reason': extract_control_field(content, 'stop_reason', None),
        'atoms': atoms,
        'executable_atoms': executable,
        'bindings': bindings,
        'summary': {
            'total': len(atoms),
            'pending': len([a for a in atoms if a.get('status') == 'pending']),
            'in_progress': len([a for a in atoms if a.get('status') == 'in_progress']),
            'resolved': len([a for a in atoms if a.get('status') == 'resolved']),
            'executable': len(executable)
        }
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
