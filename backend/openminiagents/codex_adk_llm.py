"""ADK BaseLlm adapter for ChatGPT subscription (Codex OAuth API)."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from .codex_client import codex_responses_create

log = logging.getLogger(__name__)


def _schema_to_dict(schema: Any) -> dict[str, Any]:
    if schema is None:
        return {"type": "object", "properties": {}}
    if isinstance(schema, dict):
        return schema
    if hasattr(schema, "model_dump"):
        return schema.model_dump(exclude_none=True)
    if hasattr(schema, "to_json_dict"):
        return schema.to_json_dict()
    return {"type": "object", "properties": {}}


def _tools_from_request(llm_request: LlmRequest) -> list[dict[str, Any]] | None:
    config = llm_request.config
    if not config or not config.tools:
        return None
    out: list[dict[str, Any]] = []
    for tool in config.tools:
        if not isinstance(tool, types.Tool) or not tool.function_declarations:
            continue
        for fd in tool.function_declarations:
            if not fd.name:
                continue
            out.append(
                {
                    "type": "function",
                    "name": fd.name,
                    "description": fd.description or "",
                    "parameters": _schema_to_dict(fd.parameters),
                }
            )
    return out or None


def _part_to_message_items(part: types.Part, role: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if part.text:
        items.append({"role": role, "content": part.text})
    elif part.function_call:
        fc = part.function_call
        items.append(
            {
                "type": "function_call",
                "call_id": fc.id or fc.name or "",
                "name": fc.name,
                "arguments": json.dumps(fc.args or {}),
            }
        )
    elif part.function_response:
        fr = part.function_response
        items.append(
            {
                "type": "function_call_output",
                "call_id": fr.id or fr.name or "",
                "output": json.dumps(fr.response) if fr.response is not None else "",
            }
        )
    elif part.inline_data and part.inline_data.data:
        mime = part.inline_data.mime_type or "image/png"
        import base64

        b64 = base64.standard_b64encode(part.inline_data.data).decode("ascii")
        items.append(
            {
                "role": role,
                "content": [
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime};base64,{b64}",
                    }
                ],
            }
        )
    return items


def _contents_to_messages(contents: list[types.Content]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for content in contents:
        role = content.role or "user"
        api_role = "assistant" if role == "model" else role
        for part in content.parts or []:
            messages.extend(_part_to_message_items(part, api_role))
    return messages


def _instructions_from_request(llm_request: LlmRequest) -> str | None:
    config = llm_request.config
    if not config:
        return None
    if config.system_instruction:
        if isinstance(config.system_instruction, str):
            return config.system_instruction
        parts = getattr(config.system_instruction, "parts", None) or []
        texts = [p.text for p in parts if getattr(p, "text", None)]
        if texts:
            return "\n".join(texts)
    return None


def _output_to_llm_response(resp: Any, model: str) -> LlmResponse:
    if getattr(resp, "error", None):
        err = resp.error
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        return LlmResponse(error_message=msg, error_code="codex_error")

    parts: list[types.Part] = []
    output = getattr(resp, "output", None) or []
    for item in output:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type", "")
        if item_type == "message":
            content = item.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "output_text":
                        text = block.get("text", "")
                        if text:
                            parts.append(types.Part.from_text(text=text))
            elif isinstance(content, str) and content:
                parts.append(types.Part.from_text(text=content))
        elif item_type == "function_call":
            name = item.get("name", "")
            args_raw = item.get("arguments", "{}")
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except json.JSONDecodeError:
                args = {}
            part = types.Part.from_function_call(name=name, args=args or {})
            call_id = item.get("call_id") or item.get("id")
            if call_id:
                part.function_call.id = str(call_id)
            parts.append(part)

    if not parts and getattr(resp, "output_text", ""):
        parts.append(types.Part.from_text(text=resp.output_text))

    if not parts:
        return LlmResponse(
            error_message="Codex returned empty response",
            error_code="empty_response",
        )

    return LlmResponse(
        content=types.Content(role="model", parts=parts),
        partial=False,
        model_version=model,
    )


class CodexAdkLlm(BaseLlm):
    """Routes ADK LlmAgent turns through ChatGPT Codex /responses (OAuth)."""

    @classmethod
    def supported_models(cls) -> list[str]:
        return [
            r"gpt-5.*",
            r"gpt-4.*",
            r"o3.*",
            r"o4.*",
            r"codex.*",
        ]

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        if stream:
            log.warning("CodexAdkLlm streaming not implemented; using non-streaming")

        model = llm_request.model or self.model
        messages = _contents_to_messages(llm_request.contents)
        tools = _tools_from_request(llm_request)
        instructions = _instructions_from_request(llm_request)

        resp = await codex_responses_create(
            model=model,
            messages=messages or None,
            instructions=instructions,
            tools=tools,
        )
        yield _output_to_llm_response(resp, model)
