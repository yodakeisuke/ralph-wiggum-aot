#!/usr/bin/env python3
"""
Check /enter-recursion preconditions (gate check).
Usage: python check_gate.py [--state-file PATH]

Checks:
- State file exists
- objective.goal set
- objective.base_case set
- objective.background_intent set
- objective.deliverables set
- objective.definition_of_done set
- atoms.length >= 1
- control.status is "pending" or "stopped"
"""

import sys
import json
import argparse
import re
from pathlib import Path


def extract_field(content: str, field_pattern: str) -> str:
    """Extract a field value from content."""
    match = re.search(field_pattern, content, re.MULTILINE)
    if match:
        return match.group(1).strip().strip('"').strip("'")
    return ""


def check_gate(content: str) -> dict:
    """Check if all preconditions for /enter-recursion are met."""
    missing = []
    status = None

    # Check objective fields
    objective_fields = {
        'goal': r'goal:\s*["\']?([^"\'\n]+)',
        'base_case': r'base_case:',
        'background_intent': r'background_intent:\s*["\']?([^"\'\n]+)',
        'deliverables': r'deliverables:\s*["\']?([^"\'\n]+)',
        'definition_of_done': r'definition_of_done:\s*["\']?([^"\'\n]+)',
    }

    for field, pattern in objective_fields.items():
        match = re.search(pattern, content)
        if not match:
            missing.append(f"objective.{field}")
        elif field != 'base_case':
            value = match.group(1) if match.lastindex else ""
            if not value or value.lower() in ('null', '~', '""', "''"):
                missing.append(f"objective.{field} (empty)")

    # Check atoms exist
    atoms_match = re.search(r'atoms:\s*\n\s*- id:', content)
    if not atoms_match:
        missing.append("atoms (must have at least 1)")

    # Check control.status
    status_match = re.search(r'\n  status:\s*(\w+)', content)
    if status_match:
        status = status_match.group(1)
        if status not in ('pending', 'stopped', 'running'):
            missing.append(f"control.status must be 'pending' or 'stopped', got '{status}'")
    else:
        missing.append("control.status")

    ready = len(missing) == 0

    return {
        'ready': ready,
        'missing': missing,
        'status': status
    }


def main():
    parser = argparse.ArgumentParser(description='Check /enter-recursion preconditions')
    parser.add_argument('--state-file', default='.claude/aot-loop-state.md')
    args = parser.parse_args()

    state_file = Path(args.state_file)

    if not state_file.exists():
        print(json.dumps({
            'ready': False,
            'missing': ['State file does not exist'],
            'status': None
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    content = state_file.read_text()
    result = check_gate(content)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result['ready'] else 1)


if __name__ == '__main__':
    main()
