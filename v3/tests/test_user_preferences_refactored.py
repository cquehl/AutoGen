"""
Test suite for refactored user_preferences.py
TDD-first approach: Tests written BEFORE refactoring

Focus areas:
1. Async lock behavior (no threading.Lock!)
2. PreferenceStorage isolation
3. Simplified update flow
4. No event loop detection needed
"""

import asyncio
import pytest
from typing import Dict, Optional
from unittest.mock import Mock, AsyncMock, patch, MagicMock


# ============================================================================
# MOCK DEPENDENCIES
# ============================================================================

class MockVectorManager:
    """Mock vector manager for testing"""

    def __init__(self):
        self.collections = {}
        self.stored_data = {}

    def get_or_create_collection(self, name: str):
        if name not in self.collections:
            self.collections[name] = MockCollection(name)
        return self.collections[name]

    def add_memory(self, collection_name: str, documents: list, metadatas: list, ids: list):
        """Store documents in mock storage"""
        if collection_name not in self.stored_data:
            self.stored_data[collection_name] = {}
        for doc, metadata, doc_id in zip(documents, metadatas, ids):
            self.stored_data[collection_name][doc_id] = {
                "document": doc,
                "metadata": metadata
            }

    def query_memory(self, collection_name: str, query_texts: list, n_results: int = 10) -> Dict:
        """Query documents from mock storage"""
        if collection_name not in self.stored_data:
            return {"metadatas": [[]]}

        all_metadata = []
        for doc_id, data in list(self.stored_data[collection_name].items())[:n_results]:
            all_metadata.append(data["metadata"])

        return {"metadatas": [all_metadata]}


class MockCollection:
    """Mock ChromaDB collection"""

    def __init__(self, name: str):
        self.name = name
        self.deleted_ids = []

    def delete(self, ids: list):
        """Track deleted IDs"""
        self.deleted_ids.extend(ids)


# ============================================================================
# PREFERENCE STORAGE TESTS
# ============================================================================

class TestPreferenceStorage:
    """Test the extracted PreferenceStorage class"""

    def test_storage_initialization(self):
        """Storage should initialize with user_id"""
        from v3.src.alfred.user_preferences import PreferenceStorage

        vector_manager = MockVectorManager()
        storage = PreferenceStorage(vector_manager, "user123")

        assert storage.user_id == "user123"
        assert storage.vector_manager == vector_manager

    def test_save_preferences(self):
        """Should save preferences to vector storage"""
        from v3.src.alfred.user_preferences import PreferenceStorage

        vector_manager = MockVectorManager()
        storage = PreferenceStorage(vector_manager, "user123")

        preferences = {"gender": "male", "name": "Charles"}
        storage.save(preferences, session_id="session456")

        # Verify data was saved
        collection_name = "user_preferences_user123"
        assert collection_name in vector_manager.stored_data
        assert len(vector_manager.stored_data[collection_name]) == 2

    def test_id_sanitization_prevents_injection(self):
        """ID sanitization should prevent injection attacks"""
        from v3.src.alfred.user_preferences import PreferenceStorage

        vector_manager = MockVectorManager()
        storage = PreferenceStorage(vector_manager, "user../../../etc/passwd")

        preferences = {"key<script>": "value"}
        storage.save(preferences, session_id="session123")

        # Check that IDs are sanitized (no special chars)
        saved_ids = list(vector_manager.stored_data["user_preferences_user_________etc_passwd"].keys())
        for doc_id in saved_ids:
            # Should only contain alphanumeric and underscores
            assert all(c.isalnum() or c == '_' for c in doc_id)

    def test_load_preferences(self):
        """Should load preferences from storage"""
        from v3.src.alfred.user_preferences import PreferenceStorage

        vector_manager = MockVectorManager()
        storage = PreferenceStorage(vector_manager, "user123")

        # First save
        preferences = {"gender": "female", "name": "Alice"}
        storage.save(preferences, session_id="session456")

        # Then load
        loaded = storage.load()

        assert loaded == preferences

    def test_deduplication_on_save(self):
        """Should delete existing preferences before saving (deduplication)"""
        from v3.src.alfred.user_preferences import PreferenceStorage

        vector_manager = MockVectorManager()
        storage = PreferenceStorage(vector_manager, "user123")

        # Save first time
        storage.save({"gender": "male"}, session_id="session1")

        # Save again with update
        storage.save({"gender": "male", "name": "Bob"}, session_id="session1")

        # Should have deleted old entries first (deduplication)
        collection = vector_manager.get_or_create_collection("user_preferences_user123")
        assert "user123_gender" in collection.deleted_ids

    def test_retry_logic_on_chroma_error(self):
        """Should retry on ChromaDB errors"""
        from v3.src.alfred.user_preferences import PreferenceStorage
        import chromadb.errors

        vector_manager = MockVectorManager()

        # Make add_memory fail twice then succeed
        call_count = 0

        def failing_add_memory(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise chromadb.errors.ChromaError("Temporary failure")
            # Third time succeeds (no-op, would normally save)

        vector_manager.add_memory = failing_add_memory

        storage = PreferenceStorage(vector_manager, "user123")

        # Should retry and eventually succeed
        storage.save({"gender": "male"}, session_id="session1", max_retries=3)
        assert call_count == 3


# ============================================================================
# ASYNC LOCK TESTS (Critical - Must Use asyncio.Lock, Not threading.Lock!)
# ============================================================================

class TestAsyncLockBehavior:
    """Test that refactored code uses asyncio.Lock properly"""

    @pytest.mark.asyncio
    async def test_uses_asyncio_lock_not_threading_lock(self):
        """CRITICAL: Must use asyncio.Lock, not threading.Lock"""
        from v3.src.alfred.user_preferences import UserPreferencesManager

        manager = UserPreferencesManager("session123", use_llm_extraction=False)

        # Verify it's an asyncio.Lock
        assert isinstance(manager._update_lock, asyncio.Lock), \
            "MUST use asyncio.Lock in async context, not threading.Lock!"

    @pytest.mark.asyncio
    async def test_concurrent_updates_prevented(self):
        """Async lock should prevent concurrent modification"""
        from v3.src.alfred.user_preferences import UserPreferencesManager

        manager = UserPreferencesManager("session123", use_llm_extraction=False)

        # Simulate two concurrent updates
        update_order = []

        async def update1():
            await manager.update_from_message_async("memorize: my name is Alice")
            update_order.append(1)

        async def update2():
            await manager.update_from_message_async("memorize: my name is Bob")
            update_order.append(2)

        # Run concurrently
        await asyncio.gather(update1(), update2())

        # Both should complete (order doesn't matter, but no corruption)
        assert len(update_order) == 2
        assert manager.get_preferences().get("name") in ["Alice", "Bob"]


# ============================================================================
# SIMPLIFIED UPDATE FLOW TESTS
# ============================================================================

class TestSimplifiedUpdateFlow:
    """Test the refactored update logic (no event loop detection!)"""

    @pytest.mark.asyncio
    async def test_update_with_memorize_keyword(self):
        """Should extract preferences when 'memorize' keyword present"""
        from v3.src.alfred.user_preferences import UserPreferencesManager

        manager = UserPreferencesManager("session123", use_llm_extraction=False)

        updated = await manager.update_from_message_async("memorize: my name is Charles")

        assert "name" in updated
        assert updated["name"] == "Charles"

    @pytest.mark.asyncio
    async def test_skip_extraction_without_memorize(self):
        """Should skip extraction when 'memorize' keyword absent"""
        from v3.src.alfred.user_preferences import UserPreferencesManager

        manager = UserPreferencesManager("session123", use_llm_extraction=False)

        updated = await manager.update_from_message_async("Hello, how are you?")

        assert updated == {}

    @pytest.mark.asyncio
    async def test_no_event_loop_detection_needed(self):
        """Should NOT need complex event loop detection logic"""
        from v3.src.alfred.user_preferences import UserPreferencesManager
        import inspect

        # Check that _update_from_message_async doesn't have event loop detection
        manager = UserPreferencesManager("session123", use_llm_extraction=False)
        source = inspect.getsource(manager.update_from_message_async)

        # Should NOT contain event loop detection code
        assert "get_running_loop" not in source, \
            "Refactored code should NOT need event loop detection!"
        assert "RuntimeError" not in source, \
            "Refactored code should NOT catch RuntimeError for event loops!"

    @pytest.mark.asyncio
    async def test_gender_extraction_regex(self):
        """Should extract gender using regex"""
        from v3.src.alfred.user_preferences import UserPreferencesManager

        manager = UserPreferencesManager("session123", use_llm_extraction=False)

        updated = await manager.update_from_message_async("memorize: I am a sir")

        assert "gender" in updated
        assert updated["gender"] == "male"

    @pytest.mark.asyncio
    async def test_save_called_on_update(self):
        """Should save to storage when preferences updated"""
        from v3.src.alfred.user_preferences import UserPreferencesManager

        manager = UserPreferencesManager("session123", use_llm_extraction=False)

        # Mock the storage save method
        save_called = False

        original_save = manager._storage.save

        def mock_save(*args, **kwargs):
            nonlocal save_called
            save_called = True
            return original_save(*args, **kwargs)

        manager._storage.save = mock_save

        await manager.update_from_message_async("memorize: my name is David")

        assert save_called, "Storage save should be called when preferences update"


# ============================================================================
# CONFIRMATION MESSAGE TESTS
# ============================================================================

class TestConfirmationMessages:
    """Test confirmation message generation"""

    def test_gender_confirmation(self):
        """Should generate confirmation for gender update"""
        from v3.src.alfred.user_preferences import UserPreferencesManager

        manager = UserPreferencesManager("session123")

        message = manager.get_confirmation_message({"gender": "male"})

        assert message is not None
        assert "sir" in message.lower()

    def test_name_confirmation(self):
        """Should generate confirmation for name update"""
        from v3.src.alfred.user_preferences import UserPreferencesManager

        manager = UserPreferencesManager("session123")

        message = manager.get_confirmation_message({"name": "Emma"})

        assert message is not None
        assert "Emma" in message

    def test_combined_confirmation(self):
        """Should generate combined confirmation for multiple updates"""
        from v3.src.alfred.user_preferences import UserPreferencesManager

        manager = UserPreferencesManager("session123")

        message = manager.get_confirmation_message({"gender": "female", "name": "Emma"})

        assert message is not None
        assert "madam" in message.lower()
        assert "Emma" in message

    def test_no_confirmation_for_empty_updates(self):
        """Should return None for empty updates"""
        from v3.src.alfred.user_preferences import UserPreferencesManager

        manager = UserPreferencesManager("session123")

        message = manager.get_confirmation_message({})

        assert message is None


# ============================================================================
# BACKWARDS COMPATIBILITY TESTS
# ============================================================================

class TestBackwardsCompatibility:
    """Ensure public API remains unchanged"""

    def test_sync_update_method_exists(self):
        """Old sync method should still exist for backwards compat"""
        from v3.src.alfred.user_preferences import UserPreferencesManager

        manager = UserPreferencesManager("session123", use_llm_extraction=False)

        # Should still have sync version (deprecated but functional)
        assert hasattr(manager, "update_from_message")
        assert callable(manager.update_from_message)

    def test_sync_update_calls_async_version(self):
        """Sync update should call async version internally"""
        from v3.src.alfred.user_preferences import UserPreferencesManager

        manager = UserPreferencesManager("session123", use_llm_extraction=False)

        # Call sync version
        updated = manager.update_from_message("memorize: my name is Frank")

        # Should work (calls async internally)
        assert "name" in updated
        assert updated["name"] == "Frank"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """End-to-end integration tests"""

    @pytest.mark.asyncio
    async def test_full_preference_lifecycle(self):
        """Test complete lifecycle: extract → save → load"""
        from v3.src.alfred.user_preferences import UserPreferencesManager

        manager = UserPreferencesManager("session123", user_id="user456", use_llm_extraction=False)

        # 1. Extract preferences
        updated = await manager.update_from_message_async("memorize: I am a sir and my name is George")

        assert "gender" in updated
        assert "name" in updated

        # 2. Get preferences
        prefs = manager.get_preferences()
        assert prefs["gender"] == "male"
        assert prefs["name"] == "George"

        # 3. Create new manager instance for same user
        manager2 = UserPreferencesManager("session789", user_id="user456", use_llm_extraction=False)

        # 4. Load from storage
        loaded_prefs = manager2.load_from_storage()

        # Should have loaded the preferences
        assert loaded_prefs.get("gender") == "male"
        assert loaded_prefs.get("name") == "George"

    @pytest.mark.asyncio
    async def test_update_existing_preference(self):
        """Should update existing preference value"""
        from v3.src.alfred.user_preferences import UserPreferencesManager

        manager = UserPreferencesManager("session123", use_llm_extraction=False)

        # First update
        await manager.update_from_message_async("memorize: my name is Original")
        assert manager.get_preferences()["name"] == "Original"

        # Second update (change)
        await manager.update_from_message_async("memorize: my name is Updated")
        assert manager.get_preferences()["name"] == "Updated"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
