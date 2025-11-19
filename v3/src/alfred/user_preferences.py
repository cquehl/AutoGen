"""
Suntory v3 - User Preferences Manager
Extract and store user preferences from conversation
"""

import re
from typing import Dict, Optional

from ..core import get_logger, get_vector_manager

logger = get_logger(__name__)

# Import LLM extractor (will be None if import fails, allowing fallback)
try:
    from .preference_extractor import get_preference_extractor
    LLM_EXTRACTION_AVAILABLE = True
except ImportError:
    LLM_EXTRACTION_AVAILABLE = False
    logger.warning("LLM preference extraction not available, using regex only")


class UserPreferencesManager:
    """
    Manages user preferences extracted from conversation.

    Handles:
    - Gender preferences (sir/madam)
    - Name
    - Other preferences as they emerge
    """

    def __init__(self, session_id: str, user_id: Optional[str] = None, use_llm_extraction: bool = True):
        self.session_id = session_id
        # Use user_id for persistence across sessions, fallback to session_id for now
        self.user_id = user_id or session_id
        self.preferences: Dict[str, str] = {}
        self.vector_manager = get_vector_manager()
        # Use user_id for cross-session persistence
        self.preferences_collection = f"user_preferences_{self.user_id}"
        # LLM extraction mode
        self.use_llm_extraction = use_llm_extraction and LLM_EXTRACTION_AVAILABLE

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
        # Patterns supporting multi-word names (titles + names)
        # Case-preserving patterns to capture "Master Charles", "Dr. Smith", etc.
        patterns = [
            # Multi-word with titles: "Master Charles", "Dr. Smith", "Mr. John Doe"
            r"(?:my name is|call me|i'?m) ((?:Master|Mister|Mr\.?|Miss|Ms\.?|Mrs\.?|Dr\.?|Professor|Prof\.?) [A-Z][a-z]+(?: [A-Z][a-z]+)*)",
            # Multi-word names: "John Smith", "Mary Jane Watson"
            r"my name is ([A-Z][a-z]+(?: [A-Z][a-z]+)+)",
            # Single word with capital (proper names): "Charles", "Alice"
            r"(?:my name is|call me) ([A-Z][a-z]+)",
            # Lowercase patterns (will capitalize): "my name is john"
            r"my name is ([a-z]+)",
            r"call me ([a-z]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, user_message, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Avoid common false positives
                name_lower = name.lower()
                blacklist = ["a", "not", "the", "sir", "madam", "male", "female", "tired", "busy"]
                if name_lower not in blacklist and len(name) <= 100:
                    # Capitalize properly if all lowercase
                    if name.islower():
                        return name.capitalize()
                    # Preserve existing capitalization (for titles)
                    return name

        return None

    async def update_from_message_async(self, user_message: str) -> Dict[str, str]:
        """
        Update preferences from user message using LLM extraction (async version).

        Args:
            user_message: User's message

        Returns:
            Dictionary of ONLY updated preferences (not all preferences)
        """
        updated_prefs = {}

        if self.use_llm_extraction and LLM_EXTRACTION_AVAILABLE:
            # Use LLM-based structured extraction
            try:
                extractor = get_preference_extractor()
                extracted = await extractor.extract_preferences(user_message, use_llm=True)

                # Update any extracted preferences
                for field, value in extracted.to_dict().items():
                    if value is not None:
                        old_value = self.preferences.get(field)
                        if old_value != value:
                            self.preferences[field] = value
                            updated_prefs[field] = value
                            logger.info(f"Updated {field} preference to: {value}")

            except Exception as e:
                logger.warning(f"LLM extraction failed, falling back to regex: {e}")
                # Fall back to regex extraction
                updated_prefs = self._update_with_regex(user_message)
        else:
            # Use legacy regex extraction
            updated_prefs = self._update_with_regex(user_message)

        # Save to vector store if updated
        if updated_prefs:
            self._save_to_storage()

        return updated_prefs

    def update_from_message(self, user_message: str) -> Dict[str, str]:
        """
        Synchronous version for backwards compatibility.
        Uses regex extraction only.

        Args:
            user_message: User's message

        Returns:
            Dictionary of ONLY updated preferences (not all preferences)
        """
        return self._update_with_regex(user_message)

    def _update_with_regex(self, user_message: str) -> Dict[str, str]:
        """
        Update preferences using regex extraction (legacy method).

        Args:
            user_message: User's message

        Returns:
            Dictionary of updated preferences
        """
        updated_prefs = {}

        # Check for gender preference
        gender = self.extract_gender_preference(user_message)
        if gender:
            old_gender = self.preferences.get("gender")
            if old_gender != gender:
                self.preferences["gender"] = gender
                updated_prefs["gender"] = gender
                logger.info(f"Updated gender preference to: {gender}")

        # Check for name
        name = self.extract_name(user_message)
        if name:
            old_name = self.preferences.get("name")
            if old_name != name:
                self.preferences["name"] = name
                updated_prefs["name"] = name
                logger.info(f"Updated name preference to: {name}")

        # Save to vector store if updated
        if updated_prefs:
            self._save_to_storage()

        return updated_prefs

    def _save_to_storage(self):
        """Save preferences to vector storage with deduplication"""
        try:
            # First, delete existing preferences for this user to avoid duplicates
            self._delete_existing_preferences()

            # Store each preference as a searchable document
            documents = []
            metadatas = []
            ids = []

            for key, value in self.preferences.items():
                documents.append(f"User preference: {key} = {value}")
                metadatas.append({
                    "preference_type": key,
                    "preference_value": value,
                    "user_id": self.user_id,
                    "session_id": self.session_id
                })
                # Use deterministic IDs for deduplication
                ids.append(f"{self.user_id}_{key}")

            if documents:
                self.vector_manager.add_memory(
                    collection_name=self.preferences_collection,
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                logger.info(
                    "Saved user preferences to storage",
                    user_id=self.user_id,
                    preferences=self.preferences
                )

        except Exception as e:
            logger.warning(f"Failed to save preferences: {e}")

    def _delete_existing_preferences(self):
        """Delete existing preferences to enable deduplication"""
        try:
            collection = self.vector_manager.get_or_create_collection(
                self.preferences_collection
            )

            # Try to delete existing preference entries by deterministic IDs
            for key in self.preferences.keys():
                pref_id = f"{self.user_id}_{key}"
                try:
                    collection.delete(ids=[pref_id])
                except Exception:
                    # ID might not exist yet, that's fine
                    pass

        except Exception as e:
            logger.warning(f"Failed to delete existing preferences: {e}")

    def load_from_storage(self) -> Dict[str, str]:
        """
        Load preferences from vector storage.

        Returns:
            Dictionary of preferences
        """
        try:
            # Query for all preferences (fix: query_texts expects a list)
            results = self.vector_manager.query_memory(
                collection_name=self.preferences_collection,
                query_texts=["User preference"],  # Fixed: was query_text (string)
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
                    user_id=self.user_id,
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
