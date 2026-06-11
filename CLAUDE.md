## File Safety

Before copying or overwriting any file, always check whether the target file already exists. If it exists, show its current content and ask for explicit confirmation before overwriting. Never silently replace an existing file.

## Code Review

When asked to review code (ревьюить, сделай ревью, проверь код, code review), always use the `code-quality-reviewer` agent via the Agent tool — never the built-in `/code-review` skill. Specify exact file paths when invoking the agent.

After the agent completes, save its full output to `reviews/YYYY-MM-DD_<filename>.md` (use today's date and the reviewed file's name). Create the `reviews/` directory if it doesn't exist.

## Overview

A Telegram bot for managing household inventory. Users interact via bot commands; data is stored in PostgreSQL, full-text search runs on Elasticsearch (with graceful fallback to PostgreSQL ILIKE), and search results are cached in Redis.

## References

- Please read if you need more info: @README.md
- The database schema is defined in the @prisma/schema.prisma file. Reference it anytime you need to understand the structure of data stored in the database.

## Before starting

```bash
python utils/setup.py
```

## Running the Bot

**Docker Compose (recommended):**
```bash
cp .env.example .env  # fill in TELEGRAM_TOKEN and DATABASE_* credentials
docker-compose up -d
```

**Manually:**
```bash
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python main.py
```

## Running Tests

```bash
python -m pytest tests/ -v
# or a single file:
python -m pytest tests/test_cache.py -v
```

Tests use mocks only — no live PostgreSQL, Elasticsearch, or Redis required.

## Architecture

```
api.py  (Telegram bot, FSM conversation state)
  └─► homemanager.py  (business logic, singleton)
        ├─► database.py  (SQLAlchemy CRUD + raw ALTER TABLE)
        ├─► elastic.py   (Elasticsearch index management)
        └─► cache.py     (Redis get/set/invalidate)
```

**Entry point:** `main.py` — instantiates `Bot` and `HomeManager`, then calls `bot.infinity_polling()`.

**Conversation state machine (FSM) lives in `api.py`:**
- `Bot.user_states` is a dict keyed by `user_id` with keys `step`, `data`, `action`.
- Each command handler sets `user_states[user_id]` to start a flow.
- `_process_step()` advances the FSM, validates input, and calls `complete_answering()` when all steps are done.
- `complete_answering()` dispatches to `HomeManager` based on `action`, then clears the user's state.

**Inline keyboard callbacks** use the format `"step:value"` (e.g., `"type:text"`), parsed in `handle_callbacks()`. Special prefixes: `deletecol:<name>`, `renamecol:<name>`, `skip`.

**`HomeManager` is a singleton** (via the `@singleton` decorator). It owns the single `MyPostgresConnection` instance and calls `elastic.*` and `cache.*` directly after each mutation to keep all three stores in sync.

**Dynamic schema:** custom columns are added/dropped/renamed via raw `ALTER TABLE` SQL in `database.py` (`add_new_col`, `delete_col`, `rename_col`). Protected built-in columns are listed in `PROTECTED_COLS` in `homemanager.py`.

**Search flow (`/search`):**
1. Check Redis cache (`search:{user_id}:{query}`).
2. Query Elasticsearch `household_items` index with `multi_match` + `fuzziness: AUTO`, filtered by `owner_id`.
3. If ES unavailable or no results → fall back to PostgreSQL ILIKE across `name`, `brand`, `model`, `category`, `storage_place`.
4. Cache results in Redis with a 5-minute TTL; invalidate on any add/update/delete for that user.

**ORM models** (`models.py`): `Users` (telegram_id, username, first_name) and `AllHouseholdItems` (name, brand, model, category, quantity, storage_place, belong_to, owner_id FK). The `Task` model and RQ task queue (`tasks.py`) exist for background exports but are largely stubbed out.

## Environment Variables

Set in `.env` (copy from `.env.example`):

| Variable | Notes |
|---|---|
| `TELEGRAM_TOKEN` | Required |
| `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT` | Required |
| `SQLALCHEMY_DATABASE_URI` | Auto-built from above if omitted |
| `ELASTICSEARCH_URL` | Optional; leave empty to disable ES and fall back to ILIKE |
| `REDIS_URL` | Optional; defaults to `redis://localhost:6379`; silently skipped if unavailable |

## Key Conventions

- **Callback data format:** `"step:value"` — parsed by splitting on `":"` with `maxsplit=1`.
- **Column slugification:** user-provided column labels are lowercased, spaces→underscores, non-alphanumeric characters stripped (see `Bot._slugify_key()`).
- **`HomeManager` import is deferred** inside handler methods (e.g., `from homemanager import HomeManager`) to avoid circular imports with `api.py`.
- **No Alembic** — schema migrations are raw SQL; adding Alembic is noted as a future TODO in several places.

## Code Style

- Prefer clear, explicit code over "clever" or overly abstract solutions
- Follow PEP8 strictly (including naming, spacing, imports)
- Use type hints for all service layer and API functions
- Use comments sparingly. Only comment complex or confusing code
- Keep functions small and single-purpose (one responsibility per function)
- Avoid business logic inside handlers; move it to service layer
- Repository pattern must be used for all database operations (no raw SQL in handlers)
- All DB writes must be explicitly committed (no implicit commits)
- Prefer dependency injections for DB sessions and external services
- All external interactions (Postgres, Elasticsearch, Telegram API) must be isolated in dedicated modules
- Avoid hardcoding configuration values (use environment variables via config module)
- Use structured logging
- All errors must be handled explicitly; no silent failures 
  - Log errors with context (user_id, operation, payload where relevant)

- Docker environment must be treated as production-like:
  - All services must communicate via docker-compose network
  - Do not use localhost inside containers; use service names instead

- Keep Telegram bot handlers thin
  - handler -> validation + routing only
  - services -> business logic
  - repositories -> DB access

- Prefer explicit over implicit control flow (avoid hidden side effects)

- Any new feature must include:
  - input validation
  - error handling
  - logging