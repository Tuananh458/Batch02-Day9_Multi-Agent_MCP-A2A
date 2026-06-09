"""In-process conversation memory for Customer Agent (keyed by A2A context_id)."""

from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
