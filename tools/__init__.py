from tools.search import web_health_search, search_hospitals
from tools.emergency import trigger_emergency_alert
from tools.media_analysis import analyze_medical_media
from tools.image_generation import generate_health_image

ALL_TOOLS = [
    web_health_search,
    search_hospitals,
    trigger_emergency_alert,
    analyze_medical_media,
    generate_health_image,
]

__all__ = ["ALL_TOOLS"]
