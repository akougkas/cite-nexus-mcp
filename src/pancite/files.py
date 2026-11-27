"""File arguments (io.modelcontextprotocol/files, experimental draft) for a local server.

PanCite stores nothing, so it accepts files inline only: the server advertises maxInlineBytes and
no upload. Every field name of the extension lives in this module. A file is checked against its
declared type, size and optional SHA-256 digest before the tool runs; a failed check is reported
as a tool error, never as a protocol error, and the bytes are never echoed back.
"""

import base64
import binascii
import copy
import hashlib
from typing import Any, Literal, cast

from mcp.server.context import ServerRequestContext
from mcp.server.extension import Extension
from mcp.server.lowlevel.server import Server
from mcp.types import ListToolsResult, PaginatedRequestParams
from pydantic import BaseModel, ConfigDict, Field

FILES_EXTENSION = "io.modelcontextprotocol/files"
KEYWORD = "x-mcp-file"
MAX_INLINE_BYTES = 1_048_576
# Each file is at most the 100,000 characters a string argument may carry.
MAX_FILE_BYTES = 100_000

# Accepted extensions and media types, and the citation format each one carries.
FORMATS = {
    ".bib": "bibtex",
    "application/x-bibtex": "bibtex",
    "text/x-bibtex": "bibtex",
    ".ris": "ris",
    "application/x-research-info-systems": "ris",
    ".json": "csl-json",
    "application/vnd.citationstyles.csl+json": "csl-json",
    "application/json": "csl-json",
    ".txt": "text",
    "text/plain": "text",
}


class FileRejected(ValueError):
    """A file argument failed a check; the tool does not run."""


class FileDigest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    algorithm: Literal["sha-256"]
    value: str = Field(description="SHA-256 of the file bytes, base64url without padding.")


class FileInput(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    id: str = Field(min_length=1, max_length=128)
    name: str | None = None
    mime_type: str = Field(alias="mimeType")
    size: int = Field(ge=0)
    digest: FileDigest | None = None
    data: str | None = None


def file_schema(description: str, accept: tuple[str, ...]) -> dict[str, Any]:
    """The FileInput object schema carrying the x-mcp-file marker, as the spec shows it."""
    return {
        "type": "object",
        "description": description,
        KEYWORD: {"accept": list(accept), "maxSize": MAX_FILE_BYTES},
        "properties": {
            "id": {"type": "string", "minLength": 1, "maxLength": 128},
            "name": {"type": "string"},
            "mimeType": {"type": "string"},
            "size": {"type": "integer", "minimum": 0},
            "digest": {
                "type": "object",
                "properties": {
                    "algorithm": {"const": "sha-256"},
                    "value": {"type": "string"},
                },
                "required": ["algorithm", "value"],
            },
            "data": {"type": "string"},
        },
        "required": ["id", "mimeType", "size"],
    }


def kind(file: FileInput, accept: tuple[str, ...]) -> str:
    """The format of the accepted extension or media type the file matches, by name first."""
    name = (file.name or "").replace("\\", "/").rsplit("/", 1)[-1].lower()
    suffix = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    media = file.mime_type.split(";", 1)[0].strip().lower()
    for candidate in (suffix, media):
        if candidate and candidate in accept:
            return FORMATS[candidate]
    raise FileRejected(
        f"File {file.name or file.id!r} ({file.mime_type}) is not an accepted type. "
        f"Accepted: {', '.join(accept)}."
    )


def read(file: FileInput, accept: tuple[str, ...]) -> tuple[str, str]:
    """Check a file argument and return (format, UTF-8 text). Raises FileRejected."""
    label = repr(file.name or file.id)
    matched = kind(file, accept)
    if file.size > MAX_FILE_BYTES:
        raise FileRejected(f"File {label} is {file.size} bytes; the limit is {MAX_FILE_BYTES}.")
    if "data" in file.model_fields_set and file.data is None:
        raise FileRejected(f"File {label} has null data, which is not valid base64.")
    if file.data is None and file.size > 0:
        raise FileRejected(
            f"File {label} has no data. PanCite has no upload storage: send the file inline as "
            f"base64 data, at most {MAX_FILE_BYTES} bytes."
        )
    encoded = file.data or ""
    if len(encoded) > (MAX_FILE_BYTES + 2) // 3 * 4:
        raise FileRejected(f"File {label} is over the {MAX_FILE_BYTES}-byte limit.")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise FileRejected(f"File {label} data is not valid base64.") from None
    if len(content) != file.size:
        raise FileRejected(
            f"File {label} decodes to {len(content)} bytes but declares size {file.size}."
        )
    if file.digest is not None:
        actual = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=")
        if actual.decode() != file.digest.value.rstrip("="):
            raise FileRejected(f"File {label} does not match its sha-256 digest.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise FileRejected(f"File {label} is not UTF-8 text.") from None
    return matched, text


def declared(ctx: ServerRequestContext[Any, Any]) -> bool:
    capabilities = ctx.session.client_capabilities
    return bool(
        capabilities and capabilities.extensions and FILES_EXTENSION in capabilities.extensions
    )


def _without_file_arguments(tool: Any) -> Any:
    schema = tool.input_schema
    marked = [key for key, value in schema.get("properties", {}).items() if KEYWORD in value]
    if not marked:
        return tool
    schema = copy.deepcopy(schema)
    for key in marked:
        del schema["properties"][key]
    schema["required"] = [key for key in schema.get("required", []) if key not in marked]
    if not schema["required"]:
        del schema["required"]
    return tool.model_copy(update={"input_schema": schema})


def list_file_arguments_only_when_declared(server: Server[Any]) -> None:
    """List tools without their file arguments for requests that did not declare the extension.

    The draft asks servers to hide x-mcp-file schemas from such clients or offer another way to
    pass the file. Each tool keeps its string argument, so this variant is the same tool. Inline
    files sent anyway are still accepted.
    """
    entry = server.get_request_handler("tools/list")
    assert entry is not None
    listed = entry.handler

    async def handler(
        ctx: ServerRequestContext[Any, Any], params: PaginatedRequestParams
    ) -> ListToolsResult:
        result = cast(ListToolsResult, await listed(ctx, params))
        if declared(ctx):
            return result
        return result.model_copy(
            update={"tools": [_without_file_arguments(t) for t in result.tools]}
        )

    server.add_request_handler("tools/list", PaginatedRequestParams, handler)


class FilesExtension(Extension):
    identifier = FILES_EXTENSION

    def settings(self) -> dict[str, Any]:
        return {"maxInlineBytes": MAX_INLINE_BYTES}
