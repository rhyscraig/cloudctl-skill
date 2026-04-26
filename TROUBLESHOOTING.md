# CloudctlSkill Troubleshooting Guide

## If `/cloudctl` Doesn't Show After Restart

### Symptom: "I can see /jira but not /cloudctl"

---

## Diagnostic Checklist

### ✅ Step 1: Verify settings.json is correct
```bash
cat /Users/craighoad/.claude/settings.json | grep -A 6 cloudctl
```

**Expected output:**
```json
"cloudctl": {
  "command": "python3",
  "args": ["-m", "cloudctl_skill.mcp"],
  "cwd": "/private/tmp/cloudctl-skill",
  "description": "Cloud context management skill..."
}
```

**If missing `cwd`:** Add it with the absolute path `/private/tmp/cloudctl-skill`

---

### ✅ Step 2: Verify Python can find the module
```bash
cd /private/tmp/cloudctl-skill
python3 -c "import cloudctl_skill; print('✅ Module found')"
```

**Expected:** ✅ Module found

**If fails:** The module might not be installed properly
- Solution: `cd /private/tmp/cloudctl-skill && pip install -e .`

---

### ✅ Step 3: Verify MCP server starts
```bash
cd /private/tmp/cloudctl-skill
echo '{"method":"health","params":{}}' | python3 -m cloudctl_skill.mcp
```

**Expected:** JSON response with `"is_healthy": true`

**If fails:** There's a startup error
- Check error output for missing dependencies
- Solution: `pip install -r requirements.txt`

---

### ✅ Step 4: Check if Claude is actually restarted
The most common issue is Claude caching the old settings.json

**Solution:**
1. Close Claude completely (not just the window, fully quit)
2. Wait 5 seconds
3. Reopen Claude
4. Try typing `/cloudctl`

---

### ✅ Step 5: Compare with /jira setup
```bash
# Check how Jira is registered
cat /Users/craighoad/.claude/skills/jira.json | head -20

# Check how cloudctl is registered  
cat /Users/craighoad/.claude/skills/cloudctl.json | head -20
```

**Note:** Both should have similar manifest structure with `commands` and `description` fields

---

## Common Issues & Fixes

### Issue 1: "Module not found: cloudctl_skill"
**Cause:** Python can't find the cloudctl_skill package  
**Fix:**
```bash
cd /private/tmp/cloudctl-skill
pip install -e .
```

### Issue 2: "ModuleNotFoundError: No module named 'pydantic'"
**Cause:** Missing dependencies  
**Fix:**
```bash
pip install pydantic pyyaml rich
```

### Issue 3: "cloudctl command not found"
**Cause:** cloudctl binary not installed  
**Fix:**
```bash
which cloudctl  # Check if installed
cloudctl status # Test if working
```

### Issue 4: "No active context found"
**Cause:** You're not logged into any cloud provider  
**Fix:**
```bash
cloudctl login
```

### Issue 5: Claude shows `/jira` but not `/cloudctl`
**Cause:** settings.json not reloaded by Claude  
**Fix:**
1. Fully close Claude (not just minimize)
2. Open Claude again
3. Try `/cloudctl health`

---

## Full Diagnostic Script

Run this to test all layers:
```bash
bash /tmp/debug_cloudctl_mcp.sh
```

This will:
- ✅ Verify settings.json registration
- ✅ Check working directory
- ✅ Verify Python installation
- ✅ Test module imports
- ✅ Test MCP server startup
- ✅ Verify cloudctl binary
- ✅ Test all core commands

---

## If All Diagnostics Pass But Still No `/cloudctl`

**The issue is likely Claude's settings caching:**

1. **Close Claude completely** (Force quit if needed)
   ```bash
   # On Mac
   killall Claude
   ```

2. **Clear Claude's cache** (optional)
   ```bash
   # Backup first
   cp ~/Library/Caches/com.anthropic.claude/Library/Saved\ Application\ State -r ~/Library/Caches/com.anthropic.claude/Library/Saved\ Application\ State.bak
   
   # Clear cache
   rm -rf ~/Library/Caches/com.anthropic.claude/Library/Saved\ Application\ State/*
   ```

3. **Reopen Claude**

4. **Try `/cloudctl health`**

---

## Advanced Debugging

### View MCP Server Errors (if Claude logs them)
Check if Claude has any error logs:
```bash
# Mac logs
log stream --predicate 'process == "Claude"' --level debug
```

### Test MCP Server Directly
```bash
# Test context retrieval
cd /private/tmp/cloudctl-skill
python3 << 'EOF'
import asyncio
import json
import sys
from cloudctl_skill import CloudctlSkill

async def test():
    skill = CloudctlSkill()
    context = await skill.get_context()
    print(json.dumps({
        "provider": context.provider.value,
        "organization": context.organization,
        "account_id": context.account_id,
    }))

asyncio.run(test())
EOF
```

### Verify settings.json Format
```bash
# Validate JSON syntax
python3 -m json.tool /Users/craighoad/.claude/settings.json
```

---

## When All Else Fails

If the diagnostic passes but `/cloudctl` still doesn't appear:

1. **Verify the exact path exists**
   ```bash
   ls -la /private/tmp/cloudctl-skill/src/cloudctl_skill/mcp.py
   ```

2. **Check Python version compatibility**
   ```bash
   python3 --version  # Should be 3.12+
   ```

3. **Reinstall from scratch**
   ```bash
   cd /private/tmp/cloudctl-skill
   pip uninstall cloudctl-skill
   pip install -e .
   ```

4. **Contact support** with output of:
   ```bash
   bash /tmp/debug_cloudctl_mcp.sh > /tmp/cloudctl_debug_output.txt 2>&1
   cat /tmp/cloudctl_debug_output.txt
   ```

---

## Summary

✅ If all diagnostic layers pass → The infrastructure is correct  
⚠️ If Claude still won't show `/cloudctl` → It's likely a settings reload issue  
🔧 Solution: Fully close and reopen Claude (don't just minimize)

