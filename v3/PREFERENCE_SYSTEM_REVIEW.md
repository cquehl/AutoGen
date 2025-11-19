# User Preference System - Feature & Code Review

**Date:** 2025-11-19
**Reviewer:** Claude Code
**Status:** Production Review
**Files Reviewed:**
- `src/alfred/user_preferences.py` (224 lines)
- `src/alfred/main_enhanced.py` (614 lines, integration)
- `src/alfred/personality.py` (262 lines, integration)
- `src/core/persistence.py` (261+ lines, storage backend)
- `test_team_mode_fix.py` (213 lines, test coverage)

---

## Executive Summary

**Overall Assessment: 6.5/10** - Functional with significant room for improvement

### Strengths ✅
- Core feature works: detects gender/name preferences from natural language
- Clean integration with Alfred's personality system
- Good separation of concerns (extraction, storage, injection)
- Proper logging throughout
- Basic test coverage exists

### Critical Issues 🔴
1. **Vector store query API mismatch** - Wrong parameter name breaks loading
2. **No session persistence** - Preferences lost between Alfred restarts
3. **Race condition** - Preferences updated synchronously in async context
4. **Confirmation logic bug** - Shows all prefs, not just updated ones
5. **Poor error handling** - Silent failures on storage errors

### Feature Gaps ⚠️
- No cross-session persistence (defeats the purpose)
- Limited preference types (only gender & name)
- No user-facing commands to view/edit preferences
- No preference deletion or correction mechanism
- "Master Charles" hardcoded, not actually from preferences

---

## 1. Architecture Review

### 1.1 Design Pattern
```
User Message → Extract Preferences → Update In-Memory → Save to Vector Store
                                                        ↓
                                     Inject into System Prompt → LLM
```

**Assessment:** ✅ Sound design, but implementation has gaps

### 1.2 Integration Points

| Component | Integration | Quality |
|-----------|-------------|---------|
| AlfredEnhanced | ✅ Instantiates manager per session | Good |
| process_message_streaming | ✅ Extracts & confirms | Good |
| _process_direct_streaming | ✅ Injects into system prompt | Good |
| VectorStoreManager | ❌ API mismatch breaks loading | **BROKEN** |
| DatabaseManager | ❌ Not used for preferences | Missing |

---

## 2. Code Quality Review

### 2.1 **UserPreferencesManager Class** (user_preferences.py)

#### Pattern Matching (Lines 30-65)
```python
def extract_gender_preference(self, user_message: str) -> Optional[str]:
    message_lower = user_message.lower()

    if any(phrase in message_lower for phrase in [
        "i am a sir",
        "i'm a sir",
        # ... more patterns
    ]):
        return "male"
```

**Issues:**
1. ⚠️ **False positives**: "I am not a sir" matches "i am a sir" substring
   - Mitigated by separate "not" patterns, but fragile
2. ⚠️ **Case sensitivity**: Lowercasing loses proper names (though not used)
3. ✅ **Good:** Simple, readable, extensible

**Recommendation:** Use regex with word boundaries:
```python
import re

patterns_male = [
    r"\bi'?m a sir\b",
    r"\bcall me sir\b",
    r"\bi'?m male\b",
    r"\bnot (?:a )?madam\b"
]
if any(re.search(p, message_lower) for p in patterns_male):
    return "male"
```

#### Name Extraction (Lines 67-95)
```python
def extract_name(self, user_message: str) -> Optional[str]:
    patterns = [
        r"my name is (\w+)",
        r"i'm (\w+)",
        r"i am (\w+)",
        r"call me (\w+)"
    ]
```

**Critical Issues:**
1. 🔴 **Over-matching:** "i'm a sir" → captures "a" as name
   - Filtered by blacklist, but brittle
2. 🔴 **Doesn't capture "Master Charles":** Multi-word names fail
3. ⚠️ **Context-blind:** "i'm tired" → captures "tired" (filtered)

**Recommendation:**
```python
# Match multi-word names
r"my name is ([A-Z][a-z]+(?: [A-Z][a-z]+)*)",
r"call me ((?:Master|Mister|Miss|Ms\.?) [A-Z][a-z]+)",
# Avoid adjectives/articles with lookahead
r"i'?m ([A-Z][a-z]+)(?:\s|,|\.)"
```

### 2.2 **Storage Implementation** (Lines 133-161)

#### Save to Storage (Lines 133-160)
```python
def _save_to_storage(self):
    """Save preferences to vector storage"""
    try:
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
```

**Issues:**
1. ✅ **Good:** Stores as searchable documents
2. ⚠️ **No deduplication:** Updates add new entries, doesn't replace old ones
3. ⚠️ **Per-session collection:** `preferences_{session_id}` means prefs lost between sessions

**Critical Bug:**
```python
self.preferences_collection = f"preferences_{session_id}"
```
Each session gets a NEW collection → **no persistence across restarts**

**Should be:**
```python
# Option 1: Global preferences per user
self.preferences_collection = "user_preferences_global"

# Option 2: User-specific (if multi-user)
self.preferences_collection = f"user_preferences_{user_id}"
```

#### Load from Storage (Lines 162-192)
```python
def load_from_storage(self) -> Dict[str, str]:
    try:
        results = self.vector_manager.query_memory(
            collection_name=self.preferences_collection,
            query_text="User preference",  # ❌ WRONG PARAMETER
            n_results=10
        )
```

**CRITICAL BUG 🔴:**
```python
# Vector store API (persistence.py:241-245)
def query_memory(
    self,
    collection_name: str,
    query_texts: List[str],  # ← EXPECTS LIST
    n_results: int = 5
) -> Dict[str, Any]:
```

**UserPreferencesManager passes:**
```python
query_text="User preference"  # ❌ String instead of List[str]
```

**This call will FAIL** → Preferences never load from storage

**Fix:**
```python
results = self.vector_manager.query_memory(
    collection_name=self.preferences_collection,
    query_texts=["User preference"],  # ✅ List
    n_results=10
)
```

### 2.3 **Error Handling**

**Current approach:**
```python
except Exception as e:
    logger.warning(f"Failed to save preferences: {e}")
```

**Issues:**
1. ❌ **Silent failures:** User never knows preferences weren't saved
2. ❌ **No retry logic:** Transient failures = permanent data loss
3. ❌ **Broad exception catch:** Masks bugs

**Recommendation:**
```python
except chromadb.errors.ChromaError as e:
    logger.error(f"Vector store error saving preferences: {e}")
    # Could fallback to in-memory only with warning to user
    self._fallback_mode = True
except Exception as e:
    logger.exception("Unexpected error saving preferences")
    raise  # Re-raise unexpected errors in development
```

### 2.4 **Integration in AlfredEnhanced** (main_enhanced.py)

#### Initialization (Lines 54-55, 74-75)
```python
# __init__
self.preferences_manager = UserPreferencesManager(self.session_id)

# initialize()
self.preferences_manager.load_from_storage()
```

**Issues:**
1. ✅ **Good:** Clean instantiation
2. 🔴 **BROKEN:** load_from_storage() has API bug (see above)
3. ⚠️ **Sync in async:** load_from_storage() is sync, called in async initialize()
   - Works now, but could block event loop if vector store is slow

#### Message Processing (Lines 168-176)
```python
# Update user preferences from message
prefs_updated = self.preferences_manager.update_from_message(user_message)
if prefs_updated:
    confirmation = self.preferences_manager.get_confirmation_message(
        self.preferences_manager.get_preferences()  # ❌ BUG
    )
    if confirmation:
        yield confirmation + "\n\n"
```

**BUG 🔴:**
```python
# get_confirmation_message expects ONLY updated prefs
def get_confirmation_message(self, updated_prefs: Dict[str, str]) -> Optional[str]:
    if not updated_prefs:
        return None
```

**But gets ALL preferences:**
```python
self.preferences_manager.get_preferences()  # Returns ALL, not just updated
```

**This causes:**
- First update: "Noted. I'll address you as 'sir' and I'll remember your name is Charles."
- Second update (change name): "Noted. I'll address you as 'sir' and I'll remember your name is Charlie."
  - Should only say name changed!

**Fix:**
```python
# UserPreferencesManager.update_from_message should return updated prefs
def update_from_message(self, user_message: str) -> Dict[str, str]:
    """Returns dict of ONLY updated preferences"""
    updated = {}

    gender = self.extract_gender_preference(user_message)
    if gender and self.preferences.get("gender") != gender:
        self.preferences["gender"] = gender
        updated["gender"] = gender

    name = self.extract_name(user_message)
    if name and self.preferences.get("name") != name:
        self.preferences["name"] = name
        updated["name"] = name

    if updated:
        self._save_to_storage()

    return updated

# main_enhanced.py
prefs_updated = self.preferences_manager.update_from_message(user_message)
if prefs_updated:
    confirmation = self.preferences_manager.get_confirmation_message(prefs_updated)
```

#### System Prompt Injection (Lines 256-258)
```python
user_prefs = self.preferences_manager.get_preferences()
system_message = self.personality.get_system_message(user_prefs)
```

**✅ Clean and correct**

### 2.5 **Personality Integration** (personality.py:166-180)

```python
if user_preferences:
    prefs = []
    if "gender" in user_preferences:
        gender = user_preferences["gender"]
        if gender == "male":
            prefs.append("Address the user as 'sir' (not 'madam')")
        elif gender == "female":
            prefs.append("Address the user as 'madam' (not 'sir')")

    if "name" in user_preferences:
        prefs.append(f"User's name is {user_preferences['name']}")

    if prefs:
        preference_context = "\n\n**IMPORTANT USER PREFERENCES:**\n" + "\n".join(f"- {p}" for p in prefs)
```

**Issues:**
1. ✅ **Good:** Clear, explicit instructions to LLM
2. ⚠️ **"Master Charles" not implemented:**
   - System prompt says use "Master Charles" but doesn't check if name is Charles
   - Should be: `"Use 'sir' or 'Master {name}' occasionally"`
3. ⚠️ **No title preference:** Can't choose Mr./Dr./Professor/etc.

---

## 3. Feature Gaps & Bugs

### 3.1 Critical Bugs

| # | Severity | Issue | Location |
|---|----------|-------|----------|
| 1 | 🔴 Critical | Vector store query API mismatch | user_preferences.py:173 |
| 2 | 🔴 Critical | Preferences not persisted across sessions | user_preferences.py:28 |
| 3 | 🔴 High | Confirmation shows all prefs, not updates | main_enhanced.py:172-173 |
| 4 | 🟡 Medium | Name extraction fails on multi-word names | user_preferences.py:78-83 |
| 5 | 🟡 Medium | No deduplication = duplicate entries | user_preferences.py:149-153 |

### 3.2 Missing Features

1. **Cross-session persistence**
   - Current: Preferences reset every Alfred restart
   - Need: Global user preference store

2. **User commands**
   - No `/preferences` command to view current settings
   - No `/preferences set gender=male` to manually edit
   - No `/preferences reset` to clear

3. **Additional preference types**
   - Formality level (casual/formal/very formal)
   - Timezone (for time-aware greetings)
   - Preferred name style (first name / Mr. Last Name / nickname)
   - Communication style (verbose/concise)

4. **Preference correction**
   - "Actually, I prefer madam" → No easy way to update
   - Should detect corrections and update

5. **Multi-user support**
   - No user authentication/identification
   - Can't distinguish between multiple users

### 3.3 Edge Cases Not Handled

```python
# False positives
"My colleague is a sir" → Detects as gender preference
"Not sure if I'm a sir or madam" → Extracts "a" as name

# Ambiguous input
"Call me Alex" → Is Alex male/female? (Gender-neutral names)

# Conflicting input
"I'm a sir" ... later ... "Actually I'm a madam"
→ Updates, but no warning that preference changed

# Malicious input
"I'm a sir madam male female" → Which one wins?
```

---

## 4. Testing Analysis

### 4.1 Test Coverage

**test_team_mode_fix.py** (Lines 56-71):
```python
print("User: I am a sir, not a madam")
response = await alfred.handle_message("I am a sir, not a madam")
print(f"Alfred: {response}")

prefs = alfred.preferences_manager.get_preferences()
print(f"Stored preferences: {prefs}")

if prefs.get("gender") == "male":
    print("✓ User preference test passed")
else:
    print("✗ User preference test FAILED")
```

**Coverage:**
- ✅ Basic extraction works
- ✅ In-memory storage works
- ❌ Doesn't test persistence (reload)
- ❌ Doesn't test system prompt injection
- ❌ Doesn't test name extraction
- ❌ Doesn't test confirmation message

**Missing tests:**
1. Edge cases (false positives, multi-word names)
2. Persistence across sessions
3. Update vs. initial set
4. Conflicting preferences
5. Storage failure scenarios

### 4.2 Recommended Test Suite

```python
class TestUserPreferences:

    def test_gender_extraction_positive():
        """Test all gender pattern variations"""
        cases = [
            ("I am a sir", "male"),
            ("I'm a sir, not a madam", "male"),
            ("Call me madam", "female"),
            ("i'm male", "male")
        ]
        for msg, expected in cases:
            assert manager.extract_gender_preference(msg) == expected

    def test_gender_extraction_false_positives():
        """Ensure we don't match incorrectly"""
        cases = [
            "My boss is a sir",
            "What is a sir?",
            "Sir is a title"
        ]
        for msg in cases:
            assert manager.extract_gender_preference(msg) is None

    def test_name_extraction_multiword():
        """Test multi-word names"""
        assert manager.extract_name("Call me Master Charles") == "Master Charles"
        assert manager.extract_name("My name is John Smith") == "John Smith"

    async def test_persistence_across_sessions():
        """Critical: Prefs survive Alfred restart"""
        # Session 1
        alfred1 = AlfredEnhanced()
        await alfred1.initialize()
        await alfred1.handle_message("I'm a sir")
        session1_id = alfred1.session_id
        await alfred1.shutdown()

        # Session 2 (new instance)
        alfred2 = AlfredEnhanced()
        await alfred2.initialize()
        prefs = alfred2.preferences_manager.get_preferences()

        # Should still know I'm a sir
        assert prefs.get("gender") == "male"

    def test_confirmation_message_only_updated():
        """Bug fix: Only show changed prefs"""
        manager = UserPreferencesManager("test")
        manager.preferences = {"gender": "male"}

        updated_only = {"name": "Charles"}
        msg = manager.get_confirmation_message(updated_only)

        assert "Charles" in msg
        assert "sir" not in msg  # Don't mention unchanged gender
```

---

## 5. Security & Privacy Review

### 5.1 Security Issues

1. ✅ **No injection risk:** Prefs are not eval'd or executed
2. ✅ **No SQL injection:** Using ORM/ChromaDB properly
3. ⚠️ **No input sanitization:**
   ```python
   # Could store very long strings
   "My name is " + "A" * 1000000
   ```
   **Recommendation:** Limit length
   ```python
   if len(name) > 100:
       return None
   ```

4. ⚠️ **No access control:** Any process can read ChromaDB files
   - Preferences stored in plaintext on disk
   - For sensitive data (medical, legal use), should encrypt

### 5.2 Privacy Concerns

1. ⚠️ **PII storage:** Name & gender are personally identifiable
   - Should document in privacy policy
   - Consider GDPR right-to-delete

2. ⚠️ **No data retention policy:**
   - Preferences stored forever
   - Should have expiry or manual cleanup

3. ✅ **Session isolation:** Different sessions use different collections
   - Actually **bad** for persistence (see bug #2)

---

## 6. Performance Analysis

### 6.1 Bottlenecks

```python
# Every message:
prefs_updated = self.preferences_manager.update_from_message(user_message)
```

**Performance:**
- Regex matching on every message: ~0.1ms (negligible)
- Vector store write if updated: ~10-50ms (noticeable)

**Issue:** Writes to disk on EVERY preference update
- If user says "I'm a sir" 5 times, writes 5 times
- Should debounce or batch writes

**Recommendation:**
```python
# Only save every N seconds or on shutdown
self._dirty = True
self._last_save = time.time()

if self._dirty and (time.time() - self._last_save > 30):
    self._save_to_storage()
    self._dirty = False
```

### 6.2 Memory Usage

- In-memory dict: ~100 bytes per user (trivial)
- ChromaDB collection: ~1KB per user (acceptable)
- No memory leaks detected

---

## 7. Recommendations

### 7.1 Critical Fixes (Do First)

1. **Fix vector store query API (5 min)**
   ```python
   # user_preferences.py:173
   - query_text="User preference",
   + query_texts=["User preference"],
   ```

2. **Fix cross-session persistence (10 min)**
   ```python
   # user_preferences.py:28
   - self.preferences_collection = f"preferences_{session_id}"
   + self.preferences_collection = "user_preferences_global"
   ```

3. **Fix confirmation message bug (15 min)**
   - Change `update_from_message()` to return only updated prefs
   - Pass only updated to `get_confirmation_message()`

4. **Add input validation (10 min)**
   ```python
   if name and len(name) <= 100:
       self.preferences["name"] = name
   ```

### 7.2 High-Priority Enhancements (This Sprint)

5. **Multi-word name support (30 min)**
   - Update regex to capture "Master Charles", "Dr. Smith", etc.

6. **Add `/preferences` command (1 hour)**
   ```python
   /preferences view
   /preferences set gender=male
   /preferences set name="Master Charles"
   /preferences reset
   ```

7. **Deduplication in vector store (1 hour)**
   - Before adding, delete existing prefs for this user
   - Or use upsert if ChromaDB supports it

8. **Add comprehensive tests (2 hours)**
   - Implement test suite from section 4.2

### 7.3 Future Enhancements (Next Sprint)

9. **Additional preference types**
   - Formality level
   - Title (Mr./Dr./Professor)
   - Timezone
   - Communication style

10. **Multi-user support**
    - User authentication/identification
    - Per-user preference collections

11. **Preference analytics**
    - Track what users configure
    - A/B test different default behaviors

12. **Export/import preferences**
    - `/preferences export` → JSON file
    - `/preferences import <file>`

---

## 8. Scoring Breakdown

| Category | Score | Weight | Weighted |
|----------|-------|--------|----------|
| **Functionality** | 5/10 | 30% | 1.5 |
| Core works but cross-session broken | | | |
| **Code Quality** | 6/10 | 25% | 1.5 |
| Clean structure, but bugs & no validation | | | |
| **Testing** | 4/10 | 15% | 0.6 |
| Basic test exists, no edge cases | | | |
| **Performance** | 8/10 | 10% | 0.8 |
| Fast enough, minor inefficiencies | | | |
| **Security** | 7/10 | 10% | 0.7 |
| No major issues, but no sanitization | | | |
| **Maintainability** | 7/10 | 10% | 0.7 |
| Well-organized, good logging | | | |
| **Total** | **6.5/10** | | |

---

## 9. Conclusion

The user preference system is a **solid MVP with critical bugs**:

**What works:**
- ✅ Natural language extraction
- ✅ Clean architecture
- ✅ System prompt injection

**What's broken:**
- 🔴 Doesn't persist across sessions (defeats the purpose)
- 🔴 Vector store API mismatch prevents loading
- 🔴 Confirmation message shows wrong data

**Priority:**
1. Fix the 3 critical bugs (30 min)
2. Add comprehensive tests (2 hours)
3. Add user-facing `/preferences` commands (1 hour)

**After fixes:** Would score **8/10** - a genuinely useful feature

**Total effort to production-ready:** ~4 hours

---

## Appendix: Files to Modify

### Immediate Fixes
- [ ] `src/alfred/user_preferences.py` - Fix query API, add validation
- [ ] `src/alfred/main_enhanced.py` - Fix confirmation message logic
- [ ] `test_team_mode_fix.py` - Add persistence test

### Enhancement
- [ ] `src/alfred/user_preferences.py` - Multi-word names, dedup
- [ ] `src/alfred/main_enhanced.py` - Add `/preferences` command
- [ ] `tests/test_user_preferences.py` - New comprehensive test file

---

**End of Review**
