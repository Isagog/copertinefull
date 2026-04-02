"""
import_to_pg.py - Weaviate Backup -> PostgreSQL Import Script

Reads the copertine_export.jsonl file exported from the old Weaviate instance
and upserts every record into the PostgreSQL `editions` table.

Usage (from repo root on mema3):
    # 1. Extract the archive first (skip if already done):
    tar xzf backups/copertine_export.tar.gz -C backups/

    # 2. Run the importer:
    cd backend
    uv run python src/import_to_pg.py --input ../backups/copertine_export/

Environment variables (from project-root .secrets):
    PSQL_COPERTINE_USER  - PostgreSQL username (e.g. copertine_app)
    PSQL_COPERTINE_PASS  - PostgreSQL password
    PSQL_COPERTINE_HOST  - PostgreSQL host (default: 127.0.0.1)
    PSQL_COPERTINE_PORT  - PostgreSQL port (default: 5432)
    PSQL_COPERTINE_DB    - PostgreSQL database name (default: copertine)

    Alternatively, set DATABASE_URL directly and the above are ignored.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------
UPSERT_SQL = """
INSERT INTO editions (edition_id, edition_date, caption, kicker, image_filename)
VALUES (%(edition_id)s, %(edition_date)s, %(caption)s, %(kicker)s, %(image_filename)s)
ON CONFLICT (edition_id) DO UPDATE
    SET caption        = EXCLUDED.caption,
        kicker         = EXCLUDED.kicker,
        image_filename = EXCLUDED.image_filename,
        updated_at     = now()
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_env() -> str:
    """Load project-root .secrets and return a DATABASE_URL connection string."""
    # Project root is three levels up: backend/src/ -> backend/ -> project-root
    project_root = Path(__file__).parent.parent.parent
    secrets_path = project_root / ".secrets"
    if secrets_path.exists():
        load_dotenv(dotenv_path=secrets_path, override=True)
        log.info("Loaded secrets from %s", secrets_path)
    else:
        load_dotenv()  # fall back to environment variables

    # Prefer an explicit DATABASE_URL
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    # Build from individual PSQL_COPERTINE_* variables
    user     = os.getenv("PSQL_COPERTINE_USER")
    password = os.getenv("PSQL_COPERTINE_PASS")
    host     = os.getenv("PSQL_COPERTINE_HOST", "127.0.0.1")
    port     = os.getenv("PSQL_COPERTINE_PORT", "5432")
    dbname   = os.getenv("PSQL_COPERTINE_DB", "copertine")

    if not user or not password:
        log.error(
            "No database credentials found. "
            "Set PSQL_COPERTINE_USER + PSQL_COPERTINE_PASS (or DATABASE_URL) "
            "in the project-root .secrets file."
        )
        sys.exit(1)

    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


def find_jsonl(input_dir: Path) -> Path:
    """Locate the .jsonl file inside input_dir."""
    candidates = list(input_dir.glob("*.jsonl"))
    if not candidates:
        log.error("No .jsonl file found in %s", input_dir)
        sys.exit(1)
    if len(candidates) > 1:
        log.warning("Multiple .jsonl files found; using %s", candidates[0])
    return candidates[0]


def parse_record(raw: str) -> dict | None:
    """Parse one JSONL line into a dict compatible with UPSERT_SQL."""
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.warning("Skipping malformed JSON line: %s", exc)
        return None

    # Validate required keys
    required = ("edition_id", "edition_date", "caption", "image_filename")
    missing = [k for k in required if not obj.get(k)]
    if missing:
        log.warning(
            "Skipping record missing fields %s: %s",
            missing,
            obj.get("edition_id", "??"),
        )
        return None

    return {
        "edition_id":     obj["edition_id"],
        "edition_date":   obj["edition_date"],        # 'YYYY-MM-DD' - psycopg2 coerces to DATE
        "caption":        obj["caption"],
        "kicker":         obj.get("kicker") or None,  # nullable
        "image_filename": obj["image_filename"],
    }


# ---------------------------------------------------------------------------
# Main import logic
# ---------------------------------------------------------------------------

def import_jsonl(db_url: str, jsonl_path: Path, batch_size: int = 200) -> None:
    log.info("Connecting to PostgreSQL ...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    stats = {"processed": 0, "upserted": 0, "skipped": 0, "errors": 0}
    batch: list[dict] = []

    def flush(b: list[dict]) -> None:
        if not b:
            return
        try:
            psycopg2.extras.execute_batch(cur, UPSERT_SQL, b, page_size=batch_size)
            conn.commit()
            stats["upserted"] += len(b)
        except Exception as exc:
            conn.rollback()
            log.error("Batch commit failed (%d records rolled back): %s", len(b), exc)
            stats["errors"] += len(b)

    log.info("Reading %s ...", jsonl_path)
    with jsonl_path.open(encoding="utf-8") as fh:
        for raw_line in fh:
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            stats["processed"] += 1
            record = parse_record(raw_line)
            if record is None:
                stats["skipped"] += 1
                continue

            batch.append(record)

            if len(batch) >= batch_size:
                flush(batch)
                batch.clear()
                log.info("  ... %d records processed", stats["processed"])

    # Flush remainder
    flush(batch)

    cur.close()
    conn.close()

    # Summary
    print()
    print("=" * 52)
    print("  IMPORT SUMMARY")
    print("=" * 52)
    print(f"  Total lines processed : {stats['processed']}")
    print(f"  Records upserted      : {stats['upserted']}")
    print(f"  Records skipped       : {stats['skipped']}")
    print(f"  Records errored       : {stats['errors']}")
    print("=" * 52)

    if stats["errors"]:
        log.warning("%d records failed to import - check logs above.", stats["errors"])
        sys.exit(2)
    else:
        log.info("Import completed successfully.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import copertine_export.jsonl into the PostgreSQL editions table."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the extracted export directory (must contain a .jsonl file)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Number of rows per INSERT batch (default: 200)",
    )
    args = parser.parse_args()

    input_dir = Path(args.input).expanduser().resolve()
    if not input_dir.is_dir():
        log.error("--input path is not a directory: %s", input_dir)
        sys.exit(1)

    db_url = load_env()
    jsonl  = find_jsonl(input_dir)
    import_jsonl(db_url, jsonl, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
