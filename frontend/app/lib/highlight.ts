// app/lib/highlight.ts — client-side highlighting for the literal (Esatta)
// search modes. The Varianti mode is highlighted server-side by ts_headline.

/**
 * Folds case, accents and apostrophes the same way the SQL cop_norm() does,
 * while recording where each folded character came from.
 *
 * Folding changes string length — é decomposes to two code points before the
 * combining mark is dropped — so highlighting positions in the *original*
 * text requires this index map. map[i] is the index, in original code units,
 * of the character that produced folded character i.
 */
export function foldWithMap(input: string): { text: string; map: number[] } {
  let text = '';
  const map: number[] = [];
  let origIndex = 0;

  for (const ch of input) {
    const folded = ch
      .normalize('NFD')
      .replace(/\p{M}/gu, '')
      .replace(/[’‘´`]/g, "'")
      .toLowerCase();

    // One entry per code *unit*, not per code point: regex match indices are
    // code-unit based, so a surrogate pair must contribute two entries or the
    // map desyncs from `text` for everything after it.
    text += folded;
    for (let k = 0; k < folded.length; k++) map.push(origIndex);

    origIndex += ch.length;
  }

  return { text, map };
}

/**
 * Ranges of `text`, as [start, end) original-string indices, matching `term`
 * under the given granularity.
 */
export function matchRanges(
  text: string,
  term: string,
  wholeWord: boolean,
): Array<[number, number]> {
  const haystack = foldWithMap(text);
  const needle = foldWithMap(term).text;
  if (!needle) return [];

  const escaped = needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  // Lookarounds rather than \b: JavaScript's \b is ASCII-only and would
  // mis-anchor on accented letters. Omitted where the needle starts or ends
  // with punctuation, which could never sit against a word boundary.
  const left = wholeWord && /^[\p{L}\p{N}_]/u.test(needle) ? '(?<![\\p{L}\\p{N}_])' : '';
  const right = wholeWord && /[\p{L}\p{N}_]$/u.test(needle) ? '(?![\\p{L}\\p{N}_])' : '';

  const ranges: Array<[number, number]> = [];
  for (const match of haystack.text.matchAll(new RegExp(left + escaped + right, 'gu'))) {
    const start = match.index;
    const end = start + match[0].length;
    ranges.push([
      haystack.map[start],
      end < haystack.map.length ? haystack.map[end] : text.length,
    ]);
  }
  return ranges;
}
