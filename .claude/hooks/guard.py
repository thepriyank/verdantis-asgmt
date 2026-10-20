#!/usr/bin/env python3
"""PreToolUse guard: blocks coding-agent edits to red-zone paths (see docs/AGENT_POLICY.md).

Claude Code passes the tool call as JSON on stdin. Exit code 2 blocks the call and
shows stderr to the agent, so it must ask the human instead.
"""
import json
import sys
from fnmatch import fnmatch

RED_ZONE = [
    "CLAUDE.md",
    ".claude/*",
    "docs/AGENT_POLICY.md",
    ".github/workflows/*",
    ".env",
    ".env.*",
    "tests/golden/expected_output.json",
]

def main() -> int:
    try:
        call = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    tool_input = call.get("tool_input", {}) or {}
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    cwd = call.get("cwd", "")
    if cwd and path.startswith(cwd):
        path = path[len(cwd):].lstrip("/")
    if path.endswith(".env.example"):
        return 0
    for pattern in RED_ZONE:
        if fnmatch(path, pattern):
            print(
                f"BLOCKED by agent policy: '{path}' is a red-zone file. "
                "Propose the change in the PR description; a human must make it.",
                file=sys.stderr,
            )
            return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
