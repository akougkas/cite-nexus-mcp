"""Tasks (io.modelcontextprotocol/tasks, SEP-2663) on the SDK's Extension seam.

A tools/call the server chooses to run in the background answers with a CreateTaskResult, and the
client polls tasks/get. Only requests on the 2026-07-28 wire that declare the extension can get a
task; every other request runs synchronously as before. Tasks live in this process: they are lost
on restart and expire after TASK_TTL_MS. Task IDs carry 256 random bits and are the only handle
to a task, since there is no tasks/list.
"""

import asyncio
import logging
import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from mcp.server.context import CallNext, ServerRequestContext
from mcp.server.extension import Extension, MethodBinding
from mcp.server.mcpserver import require_client_extension
from mcp.shared.exceptions import MCPError
from mcp.types import INTERNAL_ERROR, INVALID_PARAMS, CallToolRequestParams, RequestParams
from mcp_types.version import MODERN_PROTOCOL_VERSIONS
from pydantic import BaseModel, ConfigDict, Field

from .service import task_run

TASKS_EXTENSION = "io.modelcontextprotocol/tasks"
TASK_TTL_MS = 3_600_000
POLL_INTERVAL_MS = 1_000
# Beyond this many retained tasks a call runs synchronously, which the extension allows.
MAX_TASKS = 64

logger = logging.getLogger(__name__)

Status = Literal["working", "completed", "failed", "cancelled"]
MESSAGES: dict[Status, str] = {
    "working": "The tool call is running.",
    "completed": "The tool call finished; result holds its CallToolResult.",
    "failed": "The tool call failed with a JSON-RPC error.",
    "cancelled": "The task was cancelled.",
}


class TaskParams(RequestParams):
    model_config = ConfigDict(extra="ignore")
    task_id: str = Field(alias="taskId")


def _timestamp(moment: datetime) -> str:
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _wire(result: Any) -> dict[str, Any]:
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json", by_alias=True, exclude_none=True)
    return dict(result)


@dataclass
class _Task:
    id: str
    created: datetime
    updated: datetime
    status: Status = "working"
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    runner: asyncio.Task[None] | None = field(default=None, repr=False)

    def expired(self, now: datetime) -> bool:
        return now - self.created > timedelta(milliseconds=TASK_TTL_MS)

    def finish(self, status: Status, **payload: Any) -> None:
        if self.status == "working":
            self.status, self.updated = status, datetime.now(UTC)
            for key, value in payload.items():
                setattr(self, key, value)

    def view(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "taskId": self.id,
            "status": self.status,
            "statusMessage": MESSAGES[self.status],
            "createdAt": _timestamp(self.created),
            "lastUpdatedAt": _timestamp(self.updated),
            "ttlMs": TASK_TTL_MS,
            "pollIntervalMs": POLL_INTERVAL_MS,
        }
        if self.status == "completed":
            data["result"] = self.result
        if self.status == "failed":
            data["error"] = self.error
        return data


class TasksExtension(Extension):
    identifier = TASKS_EXTENSION

    def __init__(self, eligible: Callable[[str, Mapping[str, Any]], bool]):
        """`eligible(tool name, arguments)` says whether a call is long enough to run as a task."""
        self._eligible = eligible
        self._tasks: dict[str, _Task] = {}

    def methods(self) -> list[MethodBinding]:
        versions = frozenset(MODERN_PROTOCOL_VERSIONS)
        return [
            MethodBinding("tasks/get", TaskParams, self._get, versions),
            MethodBinding("tasks/update", TaskParams, self._update, versions),
            MethodBinding("tasks/cancel", TaskParams, self._cancel, versions),
        ]

    async def intercept_tool_call(
        self,
        params: CallToolRequestParams,
        ctx: ServerRequestContext[Any, Any],
        call_next: CallNext,
    ) -> Any:
        capabilities = ctx.session.client_capabilities
        declared = bool(
            capabilities and capabilities.extensions and TASKS_EXTENSION in capabilities.extensions
        )
        if (
            not declared
            or ctx.protocol_version not in MODERN_PROTOCOL_VERSIONS
            or not self._eligible(params.name, params.arguments or {})
        ):
            return await call_next(ctx)
        self._purge()
        if len(self._tasks) >= MAX_TASKS:
            return await call_next(ctx)
        now = datetime.now(UTC)
        task = _Task(secrets.token_urlsafe(32), now, now)
        # Stored before the CreateTaskResult is returned, so tasks/get resolves it at once.
        self._tasks[task.id] = task
        task.runner = asyncio.create_task(self._run(task, call_next, ctx))
        return {"resultType": "task", **task.view()}

    async def _run(
        self, task: _Task, call_next: CallNext, ctx: ServerRequestContext[Any, Any]
    ) -> None:
        task_run.set(True)
        try:
            result = await call_next(ctx)
        except asyncio.CancelledError:
            task.finish("cancelled")
        except MCPError as exc:
            task.finish("failed", error=exc.error.model_dump(mode="json", exclude_none=True))
        except Exception:
            logger.exception("Task %s failed", task.id[:8])
            task.finish("failed", error={"code": INTERNAL_ERROR, "message": "Internal error"})
        else:
            # A tool result with isError is still a completed call; failed is for JSON-RPC errors.
            task.finish("completed", result=_wire(result))

    def _purge(self) -> None:
        now = datetime.now(UTC)
        for task_id, task in list(self._tasks.items()):
            if task.expired(now):
                if task.runner and not task.runner.done():
                    task.runner.cancel()
                del self._tasks[task_id]

    def _find(self, ctx: ServerRequestContext[Any, Any], params: TaskParams) -> _Task:
        require_client_extension(ctx, TASKS_EXTENSION)
        self._purge()
        task = self._tasks.get(params.task_id)
        if task is None:
            raise MCPError(INVALID_PARAMS, "Failed to retrieve task: task not found or expired")
        return task

    async def _get(self, ctx: ServerRequestContext[Any, Any], params: TaskParams) -> dict[str, Any]:
        return self._find(ctx, params).view()

    async def _update(
        self, ctx: ServerRequestContext[Any, Any], params: TaskParams
    ) -> dict[str, Any]:
        # PanCite tasks never ask for input, so there is nothing outstanding to answer.
        self._find(ctx, params)
        return {}

    async def _cancel(
        self, ctx: ServerRequestContext[Any, Any], params: TaskParams
    ) -> dict[str, Any]:
        task = self._find(ctx, params)
        if task.status == "working" and task.runner is not None:
            task.finish("cancelled")
            task.runner.cancel()
        return {}

    async def aclose(self) -> None:
        runners = [t.runner for t in self._tasks.values() if t.runner and not t.runner.done()]
        for runner in runners:
            runner.cancel()
        await asyncio.gather(*runners, return_exceptions=True)
