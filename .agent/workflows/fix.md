---
description: Fix the current issue or error (Self-Healing)
---

# /fix - Smart Error Fixing Workflow

## Step 1: Get Error Context
- Ask user for error message OR
- Check terminal output for recent errors
- Check IDE diagnostics if available

## Step 2: Auto-Detect Error Type
Analyze error and match against known patterns:

### Node.js / JavaScript
| Error Pattern | Likely Cause | Quick Fix |
|---------------|--------------|-----------|
| `Cannot find module 'X'` | Missing dependency | `npm install X` |
| `ENOENT: no such file` | File path wrong | Check path, create file |
| `EADDRINUSE` | Port in use | Kill process or change port |
| `SyntaxError: Unexpected token` | Invalid JSON/JS syntax | Check syntax |
| `TypeError: X is not a function` | Wrong import/export | Check module exports |

### Python
| Error Pattern | Likely Cause | Quick Fix |
|---------------|--------------|-----------|
| `ModuleNotFoundError: No module named 'X'` | Missing package | `pip install X` |
| `IndentationError` | Wrong indentation | Fix spaces/tabs |
| `SyntaxError: invalid syntax` | Syntax error | Check line above |
| `FileNotFoundError` | File path wrong | Check path |
| `ImportError: cannot import name` | Circular import | Restructure imports |

### Git
| Error Pattern | Likely Cause | Quick Fix |
|---------------|--------------|-----------|
| `CONFLICT (content)` | Merge conflict | Resolve in file |
| `detached HEAD` | Not on branch | `git checkout main` |
| `fatal: not a git repository` | No git init | `git init` |

### TypeScript / Build
| Error Pattern | Likely Cause | Quick Fix |
|---------------|--------------|-----------|
| `TS2307: Cannot find module` | Missing types | `npm i -D @types/X` |
| `TS2339: Property does not exist` | Wrong type | Add type definition |
| `ESLint: Parsing error` | Config issue | Check .eslintrc |

## Step 3: Propose Solution
Based on detected pattern:
1. Show what was detected
2. Explain the likely cause
3. Propose specific fix command or code change

## Step 4: Apply Fix
If user confirms:
1. Execute the fix (run command or edit code)
2. Verify fix worked
3. If still broken, try next solution

## Step 5: Learn & Log
- Note the issue in CONTEXT.md if it's project-specific
- Suggest preventive measures if applicable
