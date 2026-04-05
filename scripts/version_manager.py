#!/usr/bin/env python3
"""Version management utility for the Personal Semantic Engine."""

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def get_current_version():
    """Get the current version from pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        raise FileNotFoundError("pyproject.toml not found")

    content = pyproject_path.read_text()
    match = re.search(r'version = "([^"]+)"', content)
    if not match:
        raise ValueError("Version not found in pyproject.toml")

    return match.group(1)


def update_version(new_version):
    """Update version in pyproject.toml."""
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()

    # Update version
    updated_content = re.sub(
        r'version = "[^"]+"', f'version = "{new_version}"', content
    )

    pyproject_path.write_text(updated_content)
    print(f"Updated pyproject.toml version to {new_version}")


def update_changelog(version, changes):
    """Update CHANGELOG.md with new version."""
    changelog_path = Path("CHANGELOG.md")
    if not changelog_path.exists():
        print("CHANGELOG.md not found, skipping changelog update")
        return

    content = changelog_path.read_text()
    today = datetime.now().strftime("%Y-%m-%d")

    # Replace [Unreleased] with new version
    unreleased_pattern = r"## \[Unreleased\].*?(?=## \[|\Z)"

    new_section = f"""## [Unreleased]

### Added
- Features in development

### Changed
- Changes to existing functionality

### Fixed
- Bug fixes

## [{version}] - {today}

{changes}

"""

    if "## [Unreleased]" in content:
        updated_content = re.sub(
            r"## \[Unreleased\].*?(?=## \[)", new_section, content, flags=re.DOTALL
        )
    else:
        # Insert after the header
        lines = content.split("\n")
        header_end = 0
        for i, line in enumerate(lines):
            if line.startswith("## "):
                header_end = i
                break

        lines.insert(header_end, new_section)
        updated_content = "\n".join(lines)

    changelog_path.write_text(updated_content)
    print(f"Updated CHANGELOG.md with version {version}")


def create_git_tag(version, message):
    """Create and push git tag."""
    try:
        # Create tag
        subprocess.run(["git", "tag", "-a", f"v{version}", "-m", message], check=True)
        print(f"Created git tag v{version}")

        # Push tag
        subprocess.run(["git", "push", "origin", f"v{version}"], check=True)
        print(f"Pushed git tag v{version}")

    except subprocess.CalledProcessError as e:
        print(f"Git operation failed: {e}")
        return False

    return True


def bump_version(current_version, bump_type):
    """Bump version based on type (major, minor, patch)."""
    parts = current_version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {current_version}")

    major, minor, patch = map(int, parts)

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")

    return f"{major}.{minor}.{patch}"


def main():
    """Main version management function."""
    parser = argparse.ArgumentParser(description="Manage project versions")
    parser.add_argument("--current", action="store_true", help="Show current version")
    parser.add_argument(
        "--bump", choices=["major", "minor", "patch"], help="Bump version"
    )
    parser.add_argument("--set", help="Set specific version")
    parser.add_argument("--tag", action="store_true", help="Create git tag")
    parser.add_argument("--message", help="Tag message")
    parser.add_argument("--changelog", help="Changelog entry for this version")

    args = parser.parse_args()

    try:
        current_version = get_current_version()

        if args.current:
            print(f"Current version: {current_version}")
            return

        new_version = None

        if args.bump:
            new_version = bump_version(current_version, args.bump)
            print(f"Bumping version from {current_version} to {new_version}")
            update_version(new_version)

        elif args.set:
            new_version = args.set
            print(f"Setting version from {current_version} to {new_version}")
            update_version(new_version)

        if new_version and args.changelog:
            update_changelog(new_version, args.changelog)

        if args.tag and new_version:
            message = args.message or f"Release v{new_version}"
            create_git_tag(new_version, message)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
