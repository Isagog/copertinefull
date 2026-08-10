-- backend/src/setup_db.sql
-- Run as your specific superuser (isagog):
-- docker exec -i mema-postgres psql -U isagog -d postgres < backend/src/setup_db.sql

-----------------------------------------------------------
-- 1. Create Database and User
-----------------------------------------------------------
-- We check if the user exists first to avoid errors on re-runs
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'copertine_app') THEN
        CREATE USER copertine_app WITH PASSWORD 'h1khCzVxKiBPK0G0SXWpr8ZGxgdET_XQkaaZTb8gEvA';
    END IF;
END
$$;

-- Drop and recreate or just create the database
-- Note: You cannot run CREATE DATABASE inside a transaction block or DO block
CREATE DATABASE copertine OWNER copertine_app;

-----------------------------------------------------------
-- 2. Switch to the new database
-----------------------------------------------------------
\c copertine

-----------------------------------------------------------
-- 3. Extensions (requires superuser)
-----------------------------------------------------------
-- Since you are logged in as 'isagog', you have rights to do this
CREATE EXTENSION IF NOT EXISTS unaccent;

-----------------------------------------------------------
-- 4. Italian FTS with accent-insensitive search
-----------------------------------------------------------
-- We create this in the 'public' schema of the 'copertine' DB
CREATE TEXT SEARCH CONFIGURATION italian_unaccent (COPY = italian);
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
CREATE TABLE editions (
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

CREATE INDEX idx_editions_date ON editions (edition_date DESC);
CREATE INDEX idx_editions_search ON editions USING GIN (search_vector);
CREATE INDEX idx_editions_caption_search ON editions USING GIN (caption_vector);

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
