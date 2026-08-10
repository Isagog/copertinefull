-- 001_search_switches.sql
-- Adds the DB support for the three search switches:
--   Corrispondenza  Esatta / Varianti
--   Granularita     Parola intera / Stringa   (only under Esatta)
--   Ambito          Solo titolo / Tutto il testo
--
-- Idempotent: safe to re-run. Runs in one transaction, so a failure leaves
-- the database untouched.
--
-- Must run as the owner of the editions table. Despite the ALTER SCHEMA in
-- setup_db.sql, the live table is owned by isagog, not copertine_app, so
-- the ALTER TABLE below needs that role:
--
--   docker exec -i mema-postgres \
--     psql -U isagog -d copertine -v ON_ERROR_STOP=1 \
--     < backend/src/migrations/001_search_switches.sql
--
-- cop_norm() is left with the default PUBLIC execute grant, so the
-- application role copertine_app can call it without an extra GRANT.

\set ON_ERROR_STOP on

BEGIN;

-----------------------------------------------------------
-- 1. Normalizer used by the two literal ("Esatta") modes
-----------------------------------------------------------
-- Folds the three differences that made literal search miss obvious hits:
--   * case            -> lower()
--   * accents         -> unaccent(), so "perche" finds "Perche' no"
--   * apostrophes     -> the corpus mixes ASCII ' (468 rows) with the
--                        typographic U+2019 (41 rows); both become ASCII
--
-- The two-argument unaccent() form is IMMUTABLE (the one-argument form is
-- only STABLE), which is what lets this function be IMMUTABLE and therefore
-- inlinable by the planner and usable in an expression index later on.
--
-- No SET search_path clause on purpose: it would block inlining. unaccent
-- lives in public, which is on the default search_path for this database.
CREATE OR REPLACE FUNCTION cop_norm(t text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS
$$ SELECT lower(unaccent('unaccent', regexp_replace(t, '[’‘´`]', '''', 'g'))) $$;

COMMENT ON FUNCTION cop_norm(text) IS
    'Case/accent/apostrophe folding for literal search (Esatta modes).';

-----------------------------------------------------------
-- 2. Title-only search vector ("Solo titolo" under Varianti)
-----------------------------------------------------------
-- editions.search_vector already covers caption (weight A) + kicker (weight B)
-- as one blob, so it cannot answer a title-only query: a kicker hit would
-- still satisfy @@. This second vector indexes the caption alone.
ALTER TABLE editions
    ADD COLUMN IF NOT EXISTS caption_vector tsvector
    GENERATED ALWAYS AS (
        to_tsvector('italian_unaccent', coalesce(caption, ''))
    ) STORED;

CREATE INDEX IF NOT EXISTS idx_editions_caption_search
    ON editions USING GIN (caption_vector);

COMMIT;
