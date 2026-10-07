"""Task 2: one evidence-backed LangChain agent, independent of memory construction."""
from .agent import OrganizationalAgent, save_result
from .models import AgentConfig, AnswerResult

__all__ = ["OrganizationalAgent", "AgentConfig", "AnswerResult", "save_result"]
