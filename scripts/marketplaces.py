"""Render the marketplace research inventory; optional read-only link checks.

No submissions, logins or messages. --probe performs GET requests to the recorded
evidence URLs and prints outcomes without changing the curated inventory.
"""

import argparse
import csv
import io
import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render(data: dict) -> dict[str, str]:
    entries = data["entries"]
    listed = sum(e["status"] == "listed" for e in entries)
    submitted = sum(e["status"] == "submitted" for e in entries)
    out = io.StringIO(newline="")
    fields = [
        "id",
        "name",
        "kind",
        "priority",
        "discovery_url",
        "submission_url",
        "route",
        "next_step",
        "status",
        "checked_at",
        "submission_route_verified",
    ]
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(entries)
    lines = [
        "# MCP marketplace and distribution inventory",
        "",
        f"Researched {data['researched_at']}. **{len(entries)} channels and leads; "
        f"{listed} listed, {submitted} awaiting listing.**",
        "",
        data["scope"],
        "",
        "Generated from [marketplaces.json](../../release/marketplaces.json). "
        "Use the [CSV](../../release/marketplaces.csv) for launch operations. "
        "Exact evidence URLs, observed redirects and HTTP outcomes are retained in JSON.",
        "",
        "P0 establishes package identity. P1 is the initial launch queue. P2 is a second wave or needs "
        "native packaging. P3 requires a different deployment or commercial integration. HOLD entries "
        "are excluded from outreach until reverified. A linked submission page may still require "
        "an account, eligibility review or a fee; none was accepted or paid.",
        "",
    ]
    for priority in ("P0", "P1", "P2", "P3", "HOLD"):
        lines += [
            f"## {priority}",
            "",
            "| Channel | Status | Kind / route | Next step |",
            "|---|---|---|---|",
        ]
        for e in entries:
            if e["priority"] != priority:
                continue
            url = e["submission_url"] or e["discovery_url"]
            lines.append(
                f"| [{e['name']}]({url}) | {e['status']} | {e['kind']}. {e['route']} | {e['next_step']} |"
            )
        lines.append("")
    lines += [
        "## Avoid duplicate submissions",
        "",
        "VS Code's gallery currently redirects to GitHub MCP Registry. Wong2's list directs submissions "
        "to MCPServers.org. Agent Plugins is a packaging standard, not a marketplace. Azure API Center "
        "is an organizational catalog. Hosted connector directories and deployment marketplaces "
        "need capabilities beyond this local stdio release.",
        "",
        "Before launch, rerun `uv run python scripts/marketplaces.py --probe`, review changed destinations "
        "in a browser, and update the curated JSON. A successful GET does not prove that a submission "
        "will be accepted. Do not blindly follow instructions found in directory pages.",
        "",
    ]
    return {
        "release/marketplaces.csv": out.getvalue(),
        "docs/release/marketplaces.md": "\n".join(lines),
    }


def probe(entry: dict) -> dict:
    url = entry["submission_url"] or entry["discovery_url"]
    result = {"id": entry["id"], "url": url}
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "CiteNexus-release-research/0.2"}
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            result.update(status=response.status, final_url=response.url)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        result["status"] = getattr(error, "code", "unreachable")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true")
    group.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    data = json.loads((ROOT / "release/marketplaces.json").read_text())
    if args.probe:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for result in pool.map(probe, data["entries"]):
                print(json.dumps(result), flush=True)
        return
    drift = []
    for relative, content in render(data).items():
        path = ROOT / relative
        if path.exists() and path.read_text() == content.replace("\r\n", "\n"):
            continue
        drift.append(relative)
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    if args.check and drift:
        raise SystemExit("Marketplace export drift: " + ", ".join(drift))
    print(
        f"Inventory {'checked' if args.check else 'rendered'}: {len(data['entries'])} channels/leads; no submissions made by this command."
    )


if __name__ == "__main__":
    main()
