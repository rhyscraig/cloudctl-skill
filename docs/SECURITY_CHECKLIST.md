# CloudctlSkill Security Checklist

**Use this checklist for every pull request, release, and major milestone.**

## Before Every Commit

- [ ] Pre-commit hook is installed and active
  ```bash
  ls -la .git/hooks/pre-commit
  chmod +x .git/hooks/pre-commit
  ```

- [ ] No `.cloudctl.yaml` files staged for commit
  ```bash
  git diff --cached --name-only | grep ".cloudctl.yaml"
  # Should output nothing
  ```

- [ ] No files with secret patterns in staged changes
  ```bash
  git diff --cached | grep -i "password\|api_key\|secret\|token" | grep -v test
  # Should output nothing or only false positives
  ```

- [ ] Configuration examples show no real values
  ```bash
  grep -E "AKIA|password:|api_key:" .cloudctl.example.yaml
  # Should output nothing
  ```

## Before Every Pull Request

- [ ] Code review security checklist passed
  - [ ] No hardcoded credentials anywhere
  - [ ] No credentials in function parameters
  - [ ] No credentials in model fields
  - [ ] No credentials in test fixtures
  - [ ] Error messages are generic and safe
  - [ ] No credentials in documentation

- [ ] All security tests pass
  ```bash
  pytest tests/test_security.py -v
  # All tests should pass
  ```

- [ ] No new code touches credentials
  ```bash
  git diff main --name-only | xargs grep -l "password\|api_key\|secret\|token"
  # Should output nothing (excluding tests)
  ```

- [ ] Example code uses only fake data
  ```bash
  grep -r "AKIA\|BEGIN PRIVATE KEY" examples/
  # Should output nothing
  ```

- [ ] Documentation shows only generic examples
  ```bash
  grep -r "AKIA\|password:" docs/
  # Should output nothing
  ```

## Before Each Release

- [ ] Security tests pass in CI/CD
  - [ ] detect-secrets scan completed
  - [ ] TruffleHog scan completed
  - [ ] git-secrets scan completed
  - [ ] All security tests pass

- [ ] No secrets found in commit history
  ```bash
  git log --all --oneline | head -20
  git log -p | grep -i "password\|api_key" | head -0
  # Should find nothing
  ```

- [ ] SECURITY.md is up to date
  - [ ] All security practices documented
  - [ ] Examples show correct patterns
  - [ ] Anti-patterns clearly marked
  - [ ] Setup guide is comprehensive

- [ ] Pre-commit hooks are current
  - [ ] Hook script is up to date
  - [ ] All patterns are covered
  - [ ] False positives are handled
  - [ ] Documentation is clear

- [ ] GitHub Actions workflows include security
  - [ ] Secret scanning configured
  - [ ] Security tests in pipeline
  - [ ] All scans pass before release

- [ ] CHANGELOG documents security fixes
  ```bash
  grep -i "security\|secret\|credential" CHANGELOG.md
  # Recent releases should mention any security work
  ```

## For Code Reviewers

**Check these for every PR:**

### Architecture & Design

- [ ] Code doesn't handle credentials
- [ ] No credential parameters in functions
- [ ] No credential fields in models
- [ ] Subprocess isolation used correctly
- [ ] Configuration is separate from code

### Error Messages

- [ ] Error messages are generic
- [ ] No credentials in error output
- [ ] Helpful guidance provided
- [ ] No stack traces showing secrets
- [ ] Log messages are safe

### Tests

- [ ] All tests use fake credentials
- [ ] No real account IDs in fixtures
- [ ] No credentials in test setup
- [ ] Mocking prevents real calls
- [ ] Integration tests use dry-run

### Documentation

- [ ] Examples use dummy data only
- [ ] No real organization names
- [ ] No real account IDs
- [ ] Configuration templates are shown
- [ ] .cloudctl.example.yaml referenced

### Configuration

- [ ] No credentials in config files
- [ ] .gitignore includes local configs
- [ ] Environment variables are used
- [ ] Configuration precedence is correct
- [ ] Defaults are safe and sensible

### Questions to Ask

- [ ] Does this code touch any credentials?
- [ ] Could this leak environment variables?
- [ ] Are there any hardcoded values?
- [ ] Are error messages safe?
- [ ] Do tests use real data?
- [ ] Is documentation showing real values?

## For Release Managers

**Before releasing a new version:**

- [ ] All security tests pass
- [ ] No commits found with potential secrets
- [ ] SECURITY.md is up to date
- [ ] Release notes mention any security improvements
- [ ] Pre-commit hooks work correctly
- [ ] CI/CD security scanning is enabled
- [ ] Team is trained on security practices

### Release Checklist

```bash
# 1. Verify no secrets in history
git log -p | grep -i "password\|api_key\|secret\|token" | wc -l
# Should output 0

# 2. Run all security tests
pytest tests/test_security.py -v
# All tests should pass

# 3. Scan for secrets
detect-secrets scan
trufflehog filesystem .
# Should find no real secrets

# 4. Check documentation
grep -r "AKIA\|password:" docs/ examples/
# Should find nothing

# 5. Create release tag
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0

# 6. GitHub Actions will:
# - Run all security scans
# - Run test suite
# - Build and publish package
```

## Quarterly Security Audit

**Every 3 months, perform a full security audit:**

### Code Audit

- [ ] Search entire codebase for secret patterns
  ```bash
  grep -r "password\|secret\|api_key\|token" src/ --include="*.py"
  # Review any findings
  ```

- [ ] Check all test fixtures
  ```bash
  grep -r "AKIA\|password:" tests/
  # Should find no real credentials
  ```

- [ ] Review error handling
  ```bash
  grep -r "raise\|except\|error" src/ --include="*.py" | head -20
  # Verify error messages are safe
  ```

### Configuration Audit

- [ ] Check .gitignore is comprehensive
  ```bash
  cat .gitignore | grep -E "\.cloudctl|\.env|\.key|credentials"
  # Should have comprehensive exclusions
  ```

- [ ] Verify no local configs in git
  ```bash
  git ls-files | grep "\.cloudctl\.yaml\|\.env\|\.key"
  # Should output nothing
  ```

- [ ] Review documentation examples
  ```bash
  grep -r "export\|password\|api_key" docs/ examples/
  # Verify only safe examples are shown
  ```

### Process Audit

- [ ] Review security issues (none should exist!)
- [ ] Check pre-commit hook is working
- [ ] Verify CI/CD security scanning is enabled
- [ ] Confirm team understands security practices
- [ ] Update SECURITY.md if needed

### Tool Audit

- [ ] Update security scanning tools
  ```bash
  pip install --upgrade detect-secrets truffleHog
  ```

- [ ] Review pre-commit hook script
  - [ ] All patterns still relevant
  - [ ] No false positives
  - [ ] Documentation is clear

- [ ] Test security tools
  ```bash
  echo "password: test123" > /tmp/test.yaml
  detect-secrets scan /tmp/test.yaml
  # Should detect it
  rm /tmp/test.yaml
  ```

## Incident Response Checklist

**If a secret is accidentally committed:**

**IMMEDIATE (within 1 hour):**
- [ ] Stop all work
- [ ] Revert the commit (do NOT push)
  ```bash
  git revert <commit-hash>
  # OR
  git reset --hard HEAD~1
  ```
- [ ] Rotate the compromised credential immediately
- [ ] Verify rotation worked

**SHORT-TERM (within 1 day):**
- [ ] Clean git history
  ```bash
  git push --force-with-lease origin main
  ```
- [ ] Scan commit history for the secret
  ```bash
  git log -p --all | grep -c "secret-value"
  # Should be 0
  ```
- [ ] Notify team of the incident
- [ ] Document what happened
- [ ] Identify how it happened

**MEDIUM-TERM (within 1 week):**
- [ ] Update security processes to prevent recurrence
- [ ] Enhance pre-commit hook if needed
- [ ] Add additional CI/CD scanning if needed
- [ ] Train team on what went wrong
- [ ] Update SECURITY.md with lessons learned

**LONG-TERM:**
- [ ] Monitor for any misuse of credential
- [ ] Implement additional monitoring
- [ ] Quarterly review to ensure similar incident doesn't happen

## Team Training Checklist

**New team members should:**

- [ ] Read SECURITY.md fully
- [ ] Understand the architecture prevents credential storage
- [ ] Know how to set up pre-commit hooks
- [ ] Understand the configuration pattern
- [ ] Know what's a secret vs. what's safe
- [ ] Practice committing with fake credentials
- [ ] Know incident response procedures
- [ ] Have questions answered by security lead

**For each team member:**
```bash
# 1. Verify pre-commit hook is installed
ls -la .git/hooks/pre-commit

# 2. Test the hook with fake secret
echo "password: test123" > test.yaml
git add test.yaml
git commit -m "test"  # Should fail
# Remove test file and reset

# 3. Understand configuration
cat ~/.cloudctl.yaml
# Should have only safe settings

# 4. Verify environment is set
env | grep AWS
env | grep GCLOUD
# Credentials should be set
```

## Automated Checks

These checks run automatically:

### Pre-commit Hook

```bash
# Runs on every commit
.git/hooks/pre-commit
# Checks for: AWS keys, private keys, passwords, tokens, etc.
# Blocks commit if secrets found
```

### CI/CD Pipeline

```yaml
# On every push/PR
- detect-secrets scan
- trufflehog filesystem .
- pytest tests/test_security.py
- bandit src/  # Security linting
```

### Dependency Scanning

```bash
# Monthly
pip-audit  # Check for vulnerable dependencies
safety check  # Additional dependency security
```

## Documentation References

- [SECURITY.md](./SECURITY.md) - Complete security policy
- [SECURITY_SETUP.md](./SECURITY_SETUP.md) - Setup and tools guide
- [examples/safe_configuration.py](../examples/safe_configuration.py) - Safe patterns
- [tests/test_security.py](../tests/test_security.py) - Security test suite

## Quick Links

| Task | Command |
|------|---------|
| Install pre-commit hook | `chmod +x scripts/pre-commit-secrets && cp scripts/pre-commit-secrets .git/hooks/pre-commit` |
| Scan for secrets locally | `detect-secrets scan` |
| Test the hook | `echo "password: test" > test.txt && git add test.txt && git commit -m test` |
| Run security tests | `pytest tests/test_security.py -v` |
| Check git history | `git log -p \| grep -i password` |
| View configuration | `cat ~/.cloudctl.yaml` |
| Set environment | `export AWS_ACCESS_KEY_ID=... && export AWS_SECRET_ACCESS_KEY=...` |
| View this checklist | `cat docs/SECURITY_CHECKLIST.md` |

## Summary

CloudctlSkill maintains security through:

✅ **Architecture** - Code can't store credentials  
✅ **Configuration** - Secrets via environment only  
✅ **Automation** - Pre-commit and CI/CD checks  
✅ **Testing** - Security test suite  
✅ **Documentation** - Clear guidelines  
✅ **Training** - Team knowledge  
✅ **Monitoring** - Regular audits  
✅ **Response** - Incident procedures  

**Result: Secrets cannot leak to this repository.**
