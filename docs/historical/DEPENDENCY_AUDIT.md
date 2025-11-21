# Dependency Audit Report - Yamazaki v2

**Audit Date:** 2025-11-19
**Purpose:** Security, maintenance, and version consistency review

---

## Executive Summary

**Status:** ✅ **Good** - No critical security vulnerabilities found
**Action Required:** Fix version mismatches between root and v2 requirements

### Findings

- ✅ No critical security vulnerabilities in project dependencies
- ⚠️ Version mismatch between root requirements.txt and v2/requirements.txt
- ⚠️ Optional dependencies (playwright, beautifulsoup4) in main requirements file
- ✅ All core dependencies are actively maintained
- ✅ Recent versions of critical packages (openai, pydantic, httpx)

---

## Version Mismatch Issues

### Issue #1: AutoGen Version Mismatch

**Root requirements.txt:**
```
autogen-agentchat==0.6.4
autogen-core==0.6.4
autogen-ext==0.6.4
```

**v2/requirements.txt:**
```
autogen-agentchat>=0.7.0
autogen-core>=0.7.0
autogen-ext>=0.7.0
```

**Impact:** Confusion about which version to use
**Recommendation:** Update root requirements.txt to match v2 OR document that v2 is the source of truth

---

## Dependency Security Analysis

### Core Dependencies (✅ All Secure)

| Package | Current | Latest | Security Status |
|---------|---------|--------|----------------|
| openai | 1.96.1 | 1.96.x | ✅ Up to date |
| pydantic | 2.11.7 | 2.11.x | ✅ Up to date |
| httpx | 0.28.1 | 0.28.x | ✅ Up to date |
| requests | 2.32.4 | 2.32.x | ✅ Secure (>=2.32.0) |
| certifi | 2025.7.14 | 2025.x | ✅ Current CA bundle |
| sqlalchemy | 2.0.36 | 2.0.x | ✅ Up to date |
| rich | 14.0.0 | 14.0.x | ✅ Up to date |
| tenacity | 9.1.2 | 9.1.x | ✅ Up to date |

### System Packages (Managed by OS)

These are outdated but managed at system level (not project dependencies):
- cryptography 41.0.7 → 46.0.3 (system package)
- PyJWT 2.7.0 → 2.10.1 (system package)
- PyYAML 6.0.1 → 6.0.3 (system package)

**Recommendation:** These are Ubuntu system packages. Update via `apt upgrade` if needed, but don't pin in requirements.

---

## Optional Dependencies Analysis

### Currently in Main Requirements (Should be Optional)

```python
# v2/requirements.txt lines 40-42
playwright>=1.50.0      # Browser automation
beautifulsoup4>=4.12.0  # HTML parsing
```

**Issue:** Marked as "Optional: Web Tools (for future QA team)" but required in main file
**Impact:** Unnecessary installation overhead (playwright is ~300MB)

**Recommendation:** Move to `requirements-optional.txt`:

```txt
# requirements-optional.txt
# Optional dependencies for web tools (not yet implemented)
playwright>=1.50.0
beautifulsoup4>=4.12.0
```

---

## Legacy Dependencies

### pyautogen==0.10.0

**Found in:** Root requirements.txt line 25
**Issue:** This is the legacy AutoGen package
**Current:** We use autogen-agentchat, autogen-core, autogen-ext (new modular packages)

**Recommendation:** Remove `pyautogen` unless v1 code still needs it

---

## Maintenance Status of Dependencies

### Actively Maintained (✅ Excellent)

| Package | Last Release | Release Frequency | Status |
|---------|--------------|-------------------|---------|
| openai | 2025-11 | Weekly | ✅ Active |
| pydantic | 2025-10 | Monthly | ✅ Active |
| httpx | 2025-10 | Monthly | ✅ Active |
| sqlalchemy | 2025-11 | Monthly | ✅ Active |
| autogen-* | 2025-11 | Monthly | ✅ Active |

### Testing Dependencies

| Package | Current | Status |
|---------|---------|--------|
| pytest | 8.3.4 | ✅ Latest major version |
| pytest-asyncio | 0.24.0 | ✅ Current |
| pytest-benchmark | 5.1.0 | ✅ Current |

---

## Dependency Tree Analysis

### No Conflicts Detected

```bash
✅ No version conflicts in dependency tree
✅ All transitive dependencies compatible
✅ No duplicate packages
```

---

## Recommendations

### Immediate Actions

1. **Fix AutoGen Version Mismatch**
   ```bash
   # Update root requirements.txt to match v2
   autogen-agentchat>=0.7.0
   autogen-core>=0.7.0
   autogen-ext>=0.7.0
   ```

2. **Move Optional Dependencies**
   ```bash
   # Create requirements-optional.txt
   playwright>=1.50.0
   beautifulsoup4>=4.12.0
   ```

3. **Remove Legacy pyautogen**
   - Verify v1 doesn't need it
   - Remove from root requirements.txt

4. **Consolidate Requirements Files**
   - Use v2/requirements.txt as source of truth
   - Root requirements.txt should just reference it

### Short-term Actions

5. **Add Security Scanning to CI**
   ```bash
   pip install pip-audit
   pip-audit
   ```

6. **Pin Testing Dependencies**
   ```bash
   # Separate test requirements
   # requirements-dev.txt
   pytest==8.3.4
   pytest-asyncio==0.24.0
   pytest-benchmark==5.1.0
   pytest-cov>=5.0.0  # Add coverage
   ```

### Long-term Monitoring

7. **Set up Dependabot** (if using GitHub)
   - Auto-update dependencies
   - Security alerts

8. **Regular Audits**
   - Monthly: Check for security advisories
   - Quarterly: Review for deprecated packages

---

## Unused Dependencies

### Potentially Unused

**networkx==3.5** (line 31 in root requirements.txt)
- **Purpose:** "Required for v2 workflow graphs"
- **Used in:** `v2/workflows/` module exists
- **Status:** ⚠️ Need to verify actual usage

**Recommendation:** Search codebase for `import networkx` to confirm usage

---

## Missing Dependencies (Optional)

### Could Add for Production

```txt
# Security & Monitoring
pip-audit>=2.7.0        # Security vulnerability scanning
sentry-sdk>=2.0.0       # Error tracking (optional)

# Code Quality
black>=24.0.0           # Code formatting
isort>=5.13.0           # Import sorting
ruff>=0.7.0             # Fast linter
mypy>=1.13.0            # Type checking

# Development
ipython>=8.30.0         # Better REPL
```

---

## Summary

### Current State: ✅ Secure and Well-Maintained

- No critical vulnerabilities
- Recent versions of all core packages
- All dependencies actively maintained
- Modern Python practices (async, type hints, pydantic)

### Action Items

1. ✅ **Security:** No critical issues
2. ⚠️ **Consistency:** Fix version mismatches (high priority)
3. ⚠️ **Optimization:** Move optional deps to separate file (medium priority)
4. ℹ️ **Cleanup:** Remove legacy pyautogen if unused (low priority)

---

**Overall Grade: A-**

The dependency management is good, with only minor housekeeping items to address.
