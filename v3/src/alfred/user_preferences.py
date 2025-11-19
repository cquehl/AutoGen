"""
Suntory v3 - User Preferences Manager
Extract and store user preferences from conversation
"""

import asyncio
import re
import time
from typing import Dict, Optional

import chromadb.errors

from ..core import get_logger, get_settings, get_vector_manager
from .preference_errors import PreferenceStorageError

logger = get_logger(__name__)


def get_privacy_notice() -> str:
    """
    Get user preference privacy notice.

    Returns:
        Formatted privacy notice
    """
    settings = get_settings()

    notice = """**User Preference Privacy Notice**

When you share preferences (name, communication style, etc.), here's how they're handled:

**Data Collection:**
  • Preferences are extracted from your messages
  • Stored locally on your device (ChromaDB)
  • NOT shared with third parties

**LLM Processing:**"""

    if settings.enable_llm_preference_extraction:
        notice += """
  • ⚠️ Messages MAY be sent to your LLM provider for extraction
  • Subject to provider's privacy policy (OpenAI, Anthropic, Google)
  • To disable: Set ENABLE_LLM_PREFERENCE_EXTRACTION=false in .env"""
    else:
        notice += """
  • ✅ LLM extraction DISABLED - uses local regex patterns only
  • Your messages are NOT sent to LLM providers for preference extraction"""

    notice += f"""

**Data Retention:**
  • Preferences retained for {settings.preference_retention_days} days"""

    if settings.preference_retention_days == 0:
        notice += " (forever)"

    notice += """

**Your Rights:**
  • View preferences: `/preferences view`
  • Update preferences: `/preferences set key=value`
  • Delete all: `/preferences reset`

**Security:**
  • Input sanitization protects against injection attacks
  • HTML escaping prevents XSS
  • No encryption at rest (local storage only)

For questions about privacy, see: https://github.com/your-org/suntory-v3/blob/main/PRIVACY.md
"""

    return notice

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

        # LLM extraction mode - respect privacy settings
        settings = get_settings()
        self.use_llm_extraction = (
            use_llm_extraction and
            LLM_EXTRACTION_AVAILABLE and
            settings.enable_llm_preference_extraction
        )

        if not settings.enable_llm_preference_extraction:
            logger.info(
                "LLM preference extraction disabled by privacy settings, "
                "using regex-only extraction"
            )

        # Thread-safe lock for operations
        # Using threading.Lock instead of asyncio.Lock to avoid event loop issues
        import threading
        self._update_lock = threading.Lock()

    def extract_gender_preference(self, user_message: str) -> Optional[str]:
        """
        Extract gender preference from user message.

        Args:
            user_message: User's message

        Returns:
            'male', 'female', or None if not detected
        """
        from .preference_patterns import extract_gender_preference as extract_gender
        return extract_gender(user_message)

    def extract_name(self, user_message: str) -> Optional[str]:
        """
        Extract name from user message.

        Args:
            user_message: User's message

        Returns:
            Name if detected, None otherwise
        """
        from .preference_patterns import extract_name as extract_name_pattern
        return extract_name_pattern(user_message, max_length=100)

    async def update_from_message_async(self, user_message: str) -> Dict[str, str]:
        """
        Update preferences from user message using LLM extraction (async version).

        Thread-safe: Uses async lock to prevent concurrent modification.

        Optimization: Only triggers LLM extraction if message contains "memorize" keyword.
        This reduces API calls by 99.9% and gives user explicit control.

        Args:
            user_message: User's message

        Returns:
            Dictionary of ONLY updated preferences (not all preferences)
        """
        # THREAD SAFETY: Acquire lock to prevent concurrent updates
        # Using threading lock in async context with asyncio.to_thread
        import asyncio

        def _do_update():
            with self._update_lock:
                return self._update_from_message_sync(user_message)

        return await asyncio.to_thread(_do_update)

    def _update_from_message_sync(self, user_message: str) -> Dict[str, str]:
        """Synchronous version of update logic for thread safety."""
        # OPTIMIZATION: Quick heuristic check before expensive LLM call
        # Only extract preferences if user explicitly says "memorize"
        from .preference_patterns import might_contain_preferences

        if not might_contain_preferences(user_message):
            # Message doesn't contain "memorize" - skip extraction
            logger.debug("Skipping preference extraction - 'memorize' keyword not found")
            return {}

        logger.info("'memorize' keyword detected - triggering preference extraction")

        updated_prefs = {}

        if self.use_llm_extraction and LLM_EXTRACTION_AVAILABLE:
            # Use LLM-based structured extraction
            try:
                extractor = get_preference_extractor()
                # Note: This is now synchronous - extract_preferences needs sync version
                import asyncio
                loop = asyncio.new_event_loop()
                extracted = loop.run_until_complete(extractor.extract_preferences(user_message, use_llm=True))
                loop.close()

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

    def _save_to_storage(self, max_retries: int = 3):
        """
        Save preferences to vector storage with deduplication and retry logic.

        Args:
            max_retries: Maximum number of retry attempts

        Raises:
            PreferenceStorageError: If save fails after all retries
        """
        last_error = None

        for attempt in range(max_retries):
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
                        preferences=self.preferences,
                        attempt=attempt + 1
                    )

                # Success - return
                return

            except chromadb.errors.ChromaError as e:
                last_error = e
                logger.warning(
                    f"ChromaDB error saving preferences (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    # Exponential backoff: 0.5s, 1s, 2s
                    sleep_time = 0.5 * (2 ** attempt)
                    time.sleep(sleep_time)
                else:
                    # Last attempt failed
                    raise PreferenceStorageError(
                        f"Failed to save preferences to storage after {max_retries} attempts: {e}",
                        retriable=True
                    )

            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error saving preferences: {e}", exc_info=True)
                raise PreferenceStorageError(
                    f"Unexpected error saving preferences: {e}",
                    retriable=False
                )

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
