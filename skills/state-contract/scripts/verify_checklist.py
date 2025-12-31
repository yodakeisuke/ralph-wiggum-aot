#!/usr/bin/env python3
"""
Verify base_case checklist from state file.
Usage: python verify_checklist.py [--state-file PATH]

Evaluates each item recursively:
- type: command → verify_command.py
- type: file → verify_file.py
- type: not_command → verify_command.py --expect-fail
- type: not_file → verify_file.py --expect-missing
- type: quality → skip (needs LLM judgment by Verifier agent)
- group → AND (all must pass)
- any_of → OR (any one passes)
"""

import sys
import json
import subprocess
import argparse
import re
from pathlib import Path


def run_verify_script(script_name: str, args: list) -> dict:
    """Run a verification script and return parsed result."""
    script_dir = Path(__file__).parent
    script_path = script_dir / script_name

    try:
        result = subprocess.run(
            ["python3", str(script_path)] + args,
            capture_output=True,
            text=True,
            timeout=120
        )
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"passed": False, "evidence": "Verification timed out"}
    except json.JSONDecodeError:
        return {"passed": False, "evidence": f"Invalid JSON from {script_name}"}
    except Exception as e:
        return {"passed": False, "evidence": str(e)}


def parse_checklist_items(lines: list, start_idx: int, base_indent: int) -> tuple:
    """
    Parse checklist items recursively.
    Returns (items, next_index)
    """
    items = []
    idx = start_idx

    while idx < len(lines):
        line = lines[idx]
        if not line.strip():
            idx += 1
            continue

        # Calculate indent
        indent = len(line) - len(line.lstrip())

        # If we've gone back to parent level, stop
        if indent < base_indent and line.strip():
            break

        # If this is a list item at our level
        if line.strip().startswith('- item:'):
            item = {}
            # Extract item name
            match = re.search(r'- item:\s*"?([^"]+)"?', line)
            if match:
                item['item'] = match.group(1).strip('"').strip("'")

            idx += 1
            item_indent = indent + 2  # Expected indent for item content

            # Parse item content
            while idx < len(lines):
                content_line = lines[idx]
                if not content_line.strip():
                    idx += 1
                    continue

                content_indent = len(content_line) - len(content_line.lstrip())
                content_stripped = content_line.strip()

                # Back to same or lower indent means end of item
                if content_indent <= indent and content_stripped:
                    break

                # group: starts a nested AND group
                if content_stripped == 'group:':
                    idx += 1
                    sub_items, idx = parse_checklist_items(lines, idx, content_indent + 2)
                    item['group'] = sub_items
                    continue

                # any_of: starts a nested OR group
                if content_stripped == 'any_of:':
                    idx += 1
                    sub_items, idx = parse_checklist_items(lines, idx, content_indent + 2)
                    item['any_of'] = sub_items
                    continue

                # check: starts a check definition
                if content_stripped == 'check:':
                    idx += 1
                    check = {}
                    check_indent = content_indent + 2
                    while idx < len(lines):
                        check_line = lines[idx]
                        if not check_line.strip():
                            idx += 1
                            continue
                        ci = len(check_line) - len(check_line.lstrip())
                        if ci < check_indent and check_line.strip():
                            break
                        cs = check_line.strip()

                        # Parse check fields
                        for field in ['type', 'value', 'criteria', 'pass_threshold']:
                            if cs.startswith(f'{field}:'):
                                val = cs.split(':', 1)[1].strip().strip('"').strip("'")
                                if field == 'pass_threshold':
                                    try:
                                        check[field] = int(val)
                                    except ValueError:
                                        try:
                                            check[field] = float(val)
                                        except ValueError:
                                            check[field] = val
                                else:
                                    check[field] = val
                                break
                        idx += 1
                    item['check'] = check
                    continue

                idx += 1

            items.append(item)
        else:
            idx += 1

    return items, idx


def parse_base_case(content: str) -> dict:
    """Parse base_case from state file content."""
    lines = content.split('\n')

    # Find base_case section
    base_case_start = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('base_case:'):
            base_case_start = i
            break

    if base_case_start < 0:
        return {}

    # Check for checklist format
    for i in range(base_case_start + 1, min(base_case_start + 5, len(lines))):
        if 'checklist:' in lines[i]:
            # Parse checklist
            checklist_indent = len(lines[i]) - len(lines[i].lstrip()) + 2
            items, _ = parse_checklist_items(lines, i + 1, checklist_indent)
            return {'checklist': items}

    # Check for legacy format (type: value:)
    legacy = {}
    for i in range(base_case_start + 1, min(base_case_start + 10, len(lines))):
        line = lines[i].strip()
        if not line:
            continue
        # Stop at next top-level key under objective
        if not lines[i].startswith('    ') and ':' in line:
            break
        for field in ['type', 'value']:
            if line.startswith(f'{field}:'):
                legacy[field] = line.split(':', 1)[1].strip().strip('"').strip("'")

    if legacy:
        return legacy

    return {}


def verify_check(check: dict) -> dict:
    """Verify a single check item."""
    check_type = check.get("type", "")
    value = check.get("value", "")

    if check_type == "command":
        return run_verify_script("verify_command.py", [value])

    elif check_type == "not_command":
        return run_verify_script("verify_command.py", [value, "--expect-fail"])

    elif check_type == "file":
        return run_verify_script("verify_file.py", [value])

    elif check_type == "not_file":
        return run_verify_script("verify_file.py", [value, "--expect-missing"])

    elif check_type == "quality":
        # Quality checks need LLM judgment - mark as skipped
        criteria = check.get("criteria", "")
        threshold = check.get("pass_threshold", "")
        return {
            "passed": None,
            "skipped": True,
            "type": "quality",
            "evidence": f"Quality check requires LLM judgment (threshold: {threshold}): {criteria}"
        }

    else:
        return {
            "passed": False,
            "evidence": f"Unknown check type: {check_type}"
        }


def verify_item(item: dict, depth: int = 0) -> dict:
    """Recursively verify a checklist item."""
    item_name = item.get("item", "Unknown")
    result = {"item": item_name}

    # Check if this item has a 'group' (AND)
    if "group" in item:
        sub_results = []
        all_passed = True
        skipped_items = []

        for sub_item in item["group"]:
            sub_result = verify_item(sub_item, depth + 1)
            sub_results.append(sub_result)

            if sub_result.get("skipped"):
                skipped_items.append(sub_result.get("item", "?"))
            elif not sub_result.get("passed"):
                all_passed = False

        result["passed"] = all_passed
        result["group_results"] = sub_results
        result["evidence"] = f"AND group: {sum(1 for r in sub_results if r.get('passed'))}/{len(sub_results)} passed"
        if skipped_items:
            result["skipped_items"] = skipped_items

    # Check if this item has 'any_of' (OR)
    elif "any_of" in item:
        sub_results = []
        any_passed = False
        skipped_items = []

        for sub_item in item["any_of"]:
            sub_result = verify_item(sub_item, depth + 1)
            sub_results.append(sub_result)

            if sub_result.get("skipped"):
                skipped_items.append(sub_result.get("item", "?"))
            elif sub_result.get("passed"):
                any_passed = True

        result["passed"] = any_passed
        result["any_of_results"] = sub_results
        result["evidence"] = f"OR group: {sum(1 for r in sub_results if r.get('passed'))}/{len(sub_results)} passed (need 1)"
        if skipped_items:
            result["skipped_items"] = skipped_items

    # This item has a direct 'check'
    elif "check" in item:
        check_result = verify_check(item["check"])
        result.update(check_result)

    else:
        result["passed"] = False
        result["evidence"] = "No check, group, or any_of defined"

    return result


def main():
    parser = argparse.ArgumentParser(description='Verify base_case checklist')
    parser.add_argument('--state-file', default='.claude/aot-loop-state.md')
    args = parser.parse_args()

    state_file = Path(args.state_file)

    if not state_file.exists():
        print(json.dumps({
            "error": f"State file not found: {state_file}",
            "passed": False
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    content = state_file.read_text()
    base_case = parse_base_case(content)

    # Handle checklist format
    if "checklist" in base_case:
        checklist = base_case["checklist"]
        results = []
        all_passed = True
        skipped = []

        for item in checklist:
            item_result = verify_item(item)
            results.append(item_result)

            if item_result.get("skipped"):
                skipped.append(f"{item_result.get('item')} (type: quality)")
            elif item_result.get("skipped_items"):
                skipped.extend([f"{s} (type: quality)" for s in item_result.get("skipped_items", [])])

            # If not skipped and not passed, overall fails
            if not item_result.get("skipped") and not item_result.get("passed"):
                all_passed = False

        output = {
            "passed": all_passed,
            "checklist": results,
            "skipped": skipped
        }

    # Handle legacy format (single check)
    elif "type" in base_case:
        check_result = verify_check(base_case)
        output = {
            "passed": check_result.get("passed", False),
            "checklist": [{"item": "base_case", **check_result}],
            "skipped": ["base_case (type: quality)"] if check_result.get("skipped") else []
        }

    else:
        output = {
            "error": "No checklist or valid base_case found",
            "passed": False,
            "checklist": []
        }

    print(json.dumps(output, ensure_ascii=False, indent=2))
    sys.exit(0 if output.get("passed") else 1)


if __name__ == '__main__':
    main()
