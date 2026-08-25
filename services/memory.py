import json
import logging
import os
import re
from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from config.settings import settings

logger = logging.getLogger(__name__)


class MemoryService:
    """Persistent memory: conversation history, user profile, and rolling summary."""

    def __init__(self) -> None:
        self.history_path = settings.CHAT_HISTORY_FILE
        self.profile_path = settings.PROFILE_FILE
        self._ensure_files()

    def _ensure_files(self) -> None:
        for path in (self.history_path, self.profile_path):
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({}, f)

    def _load(self, path: str) -> dict:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save(self, path: str, data: dict) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def get_profile(self, user_id: str) -> dict[str, Any]:
        profiles = self._load(self.profile_path)
        return profiles.get(user_id, {"name": "", "location": "", "symptoms": "", "summary": ""})

    def update_profile(self, user_id: str, **fields: str) -> None:
        profiles = self._load(self.profile_path)
        profile = profiles.get(user_id, {"name": "", "location": "", "symptoms": "", "summary": ""})
        for key, value in fields.items():
            if value and key in profile:
                profile[key] = value
        profiles[user_id] = profile
        self._save(self.profile_path, profiles)

    def get_history(self, user_id: str) -> list[dict]:
        histories = self._load(self.history_path)
        return histories.get(user_id, [])

    def add_exchange(self, user_id: str, user_message: str, bot_response: str) -> None:
        histories = self._load(self.history_path)
        if user_id not in histories:
            histories[user_id] = []

        histories[user_id].extend([
            {"role": "user", "content": user_message, "ts": datetime.now().isoformat()},
            {"role": "assistant", "content": bot_response, "ts": datetime.now().isoformat()},
        ])

        max_messages = settings.MAX_HISTORY_TURNS * 2
        histories[user_id] = histories[user_id][-max_messages:]
        self._save(self.history_path, histories)

        self._extract_profile_from_message(user_id, user_message)

    def _extract_profile_from_message(self, user_id: str, message: str) -> None:
        text = message.lower().strip()
        updates: dict[str, str] = {}

        name_match = re.search(r"(?:my name is|i am|i'm|this is)\s+([a-zA-Z]+)", text)
        if name_match:
            updates["name"] = name_match.group(1).capitalize()

        location_match = re.search(
            r"(?:i am in|i live in|located in|from|near|in)\s+([a-zA-Z\s,]+?)(?:\.|$|,|\s+and|\s+but)",
            text,
        )
        if location_match and len(location_match.group(1).strip()) < 40:
            updates["location"] = location_match.group(1).strip().title()

        symptom_keywords = [
            "headache", "fever", "pain", "cough", "vomiting", "dizziness",
            "rash", "breathing", "chest", "stomach", "diabetes", "bp", "blood pressure",
        ]
        if any(kw in text for kw in symptom_keywords):
            updates["symptoms"] = message[:200]

        if updates:
            self.update_profile(user_id, **updates)

    def history_to_messages(self, user_id: str) -> list[BaseMessage]:
        messages: list[BaseMessage] = []
        for entry in self.get_history(user_id):
            if entry["role"] == "user":
                messages.append(HumanMessage(content=entry["content"]))
            else:
                messages.append(AIMessage(content=entry["content"]))
        return messages

    def build_context_block(self, user_id: str) -> str:
        profile = self.get_profile(user_id)
        parts = []
        if profile.get("name"):
            parts.append(f"Name: {profile['name']}")
        if profile.get("location"):
            parts.append(f"Location: {profile['location']}")
        if profile.get("symptoms"):
            parts.append(f"Recent symptoms: {profile['symptoms']}")
        if profile.get("summary"):
            parts.append(f"Earlier conversation summary: {profile['summary']}")

        recent = self.get_history(user_id)[-6:]
        if recent:
            parts.append("Recent exchanges:")
            for entry in recent:
                role = "User" if entry["role"] == "user" else "Assistant"
                parts.append(f"  {role}: {entry['content'][:120]}")

        return "\n".join(parts) if parts else "No prior context for this user."
