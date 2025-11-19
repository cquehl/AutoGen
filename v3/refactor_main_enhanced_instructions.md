# Instructions for Refactoring main_enhanced.py

**Status:** CommandHandler extracted, ready to integrate into main_enhanced.py

## Changes Required

### 1. Add Import (Top of File)

```python
from .command_handler import CommandHandler
```

### 2. Update __init__ Method

Add after line 56 (after preferences_manager initialization):

```python
# Command handler (extracted for separation of concerns)
self.command_handler = CommandHandler(self)
```

### 3. Replace _handle_command Method (Lines 305-358)

**REMOVE:** Current 53-line method with if/elif chain

**REPLACE WITH:**

```python
async def _handle_command(self, command: str) -> str:
    """
    Handle special commands (delegated to CommandHandler).

    Args:
        command: Command string (starts with /)

    Returns:
        Command response
    """
    logger.info(f"Handling command: {command}")

    try:
        return await self.command_handler.handle(command)
    except Exception as e:
        error = handle_exception(e)
        log_error(error)
        return error.format_for_user()
```

### 4. DELETE All Command Methods (Lines 359-653)

**DELETE THESE METHODS (294 lines total):**

- `_cmd_switch_model()` (lines 359-384)
- `_cmd_agent()` (lines 385-427)
- `_cmd_show_mode()` (lines 428-437)
- `_cmd_show_cost()` (lines 439-442)
- `_cmd_set_budget()` (lines 443-477)
- `_cmd_show_history()` (lines 478-497)
- `_cmd_clear_history()` (lines 498-502)
- `_cmd_preferences()` (lines 503-603) **100 lines!**
- `_cmd_help()` (lines 604-653) **50 lines!**

All these are now in `CommandHandler` class.

## Result

**Before:** 732 lines
**After:** ~420 lines (42% reduction)

## Verification

Run the verification script to confirm changes:

```bash
python v3/verify_main_enhanced_refactoring.py
```

## Testing

```bash
# Run command handler tests
pytest v3/tests/test_command_handler.py -v

# Run integration tests
pytest v3/tests/test_main_enhanced*.py -v
```

## Summary of Changes

| Change | Impact |
|--------|--------|
| Extracted CommandHandler | 348 lines moved to separate class |
| Simplified _handle_command | 53 lines → 14 lines |
| Added command_handler init | 1 line added |
| Updated imports | 1 line added |
| **Total Reduction** | **~310 lines (42%)** |

## Encapsulation Fixes Applied

- ✅ UserPreferencesManager.save() - public method added
- ✅ UserPreferencesManager.clear() - public method added
- ✅ CommandHandler uses public API only (no `._save_to_storage()` calls)
