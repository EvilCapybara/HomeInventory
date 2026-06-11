---
name: codebase-onboarding
description: Helps new developers understand the system works, incliding architecture, data flow and project structure. Use when explaining how components interact or how the project is organized.
allowed-tools: Read, Glob, Grep, LS
model: sonnet
metadata: 
  references:
    - See [README.md](HomeInventory/README.md)
---

When onboarding a new developer into the codebase:

1. Identify the scope of the system:
  - High-level architecture (backend, services, integrations)
  - Core domains (e.g. models, database, notifications)
  - External integrations (MCP, Telegram, Postgres, Redis, Elasticsearch)

2. Explore the codebase structure:
  - Use directory structure to understand major modules
  - Identify entry points (main application, API server, bot handlers)
  - Locate service layer, repository layer, and data models

3. Trace main data flows:
  - Request -> handler -> service -> database
  - Background jobs or event-driven flows if present
  - External API or MCP integrations

4. Identify key components and responsibilities:
  - What each module is responsible for
  - How modules depend on each other
  - Where business logic is concentrated

5. Write onboarding documentation using a clear structure:

## System overview
One paragraph explaining what the system does and its purpose

## Architecture
- High-level description of system components
- How data flows between them
- Key architectural patterns used (layered, event-driven, etc.)

## Core modules
- List main modules and their responsibilities
- Explain how they interact

## Data flow
- Step-by-step explanation of how a request or event moves through the system
- Include important internal transitions (handler -> service -> DB)

## External integrations
- Describe integrations such as MCP servers, Telegram bot, databases, Redis caches
- Explain their role in the system

## How to navigate the codebase
- Where to start reading the code
- Key files or directories to focus on first
- Suggested entry points for new developers

## Notes
- Important constraints or design decisions
- Common confusion points for newcomers
- Areas that require extra attention when modifying the system

## Style rules
- Be clear and structured
- Prefer simple explanations over deep theory
- Focus on practical understanding of the system
- Use examples when helpful
- Avoid unnecessary detail unless relevant to understanding architecture