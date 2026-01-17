from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Dict, Any
import requests
import os
import time
import google.generativeai as genai
from PIL import Image
import io
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class ImageGenerationInput(BaseModel):
    prompt: str = Field(description="Prompt for image generation")
    user_id: str = Field(description="User ID for the request")


class ImageGenerationTool(BaseTool):
    name = "image_generation_tool"
    description = "Generate health-related images based on user prompts"
    args_schema: Type[BaseModel] = ImageGenerationInput

    def __init__(self):
        super().__init__()
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-1.5-pro")
        self.clipdrop_api_key = settings.CLIPDROP_API_KEY
        self.image_dir = "generated_images"
        
        # Create image directory if it doesn't exist
        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir)

    def _get_ngrok_url(self):
        """Get the public URL from ngrok if it's running."""
        try:
            response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
            if response.status_code == 200:
                tunnels = response.json()
                # Get the first HTTPS tunnel if available, otherwise HTTP
                for tunnel in tunnels.get('tunnels', []):
                    if tunnel.get('proto') == 'https':
                        return tunnel.get('public_url')
                # Fallback to first tunnel
                if tunnels.get('tunnels'):
                    return tunnels['tunnels'][0]['public_url']
        except requests.RequestException:
            pass
        return None

    def _generate_image_and_save(self, prompt: str, user_id: str) -> str:
        """Generates an image, saves it, and returns its filename."""
        try:
            print(f"Generating image with prompt: {prompt}")
            response = requests.post(
                'https://clipdrop-api.co/text-to-image/v1',
                files={'prompt': (None, prompt, 'text/plain')},
                headers={'x-api-key': self.clipdrop_api_key},
                timeout=90
            )
            response.raise_for_status()
            
            # Generate a unique filename
            filename = f"{''.join(filter(str.isalnum, user_id))}_{int(time.time())}.png"
            filepath = os.path.join(self.image_dir, filename)
            
            # Save the image file
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print("✅ Image saved as", filepath)
            return filename
        except requests.RequestException as e:
            print(f"Error with Clipdrop API: {e}")
            return None
        except Exception as e:
            print(f"Error saving image: {e}")
            return None

    def _run(self, prompt: str, user_id: str) -> Dict[str, str]:
        """Execute the image generation tool."""
        try:
            # Create the URL for the image
            # Try to get ngrok URL, fallback to localhost for local testing
            ngrok_url = self._get_ngrok_url()
            if ngrok_url:
                image_url = f"{ngrok_url}/generated/{prompt}"  # This will be updated after image generation
            else:
                # Fallback to localhost - this will only work for local testing
                image_url = f"http://localhost:5000/generated/{prompt}"

            # Generate the image
            image_filename = self._generate_image_and_save(prompt, user_id)
            if not image_filename:
                return {
                    "error": "Failed to generate image. Please try again.",
                    "caption": "I'm sorry, I had trouble creating the image. Please try again."
                }

            # Update the image URL with the actual filename
            if ngrok_url:
                final_image_url = f"{ngrok_url}/generated/{image_filename}"
            else:
                final_image_url = f"http://localhost:5000/generated/{image_filename}"

            # Create a concise, bullet-pointed caption for the image
            caption_prompt = f"""
            Create a very short, friendly, and helpful caption for an image generated from this prompt: '{prompt}'
            
            Format the response as a concise WhatsApp-friendly message with these requirements:
            - Use bullet points (•) for key information
            - Keep it under 4 bullet points
            - Use emojis sparingly (like 🍎, 🥗, 💡)
            - Highlight only the most important words with *bold*
            - Make it informative but brief
            - Focus on the key takeaways
            
            Example format:
            Here's your visual guide 📋:
            • *Key benefit* of this approach
            • Important *consideration* to remember
            • 💡 *Tip* for best results
            """
            caption_response = self.model.generate_content(caption_prompt)
            caption = caption_response.text.strip()
            
            return {
                "image_url": final_image_url,
                "caption": caption
            }
        except Exception as e:
            logger.error(f"Error in image generation: {e}")
            return {
                "error": f"Image generation failed: {str(e)}",
                "caption": "I'm sorry, I had trouble creating the image. Please try again."
            }
    
    def run(self, inputs: Dict[str, Any]) -> Dict[str, str]:
        """Run the tool with the given inputs."""
        return self._run(
            prompt=inputs.get("prompt", ""),
            user_id=inputs.get("user_id", "")
        )