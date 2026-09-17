"""Exercise the generated WTF-P dispatcher -> companion -> MCP stdio -> fixture API.

No provider network calls, package installation, or client profile changes.
Run with: uv run python scripts/check_wtfp.py --wtfp-root ../wtf-p
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wtfp-root", type=Path, required=True)
    args = parser.parse_args()
    node = shutil.which("node")
    if not node:
        parser.error("Node.js 20+ is required")
    root = Path(__file__).resolve().parents[1]
    fixture = root / "tests/fixtures/records.json"
    with tempfile.TemporaryDirectory(prefix="cite-nexus-wtfp-") as temporary:
        directory = Path(temporary)
        server = directory / "fixture_server.py"
        pid_file = directory / "server.pid"
        server.write_text(
            "import json,os,time\nimport httpx2 as httpx\n"
            "from cite_nexus_mcp.config import Settings\n"
            "from cite_nexus_mcp.http import HTTP\n"
            "from cite_nexus_mcp.service import ResearchService\n"
            "from cite_nexus_mcp.server import create_server\n"
            f"record=json.loads(open({str(fixture)!r}).read())['crossref']\n"
            f"open({str(pid_file)!r},'w').write(str(os.getpid()))\n"
            "settings=Settings(retries=0)\n"
            "def handle(request):\n"
            "    if request.url.host != 'api.crossref.org': raise AssertionError('Unexpected provider')\n"
            "    return httpx.Response(200,json={'message':{'items':[record]}})\n"
            "client=httpx.AsyncClient(transport=httpx.MockTransport(handle))\n"
            "create_server(service=ResearchService(settings,HTTP(settings,client))).run()\n"
        )
        bridge = directory / "fixture_bridge"
        bridge.write_text(
            f"#!{sys.executable}\n"
            "from mcp import StdioServerParameters\n"
            "from cite_nexus_mcp import wtfp\n"
            f"wtfp.server_parameters=lambda: StdioServerParameters(command={sys.executable!r},args=[{str(server)!r}])\n"
            "wtfp.run()\n"
        )
        bridge.chmod(0o700)
        env = {"PATH": os.environ.get("PATH", ""), "WTFP_CITE_NEXUS_COMMAND": str(bridge)}
        # Exercise both hosts with an established tool.execute binding.
        for target in ("plugin", "claude"):
            dispatcher = args.wtfp_root.resolve() / "vendors" / target / "tools/wtfp-tool.js"
            command = [
                node,
                str(dispatcher),
                "citation-search",
                "--backend=cite-nexus",
                "--query=reliable research",
                "--providers=crossref",
                "--limit=1",
                "--timeout=15",
            ]
            result = subprocess.run(
                command,
                cwd=directory,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
                check=True,
            )
            data = json.loads(result.stdout)
            paper = data["results"][0]
            assert paper["verification"] == "candidate"
            assert paper["citeNexus"]["sources"][0]["provider"] == "crossref"
            assert "citationCount" not in paper and "wtfp_status" not in paper["bibtex"]
            assert data["metadata"]["errors"] == []
            offline = subprocess.run(
                [*command, "--offline"],
                cwd=directory,
                env=env,
                capture_output=True,
                text=True,
                timeout=5,
            )
            assert offline.returncode != 0 and not offline.stdout
            print(
                f"PASS {target}: generated dispatcher -> bridge -> real MCP stdio -> fixture; offline gate"
            )
        if sys.platform != "win32":
            # A stuck provider must not orphan the SDK's separate process group
            # when WTF-P's hard deadline terminates the companion.
            server.write_text(
                server.read_text().replace(
                    "    return httpx.Response", "    time.sleep(60)\n    return httpx.Response"
                )
            )
            pid_file.unlink(missing_ok=True)
            command[-1] = "--timeout=3"
            result = subprocess.run(
                command, cwd=directory, env=env, capture_output=True, text=True, timeout=15
            )
            assert result.returncode == 124, result.stderr
            assert pid_file.exists(), "The timeout test did not reach MCP startup"
            pid = int(pid_file.read_text())
            for _ in range(100):
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.1)
            else:
                raise AssertionError("MCP server survived companion timeout")
            print("PASS deadline: hanging provider stopped; no orphan MCP server")


if __name__ == "__main__":
    main()
