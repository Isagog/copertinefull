# Copertine Simplification — Design Spec

**Date**: 2026-04-02
**Status**: Approved
**Goal**: Replace Weaviate + FastAPI with PostgreSQL full-text search + unified Next.js fullstack app

---

## 1. Context

The Copertine project archives Il Manifesto newspaper front pages — images, headlines, and kickers scraped daily from the Directus CMS. The current architecture uses Weaviate (vector DB) exclusively for BM25F keyword search, FastAPI as a search middleware, and Next.js for the frontend. This is overengineered: Weaviate has no vector embeddings, FastAPI duplicates what Next.js API routes can do, and the system requires container restarts after scraping to bust caches.

## 2. Target Architecture

```
Daily 5:00 AM (Cron on isadue)
  └─ sd2.py -n 1
       ├─ Directus API → article metadata
       ├─ Download image → /images/
       └─ UPSERT into PostgreSQL (editions table)

User visits /copertine
  └─ copfront (Next.js, single container)
       └─ GET /api/copertine?offset=0&limit=30      → browse (date desc)
       └─ GET /api/copertine?q=immigrazione&limit=30 → FTS search
       └─ PostgreSQL (isagog-postgres) via isagog-internal network

Images served by Nginx directly from /images/
```

**Hard requirement satisfied**: No container restarts needed. Scraper writes to PostgreSQL, Next.js reads from PostgreSQL — new content is immediately available on the next request.

## 3. Infrastructure Topology

| Machine | Alias | Role |
|---------|-------|------|
| isanew | — | Current Weaviate host (source for migration) |
| isadue | mema3 | Production: PostgreSQL (`isagog-postgres`), Next.js (`copfront`), cron scraper |

### Docker Networks

| Network | Purpose |
|---------|---------|
| `isagog-internal` | Container-to-container (copfront → isagog-postgres) |
| `isagog-loopback` | Host access (scraper → PostgreSQL via localhost:5432) |
| `isagog-external` | Outbound (scraper → Directus API) |

### PostgreSQL

- Container: `isagog-postgres` (postgres:17-alpine), already running on isadue
- Database: `copertine` (new)
- Application user: `copertine_app` (SELECT, INSERT, UPDATE on `editions`)
- **Setup requires superuser** for `CREATE EXTENSION unaccent` and `CREATE TEXT SEARCH CONFIGURATION` — run `setup_db.sql` as `postgres` user, then grant privileges to `copertine_app`

## 4. PostgreSQL Schema

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
- Italian stemming + accent removal (`unaccent` extension)
- `edition_id` (DD-MM-YYYY) unique constraint for deduplication
- `updated_at` tracks when records were last upserted, useful for debugging

### Dropped Weaviate fields

The following Weaviate properties are intentionally **not** migrated to PostgreSQL:

| Field | Reason for dropping |
|-------|-------------------|
| `testataName` | Always "Il Manifesto" — hardcoded in frontend if needed |
| `captionAIStr` | Never populated (always empty/null in Weaviate) |
| `imageAIDeStr` | Never populated (always empty/null in Weaviate) |
| `modelAIName` | Never populated (always empty/null in Weaviate) |

The export script (`export_weaviate.py`) will log a warning if any of these fields contain non-empty data, so nothing is silently lost.

## 5. Scraper Changes

The scraper (`backend/src/sd2.py`) stays as a host-side Python script run by cron.

### What stays
- Directus API calls, image download, filename generation, CLI arg parsing
- Runs from `backend/.venv/`
- `.secrets` for `DIRECTUS_API_TOKEN`

### What changes
- Replace `weaviate` client → `psycopg2`
- Replace Weaviate init/store/delete methods → `_init_db()`, `_upsert_edition()`
- Add `DATABASE_URL` to `.secrets` (format: `DATABASE_URL=postgresql://copertine_app:PASSWORD@localhost:5432/copertine`). This file is gitignored and must never be committed.
- Connects via localhost:5432 (isagog-loopback)

### Deduplication
```sql
INSERT INTO editions (edition_id, edition_date, caption, kicker, image_filename)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (edition_id) DO UPDATE SET
    caption = EXCLUDED.caption,
    kicker = EXCLUDED.kicker,
    image_filename = EXCLUDED.image_filename,
    updated_at = now();
```

**Note**: `refreshbind.sh` currently calls `backend/src/scrape2.py` (which does not exist). This is a known bug. The fix replaces it with `sd2.py`, the actual scraper file.

### Cron (`refreshbind.sh`)
```bash
#!/bin/bash
/home/mema/code/copertinefull/backend/.venv/bin/python \
    /home/mema/code/copertinefull/backend/src/sd2.py -n 1
```

No container restart.

## 6. Migration Strategy

### Phase A: Export from isanew (`export_weaviate.py`)

Standalone script, runs on isanew. Connects to Weaviate using `COP_WEAVIATE_URL` and `COP_WEAVIATE_GRPC_PORT` from environment (defaults: localhost:8090, gRPC 50091 — verify actual ports on isanew before running).

Produces:
```
copertine_export/
├── copertine_export.jsonl    (one JSON line per edition)
├── images/                   (all cover images)
└── manifest.json             (counts for verification)
```

JSONL format:
```json
{"edition_id": "19-12-2025", "edition_date": "2025-12-19", "caption": "...", "kicker": "...", "image_filename": "il-manifesto_2025-12-19_slug.jpg"}
```

### Phase B: Import on isadue (`import_to_pg.py`)

Reads JSONL, copies images to production `/images/` dir (skips existing), upserts records into PostgreSQL. Validates counts and image file presence.

### Phase C: Backfill gap (Dec 19 2025 → Apr 2 2026)

```bash
python sd2.py -n 104
```

Fetches each date from Directus, idempotent via ON CONFLICT.

### Transfer workflow
```
On isanew:
  python export_weaviate.py --output ./copertine_export/
  tar czf copertine_export.tar.gz copertine_export/

Transfer:
  scp copertine_export.tar.gz mema@isadue:~/

On isadue:
  tar xzf copertine_export.tar.gz
  python import_to_pg.py --input ./copertine_export/
  python sd2.py -n 104
```

## 7. Frontend Architecture

### Unified API Route

Replace three routes (`/api/copertine`, `/api/search`, `/api/weaviate`) with one:

```
GET /api/copertine?offset=0&limit=30          → browse (date desc)
GET /api/copertine?q=immigrazione&limit=30    → FTS search (ranked by relevance)
```

**Note**: The Next.js app uses `basePath: '/copertine'` in `next.config.ts`, so the full client-side URL is `/copertine/api/copertine?...`. The API route file itself lives at `app/api/copertine/route.ts`.

### Search query (parameterized)

All queries use `$1`, `$2` placeholders via `pg` — never string interpolation:

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

### Database connection (`lib/db.ts`)
```typescript
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 5,
});

export default pool;
```

`pg.Pool` handles connection failures gracefully — if PostgreSQL is temporarily unavailable, individual queries will fail but the pool will automatically reconnect on the next attempt. No startup health gate needed beyond the existing HTTP healthcheck.

### Component changes

- **Eliminate `CustomEvent` anti-pattern**: `page.tsx` owns `searchQuery` state, passes `onSearch(query)` and `onReset()` callbacks to `SearchSection`
- **Remove `imagePathCache` from `CopertinaCard`**: currently imports from `imageCache.ts` for path resolution. Replace with direct path construction: `/images/${copertina.filename}` — no cache layer needed
- **No caching layer**: PostgreSQL responds in <1ms for ~500 rows with proper indexes
- **Response shape unchanged**: `CopertineEntry[]` with `pagination` metadata

### Dependencies
- Add: `pg`, `@types/pg`
- Remove: `weaviate-ts-client`

## 8. Docker Compose (Simplified)

```yaml
services:
  copfront:
    build:
      context: ./frontend
    image: copfront:0.2.0
    container_name: copfront
    user: "1000:1000"
    environment:
      - NODE_ENV=production
      - PORT=3000
      - HOSTNAME=0.0.0.0
      - DATABASE_URL=postgresql://copertine_app:${DB_PASSWORD}@isagog-postgres:5432/copertine
    ports:
      - "127.0.0.1:3737:3000"
    volumes:
      - /srv/projects/mema/copertinefull/images:/images:ro
    command: ["node", "server.js"]
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=64m
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    networks:
      - isagog-internal
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3000/"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  isagog-internal:
    external: true
```

Removed: `copback` service, `copertine-internal` network, `depends_on`.

## 9. File Inventory

### Created
| File | Purpose |
|------|---------|
| `backend/src/export_weaviate.py` | Standalone Weaviate dump (runs on isanew) |
| `backend/src/import_to_pg.py` | Import JSONL + images into PostgreSQL (runs on isadue) |
| `backend/src/setup_db.sql` | PostgreSQL setup DDL |
| `frontend/app/lib/db.ts` | PostgreSQL connection pool |

### Modified
| File | Changes |
|------|---------|
| `backend/src/sd2.py` | Weaviate → psycopg2 |
| `backend/pyproject.toml` | Remove weaviate-client/openai/together/fastapi/uvicorn, add psycopg2-binary |
| `backend/.secrets` | Add DATABASE_URL, remove Weaviate vars |
| `frontend/app/api/copertine/route.ts` | Weaviate GraphQL → pg queries, add ?q= search |
| `frontend/app/components/searchsection/SearchSection.tsx` | CustomEvent → callback props |
| `frontend/app/copertine/page.tsx` | Own search state, remove CustomEvent listeners, update Weaviate error messages to generic DB errors |
| `frontend/app/copertine/layout.tsx` | Remove `SearchSection` rendering (moved to page.tsx which passes callback props) |
| `frontend/app/components/copertina/CopertinaCard.tsx` | Remove Weaviate error text, replace `imagePathCache` import with direct path construction |
| `frontend/app/types/search.ts` | Simplify types |
| `frontend/app/lib/config/constants.ts` | Remove FASTAPI/WEAVIATE/CACHE constants |
| `frontend/package.json` | Remove weaviate-ts-client, add pg + @types/pg |
| `frontend/Dockerfile` | Remove Weaviate env vars |
| `docker-compose.yml` | Single service, PostgreSQL env |
| `refreshbind.sh` | Just `sd2.py -n 1`, no restart |

### Deleted
| File | Reason |
|------|--------|
| `frontend/app/api/search/route.ts` | Merged into /api/copertine |
| `frontend/app/api/weaviate/route.ts` | Unused passthrough |
| `frontend/app/lib/services/weaviate.ts` | No more Weaviate |
| `frontend/app/lib/services/cache.ts` | No caching needed |
| `frontend/app/lib/services/imageCache.ts` | Unnecessary |
| `backend/src/includes/weschema.py` | Weaviate schema |
| `backend/Dockerfile` | No more copback container |
| `frontend/app/types/weaviate.ts` | Weaviate-specific types |

### Untouched
| File | Reason |
|------|--------|
| `backend/src/includes/mytypes.py` | Still useful for scraper validation |
| `backend/src/includes/utils.py` | Utility functions |
| `backend/src/includes/prompts.py` | AI prompts (unused, but not part of this refactor) |
| `frontend/app/components/PaginationControls.tsx` | Works as-is |
| `frontend/app/components/header/Header.tsx` | Works as-is |
| `frontend/app/layout.tsx` | Works as-is (root layout) |
| `frontend/next.config.ts` | No changes needed (keeps `basePath: '/copertine'`) |
