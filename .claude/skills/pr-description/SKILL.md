---
name: pr-description
description: Writes high-quality pull request description. Use when creating a PR, writing a PR, or when the user asks to summarize changes for a pull request. Requires git CLI.
allowed-tools: Bash, Read, Glob, Grep, LS, WebFetch
model: sonnet
metadata: 
  references:
    - Official GitHub guide [Creating PR template](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository)
---

When writing a PR description:

1. Run `git diff main...HEAD` to see all changes on this branch
2. Infer :
  - intent of the change
  - affected modules
  - risk level (low / medium / high)
  - whether migration or breaking changes exist

3. Write a description following below format.

## What
One sentence explaining what this PR does

## Why
Brief context on why this change is needed
- what problem it solves
- user or system impact

## Changes
- Bullet points of specific changes made
- Group related changes together (group by feature/module)
- Mention any files added, deleted or renamed

## Impact
- What parts of the system are affected
- Any behaviour changes for users or API consumers

## Risk
- Low / Medium / High
- Explain why (e.g. DB changes, auth logic, API changes)

## Testing
- How this was tested
- What should be checked by reviewer
- Any manual test steps (if relevant)

## Notes
- Edge cases or decisions worth highlighting
- Trade-offs or alternatives considered