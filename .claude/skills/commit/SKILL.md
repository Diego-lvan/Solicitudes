---
name: commit
description: Create conventional commits by grouping changed files by shared purpose.
argument-hint: "[optional message hint]"
allowed-tools: Bash, Read, Glob, Grep
---

# Conventional Commits

Create git commits following the Conventional Commits specification. Group changed files by shared purpose so that each commit is atomic and meaningful.

## Steps

1. Run `git status` to see all changed files (staged and unstaged).
2. Run `git diff HEAD` to understand what changed in each file.
3. Analyze the changes and group files by shared purpose. Each group = one logical unit of work:
   - All files related to a new feature → one `feat:` commit
   - Bug fixes in a specific area → one `fix:` commit
   - Config/infra changes → one `chore:` or `build:` commit
   - Documentation/spec changes → one `docs:` commit
   - Refactors → one `refactor:` commit
   - Tests → one `test:` commit
4. For each group:
   a. Stage only the files in that group using `git add <files>`
   b. Commit with a conventional commit message:
      ```
      type(optional-scope): short description

      Optional body explaining why, not what.
      ```
5. After all commits, run `git log --oneline -10` to show what was committed.

## Conventional Commit Types

| Type | When to use |
|------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code restructuring without behavior change |
| `perf` | Performance improvement |
| `chore` | Maintenance, dependency updates, tooling |
| `build` | Build system or CI/CD changes |
| `docs` | Documentation or specs only |
| `test` | Adding or updating tests |
| `style` | Formatting, whitespace (no logic change) |

## Rules

- Never use `git add .` or `git add -A` — always add specific files by name.
- Keep subject lines under 72 characters.
- Use the imperative mood: "add feature" not "added feature".
- If a file spans multiple purposes, include it in the most relevant commit.
- If all changes share the same purpose, a single commit is fine.
- Do not amend existing commits.
- If `$ARGUMENTS` was provided, use it as context for the commit message(s).
