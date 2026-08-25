import logging
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import tools_condition

from agent.llm import get_llm
from agent.prompts import SYSTEM_PROMPT
from agent.state import AgentState
from services.memory import MemoryService
from tools import ALL_TOOLS

logger = logging.getLogger(__name__)


class SwasthMitraGraph:
    """LangGraph agent with LLM-driven tool calling — no keyword routing."""

    def __init__(self) -> None:
        self.memory = MemoryService()
        self.llm = get_llm().bind_tools(ALL_TOOLS)
        self._tool_map = {t.name: t for t in ALL_TOOLS}

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self._tools_node)

        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
        workflow.add_edge("tools", "agent")

        self.graph = workflow.compile()

    def _agent_node(self, state: AgentState) -> dict:
        context = self.memory.build_context_block(state["user_id"])
        system = SystemMessage(content=SYSTEM_PROMPT.format(patient_context=context))

        if state.get("media_url"):
            media_hint = HumanMessage(
                content=(
                    f"[System: user uploaded {state.get('media_type', 'media')} "
                    f"at {state['media_url']}. Use analyze_medical_media if analysis is needed.]"
                )
            )
            messages = [system, media_hint] + state["messages"]
        else:
            messages = [system] + state["messages"]

        response = self.llm.invoke(messages)
        return {"messages": [response]}

    def _tools_node(self, state: AgentState) -> dict:
        last = state["messages"][-1]
        outputs: list[ToolMessage] = []

        for call in last.tool_calls:
            name = call["name"]
            args = dict(call.get("args") or {})
            if name in ("trigger_emergency_alert", "generate_health_image"):
                args.setdefault("user_id", state["user_id"])

            tool = self._tool_map.get(name)
            if tool is None:
                result = f"Unknown tool: {name}"
            else:
                try:
                    result = tool.invoke(args)
                except Exception as exc:
                    logger.error("Tool %s failed: %s", name, exc)
                    result = f"Tool error: {exc}"

            outputs.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

        return {"messages": outputs}

    def run(
        self,
        user_input: str,
        user_id: str,
        media_url: str = "",
        media_type: str = "",
    ) -> dict:
        history = self.memory.history_to_messages(user_id)
        messages = history + [HumanMessage(content=user_input)]

        result = self.graph.invoke(
            {
                "messages": messages,
                "user_id": user_id,
                "user_language": "en",
                "media_url": media_url,
                "media_type": media_type,
                "generated_image_url": "",
                "emergency_triggered": False,
            },
            config={"recursion_limit": 10},
        )

        reply, image_url = self._extract_reply(result["messages"])
        self.memory.add_exchange(user_id, user_input, reply)

        if image_url:
            result["generated_image_url"] = image_url

        result["reply"] = reply
        return result

    @staticmethod
    def _content_to_text(content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("text"):
                    parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            return " ".join(parts)
        return str(content)

    @staticmethod
    def _extract_reply(messages: list) -> tuple[str, str]:
        image_url = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
                text = SwasthMitraGraph._content_to_text(msg.content)
                match = re.search(r"IMAGE_URL:(\S+)", text)
                if match:
                    image_url = match.group(1)
                    text = re.sub(r"IMAGE_URL:\S+\s*", "", text).strip()
                return text, image_url

            if hasattr(msg, "type") and msg.type == "tool":
                content = SwasthMitraGraph._content_to_text(msg.content)
                match = re.search(r"IMAGE_URL:(\S+)", content)
                if match:
                    image_url = match.group(1)
                    clean = re.sub(r"IMAGE_URL:\S+\s*", "", content).strip()
                    return clean, image_url

        return "How can I help with your health concern today?", image_url
