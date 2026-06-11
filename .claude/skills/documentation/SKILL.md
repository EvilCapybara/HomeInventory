---
name: documentation
description: Write documentation - READMEs, API docs, code documentation, docstrings. Use when creating or updating these types of files, or explaining how a system works.
allowed-tools: Read, Write, Glob, Grep, Edit, LS, WebFetch, WebSearch
model: sonnet
metadata: 
  references:
    -**Only load when project contains OpenAPI.** See [OpenAPI specification](https://swagger.io/specification/)
---

When writing documentation:

1. Identify the scope of the documentaton:
  - Project-level (README)
  - Module-level (package / folder docs)
  - API-level (endpoints / functions)
  - Code-level (inline comments / docstrings)

2. If needed, inspect relevant context:
  - Read key files in the repository
  - Understand public interfaces and entry points
  - Identify usage patterns

3. Write documentation using a clear structure:

## Overview
One paragraph explaining what this component/system does

## Key concepts
- List and briefly explain main concepts or components
- Keep explanation simple and practical

## Usage
Provide examples of how to use the system:
- Code examples where relevant
- CLI commands if applicable
- API request/response examples if applicable

## Structure (if applicable)
- Describe important files or modules
- Explain respnsibilities of each part

## Notes
- Edge cases or important constraints
- Common pitfalls or assumptions

## Style rules
- Write in clear, simple English
- Prefer practical explanations over theory
- Avoid unnecessary verbosity
- Use code blocks for all examples
- Keep sections consistent and predictable