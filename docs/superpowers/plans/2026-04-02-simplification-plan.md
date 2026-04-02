# Copertine Simplification Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Weaviate + FastAPI with PostgreSQL FTS and a single Next.js fullstack container, eliminating container restart requirements.

**Architecture:** Host-side Python scraper writes to PostgreSQL via localhost. Next.js API routes query PostgreSQL directly via `pg` pool over Docker `isagog-internal` network. No FastAPI, no Weaviate, no caching layer.

**Tech Stack:** PostgreSQL 17 (Italian FTS + unaccent), Next.js 15, `pg` npm package, `psycopg2` Python package, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-04-02-simplification-design.md`

---

## Chunk 1: PostgreSQL Setup & Migration Scripts

### Task 1: Create PostgreSQL setup DDL

**Files:**
- Create: `backend/src/setup_db.sql`

- [ ] **Step 1: Write the setup DDL script**

```sql
-- backend/src/setup_db.sql
-- Run as postgres superuser:
--   docker exec -i isagog-postgres psql -U postgres < setup_db.sql

-- 1. Create database and user
CREATE DATABASE copertine;
CREATE USER copertine_app WITH PASSWORD 'CHANGE_ME';
GRANT CONNECT ON DATABASE copertine TO copertine_app;

-- 2. Switch to the new database
\c copertine

-- 3. Extensions (requires superuser)
CREATE EXTENSION IF NOT EXISTS unaccent;

-- 4. Italian FTS with accent-insensitive search
CREATE TEXT SEARCH CONFIGURATION italian_unaccent (COPY = italian);
ALTER TEXT SEARCH CONFIGURATION italian_unaccent
    ALTER MAPPING FOR hword, hword_part, word
    WITH unaccent, italian_stem;

-- 5. Editions table
CREATE TABLE editions (
    id              SERIAL PRIMARY KEY,
    edition_id      VARCHAR(10) NOT NULL UNIQUE,
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

-- 6. Grant permissions to app user
GRANT USAGE ON SCHEMA public TO copertine_app;
GRANT SELECT, INSERT, UPDATE ON editions TO copertine_app;
GRANT USAGE, SELECT ON SEQUENCE editions_id_seq TO copertine_app;
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/setup_db.sql
git commit -m "feat: add PostgreSQL setup DDL with Italian FTS and unaccent"
```

---

### Task 2: Create Weaviate export script (runs on isanew)

**Files:**
- Create: `backend/src/export_weaviate.py`

- [ ] **Step 1: Write the export script**

```python
"""Export Copertine collection from Weaviate to JSONL + images archive."""
import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import weaviate
from dotenv import load_dotenv
from weaviate.classes.init import Auth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Weaviate fields that should be empty — warn if they contain data
EXPECTED_EMPTY_FIELDS = ("captionAIStr", "imageAIDeStr", "modelAIName")


def connect_weaviate() -> weaviate.WeaviateClient:
    """Connect to Weaviate using environment variables."""
    secrets_path = Path(__file__).parent.parent / ".secrets"
    load_dotenv(dotenv_path=secrets_path)

    weaviate_url = os.getenv("COP_WEAVIATE_URL", "http://localhost:8090")
    weaviate_api_key = os.getenv("COP_WEAVIATE_API_KEY", "")
    grpc_port = int(os.getenv("COP_WEAVIATE_GRPC_PORT", "50091"))

    if "://" in weaviate_url:
        _, rest = weaviate_url.split("://", 1)
        host = rest.split(":")[0]
        port = int(rest.split(":")[1]) if ":" in rest else 8090
    else:
        host = weaviate_url
        port = 8090

    kwargs = {"host": host, "port": port, "grpc_port": grpc_port}
    if weaviate_api_key and weaviate_api_key.strip():
        kwargs["auth_credentials"] = Auth.api_key(weaviate_api_key)

    client = weaviate.connect_to_local(**kwargs)
    logger.info("Connected to Weaviate at %s:%d", host, port)
    return client


def export_collection(client: weaviate.WeaviateClient, output_dir: Path, images_source: Path) -> None:
    """Export all objects from Copertine collection."""
    collection_name = os.getenv("COP_COPERTINE_COLLNAME", "Copertine")
    collection = client.collections.get(collection_name)

    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)

    jsonl_path = output_dir / "copertine_export.jsonl"
    count = 0
    warnings = 0
    images_copied = 0
    images_missing = 0

    with jsonl_path.open("w", encoding="utf-8") as f:
        for obj in collection.iterator():
            props = obj.properties

            # Check for unexpectedly non-empty AI fields
            for field in EXPECTED_EMPTY_FIELDS:
                value = props.get(field)
                if value and str(value).strip():
                    logger.warning(
                        "Non-empty dropped field %s in edition %s: %s",
                        field, props.get("editionId"), value,
                    )
                    warnings += 1

            # Parse edition date from editionDateIsoStr
            raw_date = props.get("editionDateIsoStr")
            if hasattr(raw_date, "isoformat"):
                edition_date = raw_date.strftime("%Y-%m-%d")
            else:
                edition_date = str(raw_date)[:10]

            record = {
                "edition_id": props.get("editionId", ""),
                "edition_date": edition_date,
                "caption": props.get("captionStr", ""),
                "kicker": props.get("kickerStr", ""),
                "image_filename": props.get("editionImageFnStr", ""),
            }

            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

            # Copy image file if it exists
            image_fn = record["image_filename"]
            if image_fn:
                src = images_source / image_fn
                dst = images_dir / image_fn
                if src.is_file():
                    if not dst.exists():
                        shutil.copy2(src, dst)
                    images_copied += 1
                else:
                    logger.warning("Image file not found: %s", src)
                    images_missing += 1

    # Write manifest
    manifest = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "collection": collection_name,
        "record_count": count,
        "images_copied": images_copied,
        "images_missing": images_missing,
        "warnings": warnings,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    logger.info("Export complete: %d records, %d images copied, %d missing, %d warnings",
                count, images_copied, images_missing, warnings)


def main():
    parser = argparse.ArgumentParser(description="Export Weaviate Copertine collection to JSONL + images")
    parser.add_argument("--output", type=str, default="./copertine_export",
                        help="Output directory (default: ./copertine_export)")
    parser.add_argument("--images-dir", type=str, default=None,
                        help="Source images directory (default: ../../images relative to this script)")
    args = parser.parse_args()

    output_dir = Path(args.output)
    images_source = Path(args.images_dir) if args.images_dir else Path(__file__).parent.parent.parent / "images"

    client = connect_weaviate()
    try:
        export_collection(client, output_dir, images_source)
    finally:
        client.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/export_weaviate.py
git commit -m "feat: add Weaviate export script for migration (runs on isanew)"
```

---

### Task 3: Create PostgreSQL import script (runs on isadue)

**Files:**
- Create: `backend/src/import_to_pg.py`

- [ ] **Step 1: Write the import script**

```python
"""Import Copertine JSONL export into PostgreSQL and copy images."""
import argparse
import json
import logging
import os
import shutil
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

UPSERT_SQL = """
INSERT INTO editions (edition_id, edition_date, caption, kicker, image_filename)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (edition_id) DO UPDATE SET
    caption = EXCLUDED.caption,
    kicker = EXCLUDED.kicker,
    image_filename = EXCLUDED.image_filename,
    updated_at = now();
"""


def import_data(input_dir: Path, images_dest: Path) -> None:
    """Import JSONL data into PostgreSQL and copy images."""
    secrets_path = Path(__file__).parent.parent / ".secrets"
    load_dotenv(dotenv_path=secrets_path)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)

    jsonl_path = input_dir / "copertine_export.jsonl"
    if not jsonl_path.is_file():
        logger.error("JSONL file not found: %s", jsonl_path)
        sys.exit(1)

    images_source = input_dir / "images"
    images_dest.mkdir(parents=True, exist_ok=True)

    # Copy images first
    images_copied = 0
    images_skipped = 0
    if images_source.is_dir():
        for img_file in images_source.iterdir():
            if img_file.is_file():
                dest_file = images_dest / img_file.name
                if dest_file.exists():
                    images_skipped += 1
                else:
                    shutil.copy2(img_file, dest_file)
                    images_copied += 1
    logger.info("Images: %d copied, %d skipped (already exist)", images_copied, images_skipped)

    # Import records
    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        count = 0
        errors = 0

        with jsonl_path.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    cur.execute(UPSERT_SQL, (
                        record["edition_id"],
                        record["edition_date"],
                        record["caption"],
                        record.get("kicker"),
                        record["image_filename"],
                    ))
                    count += 1
                except (json.JSONDecodeError, KeyError, psycopg2.Error) as e:
                    logger.error("Line %d: %s", line_num, e)
                    errors += 1
                    continue
        logger.info("Imported %d records, %d errors", count, errors)

        # Validate
        cur.execute("SELECT count(*) FROM editions")
        db_count = cur.fetchone()[0]
        logger.info("Total records in database: %d", db_count)

        # Check for records without matching image files
        cur.execute("SELECT image_filename FROM editions")
        missing_images = []
        for row in cur.fetchall():
            if not (images_dest / row[0]).is_file():
                missing_images.append(row[0])
        if missing_images:
            logger.warning("%d records have missing image files: %s",
                           len(missing_images), missing_images[:5])
        else:
            logger.info("All records have matching image files")

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Import Copertine JSONL export into PostgreSQL")
    parser.add_argument("--input", type=str, required=True,
                        help="Input directory containing copertine_export.jsonl and images/")
    parser.add_argument("--images-dest", type=str, default=None,
                        help="Destination images directory (default: ../../images relative to this script)")
    args = parser.parse_args()

    input_dir = Path(args.input)
    images_dest = Path(args.images_dest) if args.images_dest else Path(__file__).parent.parent.parent / "images"

    import_data(input_dir, images_dest)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/import_to_pg.py
git commit -m "feat: add PostgreSQL import script for migration (runs on isadue)"
```

---

## Chunk 2: Scraper Refactoring (Weaviate → PostgreSQL)

### Task 4: Update Python dependencies

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Update pyproject.toml**

Replace the `[tool.poetry.dependencies]` section. Remove `openai`, `together`, `weaviate-client`, `fastapi`, `uvicorn`. Add `psycopg2-binary`. Keep `python-dotenv`, `beautifulsoup4`, `pydantic`, `requests`.

```toml
[tool.poetry.dependencies]
python = "^3.11"
python-dotenv = "^1.0.1"
beautifulsoup4 = "^4.12.3"
pydantic = "^2.10.4"
requests = "^2.32.3"
psycopg2-binary = "^2.9.10"
```

- [ ] **Step 2: Install new dependencies**

```bash
cd backend && poetry lock && poetry install
```

- [ ] **Step 3: Commit**

```bash
git add backend/pyproject.toml backend/poetry.lock
git commit -m "refactor: replace weaviate/openai/fastapi deps with psycopg2-binary"
```

---

### Task 5: Refactor sd2.py — replace Weaviate with PostgreSQL

**Files:**
- Modify: `backend/src/sd2.py:1-552`

The scraper keeps all Directus API, image download, and CLI logic intact. Only the storage layer changes.

- [ ] **Step 1: Replace imports**

In `backend/src/sd2.py`, replace lines 1-21:

Old:
```python
""" Scrape Directus 2 """
import argparse
import logging
import mimetypes
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
import weaviate
import weaviate.classes as wvc
from dotenv import load_dotenv
from weaviate.classes.init import Auth

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from includes.weschema import COPERTINE_COLL_CONFIG
```

New:
```python
""" Scrape Directus 2 """
import argparse
import logging
import mimetypes
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import psycopg2
import requests
from dotenv import load_dotenv
```

- [ ] **Step 2: Remove WeaviateURLError class**

Delete lines 56-60 (the `WeaviateURLError` class) — no longer needed.

- [ ] **Step 3: Replace `_init_weaviate` and `_ensure_collection` with `_init_db`**

Replace methods `_init_weaviate` (lines 106-159) and `_ensure_collection` (lines 161-175) with:

```python
    def _init_db(self):
        """Initialize PostgreSQL connection."""
        database_url = self._get_required_env("DATABASE_URL")
        try:
            self.db_conn = psycopg2.connect(database_url)
            self.db_conn.autocommit = True
            self.logger.info("Connected to PostgreSQL")
        except psycopg2.Error:
            self.logger.exception("Failed to connect to PostgreSQL")
            raise
```

- [ ] **Step 4: Update `__init__` to call `_init_db` instead of `_init_weaviate`**

In `__init__` (line 68), change `self._init_weaviate()` to `self._init_db()`.

- [ ] **Step 5: Replace `_delete_existing_copertine` and `_store_in_weaviate` with `_upsert_edition`**

Delete `_delete_existing_copertine` (lines 341-391) and `_store_in_weaviate` (lines 487-510). Replace with:

```python
    def _upsert_edition(self, article: dict[str, Any], date: datetime, image_filename: str):
        """Upsert edition data into PostgreSQL."""
        edition_id = date.strftime("%d-%m-%Y")
        edition_date = date.strftime("%Y-%m-%d")

        try:
            with self.db_conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO editions (edition_id, edition_date, caption, kicker, image_filename)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (edition_id) DO UPDATE SET
                        caption = EXCLUDED.caption,
                        kicker = EXCLUDED.kicker,
                        image_filename = EXCLUDED.image_filename,
                        updated_at = now()
                    """,
                    (
                        edition_id,
                        edition_date,
                        article.get("referenceHeadline"),
                        article.get("articleKicker"),
                        image_filename,
                    ),
                )
            self.logger.info("Upserted edition %s", edition_id)
        except psycopg2.Error:
            self.logger.exception("Failed to upsert edition %s", edition_id)
```

- [ ] **Step 6: Update `_process_copertina` to use `_upsert_edition`**

In `_process_copertina` (lines 301-321), replace:

```python
        # Delete existing copertine with the same editionId
        deletion_successful = self._delete_existing_copertine(edition_id)
        if not deletion_successful:
            self.logger.error(f"Failed to delete existing objects with editionId {edition_id}. Aborting insertion to prevent duplicates.")
            return

        # Download image and store in Weaviate
        image_filename = self._download_and_save_image(article, date)
        if image_filename:
            self._store_in_weaviate(article, date, image_filename)
        else:
            self.logger.error(f"Failed to download image for article {article.get('id')}")
```

With:

```python
        # Download image and upsert to PostgreSQL
        image_filename = self._download_and_save_image(article, date)
        if image_filename:
            self._upsert_edition(article, date, image_filename)
        else:
            self.logger.error(f"Failed to download image for article {article.get('id')}")
```

- [ ] **Step 7: Update `cleanup` method**

Replace the Weaviate cleanup (lines 512-521) with:

```python
    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'db_conn') and self.db_conn:
            try:
                self.db_conn.close()
            except Exception:
                self.logger.exception("Error closing database connection")
            finally:
                self.db_conn = None
```

- [ ] **Step 8: Remove `_validate_weaviate_url` method**

Delete lines 101-104 (the `_validate_weaviate_url` method).

- [ ] **Step 8a: Clean up logger suppression**

In `_setup_logging`, replace:
```python
        for lib in ["weaviate", "httpx", "httpcore"]:
            logging.getLogger(lib).setLevel(logging.WARNING)
```
With:
```python
        logging.getLogger("urllib3").setLevel(logging.WARNING)
```

(The `requests` library uses `urllib3`, not `httpx`. Weaviate and httpcore are no longer used.)

- [ ] **Step 9: Verify scraper runs without errors**

```bash
cd backend && poetry run python src/sd2.py --date 2025-12-19
```

Expected: connects to PostgreSQL, fetches from Directus, downloads image, upserts record. (Requires PostgreSQL to be set up and DATABASE_URL in .secrets.)

- [ ] **Step 10: Commit**

```bash
git add backend/src/sd2.py
git commit -m "refactor: replace Weaviate storage with PostgreSQL upsert in scraper"
```

---

### Task 6: Update refreshbind.sh

**Files:**
- Modify: `refreshbind.sh`

- [ ] **Step 1: Simplify the script**

Replace entire contents of `refreshbind.sh`:

```bash
#!/bin/bash
/home/mema/code/copertinefull/backend/.venv/bin/python \
    /home/mema/code/copertinefull/backend/src/sd2.py -n 1
```

- [ ] **Step 2: Commit**

```bash
git add refreshbind.sh
git commit -m "fix: point refreshbind.sh to sd2.py, remove container restart"
```

---

### Task 7: Delete obsolete backend files

**Files:**
- Delete: `backend/src/includes/weschema.py`
- Delete: `backend/Dockerfile`

- [ ] **Step 1: Delete files**

```bash
git rm backend/src/includes/weschema.py
git rm backend/Dockerfile
```

- [ ] **Step 2: Commit**

```bash
git commit -m "chore: remove Weaviate schema and backend Dockerfile (copback eliminated)"
```

---

## Chunk 3: Frontend — Database Layer & Unified API Route

### Task 8: Update frontend dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Add pg, remove weaviate-ts-client**

```bash
cd frontend && pnpm add pg && pnpm add -D @types/pg && pnpm remove weaviate-ts-client
```

- [ ] **Step 2: Commit**

```bash
git add frontend/package.json frontend/pnpm-lock.yaml
git commit -m "refactor: replace weaviate-ts-client with pg in frontend deps"
```

---

### Task 9: Create PostgreSQL connection pool

**Files:**
- Create: `frontend/app/lib/db.ts`

- [ ] **Step 1: Write the db module**

```typescript
// frontend/app/lib/db.ts
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 5,
});

export default pool;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/lib/db.ts
git commit -m "feat: add PostgreSQL connection pool for Next.js API routes"
```

---

### Task 10: Rewrite unified API route

**Files:**
- Modify: `frontend/app/api/copertine/route.ts`

- [ ] **Step 1: Replace the entire route handler**

Replace the full contents of `frontend/app/api/copertine/route.ts`:

```typescript
// app/api/copertine/route.ts
import { NextRequest } from 'next/server';
import pool from '@/app/lib/db';
import { PAGINATION } from '@/app/lib/config/constants';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const q = searchParams.get('q')?.trim() || '';
  const offset = parseInt(searchParams.get('offset') || '0', 10);
  const limit = parseInt(searchParams.get('limit') || String(PAGINATION.ITEMS_PER_PAGE), 10);

  try {
    if (q.length > 0) {
      // Search mode: FTS with Italian stemming + unaccent
      const searchQuery = `
        SELECT edition_id, edition_date, caption, kicker, image_filename,
               ts_rank(search_vector, websearch_to_tsquery('italian_unaccent', $1)) AS rank
        FROM editions
        WHERE search_vector @@ websearch_to_tsquery('italian_unaccent', $1)
        ORDER BY rank DESC
        LIMIT $2 OFFSET $3
      `;
      const countQuery = `
        SELECT count(*) AS total
        FROM editions
        WHERE search_vector @@ websearch_to_tsquery('italian_unaccent', $1)
      `;

      const [dataResult, countResult] = await Promise.all([
        pool.query(searchQuery, [q, limit, offset]),
        pool.query(countQuery, [q]),
      ]);

      const total = parseInt(countResult.rows[0].total, 10);
      return Response.json({
        data: dataResult.rows.map(formatRow),
        pagination: { total, offset, limit, hasMore: offset + limit < total },
      });
    }

    // Browse mode: paginated, ordered by date descending
    const browseQuery = `
      SELECT edition_id, edition_date, caption, kicker, image_filename
      FROM editions
      ORDER BY edition_date DESC
      LIMIT $1 OFFSET $2
    `;
    const countQuery = `SELECT count(*) AS total FROM editions`;

    const [dataResult, countResult] = await Promise.all([
      pool.query(browseQuery, [limit, offset]),
      pool.query(countQuery),
    ]);

    const total = parseInt(countResult.rows[0].total, 10);
    return Response.json({
      data: dataResult.rows.map(formatRow),
      pagination: { total, offset, limit, hasMore: offset + limit < total },
    });
  } catch (error) {
    console.error('Database query failed:', error);
    return Response.json({ error: 'Failed to fetch data' }, { status: 500 });
  }
}

interface EditionRow {
  edition_id: string;
  edition_date: string;
  caption: string;
  kicker: string | null;
  image_filename: string;
}

function formatRow(row: EditionRow) {
  const editionDate = new Date(row.edition_date);
  return {
    extracted_caption: row.caption,
    kickerStr: row.kicker ?? '',
    date: editionDate.toLocaleDateString('it-IT'),
    isoDate: editionDate.toISOString(),
    filename: row.image_filename,
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/api/copertine/route.ts
git commit -m "feat: unified API route with PostgreSQL FTS (browse + search)"
```

---

### Task 11: Simplify constants

**Files:**
- Modify: `frontend/app/lib/config/constants.ts`

- [ ] **Step 1: Strip to essentials**

Replace the full contents of `frontend/app/lib/config/constants.ts`:

```typescript
// app/lib/config/constants.ts
export const PAGINATION = {
  ITEMS_PER_PAGE: 30,
} as const;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/lib/config/constants.ts
git commit -m "refactor: remove Weaviate/FastAPI/cache constants, keep only pagination"
```

---

### Task 13: Simplify search types

**Files:**
- Modify: `frontend/app/types/search.ts`

- [ ] **Step 1: Replace with minimal types**

Replace the full contents of `frontend/app/types/search.ts`:

```typescript
// app/types/search.ts
export interface SearchState {
  query: string;
  isSearching: boolean;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/types/search.ts
git commit -m "refactor: simplify search types — remove Weaviate/FastAPI shapes"
```

---

## Chunk 4: Frontend — Component Refactoring

### Task 14: Refactor CopertinaCard — remove imageCache dependency

**Files:**
- Modify: `frontend/app/components/copertina/CopertinaCard.tsx`

- [ ] **Step 1: Replace imageCache import with direct path**

In `CopertinaCard.tsx`, make these changes:

Remove line 5:
```typescript
import { imagePathCache } from '@/app/lib/services/imageCache';
```

Remove line 6:
```typescript
import Head from 'next/head';
```

Remove `currentOffset` from the interface (line 10):
```typescript
interface CopertinaCardProps {
  copertina: CopertineEntry;
  searchTerm?: string;
}
```

Replace line 52:
```typescript
  const imagePath = imagePathCache.getImagePath(copertina.filename, currentOffset);
```
With:
```typescript
  const imagePath = `/images/${copertina.filename}`;
```

Update the function signature (line 49):
```typescript
export default function CopertinaCard({ copertina, searchTerm }: CopertinaCardProps) {
```

Remove the `<Head>` preload block (lines 82-85):
```typescript
      <Head>
        <link rel="preload" href={imagePath} as="image" />
      </Head>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/components/copertina/CopertinaCard.tsx
git commit -m "refactor: remove imageCache dependency, use direct image path"
```

---

### Task 15: Refactor SearchSection — callbacks instead of CustomEvent

**Files:**
- Modify: `frontend/app/components/searchsection/SearchSection.tsx`

- [ ] **Step 1: Rewrite SearchSection with callback props**

Replace the full contents of `frontend/app/components/searchsection/SearchSection.tsx`:

```typescript
// app/components/searchsection/SearchSection.tsx
'use client';

import React, { useState } from 'react';
import { Search } from 'lucide-react';

interface SearchSectionProps {
  onSearch: (query: string) => void;
  onReset: () => void;
  isSearching: boolean;
  isSearchActive: boolean;
}

export default function SearchSection({ onSearch, onReset, isSearching, isSearchActive }: SearchSectionProps) {
  const [searchTerm, setSearchTerm] = useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = searchTerm.trim();
    if (trimmed.length < 2) return;
    onSearch(trimmed);
  };

  const handleReset = () => {
    setSearchTerm('');
    onReset();
  };

  const baseButtonClasses = "h-12 flex-1 sm:w-auto px-6 rounded-lg transition-colors duration-200 font-medium flex items-center justify-center";
  const activeButtonClasses = "bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200";
  const inactiveButtonClasses = "bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 cursor-not-allowed";
  const primaryButtonClasses = "bg-blue-500 hover:bg-blue-600 text-white";

  const canSearch = searchTerm.trim().length >= 2;

  return (
    <>
      <div className="bg-red-600 h-1 w-full" />
      <div className="w-full bg-white dark:bg-black border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <form onSubmit={handleSearch} className="space-y-6">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col sm:flex-row gap-4 items-center">
                <div className="flex-1 flex items-center gap-4">
                  <label htmlFor="search" className="text-lg font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">
                    Cerca
                  </label>
                  <div className="relative flex-1">
                    <input
                      type="text"
                      id="search"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full px-4 py-2 h-10 rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      placeholder="Inserisci il testo da cercare..."
                    />
                    <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                  </div>
                </div>
                <div className="sm:self-auto flex gap-2">
                  <button
                    type="submit"
                    disabled={isSearching || !canSearch}
                    className={`${baseButtonClasses} ${canSearch ? primaryButtonClasses : inactiveButtonClasses}`}
                  >
                    {isSearching ? 'Ricerca...' : 'Cerca'}
                  </button>
                  <button
                    type="button"
                    onClick={handleReset}
                    disabled={!isSearchActive}
                    className={`${baseButtonClasses} ${isSearchActive ? activeButtonClasses : inactiveButtonClasses}`}
                  >
                    Lista completa
                  </button>
                </div>
              </div>

            </div>
          </form>
        </div>
      </div>
      <div className="bg-red-600 h-1 w-full" />
    </>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/components/searchsection/SearchSection.tsx
git commit -m "refactor: replace CustomEvent with callback props in SearchSection"
```

---

### Task 16: Rewrite page.tsx — unified state management

**Files:**
- Modify: `frontend/app/copertine/page.tsx`

- [ ] **Step 1: Rewrite the page component**

Replace the full contents of `frontend/app/copertine/page.tsx`:

```typescript
"use client";

import React from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import CopertinaCard from "../components/copertina/CopertinaCard";
import PaginationControls from "../components/PaginationControls";
import SearchSection from "../components/searchsection/SearchSection";
import type { CopertineEntry, CopertineResponse, PaginationInfo } from "../types/copertine";
import { PAGINATION } from "@/app/lib/config/constants";

type SortField = "date" | "extracted_caption" | "relevance";
type SortDirection = "asc" | "desc";

export default function Home() {
  const [copertine, setCopertine] = React.useState<CopertineEntry[]>([]);
  const [originalOrder, setOriginalOrder] = React.useState<CopertineEntry[]>([]);
  const [searchQuery, setSearchQuery] = React.useState('');
  const [isSearching, setIsSearching] = React.useState(false);
  const [pagination, setPagination] = React.useState<PaginationInfo>({
    total: 0,
    offset: 0,
    limit: PAGINATION.ITEMS_PER_PAGE,
    hasMore: true,
  });
  const [sortField, setSortField] = React.useState<SortField>("date");
  const [sortDirection, setSortDirection] = React.useState<SortDirection>("desc");
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const isSearchActive = searchQuery.length > 0;

  // Unified fetch — browse or search depending on searchQuery
  const fetchData = React.useCallback(async (offset: number, query: string = '') => {
    try {
      setIsLoading(true);
      const baseUrl = window.location.origin;
      const params = new URLSearchParams({
        offset: String(offset),
        limit: String(PAGINATION.ITEMS_PER_PAGE),
      });
      if (query) {
        params.set('q', query);
      }

      const url = `${baseUrl}/copertine/api/copertine?${params}`;
      const response = await fetch(url);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to fetch data: ${response.status} ${errorText}`);
      }

      const data: CopertineResponse = await response.json();

      if (!data.data || !Array.isArray(data.data)) {
        throw new Error('Invalid data format received');
      }

      setCopertine(data.data);
      setOriginalOrder(data.data);
      setPagination(data.pagination);
      setError(null);

      if (!query) {
        setSortField('date');
      }
    } catch (err) {
      console.error('Fetch error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load data');
      setCopertine([]);
      setOriginalOrder([]);
      setPagination({ total: 0, offset: 0, limit: PAGINATION.ITEMS_PER_PAGE, hasMore: false });
    } finally {
      setIsLoading(false);
      setIsSearching(false);
    }
  }, []);

  // Initial load
  React.useEffect(() => {
    fetchData(0);
  }, [fetchData]);

  // Search handler
  const handleSearch = React.useCallback((query: string) => {
    setSearchQuery(query);
    setIsSearching(true);
    setSortField('relevance');
    setSortDirection('desc');
    fetchData(0, query);
  }, [fetchData]);

  // Reset handler
  const handleReset = React.useCallback(() => {
    setSearchQuery('');
    setSortField('date');
    setSortDirection('desc');
    fetchData(0);
  }, [fetchData]);

  // Page change
  const handlePageChange = React.useCallback((newPage: number) => {
    const newOffset = (newPage - 1) * PAGINATION.ITEMS_PER_PAGE;
    fetchData(newOffset, searchQuery);
  }, [fetchData, searchQuery]);

  // Sort handling
  const handleSort = (field: SortField) => {
    if (field === "relevance") {
      if (!isSearchActive) return;
      setSortField("relevance");
      setSortDirection("desc");
      return;
    }
    if (field === sortField) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const sortedCopertine = React.useMemo(() => {
    if (sortField === "relevance" && isSearchActive) {
      return originalOrder;
    }
    return [...copertine].sort((a, b) => {
      const modifier = sortDirection === "asc" ? 1 : -1;
      switch (sortField) {
        case "date": {
          const timeA = new Date(a.isoDate).getTime();
          const timeB = new Date(b.isoDate).getTime();
          return (timeA - timeB) * modifier;
        }
        case "extracted_caption":
          return a.extracted_caption.localeCompare(b.extracted_caption) * modifier;
        default:
          return 0;
      }
    });
  }, [copertine, sortField, sortDirection, originalOrder, isSearchActive]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <SearchSection
        onSearch={handleSearch}
        onReset={handleReset}
        isSearching={isSearching}
        isSearchActive={isSearchActive}
      />

      <section className="max-w-4xl mx-auto px-4 py-6">
        {error ? (
          <div className="flex flex-col items-center justify-center min-h-[400px]">
            <div className="max-w-lg text-center space-y-4">
              <div className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Unable to Connect to Database
              </div>
              <div className="text-gray-600 dark:text-gray-400">
                The database is currently unavailable. Please try again later.
              </div>
            </div>
          </div>
        ) : isLoading ? (
          <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
            <div className="relative w-16 h-16">
              <div className="absolute top-0 left-0 w-full h-full border-4 border-gray-200 dark:border-gray-700 rounded-full"></div>
              <div className="absolute top-0 left-0 w-full h-full border-4 border-blue-500 dark:border-blue-400 rounded-full animate-spin border-t-transparent"></div>
            </div>
            <div className="text-lg text-gray-600 dark:text-gray-400">
              Caricamento copertine...
            </div>
          </div>
        ) : (
          <div>
            <div className="mb-6 bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4">
              <PaginationControls
                currentPage={Math.floor(pagination.offset / pagination.limit) + 1}
                totalPages={Math.ceil(pagination.total / pagination.limit)}
                totalItems={pagination.total}
                onPageChange={handlePageChange}
                isLoading={isLoading}
              />

              <div className="flex gap-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => handleSort("date")}
                  className={`flex items-center gap-2 px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-blue-100 dark:hover:bg-gray-700 rounded-md transition-colors ${
                    sortField === "date" ? "bg-blue-100 dark:bg-gray-700" : ""
                  }`}
                >
                  Data
                  <div className="flex flex-col">
                    <ChevronUp className={`h-3 w-3 -mb-1 ${sortField === "date" && sortDirection === "asc" ? "text-blue-600 dark:text-blue-400" : "text-gray-400"}`} />
                    <ChevronDown className={`h-3 w-3 ${sortField === "date" && sortDirection === "desc" ? "text-blue-600 dark:text-blue-400" : "text-gray-400"}`} />
                  </div>
                </button>
                <button
                  onClick={() => handleSort("extracted_caption")}
                  className={`flex items-center gap-2 px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-blue-100 dark:hover:bg-gray-700 rounded-md transition-colors ${
                    sortField === "extracted_caption" ? "bg-blue-100 dark:bg-gray-700" : ""
                  }`}
                >
                  Titolo
                  <div className="flex flex-col">
                    <ChevronUp className={`h-3 w-3 -mb-1 ${sortField === "extracted_caption" && sortDirection === "asc" ? "text-blue-600 dark:text-blue-400" : "text-gray-400"}`} />
                    <ChevronDown className={`h-3 w-3 ${sortField === "extracted_caption" && sortDirection === "desc" ? "text-blue-600 dark:text-blue-400" : "text-gray-400"}`} />
                  </div>
                </button>
                {isSearchActive && (
                  <button
                    onClick={() => { setSortField("relevance"); setSortDirection("desc"); }}
                    className={`px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-blue-100 dark:hover:bg-gray-700 rounded-md transition-colors ${
                      sortField === "relevance" ? "bg-blue-100 dark:bg-gray-700" : ""
                    }`}
                  >
                    Rilevanza
                  </button>
                )}
              </div>
            </div>

            <div className="space-y-6">
              {sortedCopertine.map((copertina) => (
                <CopertinaCard
                  key={copertina.filename}
                  copertina={copertina}
                  searchTerm={searchQuery}
                />
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/copertine/page.tsx
git commit -m "refactor: unified state management, eliminate CustomEvent anti-pattern"
```

---

### Task 16a: Update layout.tsx — remove SearchSection rendering

**Files:**
- Modify: `frontend/app/copertine/layout.tsx`

- [ ] **Step 1: Remove SearchSection from layout**

`SearchSection` is now rendered inside `page.tsx` with callback props. The layout must stop rendering it (it would fail to compile — required props missing).

Replace the full contents of `frontend/app/copertine/layout.tsx`:

```typescript
import { Suspense } from "react";
import Header from "../components/header/Header";

export default function CopertineLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <Header />
      <main>
        <Suspense
          fallback={
            <div className="min-h-[calc(100vh-176px)] flex flex-col items-center justify-center">
              <div className="animate-pulse text-blue-700 text-lg">
                Caricamento...
              </div>
            </div>
          }
        >
          {children}
        </Suspense>
      </main>
    </>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/copertine/layout.tsx
git commit -m "refactor: move SearchSection from layout to page (needs callback props)"
```

---

### Task 16b: Delete obsolete frontend files

Now that all component imports of deleted files have been removed (CopertinaCard no longer imports imageCache, route.ts no longer imports weaviate, etc.), safely delete them.

**Files:**
- Delete: `frontend/app/api/search/route.ts`
- Delete: `frontend/app/api/weaviate/route.ts`
- Delete: `frontend/app/lib/services/weaviate.ts`
- Delete: `frontend/app/lib/services/cache.ts`
- Delete: `frontend/app/lib/services/imageCache.ts`
- Delete: `frontend/app/types/weaviate.ts`

- [ ] **Step 1: Delete all obsolete files**

```bash
cd /Volumes/2TBWDB/code/copertinefull
git rm frontend/app/api/search/route.ts
git rm frontend/app/api/weaviate/route.ts
git rm frontend/app/lib/services/weaviate.ts
git rm frontend/app/lib/services/cache.ts
git rm frontend/app/lib/services/imageCache.ts
git rm frontend/app/types/weaviate.ts
```

- [ ] **Step 2: Commit**

```bash
git commit -m "chore: remove Weaviate services, FastAPI search proxy, and caching layers"
```

---

## Chunk 5: Infrastructure & Final Cleanup

### Task 17: Update Docker Compose

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Replace docker-compose.yml**

Replace the full contents:

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

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "refactor: single-service Docker Compose, remove copback and internal network"
```

---

### Task 18: Update frontend Dockerfile

**Files:**
- Modify: `frontend/Dockerfile`

- [ ] **Step 1: Remove Weaviate env vars from Dockerfile**

In `frontend/Dockerfile`, remove lines 38-40:

```dockerfile
ENV WEAVIATE_SCHEME=http
ENV WEAVIATE_HOST=weaviate:8080
ENV WEAVIATE_COLLECTION=Copertine
```

And remove lines 24-25 (unused build arg):

```dockerfile
ARG COPERTINE_JSON_FILE
ENV COPERTINE_JSON_FILE=$COPERTINE_JSON_FILE
```

- [ ] **Step 2: Commit**

```bash
git add frontend/Dockerfile
git commit -m "refactor: remove Weaviate env vars and unused build arg from Dockerfile"
```

---

### Task 19: Update backend mytypes.py — remove Weaviate metadata

**Files:**
- Modify: `backend/src/includes/mytypes.py`

- [ ] **Step 1: Simplify Pydantic model**

Replace the full contents of `backend/src/includes/mytypes.py`:

```python
# includes/mytypes.py
from datetime import date

from pydantic import BaseModel, Field


class Copertina(BaseModel):
    edition_id: str = Field(..., description="Unique identifier for the edition (DD-MM-YYYY)")
    edition_date: date = Field(..., description="Publication date of the edition")
    image_filename: str = Field(..., description="Filename of the edition image")
    caption: str = Field(..., description="Headline text from Directus")
    kicker: str = Field("", description="Article kicker text from Directus")
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/includes/mytypes.py
git commit -m "refactor: simplify Copertina model — remove Weaviate metadata and AI fields"
```

---

### Task 20: Build and verify frontend locally

- [ ] **Step 1: Build the Next.js app**

```bash
cd frontend && pnpm build
```

Expected: build succeeds with no TypeScript errors. If there are import errors for deleted files, fix the remaining references.

- [ ] **Step 2: Fix any remaining import references**

Check for any lingering imports of deleted modules:

```bash
cd frontend && grep -r "weaviate\|imageCache\|imagePathCache\|cache\.ts\|FASTAPI_URL\|WEAVIATE" --include="*.ts" --include="*.tsx" app/
```

Expected: no results. If any found, update those files to remove dead imports.

- [ ] **Step 3: Commit any fixes**

```bash
git add -A frontend/
git commit -m "fix: remove remaining references to deleted Weaviate/cache modules"
```

---

### Task 21: Final verification commit

- [ ] **Step 1: Verify clean git state**

```bash
git status
git diff --stat HEAD~15..HEAD
```

- [ ] **Step 2: Tag the simplification milestone**

```bash
git tag -a v0.2.0 -m "Simplification: Weaviate+FastAPI replaced with PostgreSQL FTS"
```

---

## Deployment Checklist (Manual — on isadue)

These steps are run manually on the production server after pushing the code:

1. **Set up PostgreSQL** (one-time):
   ```bash
   docker exec -i isagog-postgres psql -U postgres < backend/src/setup_db.sql
   ```
   Then set the `copertine_app` password:
   ```bash
   docker exec -it isagog-postgres psql -U postgres -d copertine \
     -c "ALTER USER copertine_app WITH PASSWORD 'your-secure-password';"
   ```

2. **Add DATABASE_URL to backend/.secrets**:
   ```
   DATABASE_URL=postgresql://copertine_app:your-secure-password@localhost:5432/copertine
   ```

3. **Run Weaviate export on isanew**:
   ```bash
   cd /path/to/copertinefull/backend
   python src/export_weaviate.py --output ./copertine_export/
   tar czf copertine_export.tar.gz copertine_export/
   scp copertine_export.tar.gz mema@isadue:~/
   ```

4. **Import on isadue**:
   ```bash
   tar xzf copertine_export.tar.gz
   cd /home/mema/code/copertinefull/backend
   .venv/bin/python src/import_to_pg.py --input ~/copertine_export/
   ```

5. **Backfill the gap**:
   ```bash
   .venv/bin/python src/sd2.py -n 104
   ```

6. **Install Python deps**:
   ```bash
   cd backend && poetry install
   ```

7. **Build and deploy frontend**:
   ```bash
   cd /home/mema/code/copertinefull
   docker compose build copfront
   docker compose up -d copfront
   ```

8. **Set DB_PASSWORD in environment for Docker Compose**:
   Create `.env` file in project root (gitignored):
   ```
   DB_PASSWORD=your-secure-password
   ```

9. **Update cron** — verify `refreshbind.sh` points to `sd2.py` and has no restart commands.

10. **Verify**:
    - Browse: `curl http://localhost:3737/copertine/api/copertine?limit=5`
    - Search: `curl "http://localhost:3737/copertine/api/copertine?q=immigrazione&limit=5"`
    - Visit the web UI
