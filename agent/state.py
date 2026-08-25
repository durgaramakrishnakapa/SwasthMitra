from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    user_language: str
    media_url: str
    media_type: str
    generated_image_url: str
    emergency_triggered: bool
