"""Check release identity and, when requested, the exact annotated publication tag.

Read-only: does not create tags, change release state, log in or publish.
"""

import argparse
import json
import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_publish_state(version: str, product: dict, changelog: str, readme: str) -> None:
    if product.get("stage") != "release-ready" or product.get("release_authorized") is not True:
        raise ValueError(
            "Release is still preparation-only; finalize the reviewed release state first"
        )
    heading = rf"^## {re.escape(version)} — \d{{4}}-\d{{2}}-\d{{2}}$"
    if not re.search(heading, changelog, re.MULTILINE):
        raise ValueError("CHANGELOG needs a dated entry for the exact release version")
    if f"{version} is in release preparation" in readme or "nothing in the release" in readme:
        raise ValueError("Finalize the README preparation banner before publication")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tag",
        help="Require an approved, annotated release tag on HEAD, reachable from origin/master",
    )
    args = parser.parse_args()
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    version = project["version"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit(
            "This stable publication workflow requires a three-component release version"
        )
    manifest = json.loads((ROOT / "server.json").read_text())
    if manifest["version"] != version or manifest["packages"][0]["version"] != version:
        raise SystemExit("Registry and package versions differ; regenerate release metadata")
    if args.tag:
        if args.tag != f"v{version}":
            raise SystemExit(f"Tag must be exactly v{version}")
        try:
            validate_publish_state(
                version,
                json.loads((ROOT / "release/product.json").read_text()),
                (ROOT / "CHANGELOG.md").read_text(),
                (ROOT / "README.md").read_text(),
            )
            reference = f"refs/tags/{args.tag}"
            if git("cat-file", "-t", reference) != "tag":
                raise ValueError("An annotated tag is required")
            if git("rev-parse", f"{reference}^{{}}") != git("rev-parse", "HEAD"):
                raise ValueError("HEAD is not the selected release tag")
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", "HEAD", "origin/master"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            )
            if git("status", "--porcelain", "--untracked-files=no"):
                raise ValueError("Tracked working-tree changes are not permitted for publication")
        except (ValueError, subprocess.CalledProcessError) as error:
            raise SystemExit(f"Release gate failed: {error}") from None
    print(
        f"Release identity checked: cite-nexus-mcp {version}; publication {'gate passed' if args.tag else 'not authorized or attempted'}"
    )


if __name__ == "__main__":
    main()
