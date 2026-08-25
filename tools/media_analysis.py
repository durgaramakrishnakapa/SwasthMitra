import io
import logging
import os
import tempfile

import cv2
import google.generativeai as genai
import numpy as np
import requests
from langchain_core.tools import tool
from PIL import Image
from PyPDF2 import PdfReader

from config.settings import settings

logger = logging.getLogger(__name__)
genai.configure(api_key=settings.GEMINI_API_KEY)
_model = genai.GenerativeModel(settings.GEMINI_MODEL)


def _extract_video_frame(video_path: str):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    best_frame, best_score = None, -1.0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if score > best_score:
            best_score, best_frame = score, frame
    cap.release()
    return best_frame


def _analyze_pdf(url: str) -> str:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    reader = PdfReader(io.BytesIO(response.content))
    text = "".join(page.extract_text() or "" for page in reader.pages)
    if not text.strip():
        return "Could not extract text from this PDF."
    prompt = (
        "You are a medical document analyst. Summarize this report for a patient on WhatsApp. "
        "Highlight key findings, abnormal values, and recommended follow-ups. "
        "Remind this is not a diagnosis.\n\nReport:\n" + text[:8000]
    )
    return _model.generate_content(prompt).text


def _analyze_image(url: str) -> str:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    img = Image.open(io.BytesIO(response.content))
    prompt = [
        "You are a medical image analyst. Describe visible health-related findings in plain language. "
        "Note limitations — this is not a diagnosis. Format for WhatsApp with bullet points.",
        img,
    ]
    return _model.generate_content(prompt).text


def _analyze_video(url: str) -> str:
    temp_path = ""
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(response.content)
            temp_path = tmp.name

        frame = _extract_video_frame(temp_path)
        if frame is None:
            return "Could not extract a clear frame from the video."
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        prompt = [
            "Analyze this medical video frame. Describe any visible health concerns. "
            "This is not a diagnosis — format for WhatsApp.",
            img,
        ]
        return _model.generate_content(prompt).text
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@tool
def analyze_medical_media(media_url: str, media_type: str = "auto") -> str:
    """Analyze a medical image, PDF report, prescription, or video from a URL.
    Use when the user uploads or shares medical documents for review."""
    try:
        lowered = media_url.lower()
        if media_type == "pdf" or ".pdf" in lowered or "pdf" in media_type:
            return _analyze_pdf(media_url)
        if media_type == "video" or any(ext in lowered for ext in (".mp4", ".mov", ".avi", "video")):
            return _analyze_video(media_url)
        return _analyze_image(media_url)
    except Exception as exc:
        logger.error("Media analysis failed: %s", exc)
        return f"Sorry, I couldn't analyze that file: {exc}"
