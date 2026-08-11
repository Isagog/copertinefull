-- backend/src/setup_db.sql
--
-- Run as a superuser against the target Postgres. On mema4 that is the managed
-- pgvector instance, whose superuser is `postgres`:
--
--   docker exec -i <pg-container> psql -U postgres -d postgres \
--       -v ON_ERROR_STOP=1 -v copertine_password='<generated>' \
--       < backend/src/setup_db.sql
--
-- The password is a psql VARIABLE, never a literal in this file. An earlier
-- revision hardcoded the live one here, which put a working production
-- credential into git history.
--
-- Both steps below use \gexec rather than a DO block. That is not a style
-- choice: psql does NOT interpolate :variables inside dollar-quoted strings,
-- so a `DO $$ ... :copertine_password ... $$` would ship the literal text
-- ":copertine_password" to the server. \gexec runs outside any quoting, and it
-- is also the only way to make CREATE DATABASE conditional — that statement
-- cannot run inside a DO block or a transaction at all.

\set ON_ERROR_STOP on

-----------------------------------------------------------
-- 1. Create Database and User
-----------------------------------------------------------
-- Idempotent: each SELECT yields either one CREATE statement for \gexec to
-- run, or zero rows, in which case \gexec does nothing.
SELECT format('CREATE USER copertine_app WITH PASSWORD %L', :'copertine_password')
WHERE NOT EXISTS (
    SELECT FROM pg_catalog.pg_roles WHERE rolname = 'copertine_app'
)
\gexec

SELECT 'CREATE DATABASE copertine OWNER copertine_app'
WHERE NOT EXISTS (
    SELECT FROM pg_catalog.pg_database WHERE datname = 'copertine'
)
\gexec

-----------------------------------------------------------
-- 2. Switch to the new database
-----------------------------------------------------------
\c copertine

-----------------------------------------------------------
-- 3. Extensions (requires superuser)
-----------------------------------------------------------
-- unaccent must exist BEFORE the editions table: its generated tsvector
-- columns depend on the italian_unaccent configuration below, which in turn
-- depends on this extension.
CREATE EXTENSION IF NOT EXISTS unaccent;

-----------------------------------------------------------
-- 4. Italian FTS with accent-insensitive search
-----------------------------------------------------------
-- Created in the 'public' schema of the 'copertine' DB. There is no
-- IF NOT EXISTS form for CREATE TEXT SEARCH CONFIGURATION, hence \gexec again
-- — without the guard a re-run of this script aborts here, after the role and
-- database have already been created.
SELECT 'CREATE TEXT SEARCH CONFIGURATION italian_unaccent (COPY = italian)'
WHERE NOT EXISTS (
    SELECT FROM pg_ts_config WHERE cfgname = 'italian_unaccent'
)
\gexec

ALTER TEXT SEARCH CONFIGURATION italian_unaccent
    ALTER MAPPING FOR hword, hword_part, word
    WITH unaccent, italian_stem;

-----------------------------------------------------------
-- 5. Normalizer for literal ("Esatta") search
-----------------------------------------------------------
-- Folds case, accents and the two apostrophe forms the corpus mixes, so
-- "perche" finds "Perche' no" and "c'e" finds "nell(U+2019)emergenza".
-- The two-argument unaccent() form is IMMUTABLE (the one-argument form is
-- only STABLE), which is what allows IMMUTABLE here and lets the planner
-- inline the call. No SET search_path clause on purpose: it would block
-- that inlining, and unaccent lives in public.
CREATE OR REPLACE FUNCTION cop_norm(t text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE AS
$$ SELECT lower(unaccent('unaccent', regexp_replace(t, '[’‘´`]', '''', 'g'))) $$;

COMMENT ON FUNCTION cop_norm(text) IS
    'Case/accent/apostrophe folding for literal search (Esatta modes).';

-----------------------------------------------------------
-- 6. Editions table
-----------------------------------------------------------
CREATE TABLE IF NOT EXISTS editions (
    id              SERIAL PRIMARY KEY,
    edition_id      VARCHAR(10) NOT NULL UNIQUE,
    edition_date    DATE NOT NULL,
    caption         TEXT NOT NULL,
    kicker          TEXT,
    image_filename  TEXT NOT NULL,
    -- Whole record (caption + kicker), for "Tutto il testo" under Varianti
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        setweight(to_tsvector('italian_unaccent', coalesce(caption, '')), 'A') ||
        setweight(to_tsvector('italian_unaccent', coalesce(kicker, '')), 'B')
    ) STORED,
    -- Caption alone, for "Solo titolo" under Varianti. search_vector cannot
    -- answer that query: a kicker hit would still satisfy @@.
    caption_vector  TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('italian_unaccent', coalesce(caption, ''))
    ) STORED,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_editions_date ON editions (edition_date DESC);
CREATE INDEX IF NOT EXISTS idx_editions_search ON editions USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_editions_caption_search ON editions USING GIN (caption_vector);

-----------------------------------------------------------
-- 7. Final Permissions Check
-----------------------------------------------------------
-- Ensure the app user owns the schema and all objects within it.
-- ALTER SCHEMA alone is not enough: objects created by the superuser running
-- this script stay owned by that superuser, which then blocks copertine_app
-- from running migrations against them.
ALTER SCHEMA public OWNER TO copertine_app;
ALTER TABLE editions OWNER TO copertine_app;
ALTER FUNCTION cop_norm(text) OWNER TO copertine_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO copertine_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO copertine_app;
