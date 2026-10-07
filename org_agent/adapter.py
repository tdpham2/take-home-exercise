"""LangChain model bridge over the existing JSON-only hosted clients."""
import json
import time
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import Field

from org_memory.hosted import BudgetExceeded, _check_schema
from .models import VERSION
from .runtime import serialized


ACTION_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "tool_name": {"type": "string"},
        "arguments_json": {"type": "string", "description": "JSON object containing the selected tool's arguments."},
        "purpose": {"type": "string", "description": "One short statement of what this action will establish; no private reasoning."},
        "discarded_items": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "properties": {"item_id": {"type": "string"}, "reason": {"type": "string"}}, "required": ["item_id", "reason"]}},
        "pin_evidence_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["tool_name", "arguments_json", "purpose", "discarded_items", "pin_evidence_ids"],
}

BRIDGE_INSTRUCTIONS = """Return only the action-envelope JSON. Select exactly one registered application tool.
These are JSON action proposals executed later by Python, not native SDK tools.
arguments_json must encode an object matching the selected tool's parameter schema.
DraftAnswer is the finishing tool. Supply a short action purpose, not hidden reasoning.
discarded_items may name previously shown memory items with concise relevance reasons.
pin_evidence_ids should retain shown evidence supporting active claims or material counterevidence.
Do not fabricate tool names, IDs, observations, offsets, or quotations.
"""


class JsonChatModel(BaseChatModel):
    client: Any = Field(exclude=True)
    ledger: Any = Field(exclude=True)
    bound_tools: list[dict] = Field(default_factory=list, exclude=True)
    tool_choice: Any = Field(default=None, exclude=True)

    @property
    def _llm_type(self):
        return "organizational-json-provider"

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        if tool_choice not in (None, "auto", "any", "required") and not isinstance(tool_choice, (str, dict)):
            raise ValueError("Unsupported tool choice")
        bound = [convert_to_openai_tool(tool) for tool in tools]
        selected = tool_choice.get("function", {}).get("name") if isinstance(tool_choice, dict) else tool_choice
        if selected == "none":
            raise ValueError("This adapter requires an application action or DraftAnswer")
        if selected and selected not in {"auto", "any", "required"}:
            bound = [t for t in bound if t["function"]["name"] == selected]
        if not bound:
            raise ValueError("No tools bound")
        return self.model_copy(update={"bound_tools": bound, "tool_choice": tool_choice})

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if self.ledger.model_calls >= self.ledger.config.max_model_calls:
            raise BudgetExceeded("Question model-call budget exhausted")
        functions = [t["function"] for t in self.bound_tools]
        names = [f["name"] for f in functions]
        schema = {**ACTION_SCHEMA, "properties": {**ACTION_SCHEMA["properties"], "tool_name": {"type": "string", "enum": names}}}
        system = BRIDGE_INSTRUCTIONS + "\n" + "\n".join(str(m.content) for m in messages if isinstance(m, SystemMessage))

        def packet(selected):
            rows = []
            for m in selected:
                if isinstance(m, SystemMessage):
                    continue
                row = {"role": m.type, "content": m.content}
                if getattr(m, "tool_calls", None):
                    row["tool_calls"] = m.tool_calls
                if getattr(m, "tool_call_id", None):
                    row.update(tool_call_id=m.tool_call_id, name=m.name)
                rows.append(row)
            return {"phase": VERSION, "artifacts": self.ledger.artifacts.identity,
                    "messages": rows, "tools": functions}

        def size(selected):
            return len(serialized({"system": system, "packet": packet(selected), "schema": schema}))
        selected = self.ledger.project(messages, size)
        task = packet(selected)
        self.ledger.present(selected)
        self.ledger.model_calls += 1
        before, started = len(self.client.trace), time.monotonic()
        entry = {"call_number": self.ledger.model_calls, "status": "pending",
                 "serialized_chars": size(selected), "available_tools": names}
        self.ledger.log("model_started", **entry)
        try:
            output, request_id = self.client.json(system, task, schema, "task2_agent")
            _check_schema(output, schema)
            arguments = json.loads(output["arguments_json"])
            if not isinstance(arguments, dict):
                raise ValueError("Tool arguments must be a JSON object")
            self.ledger.select(output["discarded_items"], output["pin_evidence_ids"])
            call_id = f"action_{self.ledger.model_calls}_{request_id}"
            entry.update(status="completed", request_id=request_id, action=output)
            return ChatResult(generations=[ChatGeneration(message=AIMessage(
                content=output["purpose"], tool_calls=[{"id": call_id, "name": output["tool_name"], "args": arguments}],
                response_metadata={"request_id": request_id}))])
        except (ValueError, KeyError, TypeError) as exc:
            entry.update(status="malformed", error=str(exc)[:600])
            raise ValueError("Malformed application action: " + str(exc)[:600]) from exc
        except KeyboardInterrupt:
            entry.update(status="interrupted", error_type="KeyboardInterrupt")
            raise
        except Exception as exc:
            entry.update(status="failed", error_type=type(exc).__name__)
            raise
        finally:
            entry["latency_seconds"] = time.monotonic() - started
            if len(self.client.trace) > before:
                entry["provider"] = self.client.trace[-1].copy()
            self.ledger.log("model", **entry)
