"""Helpers to regenerate `.github/INSTRUCTIONS.md` with current project structure."""

from __future__ import annotations

from datetime import date
from pathlib import Path

DEFAULT_OUTPUT = Path(".github/INSTRUCTIONS.md")


def _build_tree(root: Path, max_depth: int = 3) -> list[str]:
    """Return a simple markdown code-block tree for the repository."""
    ignore = {".git", ".venv", "hometools-env", "__pycache__", ".idea", ".pytest_cache"}
    lines = [f"{root.name}/"]

    def walk(path: Path, prefix: str, depth: int) -> None:
        if depth > max_depth:
            return

        entries = sorted(
            [p for p in path.iterdir() if p.name not in ignore],
            key=lambda p: (p.is_file(), p.name.lower()),
        )
        for index, entry in enumerate(entries):
            connector = "└── " if index == len(entries) - 1 else "├── "
            name = f"{entry.name}/" if entry.is_dir() else entry.name
            lines.append(f"{prefix}{connector}{name}")
            if entry.is_dir():
                extension = "    " if index == len(entries) - 1 else "│   "
                walk(entry, prefix + extension, depth + 1)

    walk(root, "", depth=1)
    return lines


def render_instructions(root: Path) -> str:
    """Render the complete developer instruction document."""
    tree_lines = _build_tree(root)
    tree = "\n".join(tree_lines)
    today = date.today().isoformat()

    return f"""# INSTRUCTIONS - hometools Developer Guide

> Auto-generated overview. Run `hometools update-instructions` after structural changes.
> Last updated: {today}

## Project Structure

```text
{tree}
```

## Quick Commands

```powershell
# Run tests
pytest

# Manual audio sync from NAS source
hometools sync-audio --dry-run
hometools sync-audio

# Start local audio streaming MVP
hometools serve-audio

# Regenerate this file
hometools update-instructions
```

## Notes

- Keep secrets in `.env`, never in source files.
- Keep side effects behind explicit CLI commands.
- Add tests for new pure functions in `tests/`.
- Audio sync runs only on command (no automatic NAS polling).
"""


def update_instructions_file(repo_root: Path, output_path: Path | None = None) -> Path:
    """Write the generated instructions to disk and return the file path."""
    output = (output_path or DEFAULT_OUTPUT)
    target = output if output.is_absolute() else repo_root / output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_instructions(repo_root), encoding="utf-8")
    return target

