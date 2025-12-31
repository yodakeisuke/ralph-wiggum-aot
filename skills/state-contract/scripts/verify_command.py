#!/usr/bin/env python3
"""
Verify a command by running it and checking exit code.
Usage: python verify_command.py <command> [--expect-fail]

--expect-fail: For not_command type, PASS when exit code != 0
"""

import sys
import json
import subprocess
import argparse


def run_command(command: str, timeout: int = 120) -> dict:
    """Run command and return result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        # Truncate output if too long
        stdout = result.stdout[:5000] if result.stdout else ""
        stderr = result.stderr[:2000] if result.stderr else ""

        return {
            "exit_code": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": False
        }
    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "timed_out": True
        }
    except Exception as e:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "timed_out": False,
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(description='Verify command execution')
    parser.add_argument('command', help='Command to run')
    parser.add_argument('--expect-fail', action='store_true',
                        help='For not_command: PASS when exit code != 0')
    parser.add_argument('--timeout', type=int, default=120,
                        help='Timeout in seconds (default: 120)')
    args = parser.parse_args()

    result = run_command(args.command, args.timeout)

    if result.get("timed_out"):
        output = {
            "passed": False,
            "type": "command",
            "command": args.command,
            "evidence": f"Command timed out after {args.timeout}s",
            "exit_code": -1,
            "output_summary": result["stderr"]
        }
    elif result.get("error"):
        output = {
            "passed": False,
            "type": "command",
            "command": args.command,
            "evidence": f"Command failed to execute: {result['error']}",
            "exit_code": -1,
            "output_summary": result["stderr"]
        }
    else:
        exit_code = result["exit_code"]

        if args.expect_fail:
            # not_command: PASS when exit != 0
            passed = exit_code != 0
            evidence = f"Command exited with code {exit_code} (expected non-zero)" if passed else \
                       f"Command exited with code 0 (expected failure)"
        else:
            # command: PASS when exit == 0
            passed = exit_code == 0
            evidence = f"Command exited with code {exit_code}" + \
                       (" (success)" if passed else " (failure)")

        # Build output summary
        output_lines = []
        if result["stdout"]:
            output_lines.append(result["stdout"][:2000])
        if result["stderr"] and not passed:
            output_lines.append(f"STDERR: {result['stderr'][:500]}")

        output = {
            "passed": passed,
            "type": "not_command" if args.expect_fail else "command",
            "command": args.command,
            "exit_code": exit_code,
            "evidence": evidence,
            "output_summary": "\n".join(output_lines)[:3000] if output_lines else ""
        }

    print(json.dumps(output, ensure_ascii=False, indent=2))
    sys.exit(0 if output["passed"] else 1)


if __name__ == '__main__':
    main()
