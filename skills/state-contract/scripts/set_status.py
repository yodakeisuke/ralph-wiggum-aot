#!/usr/bin/env python3
"""
Set the loop status (running, stopped, completed).
Usage: python set_status.py <status> [--reason "..."] [--state-file PATH]
"""

import sys
import re
import json
import argparse
from pathlib import Path


def set_loop_status(content: str, status: str, reason: str = None) -> str:
    """Update control.status and optionally stop_reason."""
    lines = content.split('\n')
    result = []

    for line in lines:
        stripped = line.strip()

        # Update status field (2-space indent in control section)
        if stripped.startswith('status:') and line.startswith('  status:'):
            result.append(f'  status: {status}')
        # Update stop_reason if provided
        elif stripped.startswith('stop_reason:') and line.startswith('  stop_reason:'):
            if reason:
                result.append(f'  stop_reason: "{reason}"')
            elif status == 'completed':
                result.append('  stop_reason: null')
            else:
                result.append(line)
        else:
            result.append(line)

    return '\n'.join(result)


def main():
    parser = argparse.ArgumentParser(description='Set loop status')
    parser.add_argument('status', choices=['running', 'stopped', 'completed'],
                        help='New status')
    parser.add_argument('--reason', default=None, help='Stop reason (for stopped status)')
    parser.add_argument('--state-file', default='.claude/aot-loop-state.md')
    args = parser.parse_args()

    state_file = Path(args.state_file)

    if not state_file.exists():
        print(f'{{"error": "State file not found: {state_file}", "success": false}}')
        sys.exit(1)

    content = state_file.read_text()
    new_content = set_loop_status(content, args.status, args.reason)

    state_file.write_text(new_content)

    result = {'success': True, 'status': args.status}
    if args.reason:
        result['reason'] = args.reason

    print(json.dumps(result))


if __name__ == '__main__':
    main()
