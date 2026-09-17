"""Inspect exactly one wheel/sdist pair; optionally install and test the wheel in isolation.

The optional install downloads runtime dependencies. MCP checks call local tools only.
No publishing or user-profile installation occurs.
"""

import argparse
import configparser
import email
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SMOKE = """
import asyncio, importlib.util, json, sys
from mcp import Client, StdioServerParameters
from cite_nexus_mcp import __version__
assert __version__ == sys.argv[1], __version__
assert importlib.util.find_spec('litellm') is None
async def main():
    async with Client(StdioServerParameters(command=sys.executable,
        args=['-m', 'cite_nexus_mcp', '--no-env-file']), read_timeout_seconds=10) as client:
        result = await client.list_tools()
        assert len(result.tools) == 11
        result = await client.call_tool('enhance-citation', {'bibtex':'@misc{test, title={Observed title}}'})
        assert not result.is_error
        print(json.dumps({'version': __version__, 'tools': 11, 'local_citation_check': 'passed'}))
asyncio.run(main())
"""


def check_paths(paths: list[str]) -> None:
    for name in paths:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name:
            raise ValueError(f"Unsafe archive path: {name}")
        if any(part in {".git", ".gemini", ".venv", "__pycache__"} for part in path.parts):
            raise ValueError(f"Private/development path in artifact: {name}")
        if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
            raise ValueError(f"Environment file in artifact: {name}")


def inspect(directory: Path, version: str) -> Path:
    wheel = directory / f"cite_nexus_mcp-{version}-py3-none-any.whl"
    sdist = directory / f"cite_nexus_mcp-{version}.tar.gz"
    files = set(directory.iterdir())
    ignore = directory / ".gitignore"
    # uv creates this marker in its build directory; it is not uploaded by the
    # workflow's explicit wheel/sdist artifact paths.
    if ignore in files and not ignore.is_symlink() and ignore.read_text().strip() == "*":
        files.remove(ignore)
    if files != {wheel, sdist} or any(path.is_symlink() for path in files):
        raise ValueError(
            "Publication directory must contain exactly the expected wheel and sdist; keep ZIPs/checksums elsewhere"
        )
    with zipfile.ZipFile(wheel) as archive:
        check_paths(archive.namelist())
        metadata = email.message_from_bytes(
            archive.read(f"cite_nexus_mcp-{version}.dist-info/METADATA")
        )
        if metadata["Name"] != "cite-nexus-mcp" or metadata["Version"] != version:
            raise ValueError("Wheel identity does not match the release")
        if "mcp-name: io.github.akougkas/cite-nexus-mcp" not in metadata.get_payload():
            raise ValueError("PyPI ownership marker is missing from wheel metadata")
        entries = configparser.ConfigParser()
        entries.read_string(
            archive.read(f"cite_nexus_mcp-{version}.dist-info/entry_points.txt").decode()
        )
        if not {"cite-nexus-mcp", "cite-nexus-wtfp"} <= set(entries["console_scripts"]):
            raise ValueError("Required installed commands are missing")
        if "cite_nexus_mcp/wtfp.py" not in archive.namelist():
            raise ValueError("Companion implementation is missing")
    with tarfile.open(sdist) as archive:
        check_paths(archive.getnames())
        if any(member.issym() or member.islnk() for member in archive):
            raise ValueError("Source artifact must not contain filesystem links")
        for required in ("pyproject.toml", "server.json", "src/cite_nexus_mcp/wtfp.py", "LICENSE"):
            if f"cite_nexus_mcp-{version}/{required}" not in archive.getnames():
                raise ValueError(f"Source artifact is missing {required}")
    for path in (wheel, sdist):
        print(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    return wheel


def installed_check(wheel: Path, version: str) -> None:
    uv = shutil.which("uv")
    if not uv:
        raise ValueError("uv is required for isolated installation")
    with tempfile.TemporaryDirectory(prefix="citenexus-distribution-") as temporary:
        root = Path(temporary)
        environment = root / "venv"
        subprocess.run([uv, "venv", str(environment), "--python", sys.executable], check=True)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            [uv, "pip", "install", "--python", str(python), str(wheel.resolve())], check=True
        )
        subprocess.run([str(python), "-I", "-c", SMOKE, version], cwd=root, check=True, timeout=30)
        result = subprocess.run(
            [str(python), "-I", "-m", "cite_nexus_mcp.wtfp", "--check"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        data = json.loads(result.stdout)
        if (
            data["schema_version"] != "cite-nexus.wtfp/v1"
            or len(data["providers"]["providers"]) != 9
        ):
            raise ValueError("Installed companion diagnostic returned an incompatible response")
        print("Installed wheel and companion checks passed without provider queries")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "dist/pypi")
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    try:
        wheel = inspect(args.directory.resolve(), version)
        if args.install:
            installed_check(wheel, version)
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"Distribution check failed: {error}") from None


if __name__ == "__main__":
    main()
