# Replacing copertine's Directus code with `isagog-corpus`

**Status:** proposal, 2026-09-01
**Targets:** this repo (`copertinefull`) and [`Isagog/isagog-corpus`](https://github.com/Isagog/isagog-corpus) @ `8e34d0b`

---

## 1. The finding

Exactly **one production file in this repo talks to Directus**: `backend/src/sd2.py`
(495 lines). The frontend never does — it only reads Postgres. `import_to_pg.py`
reads a JSONL export. Everything else that mentions Directus is untracked scratch
(`backend/experiments/`, `backend/tools/`, `backend/tests/`).

So "replace all functions in this repo with those from isagog-corpus" is, in
practice, a rewrite of one class — `DirectusManifestoScraper` — plus the deletion
of a Weaviate fossil (`backend/src/includes/`).

The migration is small. What makes it worth doing is not line count: it is that
`sd2.py` currently reimplements, badly and from scratch, four things the port
already does correctly — transport policy, an error taxonomy, asset fetching with
a size guard, and edition-date resolution.

## 2. What the CMS actually says

The plan below rests on a live read of `pulse.ilmanifesto.it` on 2026-09-01
(read-only, with the repo's own token). Four facts, all verified:

| Fact | Evidence |
|---|---|
| The `editions` collection carries `editionDate` as a **plain Rome-calendar day** (`"2026-09-01"`), no timestamp, no timezone | `GET /items/editions?filter[editionDate][_eq]=2026-09-01` |
| Editions go back to **1971-04-28** — far deeper than copertine's 2013 archive — and every sampled date (2013, 2018, 2020, 2024) has one | `sort=editionDate&limit=3` |
| A non-publishing day simply **has no edition row**. 2026-08-31 (a Monday) returns `[]`, while 08-30 and 09-01 exist | same query at three dates |
| The image indirection resolves in **one request** via a relation expansion — no second hop needed — and carries mime, filename and size | `fields=articleFeaturedImage.image.{id,type,filename_download,filesize}` → `image/jpeg`, `97698` |
| `filter[articleEdition][_eq]=<uuid>` works, so articles are filterable by edition | one cover article returned for edition `ce2afbe5…` |

### 2.1 The consequence: the timezone workaround is deletable

`sd2.py` spends its most delicate code — `ROME_TZ`, the Rome-local query window in
`_fetch_copertina_for_date`, the belt-and-braces `_resolve_edition_date`, the
`MONDAY` constant, and the long comments defending all of it — solving one problem:
Directus stores `articles.datePublished` in true UTC, and il manifesto publishes the
cover at Rome-local midnight, i.e. 22:00–23:00 UTC *the day before*.

The `editions` collection does not have that problem. `editionDate` **is** the
edition's calendar day. The verified proof is in the data: the current cover
article's `datePublished` is `2026-08-31T22:01:54Z`, and its edition's `editionDate`
is `2026-09-01`.

Querying editions instead of articles therefore removes the timezone arithmetic
*structurally* rather than fixing it — and Monday stops being a special case,
because a Monday has no row.

This is the single highest-value change in the migration, and it is available only
because `corpus` models editions as a first-class entity.

## 3. Fit: what the port covers, and the three gaps

### Covered today, no changes needed

| copertine need | `corpus` surface |
|---|---|
| Find the edition for a date | `EditionQuery(date_exact=…)` → `list_editions` |
| Edition identity and date | `Edition.id`, `Edition.date` (already `YYYY-MM-DD`) |
| Download the cover image bytes | `fetch_asset(id, max_bytes=…)` — with the size guard `sd2.py` lacks |
| Timeouts, pooling, no transport retries | `Timeouts(json=…, asset=…)`, `AsyncHTTPTransport(retries=0)` |
| Auth/connectivity fail-fast at boot | `corpus.ping()` (`GET /users/me`) |
| Error handling | `CorpusError` tree, replacing the ad-hoc `ScraperError` family |
| Kicker | `Article.kicker` ← `articleKicker` |

### The three gaps

1. **`referenceHeadline` is not modelled.** copertine's `caption` column — the
   headline shown on every card in the archive — is `referenceHeadline`
   (*"Ristretto"*), **not** `headline` (*"Piovono missili per Hormuz"*). The port's
   `Article` has no such field. Verified distinct on the live row.

2. **No featured image.** `Article` carries no lead-image `AssetRef`. `AssetRef`
   itself is already the right shape (`id`, `filename`, `mime`, `size`) and the
   expansion populates all four — the model just has no place to put it.

3. **No way to select the cover article.** `ArticleQuery` cannot express
   `filter[articlePositionCover][_eq]=1`, and there is no escape hatch. Also
   `ArticleQuery(edition_id=…)` is refused outright, because
   `DirectusSchema.article_edition_field` is `None` — a one-constant fix, now that
   `articleEdition` is verified to filter.

Two further frictions, both cheap:

- `article_from_row` demands a valid `slug` and a non-empty `articleBody`, and
  `_article_id` demands a UUID. Verified true for the current cover article, but it
  makes `Article` an unnecessarily heavy vehicle for what copertine wants.
- `stream_asset` yields bytes only. `sd2.py` derives the file extension from the
  response `content-type`. Closing gap 2 with a populated `AssetRef.mime` closes
  this one too, for free.

## 4. Recommendation: add a cover concept to the port

The gaps are not copertine being unusual. They are the port being *incomplete* for
the domain it claims — "an abstract newspaper-archive data access layer". copertine
was not in the inventory of twelve call sites the library was designed against
(it appears once, as a user of the legacy instance), and it is the only consumer
that cares about the **front page as an object**.

"The front page of a dated print edition, with its display headline and its image"
is a genuinely generic newspaper concept, not a manifesto quirk. It belongs in
`corpus/`, gated by a capability, exactly like `EDITION_PDF`.

### Proposed port change (upstream, in `isagog-corpus`)

```python
# corpus/models.py
class EditionCover(BaseModel):
    """The front page as the archive presents it: display headline, kicker, image."""
    model_config = ConfigDict(frozen=True)

    article_id: str | None = None   # the cover story, when the CMS links one
    headline: str                   # the DISPLAY headline, not the article headline
    kicker: str = ""
    image: AssetRef | None = None

class Edition(BaseModel):
    ...
    cover: EditionCover | None = None

# corpus/capabilities.py
class Capability(StrEnum):
    ...
    EDITION_COVER = "edition_cover"
```

```python
# corpus/base.py
async def get_edition_cover(self, edition_id: str) -> EditionCover:
    raise CapabilityNotSupported("edition_cover")
```

### Proposed adapter change (`corpus_directus`)

All of it lands in `schema.py` as data, which is the library's own stated design
rule ("Retargeting either is a `DirectusSchema` constant — not another codebase"):

```python
COVER_FIELDS: Mapping[str, str] = {
    "headline": "referenceHeadline",
    "kicker":   "articleKicker",
    "image":    "articleFeaturedImage.image",
}

class DirectusSchema(BaseModel):
    ...
    article_edition_field: str | None = "articleEdition"   # was None; verified
    cover_fields: Mapping[str, str] = COVER_FIELDS
    cover_filter: Mapping[str, str] = {"articlePositionCover": "1"}
```

`rows.py` gains `cover_from_row`; `compile.py` gains `compile_cover_query`, which
emits the projection with the deep file expansion so `AssetRef` comes back fully
populated in one request.

### The alternative, if upstream change is unwelcome

Keep the port as-is and let copertine own a small `copertine_cover.py` that uses
`DirectusCorpus` for editions/assets/errors and issues its own cover query. This
still deletes the timezone code, the error family and the transport policy — about
70% of the value — but it reintroduces exactly the vendor-vocabulary fork the
library exists to prevent, and `scripts/check_boundaries.sh` would flag it.

**Recommended: extend the port.** The cost is ~4 small files and one contract-suite
section, paid once, in a library that has exactly one other consumer wave still
ahead of it.

## 5. Function-by-function inventory

### `backend/src/sd2.py` (495 → ~120 lines)

| Current | Fate |
|---|---|
| `_init_directus`, `directus_url`, `assets_url`, header dict | **Replaced** — `DirectusCorpus.from_settings(DirectusCorpusSettings(...))` |
| `_fetch_copertina_for_date` + `ROME_TZ` window | **Replaced** — `list_editions(EditionQuery(date_exact=day))` |
| `_resolve_edition_date` | **Deleted** — `Edition.date` is authoritative |
| `MONDAY`, the Monday branch | **Deleted** — no edition row, no special case |
| `_validate_article` | **Replaced** — required-field check on `EditionCover` (or `ArticlePolicy`) |
| `_get_asset_url` (the `/items/images/{id}` hop) | **Deleted** — relation expansion returns the file id |
| `_download_image`, `mimetypes.guess_extension` | **Replaced** — `fetch_asset(id, max_bytes=…)` + `AssetRef.mime` |
| `ScraperError`, `MissingEnvironmentVariableError`, `InvalidDateFormatError` | **Replaced** — `CorpusError` tree / `CorpusConfigError` |
| `_get_required_env`, `_load_environment` | **Replaced** — settings model reads env once |
| `HTTP_OK`, `raise_for_status` handling, `requests` timeouts | **Deleted** — transport policy lives in the adapter |
| `_init_db`, `_upsert_edition`, `cleanup` | **Kept** — Postgres write side; the port is read-only by design |
| `_slugify`, `_generate_image_filename` | **Kept** — the `il-manifesto_YYYY-MM-DD_slug.jpg` convention is product, not CMS |
| `_setup_images_dir`, `_setup_logging` | **Kept** |
| `parse_dates_from_args`, `_generate_date_range`, `_parse_single_date`, `_parse_date_file`, `DateFileNotFoundError` | **Kept**, simplified to `date` rather than `datetime` — there is no time-of-day left to carry |

### Elsewhere

| Path | Fate |
|---|---|
| `backend/src/includes/utils.py` (`init_weaviate_client`, `WeaviateClientInitializationError`, `extract_date_from_filename`) | **Delete** — Weaviate is gone; nothing imports it |
| `backend/src/includes/mytypes.py` (`Copertina`, `CopertinExtract`) | **Delete** — Weaviate schema models, unused |
| `backend/src/includes/prompts.py` | **Delete** or move to `experiments/` |
| `backend/src/import_to_pg.py` | **Keep untouched** — reads JSONL, never Directus |
| `backend/tools/directusdefect.py` | **Rewrite** as a ~30-line corpus consumer, or delete. It currently points at the *legacy* instance and filters on `articleEditionPosition`, not `articlePositionCover` — the two disagree with `sd2.py` |
| `backend/tools/gendates.py` | **Keep** — no CMS contact |
| `backend/experiments/`, `backend/tests/` | Untracked scratch. Delete, or move under `experiments/` and leave out of the image |
| `frontend/**` | **Untouched.** No Directus anywhere; it reads Postgres only |

## 6. Phases

| # | Work | Gate |
|---|---|---|
| 0 | Publish `isagog-corpus` as a tag-pinned git dependency; add it to `backend/pyproject.toml`. **Bump the scraper image to Python 3.13** — the library requires it (PEP 695 generics in `corpus/signals.py`), the current Dockerfile is 3.12 | `uv sync` resolves; image builds |
| 1 | Upstream: `EditionCover` model, `Capability.EDITION_COVER`, `get_edition_cover` on the ABC, `FakeCorpus` support, contract-suite section | fake and adapter both green on the extended suite |
| 2 | Upstream: `corpus_directus` cover support — schema constants, `cover_from_row`, `compile_cover_query`, `article_edition_field="articleEdition"` | `pytest -m staging` green against `pulse.ilmanifesto.it` |
| 3 | Rewrite `sd2.py` against the port. Keep the CLI, the filename convention and the upsert byte-identical | **Parity gate** — see §7 |
| 4 | Delete `backend/src/includes/`; rewrite or drop `tools/directusdefect.py`; run `check_boundaries.sh` over `backend/` | zero vendor-vocabulary hits in tracked backend source |
| 5 | Real tests for the scraper (there are none today — `backend/tests/` is stale HTML-scraping scratch), using `FakeCorpus` for the CMS and a throwaway Postgres for the write side | 80% coverage on `backend/src/` |

### Parity gate (phase 3)

Run old and new over the same date list — a mix of recent days, a Monday, a
pre-2015 date, and a date whose cover was published at 22:0x UTC — and diff the
resulting rows and image files.

- `edition_id`, `edition_date`, `caption`, `kicker`, `image_filename` must match exactly.
- Image bytes must be identical.
- The `2026-08-31` case is the interesting one: the old code, asked for that UTC day,
  returns the article belonging to edition `2026-09-01`. Decide deliberately whether
  the new behaviour (Monday → no edition, correctly) is the fix it appears to be, or
  whether any stored row currently depends on the old off-by-one.

## 7. Findings from the phase-3 parity run (2026-09-01)

Phase 3 is implemented. Old and new scrapers were run over the same seven dates
with the database write recorded rather than executed, and the rows and image
bytes diffed.

**Five of six editions are byte-identical** — `edition_id`, `edition_date`,
`caption`, `image_filename` and the image content all match exactly for
2026-09-01, 08-30, 08-29, 08-28 and 2024-06-10. Monday 2026-08-31 is correctly
reported as unpublished by both, the new one without any timezone code.

Two differences, both real:

### 7.1 The CMS holds four overlapping edition series — resolved

`editions` carries four imported series, measured against the live instance
2026-09-01:

| series | editions | range |
|---|---|---|
| `mema` | 7188 | 1971-04-28 → 2008-11-10 |
| `athenaPre2002` | 2129 | 1995-01-17 → 2001-12-30 |
| `athena` | 5723 | 2001-02-06 → 2023-12-31 |
| **`wp`** | **4165** | **2013-03-27 → today** |

They overlap, so a date could resolve to more than one edition — every date in
2018–2023 did — and nothing in the row says which is authoritative.

**Resolved by scoping the corpus to `wp`** (`MANIFESTO_WP_SCHEMA`, isagog-corpus
PR #3). `wp` is the live series: it alone is still written, it has 4165 editions
on 4165 distinct dates — no ambiguity anywhere in its range — and it begins
2013-03-27, which is exactly where this archive begins. The other three are
historical imports that end in 2008, 2001 and 2023.

The ambiguity refusal in `sd2.py` is now unreachable and kept only as a tripwire.

### 7.1b The historical archive is one day earlier than the publisher

Scoping to `wp` exposed a **pre-existing** discrepancy that the ambiguity check
had been masking. For a `wp` edition dated D, the cover article is published the
evening before D. Until about 2023 that evening was ~19:30–20:40 UTC, i.e.
21:30–22:40 **Rome** — still the previous calendar day in Rome. Only later did
publishing move past 22:00 UTC (Rome midnight), at which point Rome-day and
`editionDate` coincide.

Both the old scraper and the archive it built key on the article's publish day,
so they are one day early wherever those differ. Sampling one June fortnight per
year, comparing the cover's Rome-local publish day to `editionDate`:

| year | same day | one day early |
|---|---|---|
| 2013, 2014, 2018, 2020 | 0 | all |
| 2015, 2016, 2017, 2022 | 1–6 | most |
| **2024, 2026** | **all** | **0** |

The publisher's own titles settle which is right:

| CMS edition title | cover | copertine row |
|---|---|---|
| il manifesto del **04**.04.2013 | Impresa in giro | **03**-04-2013 |
| il manifesto del **05**.04.2013 | I caymani | **04**-04-2013 |
| il manifesto del **06**.04.2013 | Poveri noi | **05**-04-2013 |

So roughly 2013–2023 of the stored archive is dated one day earlier than the
paper it came from. **The daily job is unaffected** — 2024 onward agrees exactly,
which is why the parity run matched on every modern date.

This is not something to fix as a side effect. Re-dating ten years of a public
archive changes every permalink and every filename, and it is a product
decision. It is recorded here so that whoever runs a backfill knows that
backfilling from `wp` editions *moves* those rows rather than merely filling
them in.

### 7.2 Kickers lose a trailing space

The corpus normaliser strips whitespace, so `"…contribuente americano» "` is
stored as `"…contribuente americano»"`. Cosmetic and arguably a fix, but it means
a re-scrape rewrites existing kickers by one character.

## 8. Risks and open questions

1. **`referenceHeadline` is null on old editions.** Verified null for 2013-04-05.
   The pre-2015 archive in Postgres came from the Weaviate export (originally
   scraped from the website), not from `sd2.py`. Backfilling those from Directus
   would produce empty captions. Scope any backfill to the era where
   `referenceHeadline` is populated, and find that boundary before running one.

2. **`editions.editionCoverImage` is not the image copertine stores.** The edition
   carries its own cover image (`47242659-…`), distinct from the cover article's
   featured image (`81e3fd96-…`) that `sd2.py` downloads. The edition's own image may
   well be the better source — it is the actual front page — but switching is a
   *product* change that alters every future card. Keep parity by default; raise it
   with whoever owns the archive.

3. **`articlePositionCover` vs `articleEditionPosition`.** `sd2.py` filters on the
   first, `tools/directusdefect.py` and the README say the second. On the current
   row both are `1`. They are different fields and may diverge historically — pin
   the correct one in `DirectusSchema.cover_filter` and delete the other mention.

4. **Sync → async.** `sd2.py` is synchronous `requests`; the port is `httpx.AsyncClient`.
   The scraper becomes an `asyncio.run(main())` entry point. Low risk, but it touches
   `main()` and the context-manager shape.

5. **Cloudflare fronts the CMS.** A request with urllib's default User-Agent gets
   `403, error code: 1010` — a Cloudflare browser-signature block, not a Directus
   permission error. `requests` and `httpx` default UAs pass today. Worth a note in
   the adapter, and worth knowing before someone debugs a 403 as an auth problem.

6. **Two `isagog-corpus` consumers land at once.** memaflow2 and pdfmanifesto are
   phases 3 and 6 of that library's own migration plan. Adding `EditionCover` before
   they adopt is cheap; adding it after means a version bump across three repos.
   This argues for doing phases 1–2 *now*.
