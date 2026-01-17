from typing import Dict, List, Tuple
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.tools import BaseTool
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import BaseOutputParser
import json
import re
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class HealthcareAgent:
    """
    A specialized agent for healthcare-related tasks that works within the LangGraph workflow
    """
    
    def __init__(self, tools: List[BaseTool]):
        self.tools = tools
        self.tool_names = [tool.name for tool in tools]
        
    def plan(self, state: Dict) -> Tuple[List[AgentAction], List[Dict]]:
        """
        Plan the next actions based on the current state
        """
        # Analyze the user input to determine which tools to use
        user_input = state.get("user_input", "").lower()
        
        # Determine which tools to activate based on the input
        actions = []
        
        # Check for emergency
        if self._is_emergency(user_input):
            actions.append(AgentAction(
                tool="emergency_contact_tool",
                tool_input={
                    "summary": f"Emergency triggered by user: {state.get('user_input')}",
                    "user_id": state.get("user_id"),
                    "emergency_contact": state.get("emergency_contact", settings.EMERGENCY_CONTACT_NUMBER),
                    "conversation_history": state.get("conversation_history", [])
                },
                log="Emergency action triggered"
            ))
            return actions, []
        
        # Check for hospital search
        if any(keyword in user_input for keyword in ["hospital", "clinic", "doctor", "nearest", "find", "search"]):
            actions.append(AgentAction(
                tool="hospital_search_tool",
                tool_input={
                    "query": state.get("user_input"),
                    "location": state.get("user_location", ""),
                    "symptoms": state.get("user_symptoms", "")
                },
                log="Hospital search action triggered"
            ))
            return actions, []
        
        # Check for media analysis
        if any(keyword in user_input for keyword in ["pdf", "image", "photo", "scan", "report", "document"]):
            actions.append(AgentAction(
                tool="media_analysis_tool",
                tool_input={
                    "media_url": state.get("user_input"),  # Would contain media URL in real scenario
                    "user_id": state.get("user_id")
                },
                log="Media analysis action triggered"
            ))
            return actions, []
        
        # Check for image generation
        if any(keyword in user_input for keyword in ["generate", "image", "picture", "visual", "show me"]):
            actions.append(AgentAction(
                tool="image_generation_tool",
                tool_input={
                    "prompt": state.get("user_input"),
                    "user_id": state.get("user_id")
                },
                log="Image generation action triggered"
            ))
            return actions, []
        
        # Default to general conversation
        # In a real implementation, this would trigger a conversation tool
        return [], []
    
    def _is_emergency(self, user_input: str) -> bool:
        """
        Determine if the user input indicates an emergency
        """
        emergency_keywords = [
            "emergency", "urgent help", "call ambulance", "call parents now", 
            "serious problem", "critical situation", "life threatening", 
            "/emergency", "/help now", "severe", "getting worse", "heart pain",
            "difficulty breathing", "chest pain", "stroke", "heart attack", "fainting"
        ]
        return any(keyword in user_input for keyword in emergency_keywords)
    
    def should_continue(self, state: Dict) -> bool:
        """
        Determine if the agent should continue processing
        """
        # Stop if it was an emergency (handled separately)
        user_input = state.get("user_input", "").lower()
        return not self._is_emergency(user_input)