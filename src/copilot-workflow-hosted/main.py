"""GitHub Copilot SDK agent hosted with the Foundry invocations protocol."""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from azure.ai.agentserver.invocations import InvocationAgentServerHost
from copilot import CopilotClient
from copilot.session_events import AssistantMessageData
from dotenv import load_dotenv
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from workflow import run_slogan_workflow

load_dotenv(override=False)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = InvocationAgentServerHost()

MODEL = os.environ.get("COPILOT_MODEL", "claude-opus-5")
COPILOT_HOME = os.environ.get(
    "COPILOT_HOME",
    str(Path("/tmp") / "copilot-workflow-hosted"),
)

SINGLE_AGENT_INSTRUCTIONS = """
You are a senior AI solution architect.
Answer in Korean unless the user asks for another language.
Give practical, accurate, and concise guidance. Clearly label assumptions,
risks, and steps that require human approval. Do not use tools.
""".strip()

_client: CopilotClient | None = None
_client_lock = asyncio.Lock()


def _require_github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN is required and must have Copilot Requests: Read-only."
        )
    return token


async def _get_client() -> CopilotClient:
    global _client
    if _client is not None:
        return _client

    async with _client_lock:
        if _client is None:
            candidate = CopilotClient(
                github_token=_require_github_token(),
                use_logged_in_user=False,
                mode="empty",
                base_directory=COPILOT_HOME,
            )
            await candidate.start()
            _client = candidate
            logger.info("Copilot SDK runtime started with model %s", MODEL)
    return _client


async def _run_copilot_session(
    stage_name: str,
    instructions: str,
    prompt: str,
) -> str:
    client = await _get_client()
    session = await client.create_session(
        model=MODEL,
        system_message={"mode": "append", "content": instructions},
        available_tools=[],
        streaming=False,
    )
    try:
        event = await session.send_and_wait(prompt, timeout=240.0)
        if event is None or not isinstance(event.data, AssistantMessageData):
            raise RuntimeError(f"{stage_name} did not return an assistant message.")
        content = event.data.content.strip()
        if not content:
            raise RuntimeError(f"{stage_name} returned an empty response.")
        return content
    finally:
        await session.disconnect()


def _sse(event: str, payload: dict[str, Any]) -> bytes:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n".encode()


def _parse_request(data: Any) -> tuple[str, str]:
    if not isinstance(data, dict):
        raise ValueError("Request body must be a JSON object.")

    input_text = data.get("input")
    if not isinstance(input_text, str) or not input_text.strip():
        raise ValueError('"input" must be a non-empty string.')

    mode = data.get("mode", "workflow")
    if mode not in {"agent", "workflow"}:
        raise ValueError('"mode" must be either "agent" or "workflow".')

    return input_text.strip(), mode


async def _stream_result(
    invocation_id: str,
    input_text: str,
    mode: str,
):
    try:
        if mode == "agent":
            output = await _run_copilot_session(
                "agent",
                SINGLE_AGENT_INSTRUCTIONS,
                input_text,
            )
            yield _sse(
                "result",
                {
                    "mode": mode,
                    "model": MODEL,
                    "output": output,
                },
            )
        else:
            result = await run_slogan_workflow(input_text, _run_copilot_session)
            yield _sse(
                "result",
                {
                    "mode": mode,
                    "model": MODEL,
                    "stages": {
                        "writer": result.writer,
                        "legal_reviewer": result.legal_reviewer,
                        "formatter": result.formatter,
                    },
                    "output": result.output,
                },
            )

        yield _sse("done", {"invocation_id": invocation_id})
    except Exception as exc:
        logger.exception("Invocation %s failed", invocation_id)
        yield _sse(
            "error",
            {
                "invocation_id": invocation_id,
                "error": type(exc).__name__,
                "message": (
                    str(exc)
                    if isinstance(exc, RuntimeError)
                    else "Agent execution failed. Check the hosted agent logs."
                ),
            },
        )


@app.invoke_handler
async def handle_invoke(request: Request) -> Response:
    try:
        data = await request.json()
        input_text, mode = _parse_request(data)
    except (json.JSONDecodeError, ValueError) as exc:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "message": str(exc),
            },
        )

    return StreamingResponse(
        _stream_result(request.state.invocation_id, input_text, mode),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    _require_github_token()
    app.run()
