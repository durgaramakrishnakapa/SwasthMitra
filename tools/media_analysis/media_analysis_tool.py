from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Dict, Any
import requests
import io
import tempfile
import os
import cv2
import numpy as np
import google.generativeai as genai
from PyPDF2 import PdfReader
from PIL import Image
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class MediaAnalysisInput(BaseModel):
    media_url: str = Field(description="URL of the media to analyze")
    user_id: str = Field(description="User ID for the request")


class MediaAnalysisTool(BaseTool):
    name = "media_analysis_tool"
    description = "Analyze PDF, image, and video files for health-related information"
    args_schema: Type[BaseModel] = MediaAnalysisInput

    def __init__(self):
        super().__init__()
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-1.5-pro")

    def process_pdf(self, media_url: str) -> str:
        """Process PDF files."""
        try:
            response = requests.get(media_url)
            response.raise_for_status()
            reader = PdfReader(io.BytesIO(response.content))
            return "".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            return "Sorry, I couldn't read the content of that PDF."

    def process_image(self, media_url: str) -> str:
        """Process image files."""
        try:
            response = requests.get(media_url)
            response.raise_for_status()
            img = Image.open(io.BytesIO(response.content))
            prompt = ["Analyze the health-related information in this image.", img]
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return "Sorry, I couldn't analyze that image."

    def _extract_best_frame(self, video_path: str):
        """Extract the clearest frame from a video."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened(): 
            return None
        best_frame, best_score = None, -1
        while True:
            ret, frame = cap.read()
            if not ret: 
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            if lap_var > best_score:
                best_score, best_frame = lap_var, frame
        cap.release()
        return best_frame

    def process_video(self, media_url: str) -> str:
        """Process video files."""
        temp_video_path = ""
        try:
            response = requests.get(media_url)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
                temp_video.write(response.content)
                temp_video_path = temp_video.name
            
            best_frame = self._extract_best_frame(temp_video_path)
            if best_frame is not None:
                image = Image.fromarray(cv2.cvtColor(best_frame, cv2.COLOR_BGR2RGB))
                prompt = ["Analyze this video frame for any visible health concerns.", image]
                response = self.model.generate_content(prompt)
                return response.text
            return "I could not extract a clear frame from the video to analyze."
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            return "An error occurred while processing the video."
        finally:
            if os.path.exists(temp_video_path):
                os.unlink(temp_video_path)

    def _run(self, media_url: str, user_id: str) -> str:
        """Execute the media analysis tool."""
        try:
            # Determine media type from URL
            if media_url.lower().endswith('.pdf'):
                return self.process_pdf(media_url)
            elif any(img_type in media_url.lower() for img_type in ['.jpg', '.jpeg', '.png']):
                return self.process_image(media_url)
            elif any(vid_type in media_url.lower() for vid_type in ['.mp4', '.avi', '.mov', '.wmv']):
                return self.process_video(media_url)
            else:
                return "Sorry, I can only process PDF, JPG, PNG, or Video files."
        except Exception as e:
            logger.error(f"Error in media analysis: {e}")
            return f"Sorry, I encountered an error while analyzing the media: {str(e)}"
    
    def run(self, inputs: Dict[str, Any]) -> str:
        """Run the tool with the given inputs."""
        return self._run(
            media_url=inputs.get("media_url", ""),
            user_id=inputs.get("user_id", "")
        )