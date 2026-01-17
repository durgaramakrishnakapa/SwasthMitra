from typing import Dict, TypedDict, List, Union
from langchain_core.pydantic_v1 import BaseModel, Field
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import operator
from agents.healthcare_agent import HealthcareAgent


class GraphState(TypedDict):
    """
    Represents the state of the conversation graph
    """
    user_input: str
    messages: List[BaseMessage]
    user_id: str
    user_location: str
    user_symptoms: str
    is_emergency: bool
    emergency_contact: str
    hospital_search_results: List[Dict]
    generated_image_url: str
    conversation_history: List[Dict]


class SwasthMitraGraph:
    """
    Central LangGraph workflow for the SwasthMitra healthcare assistant
    """
    
    def __init__(self):
        self.workflow = StateGraph(GraphState)
        
        # Initialize tools and services
        from tools.emergency_contact.emergency_tool import EmergencyContactTool
        from tools.hospital_search.hospital_search_tool import HospitalSearchTool
        from tools.media_analysis.media_analysis_tool import MediaAnalysisTool
        from tools.image_generation.image_generation_tool import ImageGenerationTool
        from services.chat_history_service import ChatHistoryService
        from services.interactive_menu_service import InteractiveMenuService
        
        self.emergency_tool = EmergencyContactTool()
        self.hospital_search_tool = HospitalSearchTool()
        self.media_analysis_tool = MediaAnalysisTool()
        self.image_generation_tool = ImageGenerationTool()
        self.chat_history_service = ChatHistoryService()
        self.interactive_menu_service = InteractiveMenuService()
        
        # Initialize the healthcare agent
        self.healthcare_agent = HealthcareAgent([
            self.emergency_tool,
            self.hospital_search_tool,
            self.media_analysis_tool,
            self.image_generation_tool
        ])
        
        self._setup_nodes()
        self._setup_edges()
        self.graph = self.workflow.compile()

    def _setup_nodes(self):
        """Define all the nodes in the graph"""
        # Entry node that determines next action
        self.workflow.add_node("router", self.router_node)
        
        # Tool nodes
        self.workflow.add_node("handle_emergency", self.handle_emergency_node)
        self.workflow.add_node("search_hospitals", self.search_hospitals_node)
        self.workflow.add_node("analyze_media", self.analyze_media_node)
        self.workflow.add_node("generate_image", self.generate_image_node)
        self.workflow.add_node("provide_medical_advice", self.provide_medical_advice_node)
        self.workflow.add_node("handle_conversation", self.handle_conversation_node)
        
        # Start and end nodes
        self.workflow.set_entry_point("router")

    def _setup_edges(self):
        """Define the edges between nodes"""
        # Router decides where to go based on user input
        self.workflow.add_conditional_edges(
            "router",
            self.route_based_on_intent,
            {
                "emergency": "handle_emergency",
                "hospital_search": "search_hospitals",
                "media_analysis": "analyze_media",
                "image_generation": "generate_image",
                "medical_advice": "provide_medical_advice",
                "conversation": "handle_conversation",
            }
        )
        
        # Connect all tool nodes back to router for next iteration
        self.workflow.add_edge("handle_emergency", "router")
        self.workflow.add_edge("search_hospitals", "router")
        self.workflow.add_edge("analyze_media", "router")
        self.workflow.add_edge("generate_image", "router")
        self.workflow.add_edge("provide_medical_advice", "router")
        self.workflow.add_edge("handle_conversation", "router")

    def route_based_on_intent(self, state):
        """
        Determine the next node based on user intent
        """
        user_input = state.get("user_input", "").lower()
        
        # Check for emergency keywords
        emergency_keywords = [
            "emergency", "urgent help", "call ambulance", "call parents now", 
            "serious problem", "critical situation", "life threatening", 
            "/emergency", "/help now", "severe", "getting worse", "heart pain",
            "difficulty breathing", "chest pain", "stroke", "heart attack"
        ]
        
        if any(keyword in user_input for keyword in emergency_keywords) or state.get("is_emergency", False):
            return "emergency"
        
        # Check for hospital search
        hospital_keywords = ["hospital", "clinic", "doctor", "nearest", "find", "search"]
        if any(keyword in user_input for keyword in hospital_keywords):
            return "hospital_search"
        
        # Check for media analysis
        media_keywords = ["pdf", "image", "photo", "scan", "report", "document", "x-ray", "prescription"]
        if any(keyword in user_input for keyword in media_keywords):
            return "media_analysis"
        
        # Check for image generation
        image_gen_keywords = ["generate", "image", "picture", "visual", "show me", "diagram", "illustration"]
        if any(keyword in user_input for keyword in image_gen_keywords):
            return "image_generation"
        
        # Check for medical advice
        symptom_keywords = ["headache", "pain", "symptom", "ill", "sick", "medicine", "treatment", "remedy"]
        if any(keyword in user_input for keyword in symptom_keywords):
            return "medical_advice"
        
        # Default to conversation handler
        return "conversation"

    def router_node(self, state):
        """
        Router node that determines which action to take
        """
        return state

    def handle_emergency_node(self, state):
        """
        Handle emergency situations
        """
        result = self.emergency_tool.run({
            "summary": f"Emergency triggered by user: {state.get('user_input')}",
            "user_id": state.get("user_id"),
            "emergency_contact": state.get("emergency_contact", "+918790621879"),
            "conversation_history": state.get("conversation_history", [])
        })
        
        # Add response to messages
        messages = state.get("messages", [])
        messages.append(AIMessage(content=result))
        
        updated_state = state.copy()
        updated_state["messages"] = messages
        updated_state["is_emergency"] = True
        
        # Also save to chat history
        self.chat_history_service.add_to_user_history(
            state.get("user_id"),
            state.get("user_input"),
            result
        )
        
        return updated_state

    def search_hospitals_node(self, state):
        """
        Search for hospitals based on user input
        """
        result = self.hospital_search_tool.run({
            "query": state.get("user_input"),
            "location": state.get("user_location", ""),
            "symptoms": state.get("user_symptoms", "")
        })
        
        # Add response to messages
        messages = state.get("messages", [])
        messages.append(AIMessage(content=result))
        
        updated_state = state.copy()
        updated_state["messages"] = messages
        updated_state["hospital_search_results"] = result
        
        # Also save to chat history
        self.chat_history_service.add_to_user_history(
            state.get("user_id"),
            state.get("user_input"),
            result
        )
        
        return updated_state

    def analyze_media_node(self, state):
        """
        Analyze uploaded media (images, PDFs, videos)
        """
        # In a real implementation, this would handle actual media URLs
        result = self.media_analysis_tool.run({
            "media_url": state.get("user_input"),  # Would contain media URL in real scenario
            "user_id": state.get("user_id")
        })
        
        # Add response to messages
        messages = state.get("messages", [])
        messages.append(AIMessage(content=result))
        
        updated_state = state.copy()
        updated_state["messages"] = messages
        
        # Also save to chat history
        self.chat_history_service.add_to_user_history(
            state.get("user_id"),
            state.get("user_input"),
            result
        )
        
        return updated_state

    def generate_image_node(self, state):
        """
        Generate health-related images
        """
        result = self.image_generation_tool.run({
            "prompt": state.get("user_input"),
            "user_id": state.get("user_id")
        })
        
        # Add response to messages
        messages = state.get("messages", [])
        messages.append(AIMessage(content=result.get("caption", "")))
        
        updated_state = state.copy()
        updated_state["messages"] = messages
        updated_state["generated_image_url"] = result.get("image_url", "")
        
        # Also save to chat history
        self.chat_history_service.add_to_user_history(
            state.get("user_id"),
            state.get("user_input"),
            result.get("caption", "")
        )
        
        return updated_state

    def provide_medical_advice_node(self, state):
        """
        Provide medical advice based on symptoms
        """
        from utils.medical_advisor import MedicalAdvisor
        
        advisor = MedicalAdvisor()
        result = advisor.get_medical_advice(state.get("user_input"), state.get("conversation_history", []))
        
        # Add response to messages
        messages = state.get("messages", [])
        messages.append(AIMessage(content=result))
        
        updated_state = state.copy()
        updated_state["messages"] = messages
        
        return updated_state

    def handle_conversation_node(self, state):
        """
        Handle general conversation and context management
        """
        from utils.conversation_manager import ConversationManager
        
        manager = ConversationManager()
        result = manager.process_conversation(state.get("user_input"), state.get("messages"))
        
        # Add response to messages
        messages = state.get("messages", [])
        messages.append(AIMessage(content=result))
        
        updated_state = state.copy()
        updated_state["messages"] = messages
        
        return updated_state

    def run(self, user_input: str, user_id: str, initial_state: dict = None):
        """
        Run the graph with user input
        """
        initial_state = initial_state or {}
        
        # Get user's chat history to enrich the state
        user_history = self.chat_history_service.get_user_history(user_id)
        
        state = {
            "user_input": user_input,
            "messages": initial_state.get("messages", []),
            "user_id": user_id,
            "user_location": initial_state.get("user_location", ""),
            "user_symptoms": initial_state.get("user_symptoms", ""),
            "is_emergency": initial_state.get("is_emergency", False),
            "emergency_contact": initial_state.get("emergency_contact", "+918790621879"),
            "hospital_search_results": initial_state.get("hospital_search_results", []),
            "generated_image_url": initial_state.get("generated_image_url", ""),
            "conversation_history": user_history  # Use actual history from service
        }
        
        result = self.graph.invoke(state)
        
        # Update chat history with the latest interaction
        if result.get("messages"):
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                self.chat_history_service.add_to_user_history(user_id, user_input, last_message.content)
        
        return result