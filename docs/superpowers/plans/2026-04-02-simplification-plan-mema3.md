
# Copertine Simplification Implementation Plan (mema3 Production)

**Goal:** Replace Weaviate + FastAPI with PostgreSQL FTS and a single Next.js fullstack container on the **mema3** production host.

**Architecture:** * **Scraper:** Runs on the host (mema3), writes to PostgreSQL via `127.0.0.1:5432`.
* **Frontend:** Next.js container (`copfront`) queries PostgreSQL via the container alias `mema-postgres` over the `mema_docker_compose_mema_network`.

---

## Chunk 1: Database & Migration

### Task 1: Initialize PostgreSQL Schema
**Files:** `backend/src/setup_db.sql`
* **Action:** Create the `copertine` database, `copertine_app` user, and the `editions` table with Italian `tsvector` columns.
* **Command:** ```bash
    docker exec -i mema-postgres psql -U postgres < backend/src/setup_db.sql
    ```

### Task 2: Import Existing Backup
**Files:** `backend/src/import_to_pg.py`
* **Context:** The backup `backups/copertine_export.tar.gz` is already on **mema3**.
* **Action:** 1.  Extract: `tar xzf backups/copertine_export.tar.gz -C backups/`
    2.  Import: `poetry run python backend/src/import_to_pg.py --input backups/copertine_export/`

---

## Chunk 2: Scraper Refactoring

### Task 3: Update `sd2.py` for mema3
* **Storage Shift:** Remove `weaviate` client calls; replace with `psycopg2` connection to `127.0.0.1`.
* **Connection String:** `postgresql://copertine_app:${DB_PASSWORD}@127.0.0.1:5432/copertine`
* **Logic:** Use `INSERT ... ON CONFLICT (edition_id) DO UPDATE` to ensure idempotency.

---

## Chunk 3: Frontend & Infrastructure

### Task 4: Unified API Route
**Files:** `frontend/app/api/copertine/route.ts`
* **Action:** Rewrite to query PostgreSQL. Use `websearch_to_tsquery('italian_unaccent', $1)` for the search functionality to replace Weaviate's vector search.

### Task 5: Docker Compose Update
**Files:** `docker-compose.yml`
* **Network Config:**
    ```yaml
    services:
      copfront:
        networks:
          - mema_docker_compose_mema_network
        environment:
          - DATABASE_URL=postgresql://copertine_app:${DB_PASSWORD}@mema-postgres:5432/copertine

    networks:
      mema_docker_compose_mema_network:
        external: true
    ```

---

## Chunk 4: Cleanup & Cron

### Task 6: Update `refreshbind.sh`
* **Action:** Strip out all `docker restart` or `docker exec` commands. 
* **New Content:**
    ```bash
    #!/bin/bash
    /home/mema/code/copertinefull/backend/.venv/bin/python \
        /home/mema/code/copertinefull/backend/src/sd2.py -n 1
    ```

---

## Final Production Checklist (mema3)

1.  **DB Check:** `docker ps` confirms `mema-postgres` is running.
2.  **Connectivity:** Ensure the `copfront` container can resolve `mema-postgres`.
3.  **Secrets:** Update `.secrets` in the project root (shared by backend and frontend) with the new `DB_PASSWORD`.
4.  **Build:** `docker compose build copfront && docker compose up -d`.
