"""Skills over MCP (io.modelcontextprotocol/skills, SEP-2640, beta) on the SDK's Extension seam.

Each skill is a directory of files served as resources under skill://<authority>/<name>/. The
SKILL.md frontmatter is generated from the same values the listing reports, so the two cannot
drift, and every manifest entry carries the SHA-256 digest and size of the exact bytes that
resources/read returns.
"""

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from mcp.server.context import ServerRequestContext
from mcp.server.extension import Extension, MethodBinding, ResourceBinding
from mcp.server.mcpserver.resources import TextResource
from mcp.shared.exceptions import MCPError
from mcp.types import INVALID_PARAMS, PaginatedRequestParams, RequestParams
from mcp_types.version import MODERN_PROTOCOL_VERSIONS

SKILLS_EXTENSION = "io.modelcontextprotocol/skills"
# Agent Skills naming: 1-64 lowercase letters, digits and single hyphens, no edge hyphens.
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
LISTING_TTL_MS = 3_600_000


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str
    # Supporting files by path relative to the skill directory, for example references/x.md.
    files: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if len(self.name) > 64 or not NAME.fullmatch(self.name):
            raise ValueError(f"Invalid Agent Skills name: {self.name!r}")
        if not 1 <= len(self.description) <= 1024:
            raise ValueError(f"Skill {self.name} needs a 1-1024 character description")

    @property
    def title(self) -> str:
        return self.name.replace("-", " ").capitalize()

    @property
    def frontmatter(self) -> dict[str, str]:
        return {"name": self.name, "description": self.description}

    def skill_md(self) -> str:
        # The name pattern is a safe plain YAML scalar. A JSON string is a valid YAML
        # double-quoted scalar, so any description round-trips.
        return (
            f"---\nname: {self.name}\ndescription: {json.dumps(self.description)}\n---\n\n"
            + self.body.strip()
            + "\n"
        )


class SkillsExtension(Extension):
    identifier = SKILLS_EXTENSION

    def __init__(self, authority: str, skills: list[Skill]):
        names = [skill.name for skill in skills]
        if len(set(names)) != len(names):
            raise ValueError("Skill names must be unique within the server")
        self._skills: dict[str, Skill] = {}
        self._files: dict[str, dict[str, str]] = {}
        for skill in skills:
            root = f"skill://{authority}/{skill.name}"
            self._skills[f"{root}/SKILL.md"] = skill
            self._files[f"{root}/SKILL.md"] = {
                f"{root}/SKILL.md": skill.skill_md(),
                **{f"{root}/{path}": text for path, text in skill.files.items()},
            }
        self._entries = {uri: self._entry(uri) for uri in self._skills}

    def _entry(self, uri: str) -> dict[str, Any]:
        resources = []
        for file_uri, text in self._files[uri].items():
            data = text.encode()
            resources.append(
                {
                    "uri": file_uri,
                    "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
                    "size": len(data),
                }
            )
        return {"uri": uri, "frontmatter": self._skills[uri].frontmatter, "resources": resources}

    def resources(self) -> list[ResourceBinding]:
        bindings = []
        for uri, files in self._files.items():
            skill = self._skills[uri]
            for file_uri, text in files.items():
                is_root = file_uri == uri
                bindings.append(
                    ResourceBinding(
                        TextResource(
                            uri=file_uri,
                            name=skill.name if is_root else file_uri.rsplit("/", 1)[-1],
                            title=skill.title
                            if is_root
                            else f"{skill.title}: {file_uri.removeprefix(uri.removesuffix('SKILL.md'))}",
                            description=skill.description
                            if is_root
                            else f"Supporting file of the {skill.name} skill.",
                            mime_type="text/markdown" if file_uri.endswith(".md") else "text/plain",
                            text=text,
                        )
                    )
                )
        return bindings

    def methods(self) -> list[MethodBinding]:
        # Skills requests carry 2026-07-28 request metadata; earlier hosts use the plain
        # resources and prompts.
        modern = frozenset(MODERN_PROTOCOL_VERSIONS)
        return [
            MethodBinding("skills/list", PaginatedRequestParams, self._list, modern),
            MethodBinding("skills/get", GetSkillParams, self._get, modern),
        ]

    async def _list(
        self, ctx: ServerRequestContext[Any, Any], params: PaginatedRequestParams
    ) -> dict[str, Any]:
        if params.cursor is not None:
            # Every skill fits on one page, so no cursor was ever issued.
            raise MCPError(code=INVALID_PARAMS, message="Unknown skills/list cursor")
        return {
            "skills": list(self._entries.values()),
            "ttlMs": LISTING_TTL_MS,
            "cacheScope": "public",
        }

    async def _get(
        self, ctx: ServerRequestContext[Any, Any], params: "GetSkillParams"
    ) -> dict[str, Any]:
        entry = self._entries.get(params.uri)
        if entry is None:
            raise MCPError(code=INVALID_PARAMS, message=f"Unknown skill: {params.uri}")
        return {"skill": entry, "ttlMs": LISTING_TTL_MS, "cacheScope": "public"}


class GetSkillParams(RequestParams):
    uri: str
