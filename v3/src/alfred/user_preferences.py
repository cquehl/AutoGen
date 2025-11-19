"""
Suntory v3 - User Preferences Manager
Extract and store user preferences from conversation
"""

import re
from typing import Dict, Optional

from ..core import get_logger, get_vector_manager

logger = get_logger(__name__)


class UserPreferencesManager:
    """
    Manages user preferences extracted from conversation.

    Handles:
    - Gender preferences (sir/madam)
    - Name
    - Other preferences as they emerge
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.preferences: Dict[str, str] = {}
        self.vector_manager = get_vector_manager()
        self.preferences_collection = f"preferences_{session_id}"

    def extract_gender_preference(self, user_message: str) -> Optional[str]:
        """
        Extract gender preference from user message.

        Args:
            user_message: User's message

        Returns:
            'male', 'female', or None if not detected
        """
        message_lower = user_message.lower()

        # Explicit statements
        if any(phrase in message_lower for phrase in [
            "i am a sir",
            "i'm a sir",
            "call me sir",
            "i am male",
            "i'm male",
            "i am not a madam",
            "not madam"
        ]):
            return "male"

        if any(phrase in message_lower for phrase in [
            "i am a madam",
            "i'm a madam",
            "call me madam",
            "i am female",
            "i'm female",
            "i am not a sir",
            "not sir"
        ]):
            return "female"

        return None

    def extract_name(self, user_message: str) -> Optional[str]:
        """
        Extract name from user message.

        Args:
            user_message: User's message

        Returns:
            Name if detected, None otherwise
        """
        # Pattern: "my name is X" or "call me X"
        patterns = [
            r"my name is (\w+)",
            r"i'm (\w+)",
            r"i am (\w+)",
            r"call me (\w+)"
        ]

        message_lower = user_message.lower()

        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                name = match.group(1)
                # Avoid common false positives
                if name not in ["a", "not", "the", "sir", "madam"]:
                    return name.capitalize()

        return None

    def update_from_message(self, user_message: str) -> bool:
        """
        Update preferences from user message.

        Args:
            user_message: User's message

        Returns:
            True if any preferences were updated
        """
        updated = False

        # Check for gender preference
        gender = self.extract_gender_preference(user_message)
        if gender:
            old_gender = self.preferences.get("gender")
            if old_gender != gender:
                self.preferences["gender"] = gender
                logger.info(f"Updated gender preference to: {gender}")
                updated = True

        # Check for name
        name = self.extract_name(user_message)
        if name:
            old_name = self.preferences.get("name")
            if old_name != name:
                self.preferences["name"] = name
                logger.info(f"Updated name preference to: {name}")
                updated = True

        # Save to vector store if updated
        if updated:
            self._save_to_storage()

        return updated

    def _save_to_storage(self):
        """Save preferences to vector storage"""
        try:
            # Store each preference as a searchable document
            documents = []
            metadatas = []

            for key, value in self.preferences.items():
                documents.append(f"User preference: {key} = {value}")
                metadatas.append({
                    "preference_type": key,
                    "preference_value": value,
                    "session_id": self.session_id
                })

            if documents:
                self.vector_manager.add_memory(
                    collection_name=self.preferences_collection,
                    documents=documents,
                    metadatas=metadatas
                )
                logger.info(
                    "Saved user preferences to storage",
                    preferences=self.preferences
                )

        except Exception as e:
            logger.warning(f"Failed to save preferences: {e}")

    def load_from_storage(self) -> Dict[str, str]:
        """
        Load preferences from vector storage.

        Returns:
            Dictionary of preferences
        """
        try:
            # Query for all preferences
            results = self.vector_manager.query_memory(
                collection_name=self.preferences_collection,
                query_text="User preference",
                n_results=10
            )

            if results and "metadatas" in results:
                for metadata in results["metadatas"][0]:
                    pref_type = metadata.get("preference_type")
                    pref_value = metadata.get("preference_value")
                    if pref_type and pref_value:
                        self.preferences[pref_type] = pref_value

                logger.info(
                    "Loaded user preferences from storage",
                    preferences=self.preferences
                )

        except Exception as e:
            logger.warning(f"Failed to load preferences: {e}")

        return self.preferences

    def get_preferences(self) -> Dict[str, str]:
        """Get current preferences"""
        return self.preferences.copy()

    def get_confirmation_message(self, updated_prefs: Dict[str, str]) -> Optional[str]:
        """
        Generate a confirmation message for updated preferences.

        Args:
            updated_prefs: Preferences that were just updated

        Returns:
            Confirmation message or None
        """
        if not updated_prefs:
            return None

        parts = []
        if "gender" in updated_prefs:
            gender = updated_prefs["gender"]
            address = "sir" if gender == "male" else "madam"
            parts.append(f"I'll address you as '{address}'")

        if "name" in updated_prefs:
            parts.append(f"I'll remember your name is {updated_prefs['name']}")

        if parts:
            return "Noted. " + " and ".join(parts) + "."

        return None
