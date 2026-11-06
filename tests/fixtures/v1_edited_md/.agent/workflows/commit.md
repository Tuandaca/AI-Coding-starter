# Commit Workflow

## Purpose
Standardize commit messages and version control practices.

## Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no logic change
- `refactor`: Code restructuring
- `perf`: Performance improvement
- `test`: Adding/modifying tests
- `chore`: Maintenance tasks

### Examples
```
feat(auth): add OAuth2 Google provider

Implement Google OAuth2 authentication flow with PKCE support.

Closes #123
```

```
fix(api): handle null user in profile endpoint

Add null check before accessing user preferences.
Returns 404 if user not found instead of 500.

Fixes #456
```

## Branch Naming
- `feature/<ticket>-<description>`
- `fix/<ticket>-<description>`
- `hotfix/<ticket>-<description>`
- `chore/<description>`

## PR Requirements
- Descriptive title and body
- Linked issue/ticket
- Tests passing
- Code review approved
- No merge conflicts
- Changelog updated (if applicable)
