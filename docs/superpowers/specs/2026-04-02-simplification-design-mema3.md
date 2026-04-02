# Copertine Simplification — Design Spec (mema3 Production)

**Date**: 2026-04-02
**Status**: In Progress — DB + images migration COMPLETE, code changes pending
**Goal**: Replace Weaviate + FastAPI with PostgreSQL full-text search + unified Next.js fullstack app on **mema3**
**Supersedes**: `2026-04-02-simplification-design.md` (original, isadue-targeted) + `2026-04-02-simplification-plan-mema3.md` (environment addendum)

---

## 1. Context

The Copertine project archives Il Manifesto newspaper front pages — images, headlines, and kickers scraped daily from the Directus CMS. The current architecture uses Weaviate (vector DB) exclusively for BM25F keyword search, FastAPI as a search middleware, and Next.js for the frontend. This is overengineered: Weaviate has no vector embeddings, FastAPI duplicates what Next.js API routes can do, and the system requires container restarts after scraping to bust caches.

## 2. Target Architecture

```
Daily 5:00 AM (Cron on mema3 host)
  └─ sd2.py -n 1
       ├─ Directus API → article metadata
       ├─ Download image → /home/mema/code/copertinefull/images/
       └─ UPSERT into PostgreSQL (editions table)
            via 127.0.0.1:5432 (host → mema-postgres container)

User visits /copertine
  └─ copfront (Next.js, single container)
       └─ GET /api/copertine?offset=0&limit=30       → browse (date desc)
       └─ GET /api/copertine?q=immigrazione&limit=30  → FTS search
       └─ PostgreSQL (mema-postgres) via mema_docker_compose_mema_network

Images served by Nginx directly from /home/mema/code/copertinefull/images/
```

**Hard requirement satisfied**: No container restarts needed. Scraper writes to PostgreSQL, Next.js reads from PostgreSQL — new content is immediately available on the next request.

## 3. Infrastructure Topology (mema3)

| Component | Detail |
|-----------|--------|
| Host machine | `mema3`, user `mema` |
| Project root | `/home/mema/code/copertinefull/` |
| PostgreSQL container | `mema-postgres` (already running) |
| Docker network | `mema_docker_compose_mema_network` (external, pre-existing) |
| Images directory | `/home/mema/code/copertinefull/images/` (already populated) |
| Scraper DB access | `127.0.0.1:5432` (host-side, not via container network) |
| Frontend DB access | `mema-postgres:5432` (container-to-container via `mema_docker_compose_mema_network`) |

### Secrets Management

**Single source of truth**: `.secrets` at the **project root** — `/home/mema/code/copertinefull/.secrets`

This file is `gitignore`d and **must never be committed**. It is shared by:
- The host-side scraper (`sd2.py` loads it via `python-dotenv`)
- `docker-compose.yml` (referenced as `env_file: .secrets`)

```bash
# /home/mema/code/copertinefull/.secrets
DIRECTUS_API_TOKEN=<token>
DB_PASSWORD=<password>
DATABASE_URL=postgresql://copertine_app:${DB_PASSWORD}@127.0.0.1:5432/copertine
```

> **Note**: `backend/.secrets.example` is a template only. The actual secrets live at the **project root** `.secrets`, not inside `backend/`.

## 4. PostgreSQL Schema (ALREADY DEPLOYED)

> ✅ **This section is complete.** The `copertine` database, `copertine_app` user, `editions` table, and all indexes are already created on `mema-postgres`. Data has been imported and the images folder is populated. **No schema or migration actions are required.**

For reference, the deployed schema:

```sql
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE TEXT SEARCH CONFIGURATION italian_unaccent (COPY = italian);
ALTER TEXT SEARCH CONFIGURATION italian_unaccent
    ALTER MAPPING FOR hword, hword_part, word
    WITH unaccent, italian_stem;

CREATE TABLE editions (
    id              SERIAL PRIMARY KEY,
    edition_id      VARCHAR(10) NOT NULL UNIQUE,  -- 'DD-MM-YYYY'
    edition_date    DATE NOT NULL,
    caption         TEXT NOT NULL,
    kicker          TEXT,
    image_filename  TEXT NOT NULL,
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('italian_unaccent', coalesce(caption, '')), 'A') ||
        setweight(to_tsvector('italian_unaccent', coalesce(kicker, '')), 'B')
    ) STORED,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_editions_date ON editions (edition_date DESC);
CREATE INDEX idx_editions_search ON editions USING GIN (search_vector);
```

- `search_vector` is a generated column — auto-updates when caption/kicker change
- Caption weighted `A` (higher rank), kicker weighted `B`
- Italian stemming + accent removal via `unaccent` extension
- `edition_id` (DD-MM-YYYY) unique constraint for idempotent upserts
- Connection requires superuser for initial DDL; `copertine_app` has SELECT/INSERT/UPDATE on `editions`

## 5. Scraper Changes (`backend/src/sd2.py`)

### What stays
- Directus API calls, image download, filename generation, CLI arg parsing
- Runs on mema3 host from `backend/.venv/` (NOT inside a container)
- Reads `.secrets` from **project root**: `load_dotenv(Path(__file__).parents[2] / '.secrets')`

### What changes
- Remove `weaviate` / `weaviate.classes` imports and all `WeaviateURLError` / Weaviate init logic
- Remove `from includes.weschema import COPERTINE_COLL_CONFIG`
- Add `import psycopg2` dependency
- Replace Weaviate init/store/delete methods with `_init_db()` and `_upsert_edition()`
- `DATABASE_URL` comes from `.secrets` at project root (see Section 3)

### DB connection (host-side scraper)

```python
from pathlib import Path
from dotenv import load_dotenv

# Load secrets from project root
load_dotenv(Path(__file__).parents[2] / '.secrets')

DATABASE_URL = os.environ['DATABASE_URL']
# DATABASE_URL = postgresql://copertine_app:<password>@127.0.0.1:5432/copertine
```

### Upsert logic

```sql
INSERT INTO editions (edition_id, edition_date, caption, kicker, image_filename)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (edition_id) DO UPDATE SET
    caption = EXCLUDED.caption,
    kicker = EXCLUDED.kicker,
    image_filename = EXCLUDED.image_filename,
    updated_at = now();
```

Fully idempotent — safe to re-run for any date.

## 6. Frontend Architecture

### Unified API Route

Replace three routes (`/api/copertine`, `/api/search`, `/api/weaviate`) with one:

```
GET /api/copertine?offset=0&limit=30          → browse (date desc)
GET /api/copertine?q=immigrazione&limit=30    → FTS search (ranked by relevance)
```

**Note**: The Next.js app uses `basePath: '/copertine'` in `next.config.ts`, so the full client-side URL is `/copertine/api/copertine?...`. The API route file itself lives at `app/api/copertine/route.ts`.

### Search queries (parameterized — no string interpolation)

```typescript
// Browse mode
const browseQuery = `
  SELECT edition_id, edition_date, caption, kicker, image_filename
  FROM editions ORDER BY edition_date DESC LIMIT $1 OFFSET $2
`;
const { rows } = await pool.query(browseQuery, [limit, offset]);

// Search mode
const searchQuery = `
  SELECT edition_id, edition_date, caption, kicker, image_filename,
         ts_rank(search_vector, websearch_to_tsquery('italian_unaccent', $1)) AS rank
  FROM editions
  WHERE search_vector @@ websearch_to_tsquery('italian_unaccent', $1)
  ORDER BY rank DESC LIMIT $2 OFFSET $3
`;
const { rows } = await pool.query(searchQuery, [q, limit, offset]);
```

### Database connection (`frontend/app/lib/db.ts`) — NEW FILE

```typescript
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 5,
});

export default pool;
```

`DATABASE_URL` is injected into the container via `docker-compose.yml` (see Section 7). `pg.Pool` handles reconnection automatically — no startup health gate needed beyond the existing HTTP healthcheck.

### Component changes

- **Eliminate `CustomEvent` anti-pattern**: `page.tsx` owns `searchQuery` state, passes `onSearch(query)` and `onReset()` callbacks to `SearchSection`
- **Remove `imagePathCache` from `CopertinaCard`**: replace with direct path construction: `/images/${copertina.filename}` — no cache layer needed
- **No caching layer**: PostgreSQL responds in <1ms for ~500 rows with proper indexes
- **Response shape unchanged**: `CopertineEntry[]` with `pagination` metadata

### Frontend dependencies
- Add: `pg`, `@types/pg`
- Remove: `weaviate-ts-client`

## 7. Docker Compose (mema3-corrected)

```yaml
services:
  copfront:
    build:
      context: ./frontend
    image: copfront:0.2.0
    container_name: copfront
    user: "1000:1000"
    env_file: .secrets          # PROJECT ROOT .secrets — provides DB_PASSWORD
    environment:
      - NODE_ENV=production
      - PORT=3000
      - HOSTNAME=0.0.0.0
      - DATABASE_URL=postgresql://copertine_app:${DB_PASSWORD}@mema-postgres:5432/copertine
    ports:
      - "127.0.0.1:3737:3000"
    volumes:
      - /home/mema/code/copertinefull/images:/images:ro
    command: ["node", "server.js"]
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=64m
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    networks:
      - mema_docker_compose_mema_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3000/"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  mema_docker_compose_mema_network:
    external: true
```

**Removed from original**: `copback` service, `copertine-internal` network, `isagog-internal` network, `depends_on`.

Key mema3 corrections vs. original spec:
- Network: `mema_docker_compose_mema_network` (not `isagog-internal`)
- DB host in `DATABASE_URL`: `mema-postgres` (not `isagog-postgres`)
- Images volume: `/home/mema/code/copertinefull/images` (not `/srv/projects/mema/...`)
- `env_file: .secrets` — reads `DB_PASSWORD` from project root `.secrets`

## 8. Cron (`refreshbind.sh`) — FIX REQUIRED

Current `refreshbind.sh` calls non-existent `scrape2.py` and performs container restarts. Replace entirely:

```bash
#!/bin/bash
/home/mema/code/copertinefull/backend/.venv/bin/python \
    /home/mema/code/copertinefull/backend/src/sd2.py -n 1
```

No container restart. Scraper writes directly to PostgreSQL; Next.js reads on the next request.

## 9. File Inventory

### To Create
| File | Purpose |
|------|---------|
| `frontend/app/lib/db.ts` | PostgreSQL connection pool (Section 6) |

### To Modify
| File | Changes Required |
|------|-----------------|
| `backend/src/sd2.py` | Remove weaviate client → add psycopg2; load `.secrets` from project root (`parents[2]`) |
| `backend/pyproject.toml` | Remove `weaviate-client`, `openai`, `together`, `fastapi`, `uvicorn`; add `psycopg2-binary` |
| `.secrets` (project root) | Add `DB_PASSWORD` and `DATABASE_URL`; remove Weaviate vars — **never commit** |
| `frontend/app/api/copertine/route.ts` | Rewrite: Weaviate GraphQL → `pg` parameterized queries; add `?q=` FTS search |
| `frontend/app/components/searchsection/SearchSection.tsx` | Replace `CustomEvent` dispatch with `onSearch`/`onReset` callback props |
| `frontend/app/copertine/page.tsx` | Own `searchQuery` state; remove `CustomEvent` listeners; replace Weaviate error text |
| `frontend/app/copertine/layout.tsx` | Remove `SearchSection` rendering (moved to `page.tsx` with callback props) |
| `frontend/app/components/copertina/CopertinaCard.tsx` | Remove Weaviate error text; replace `imagePathCache` import with `/images/${filename}` |
| `frontend/app/types/search.ts` | Simplify types, remove Weaviate-specific fields |
| `frontend/app/lib/config/constants.ts` | Remove `FASTAPI`/`WEAVIATE`/`CACHE` constants |
| `frontend/package.json` | Remove `weaviate-ts-client`; add `pg` + `@types/pg` |
| `frontend/Dockerfile` | Remove Weaviate env vars |
| `docker-compose.yml` | Single `copfront` service; mema3 network/DB/image-path corrections (Section 7) |
| `refreshbind.sh` | Strip restarts; call `sd2.py -n 1` only (Section 8) |

### To Delete
| File | Reason |
|------|--------|
| `frontend/app/api/search/route.ts` | Merged into `/api/copertine` |
| `frontend/app/api/weaviate/route.ts` | Unused passthrough |
| `frontend/app/lib/services/weaviate.ts` | No more Weaviate |
| `frontend/app/lib/services/cache.ts` | No caching needed |
| `frontend/app/lib/services/imageCache.ts` | Unnecessary |
| `backend/src/includes/weschema.py` | Weaviate schema |
| `backend/Dockerfile` | No more `copback` container |
| `frontend/app/types/weaviate.ts` | Weaviate-specific types |

### Already Done / Untouched
| File | Status |
|------|--------|
| `backend/src/setup_db.sql` | ✅ Created and executed on mema3 |
| `backend/src/export_weaviate.py` | ✅ Used for migration (isanew → mema3), no longer needed |
| `backend/src/import_to_pg.py` | ✅ Used for migration, data already imported |
| `backend/src/includes/mytypes.py` | Untouched — still useful for scraper validation |
| `backend/src/includes/utils.py` | Untouched — utility functions |
| `backend/src/includes/prompts.py` | Untouched — unused AI prompts, not part of this refactor |
| `frontend/app/components/PaginationControls.tsx` | Untouched — works as-is |
| `frontend/app/components/header/Header.tsx` | Untouched — works as-is |
| `frontend/app/layout.tsx` | Untouched — root layout |
| `frontend/next.config.ts` | Untouched — keeps `basePath: '/copertine'` |

## 10. Production Deployment Checklist (mema3)

1. **Verify DB**: `docker exec mema-postgres psql -U copertine_app -d copertine -c "SELECT count(*) FROM editions;"` — confirms data is present
2. **Update `.secrets`** at project root: ensure `DB_PASSWORD` and `DATABASE_URL` are set; remove old Weaviate vars
3. **Update `backend/src/sd2.py`**: replace Weaviate with psycopg2 (Section 5)
4. **Update `frontend/`**: create `lib/db.ts`, rewrite `route.ts`, update components (Sections 6 + 9)
5. **Update `docker-compose.yml`**: apply mema3-corrected config (Section 7)
6. **Fix `refreshbind.sh`**: strip restarts, point to `sd2.py -n 1` (Section 8)
7. **Build and deploy**: `docker compose build copfront && docker compose up -d copfront`
8. **Verify connectivity**: `docker exec copfront wget -qO- http://localhost:3000/copertine` → expect HTML
9. **Test FTS**: `curl "http://localhost:3737/copertine/api/copertine?q=immigrazione"` → expect JSON results
10. **Verify cron**: manually run `refreshbind.sh` once, confirm new row in `editions` table
