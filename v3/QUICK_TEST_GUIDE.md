# 🚀 Quick Test Guide - Copy/Paste Commands

## 1. Quick Verification Test (30 seconds)

```bash
cd v3
source venv/bin/activate
python3 simple_verification.py
```

**Expected Output:**
```
✅ PASS - Imports (SQLAlchemy fix)
✅ PASS - Settings (.env format fix)
✅ PASS - API method (convenience added)

🎉 ALL FIXES VERIFIED!
```

---

## 2. Run Suntory Interactive Mode (Full Experience)

```bash
cd v3
./Suntory.sh
```

Then try these commands in the interface:
```
Hello Alfred!
What can you do?
/model
/help
exit
```

---

## 3. Automated Test Suite (2 minutes)

```bash
cd v3
source venv/bin/activate
python3 test_suntory_automated.py
```

**Expected:**
- System initializes ✅
- Tests run ✅
- Some tests pass (depends on LLM responses)

---

## That's It!

The fastest way: Just run command #1 to verify all fixes work!
