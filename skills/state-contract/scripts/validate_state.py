#!/usr/bin/env python3
"""
Validate state file structure and integrity.
Usage: python validate_state.py [--state-file PATH]

Checks:
- YAML frontmatter syntax
- Required sections exist (objective, control, atoms)
- At least 1 atom
- No duplicate atom IDs
- No circular dependencies
"""

import sys
import json
import argparse
import re
from pathlib import Path


def parse_atoms_basic(content: str) -> list:
    """Parse atoms for validation purposes."""
    atoms = []
    current_atom = None
    in_atoms = False

    for line in content.split('\n'):
        stripped = line.strip()

        if line.startswith('atoms:'):
            in_atoms = True
            continue

        if in_atoms:
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

    if current_atom:
        atoms.append(current_atom)

    return atoms


def detect_cycle(atoms: list) -> list:
    """Detect circular dependencies in atoms. Returns cycle path if found."""
    atom_map = {a['id']: a for a in atoms}

    def dfs(node_id, visited, path):
        if node_id in path:
            cycle_start = path.index(node_id)
            return path[cycle_start:] + [node_id]

        if node_id in visited:
            return None

        visited.add(node_id)
        path.append(node_id)

        atom = atom_map.get(node_id)
        if atom:
            for dep in atom.get('depends_on', []):
                cycle = dfs(dep, visited, path)
                if cycle:
                    return cycle

        path.pop()
        return None

    visited = set()
    for atom in atoms:
        cycle = dfs(atom['id'], visited, [])
        if cycle:
            return cycle

    return []


def validate_state_file(content: str) -> dict:
    """Validate state file and return results."""
    errors = []
    warnings = []

    # Check YAML frontmatter exists
    if not content.startswith('---'):
        errors.append("Missing YAML frontmatter (must start with ---)")
        return {'valid': False, 'errors': errors, 'warnings': warnings}

    parts = content.split('---', 2)
    if len(parts) < 3:
        errors.append("Invalid YAML frontmatter (missing closing ---)")
        return {'valid': False, 'errors': errors, 'warnings': warnings}

    frontmatter = parts[1]

    # Check required sections
    required_sections = ['objective:', 'control:', 'atoms:']
    for section in required_sections:
        if section not in frontmatter:
            errors.append(f"Missing required section: {section.rstrip(':')}")

    # Check objective sub-fields
    if 'objective:' in frontmatter:
        objective_fields = ['goal:', 'base_case:']
        for field in objective_fields:
            if field not in frontmatter:
                errors.append(f"Missing objective.{field.rstrip(':')}")

    # Check control sub-fields
    if 'control:' in frontmatter:
        control_fields = ['status:', 'iteration:', 'stall_count:']
        for field in control_fields:
            pattern = rf'\n  {field}'
            if not re.search(pattern, frontmatter):
                warnings.append(f"Missing control.{field.rstrip(':')}")

    # Parse and validate atoms
    atoms = parse_atoms_basic(content)

    if len(atoms) == 0:
        errors.append("No atoms defined (must have at least 1)")
    else:
        # Check for duplicate IDs
        ids = [a['id'] for a in atoms]
        seen = set()
        duplicates = []
        for id in ids:
            if id in seen:
                duplicates.append(id)
            seen.add(id)

        if duplicates:
            errors.append(f"Duplicate atom IDs: {', '.join(duplicates)}")

        # Check for circular dependencies
        cycle = detect_cycle(atoms)
        if cycle:
            errors.append(f"Circular dependency detected: {' -> '.join(cycle)}")

        # Check for undefined dependencies
        all_ids = set(ids)
        for atom in atoms:
            for dep in atom.get('depends_on', []):
                if dep not in all_ids:
                    warnings.append(f"Atom {atom['id']} depends on undefined atom: {dep}")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'atom_count': len(atoms)
    }


def main():
    parser = argparse.ArgumentParser(description='Validate state file')
    parser.add_argument('--state-file', default='.claude/aot-loop-state.md')
    args = parser.parse_args()

    state_file = Path(args.state_file)

    if not state_file.exists():
        print(json.dumps({
            'valid': False,
            'errors': [f'State file not found: {state_file}'],
            'warnings': []
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    content = state_file.read_text()
    result = validate_state_file(content)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result['valid'] else 1)


if __name__ == '__main__':
    main()
