import json
import os
from typing import Dict, List, Any
from datetime import datetime
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class ChatHistoryService:
    """
    Service for managing chat histories with persistence
    """
    
    def __init__(self, file_path: str = None):
        self.file_path = file_path or settings.CHAT_HISTORY_FILE
        self.ensure_file_exists()
    
    def ensure_file_exists(self):
        """
        Ensure the chat history file exists
        """
        directory = os.path.dirname(self.file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump({}, f)
    
    def load_chat_history(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load all chat histories from the file
        """
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.warning(f"Could not load chat history from {self.file_path}, returning empty dict")
            return {}
    
    def save_chat_history(self, data: Dict[str, List[Dict[str, Any]]]):
        """
        Save all chat histories to the file
        """
        try:
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=4, default=str)
        except Exception as e:
            logger.error(f"Error saving chat history: {e}")
    
    def get_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get chat history for a specific user
        """
        all_histories = self.load_chat_history()
        return all_histories.get(user_id, [])
    
    def add_to_user_history(self, user_id: str, user_message: str, bot_response: str):
        """
        Add a message exchange to a user's history
        """
        all_histories = self.load_chat_history()
        
        if user_id not in all_histories:
            all_histories[user_id] = []
        
        # Add user message
        all_histories[user_id].append({
            "role": "user", 
            "parts": [user_message],
            "timestamp": datetime.now().isoformat()
        })
        
        # Add bot response
        all_histories[user_id].append({
            "role": "model", 
            "parts": [bot_response],
            "timestamp": datetime.now().isoformat()
        })
        
        # Limit history size
        all_histories[user_id] = all_histories[user_id][-settings.MAX_HISTORY_LENGTH:]
        
        self.save_chat_history(all_histories)
    
    def clear_user_history(self, user_id: str):
        """
        Clear chat history for a specific user
        """
        all_histories = self.load_chat_history()
        
        if user_id in all_histories:
            del all_histories[user_id]
            self.save_chat_history(all_histories)
    
    def get_all_user_ids(self) -> List[str]:
        """
        Get all user IDs that have chat history
        """
        all_histories = self.load_chat_history()
        return list(all_histories.keys())
    
    def update_user_history(self, user_id: str, new_history: List[Dict[str, Any]]):
        """
        Replace a user's entire history with new history
        """
        all_histories = self.load_chat_history()
        all_histories[user_id] = new_history[-settings.MAX_HISTORY_LENGTH:]  # Limit size
        self.save_chat_history(all_histories)