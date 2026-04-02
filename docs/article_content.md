# Directus Article Fields — Cover Issue Analysis

## All fields returned per article

| Field | Value (Dec 19 2025 example) |
|---|---|
| `id` | UUID |
| `status` | `published` |
| `date_created` / `date_updated` | timestamps |
| `headline` | Full article headline |
| `articleBody` | Full HTML body |
| `excerpt` / `summary` / `accordionAbstract` | null |
| `articleTag` | `"Le mani sulla città"` |
| `articleKicker` | Long teaser text (overlay candidate) |
| `referenceHeadline` | `"Le mani sulla città"` — short title |
| `referenceSummary` | Short HTML summary |
| `referenceImage` | UUID → `images` collection |
| `articleFeaturedImage` | UUID → `images` collection |
| `articleFeaturedImageDescription` | Short plain-text caption |
| `articleFeaturedImageCopyright` | `"(Foto Andrea Alfano/LaPresse)"` |
| `articlePositionCover` | `1` (used as filter to identify cover article) |
| `articleEditionPosition` | `1` |
| `imagePosition` | `"center center"` |
| `imageOverlayColor` / `imageBorderColor` | null |
| `articleEdition` | UUID |
| `author` | `"Mario Di Vito"` |
| `datePublished` | ISO timestamp |
| `slug` | URL slug |
| `articleType` | `"notizia"` |
| `syncSource` / `syncSourceId` | `"wp"` / WordPress ID |
| `topics`, `tags`, `badges` | arrays |

---

## Deterministic identification of cover image, caption, and overlay

### The key finding: two image fields serve different purposes

Resolving both image UUIDs via `/items/images/{id}` reveals their filenames:

- `articleFeaturedImage` → `19pol1-f01-askatasuna-lapresse.jpg` — the **body article image** (`pol` = politica section)
- `referenceImage` → `19prima-le-mani-sulla-citta-lapresse.jpg` — **`prima` = front page** (Italian for "first page")

**`referenceImage` is the correct front-page cover picture.** The current `sd2.py` code uses `articleFeaturedImage`, which is the wrong image.

### Field mapping

| Element | Field | Notes |
|---|---|---|
| **Cover image** | `referenceImage` (resolve via `/items/images/{id}`) | Filename always contains `prima` |
| **Image caption** | `images.caption` (HTML) or `articleFeaturedImageDescription` (plain text) | Retrieved from the resolved `referenceImage` record |
| **Copyright** | `articleFeaturedImageCopyright` | Present directly on the article |
| **Overlay title** | `referenceHeadline` | Short, always populated |
| **Overlay kicker** | `articleKicker` | Longer teaser text, also reliably populated |

### Images collection record structure

When resolving a UUID via `/items/images/{id}`, the record contains:

| Field | Content |
|---|---|
| `id` | UUID (same as referenced) |
| `image` | Asset UUID (used to build `/assets/{uuid}` download URL) |
| `description` | HTML with full `<img>` srcset markup |
| `caption` | HTML caption text with Italian and English versions |
| `alternativeText` | Plain-text alt text |

---

## Current code gap in `sd2.py`

The `_fetch_copertina_for_date` method requests `articleFeaturedImage` but not `referenceImage`. The `_get_asset_url` method correctly resolves the image UUID via `/items/images/{id}`, but it is called on the wrong field. To get the actual front-page photo, `referenceImage` should be fetched and resolved instead.

Fields currently stored in Weaviate that are affected:

| Weaviate property | Current source | Correct source |
|---|---|---|
| `editionImageFnStr` | `articleFeaturedImage` → `/items/images/` | `referenceImage` → `/items/images/` |
| `captionStr` | `referenceHeadline` | `articleFeaturedImageDescription` or `images.caption` from `referenceImage` |
