---
name: project-context
description: HomeInventory Telegram bot — Python, PostgreSQL + Elasticsearch + Redis, strict CLAUDE.md style guide
metadata:
  type: project
---

HomeInventory is a Telegram bot for household inventory management. Stack: Python 3.11+, pyTeleBot, SQLAlchemy ORM (PostgreSQL), Elasticsearch (optional, graceful fallback to ILIKE), Redis (optional caching, silently skipped when unavailable).

Key architectural rules from CLAUDE.md:
- Handlers must be thin (validation + routing only)
- Business logic in homemanager.py (singleton via @singleton decorator)
- DB access via database.py (MyPostgresConnection)
- All errors must be handled explicitly — no silent failures
- Structured logging required
- PEP8 strictly enforced
- Type hints required on all service/API functions
- No raw SQL in handlers; repository pattern for DB ops

**Why:** These rules are codified in CLAUDE.md and must be checked on every review.
**How to apply:** Flag any deviation from these conventions as a standards violation in reviews.
