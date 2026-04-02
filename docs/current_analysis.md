# Copertine Full Stack — Architecture Analysis

## 1. Scraping

Two scrapers exist with overlapping purpose.

### `backend/src/sd2.py` — Directus API scraper (primary)

- Hits `https://directus.ilmanifesto.it/items/articles` with a Bearer token
- Filters for the cover article by position and date
- Extracts:
  - `referenceHeadline` → caption text
  - `articleKicker` → article summary/kicker
  - `articleFeaturedImage` → image ID, resolved to a Directus CDN asset URL
- Downloads the image to `/home/mema/code/copertinefull/images/` with filename pattern `il-manifesto_{YYYY-MM-DD}_{slug}.{ext}`
- Deduplicates by `editionId` (format `DD-MM-YYYY`): deletes existing record before inserting
- Inserts into Weaviate

### `backend/experiments/scrape2.py` — HTML scraper (experimental/backup)

- Parses `https://ilmanifesto.it/edizioni/il-manifesto/il-manifesto-del-{DD-MM-YYYY}` directly via BeautifulSoup4 + httpx
- Extracts headline from `<h1/h2/h3>`, body from `p.body-ns-1`, author from `span.font-serif`
- Supports date-range backfill and optional JSON export
- Lives in `experiments/` — intended as backup, not production

**Current issue**: `refreshbind.sh` calls `backend/src/scrape2.py` which does not exist (the file is at `backend/experiments/scrape2.py`). The 5 AM run today used a previous version pointing to `sd2.py`.

---

## 2. Storage

### Weaviate — collection `Copertine`

| Field | Type | Indexed |
|---|---|---|
| `editionId` | text | filterable, used as unique key (DD-MM-YYYY) |
| `editionDateIsoStr` | date | sortable, RFC3339 |
| `captionStr` | text | BM25F searchable |
| `kickerStr` | text | BM25F searchable |
| `editionImageFnStr` | text | stored only (image filename) |
| `testataName` | text | stored only ("Il Manifesto") |
| `captionAIStr` | text | BM25F searchable — **never populated** |
| `imageAIDeStr` | text | BM25F searchable — **never populated** |
| `modelAIName` | text | stored only — **never populated** |

**Critical**: vectorizer is set to `none`. There are no vector embeddings. Weaviate is used purely as a BM25F keyword search engine with date filtering.

### Filesystem

Images stored at `/home/mema/code/copertinefull/images/`, served by Nginx directly:

```nginx
location /images/ {
    alias /home/mema/code/copertinefull/images/;
    expires max;
    Cache-Control: public, max-age=31536000, immutable;
}
```

---

## 3. Backend — FastAPI (`copback`)

- Single relevant endpoint: `POST /api/v1/copertine?search=query&mode=literal|fuzzy`
- Queries Weaviate with BM25F and returns matching `Copertina` objects
- Container `copback`, port 8383
- **Currently not running** (container does not exist)

---

## 4. Frontend — Next.js 15 (`copfront`)

### Two query paths (inconsistent)

| Operation | Path |
|---|---|
| Browse (paginated) | Next.js API route → Weaviate directly |
| Search | Next.js API route → FastAPI (`copback`) → Weaviate |

### API routes

- `GET /copertine/api/copertine?offset=N&limit=30` — paginated browse, sorted by date descending, queries Weaviate directly
- `POST /copertine/api/search` — proxies to FastAPI with `{ query, mode }`
- `GET /copertine/api/weaviate` — raw Weaviate GraphQL passthrough

### Components

- `CopertinaCard` — displays one cover: image (click to fullscreen), headline, kicker, date; highlights search terms
- `SearchSection` — search form, minimum 2 chars, dispatches a browser `CustomEvent` on result
- `copertine/page.tsx` — main page; listens for `searchResults` / `resetToFullList` custom events; handles sort (date asc/desc, caption, relevance) and pagination (30 per page)

**Note**: component communication uses browser `window.dispatchEvent(CustomEvent)` rather than React state or context — an anti-pattern.

### Services

- `lib/services/weaviate.ts` — initializes Weaviate v3 client using `WEAVIATE_SCHEME` and `WEAVIATE_HOST` env vars
- `lib/services/imageCache.ts` — caches image filenames in localStorage, auto-invalidates at 5:10 AM
- `lib/services/cache.ts` — TTL-based cache for paginated data

---

## 5. Infrastructure

### Docker Compose (`/home/mema/code/copertinefull/docker-compose.yml`)

```
copfront  → port 3737:3000  — Next.js frontend
copback   → port 8383:8383  — FastAPI backend
```

Both connect to `isagog-internal` network (where Weaviate lives) and a private `copertine-internal` network.

Image volume: `/home/mema/code/copertinefull/images` mounted read-only in `copfront`, read-write in `copback`.

**Currently**: neither `copfront` nor `copback` containers exist.

### Cron (`/etc/crontab` for user `mema`)

```
0  5 * * 2-7  /home/mema/code/copertinefull/refreshbind.sh >> scrape2.log 2>&1
25 5 * * 2-7  /usr/bin/docker restart mema-demo_prod-frontend-1 mema-demo_dev-frontend-1 >> scrape2.log 2>&1
```

`refreshbind.sh` runs the scraper, then does `docker compose stop copfront && docker compose start copfront`.

The second cron line restarts `mema-demo_prod-frontend-1` and `mema-demo_dev-frontend-1` — **these containers do not exist**.

---

## 6. Complete Data Flow

```
Cron 5:00 AM
  └─ refreshbind.sh
       └─ sd2.py (or scrape2.py)
            ├─ Directus API → article metadata
            ├─ Download image → /images/il-manifesto_{date}_{slug}.jpg
            ├─ Delete existing Weaviate record for editionId
            └─ Insert new Weaviate record

Cron 5:25 AM
  └─ docker restart copfront  (frontend cache reset)

User visits /copertine
  └─ copfront (Next.js)
       ├─ Browse: API route → Weaviate (direct) → paginated cards
       └─ Search: API route → copback (FastAPI) → Weaviate (BM25F) → cards with highlights

Images served by Nginx directly from /images/
```

---

## 7. Known Issues

| Issue | Impact |
|---|---|
| `refreshbind.sh` calls `backend/src/scrape2.py` (does not exist) | Next scrape run will fail |
| `copfront` and `copback` containers do not exist | Frontend and backend are down |
| Second cron restarts `mema-demo_*` containers that do not exist | Cron error, no effect |
| Weaviate failed at 5AM (Connection refused) | Today's cover not scraped |
| `captionAIStr`, `imageAIDeStr`, `modelAIName` always empty | Dead schema fields |
| Browse queries Weaviate directly, search goes via FastAPI | Inconsistent, unnecessary complexity |
| Browser `CustomEvent` for React state | Anti-pattern |

---

## 8. Architectural Assessment

**Core mismatch**: Weaviate is a heavy vector database deployed as a dedicated service, but the application uses it exclusively for BM25F keyword search — a use case that SQLite FTS5 or PostgreSQL full-text search would handle with zero additional infrastructure.

The fields `captionAIStr` and `imageAIDeStr` suggest an original intent to add AI-generated descriptions and semantic vector search, but this was never implemented.

### Option A — Simplify (drop Weaviate)

Replace Weaviate with SQLite + FTS5 (or PostgreSQL). The `copback` FastAPI service becomes unnecessary — Next.js API routes query the database directly. No separate vector DB container to manage, no connection failures, trivial backup.

**Best if**: keyword search is sufficient and semantic search is not planned.

### Option B — Complete the vector search vision

Enable a vectorizer in Weaviate (e.g., `text2vec-openai` or `text2vec-transformers`). During scraping, populate `captionAIStr` and `imageAIDeStr` using an LLM or vision model. This enables real semantic queries like *"copertine sull'immigrazione"* without exact keyword matches.

**Best if**: semantic/conceptual search over the archive is a desired feature.

### Shared cleanup regardless of direction

- Consolidate to one scraper (`sd2.py` via Directus API is more reliable than HTML scraping)
- Fix `refreshbind.sh` path
- Fix or remove the second cron line
- Unify browse and search through a single backend (either FastAPI or Next.js API routes, not both)
- Replace browser `CustomEvent` with React Context or a state management library
