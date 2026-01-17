from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Dict, Any
import google.generativeai as genai
from crewai_tools import SerperDevTool
from config.settings import settings
import os
import logging

logger = logging.getLogger(__name__)


class HospitalSearchInput(BaseModel):
    query: str = Field(description="Query for hospital search")
    location: str = Field(description="Location for the search")
    symptoms: str = Field(description="Symptoms to find relevant specialists")


class HospitalSearchTool(BaseTool):
    name = "hospital_search_tool"
    description = "Search for hospitals and medical facilities based on location and symptoms"
    args_schema: Type[BaseModel] = HospitalSearchInput

    def __init__(self):
        super().__init__()
        genai.configure(api_key=settings.GEMINI_API_KEY)
        os.environ["SERPER_API_KEY"] = settings.SERPER_API_KEY
        self.model = genai.GenerativeModel("gemini-1.5-pro")
        self.serper_tool = SerperDevTool()

    def _run(self, query: str, location: str = "", symptoms: str = "") -> str:
        """Execute the hospital search tool."""
        try:
            # Build search query based on inputs
            if symptoms and location:
                search_query = f"best hospitals for {symptoms} in {location}"
            elif symptoms:
                search_query = f"best hospitals for {symptoms}"
            elif location:
                search_query = f"hospitals in {location}"
            else:
                search_query = query
            
            print(f"Performing web search: '{search_query}'")
            
            # Perform the web search
            search_results = self.serper_tool.run(search_query=search_query)
            
            # Extract and format hospital names
            extract_prompt = f"""
            From these search results, extract exactly 5 hospital names in {location} that treat {symptoms}.
            List them as a simple bullet list with just the hospital names.
            Make it WhatsApp-friendly with relevant emojis (🏥 for hospitals, 💡 for special notes).
            Highlight important information using asterisks for *bold text* only when needed for clarity.
            
            Format exactly like this example:
            
            Top 5 Hospitals in Vijayawada for Headaches:
            * Harini Hospitals 🏥
            * Anil Neuro & Trauma Centre 🏥
            * Sunrise Multi Speciality Hospital 🏥
            * Ramesh Hospital 🏥
            * Manipal Hospital 🏥
            
            Now do the same for these results for {location} and {symptoms}:
            Results: '{search_results}'
            
            Start with "Top 5 Hospitals in {location} for {symptoms.title()}:" and then list exactly 5 hospitals with bullets.
            Only use asterisks for *bold* when highlighting something important, not for every line.
            """
            
            raw_response = self.model.generate_content(extract_prompt)
            result = raw_response.text
            
            return result
            
        except Exception as e:
            logger.error(f"Error during hospital search: {e}")
            return f"I'm sorry, I had trouble searching for hospitals in {location} for {symptoms} at the moment. Please try again later."
    
    def run(self, inputs: Dict[str, Any]) -> str:
        """Run the tool with the given inputs."""
        return self._run(
            query=inputs.get("query", ""),
            location=inputs.get("location", ""),
            symptoms=inputs.get("symptoms", "")
        )