---
name: commit-message
description: Write conventional commit messages for staged changes. Use when you see invokation with a slash command like /commit, or when committing changes in a branch, or ask me to use them directly. Requires git CLI.
allowed-tools: Bash, WebFetch
model: haiku
metadata: 
  references:
    - See [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
---

When writing a commit message:

1. Run `git diff --staged` to understand what is being committed.
2. If nothing is staged, fall back to `git diff` to infer changes
3. Write a commit message following below format:

## Format
<type>(optional scope): <shortSummary>

## Body (if needed)
- Explain what changed and why
- Focus on intent, not implementation details
- Mention important side effects or behaviour changes

## Allowed types
- feat: new feature
- fix: bug fix
- refactor: code restructuring without behaviour change
- perf: performance improvement
- chore: maintenance tasks
- docs: documentation only changes
- test: adding or updating tests

## Rules
- Keep the subject line under 72 characters
- Use imperative mood ("add", "fix", not "added", "fixed")
- Do not repeat code diff
- Be concise but meaningful