#!/usr/bin/env python3
"""
Verify file/directory existence.
Usage: python verify_file.py <path> [--expect-missing]

--expect-missing: For not_file type, PASS when file does NOT exist
"""

import sys
import json
import argparse
from pathlib import Path
from glob import glob as glob_expand


def get_file_info(path: Path) -> dict:
    """Get file information."""
    if not path.exists():
        return {"exists": False}

    try:
        if path.is_dir():
            # Count files in directory
            files = list(path.rglob("*"))
            file_count = len([f for f in files if f.is_file()])
            return {
                "exists": True,
                "is_dir": True,
                "file_count": file_count
            }
        else:
            # Get file size
            size = path.stat().st_size
            if size < 1024:
                size_str = f"{size}B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f}KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f}MB"
            return {
                "exists": True,
                "is_dir": False,
                "size": size,
                "size_str": size_str
            }
    except Exception as e:
        return {"exists": True, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description='Verify file/directory existence')
    parser.add_argument('path', help='Path to check (supports glob patterns like *.js)')
    parser.add_argument('--expect-missing', action='store_true',
                        help='For not_file: PASS when file does NOT exist')
    args = parser.parse_args()

    # Expand glob patterns if present
    if '*' in args.path or '?' in args.path:
        matches = glob_expand(args.path, recursive=True)
        exists = len(matches) > 0
        if exists:
            info = {"exists": True, "is_glob": True, "match_count": len(matches)}
        else:
            info = {"exists": False, "is_glob": True, "match_count": 0}
    else:
        path = Path(args.path)
        info = get_file_info(path)
        exists = info.get("exists", False)

    if args.expect_missing:
        # not_file: PASS when file does NOT exist
        passed = not exists
        if passed:
            if info.get("is_glob"):
                evidence = f"No files match pattern (as expected): {args.path}"
            else:
                evidence = f"Path does not exist (as expected): {args.path}"
        else:
            if info.get("is_glob"):
                evidence = f"{info.get('match_count', '?')} files match pattern (expected none): {args.path}"
            elif info.get("is_dir"):
                evidence = f"Directory exists with {info.get('file_count', '?')} files (expected missing): {args.path}"
            else:
                evidence = f"File exists ({info.get('size_str', '?')}) (expected missing): {args.path}"
        check_type = "not_file"
    else:
        # file: PASS when file exists
        passed = exists
        if passed:
            if info.get("is_glob"):
                evidence = f"{info.get('match_count', '?')} files match pattern: {args.path}"
            elif info.get("is_dir"):
                evidence = f"Directory exists with {info.get('file_count', '?')} files: {args.path}"
            else:
                evidence = f"File exists ({info.get('size_str', '?')}): {args.path}"
        else:
            if info.get("is_glob"):
                evidence = f"No files match pattern: {args.path}"
            else:
                evidence = f"Path not found: {args.path}"
        check_type = "file"

    output = {
        "passed": passed,
        "type": check_type,
        "path": args.path,
        "exists": exists,
        "evidence": evidence
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
