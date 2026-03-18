import { distance as levenshteinDistance } from 'fastest-levenshtein';

export interface SearchConfig {
  query: string;
  mode: 'substring' | 'fuzzy' | 'both';
  threshold: number; // 0-100
  limit: number;
  caseSensitive: boolean;
  wildcards: boolean;
  ignoreSpaces: boolean;
  wholeWord: boolean;
}

export interface SearchResult {
  index: number;
  score: number;
}

/**
 * Convert a glob pattern (with `*` wildcards) to a regex string.
 */
function globToRegex(pattern: string): string {
  const parts = pattern.split('*');
  const escaped = parts.map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  return escaped.join('.*');
}

/**
 * Score a query against text using substring matching.
 * Returns 0-100.
 */
/**
 * Check whether a string contains CJK characters.
 */
function containsCJK(text: string): boolean {
  return /[\u3000-\u9FFF\uAC00-\uD7AF]/.test(text);
}

export function substringScore(
  query: string,
  text: string,
  caseSensitive = false,
  wildcards = false,
  wholeWord = false,
): number {
  if (!query || !text) return 0;

  const q = caseSensitive ? query : query.toLowerCase();
  const t = caseSensitive ? text : text.toLowerCase();

  if (wildcards) {
    const globQ = q.includes('*') ? q : `*${q}*`;
    const regexPattern = globToRegex(globQ);
    const flags = caseSensitive ? '' : 'i';
    const re = new RegExp(regexPattern, flags);

    if (re.test(t)) {
      const qClean = q.replace(/\*/g, '');
      if (!qClean) return 0;
      if (qClean === t) return 100;
      const ratio = qClean.length / t.length;
      return Math.round(75 + 25 * ratio);
    }
    return 0;
  }

  if (wholeWord && !containsCJK(q) && !containsCJK(t)) {
    const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const flags = caseSensitive ? '' : 'i';
    const re = new RegExp('\\b' + escaped + '\\b', flags);
    if (!re.test(t)) return 0;
    if (q === t) return 100;
    const ratio = q.length / t.length;
    return Math.round(75 + 25 * ratio);
  }

  if (q === t) return 100;
  if (t.includes(q)) {
    const ratio = q.length / t.length;
    return Math.round(75 + 25 * ratio);
  }
  return 0;
}


/**
 * Compute Levenshtein ratio: Math.round((1 - distance / maxLen) * 100)
 */
function levenshteinRatio(a: string, b: string): number {
  const maxLen = Math.max(a.length, b.length);
  if (maxLen === 0) return 100;
  const dist = levenshteinDistance(a, b);
  return Math.round((1 - dist / maxLen) * 100);
}


/**
 * Score a query against text using fuzzy matching.
 * Uses only levenshteinRatio (equivalent to RapidFuzz fuzz.ratio).
 * token_set_ratio is intentionally NOT used — it inflates scores when
 * query tokens are a subset of text tokens (same as desktop decision).
 */
export function fuzzyScore(query: string, text: string): number {
  if (!query || !text) return 0;
  return levenshteinRatio(query.toLowerCase(), text.toLowerCase());
}

/**
 * Search entries by a text column using the given config.
 * Returns SearchResult[] sorted by score desc, then index asc.
 */
export function search(
  entries: string[],
  config: SearchConfig,
): SearchResult[] {
  if (config.query.length < 2 || entries.length === 0) return [];

  const results: SearchResult[] = [];

  for (let i = 0; i < entries.length; i++) {
    let text = entries[i] ?? '';
    let query = config.query;

    if (config.ignoreSpaces) {
      text = text.replace(/\s+/g, '');
      query = query.replace(/\s+/g, '');
    }

    let score = 0;

    if (config.mode === 'substring' || config.mode === 'both') {
      score = substringScore(query, text, config.caseSensitive, config.wildcards, config.wholeWord);
    }

    if (config.mode === 'fuzzy' || config.mode === 'both') {
      const fs = fuzzyScore(query, text);
      score = Math.max(score, fs);
    }

    if (score >= config.threshold) {
      results.push({ index: i, score });
    }
  }

  // Sort by score descending, then index ascending
  results.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return a.index - b.index;
  });

  return results.slice(0, config.limit);
}
