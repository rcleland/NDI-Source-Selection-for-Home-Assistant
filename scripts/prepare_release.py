#!/usr/bin/env python3
"""Bump manifest version and prepend CHANGELOG entry for automated releases."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "custom_components/magewell_pro_convert_decoder/manifest.json"
CHANGELOG = ROOT / "CHANGELOG.md"


def latest_tag_version() -> str:
    """Return the highest v* tag version, or 0.0.0 if none."""
    result = subprocess.run(
        ["git", "tag", "-l", "v*", "--sort=-v:refname"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    tags = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not tags:
        return "0.0.0"
    return tags[0].removeprefix("v")


def bump_patch(version: str) -> str:
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Invalid semver: {version}")
    major, minor, patch = (int(part) for part in parts)
    return f"{major}.{minor}.{patch + 1}"


def _parse_version(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"Invalid semver: {version}")
    return int(parts[0]), int(parts[1]), int(parts[2])


def manifest_version() -> str:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return str(data["version"])


def has_release_tags() -> bool:
    result = subprocess.run(
        ["git", "tag", "-l", "v*"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    return bool(result.stdout.strip())


def next_version() -> str:
    """Next release version: respect a manual manifest bump, else patch increment."""
    current_manifest = manifest_version()
    if not has_release_tags():
        return current_manifest
    tag_version = latest_tag_version()
    if _parse_version(current_manifest) > _parse_version(tag_version):
        return current_manifest
    return bump_patch(tag_version)


def update_manifest(version: str) -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    data["version"] = version
    MANIFEST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def prepend_changelog(version: str, commit_message: str, commit_sha: str) -> str:
    """Prepend entry; return release notes body for GitHub."""
    entry_date = date.today().isoformat()
    body = f"- {commit_message} ({commit_sha})"
    section = f"## [{version}] - {entry_date}\n\n### Changed\n{body}\n"
    existing = CHANGELOG.read_text(encoding="utf-8")
    if existing.startswith("# Changelog"):
        lines = existing.splitlines(keepends=True)
        # Insert after title + blank line
        insert_at = 1
        if len(lines) > 1 and lines[1].strip() == "":
            insert_at = 2
        updated = "".join(lines[:insert_at] + ["\n", section, "\n"] + lines[insert_at:])
    else:
        updated = f"# Changelog\n\n{section}\n{existing}"
    CHANGELOG.write_text(updated, encoding="utf-8")
    return section.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        help="Release version (default: next patch after latest tag)",
    )
    parser.add_argument("--message", help="Trigger commit subject")
    parser.add_argument("--sha", help="Trigger commit short SHA")
    parser.add_argument(
        "--release-notes-file",
        help="Write GitHub release notes to this path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the next version without modifying files",
    )
    args = parser.parse_args()

    if args.dry_run:
        print(next_version())
        return 0

    if not args.message or not args.sha:
        parser.error("--message and --sha are required unless --dry-run is set")

    version = args.version or next_version()
    update_manifest(version)
    notes = prepend_changelog(version, args.message, args.sha)
    print(version)
    if args.release_notes_file:
        Path(args.release_notes_file).write_text(notes + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
