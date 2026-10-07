"""Budget and trace middleware. The adapter enforces exact serialized context size."""
import json
import time

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage, ToolMessage

from org_memory.hosted import BudgetExceeded
from .runtime import payload


class AgentControls(AgentMiddleware):
    def __init__(self, ledger):
        self.ledger = ledger
        self.repair_call_start = None

    def wrap_model_call(self, request, handler):
        ledger = self.ledger
        if ledger.model_calls >= ledger.config.max_model_calls:
            raise BudgetExceeded("Question model-call budget exhausted")
        if self.repair_call_start is not None and ledger.model_calls > self.repair_call_start:
            raise BudgetExceeded("Single citation-correction attempt exhausted")
        reason = None
        if self.repair_call_start is not None:
            reason = "citation correction"
        elif ledger.tool_calls >= ledger.config.max_tool_calls:
            reason = "data-tool budget exhausted"
        elif ledger.no_gain >= ledger.config.no_gain_limit:
            reason = "consecutive tool calls added no new evidence or items"
        elif ledger.config.max_model_calls - ledger.model_calls <= 2:
            reason = "reserved model calls reached; finalize from available evidence"
        if reason:
            ledger.stop_reason = ledger.stop_reason or reason
            # create_agent adds its structured-output tool after middleware filtering.
            request = request.override(tools=[], messages=[*request.messages, HumanMessage(
                content=f"Retrieval has stopped: {reason}. Finish with DraftAnswer; list unanswered aspects.")])
        try:
            return handler(request)
        except ValueError as exc:
            if (self.repair_call_start is not None or not str(exc).startswith("Malformed application action:")
                    or ledger.config.max_model_calls - ledger.model_calls < 2):
                raise
            ledger.log("action_repair", reason=str(exc))
            return handler(request.override(messages=[*request.messages, HumanMessage(
                content="One action-format correction: " + str(exc) + ". Return the required JSON action envelope.")]))

    def wrap_tool_call(self, request, handler):
        ledger = self.ledger
        if ledger.tool_calls >= ledger.config.max_tool_calls:
            raise BudgetExceeded("Question data-tool budget exhausted")
        call = request.tool_call
        ledger.tool_calls += 1
        started = time.monotonic()
        ledger.log("tool_started", call_id=call["id"], name=call["name"], arguments=call["args"])
        error = False
        try:
            result = handler(request)
            if not isinstance(result, ToolMessage):
                raise TypeError("Dataset tools must return ToolMessage")
            error = result.status == "error"
        except (ValueError, KeyError, TypeError) as exc:
            error = True
            result = ToolMessage(content=json.dumps({"error": type(exc).__name__, "message": str(exc)[:600]}),
                                 tool_call_id=call["id"], name=call["name"], status="error")
        ledger.tool_result(call["name"], call["args"], call["id"], payload(result), time.monotonic() - started, error)
        return result
