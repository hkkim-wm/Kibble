import { describe, it, expect } from 'vitest';
import {
  substringScore,
  fuzzyScore,
  search,
  normalizeForMatching,
  SearchConfig,
  SearchResult,
} from '../src/core/search';

describe('substringScore', () => {
  it('returns 100 for exact match', () => {
    expect(substringScore('hello', 'hello')).toBe(100);
  });

  it('returns partial score for substring match', () => {
    const score = substringScore('hel', 'hello');
    // Math.round(75 + 25 * (3/5)) = Math.round(90) = 90
    expect(score).toBe(90);
  });

  it('returns 0 for no match', () => {
    expect(substringScore('xyz', 'hello')).toBe(0);
  });

  it('returns 0 for empty query or text', () => {
    expect(substringScore('', 'hello')).toBe(0);
    expect(substringScore('hello', '')).toBe(0);
  });

  it('is case insensitive by default', () => {
    expect(substringScore('HELLO', 'hello')).toBe(100);
    expect(substringScore('hello', 'HELLO')).toBe(100);
  });

  it('respects caseSensitive flag', () => {
    expect(substringScore('HELLO', 'hello', true)).toBe(0);
    expect(substringScore('hello', 'hello', true)).toBe(100);
  });

  it('handles wildcards with explicit asterisks', () => {
    // "h*o" should match "hello" — h...o
    const score = substringScore('h*o', 'hello', false, true);
    expect(score).toBeGreaterThan(0);
  });

  it('wraps query with * when no * present in wildcard mode', () => {
    // "ell" in wildcard mode becomes "*ell*", matches "hello"
    const score = substringScore('ell', 'hello', false, true);
    expect(score).toBeGreaterThan(0);
  });

  it('returns 100 for wildcard exact match (non-wildcard chars == text)', () => {
    // "*hello*" wildcard, q_clean = "hello", text = "hello"
    const score = substringScore('hello', 'hello', false, true);
    expect(score).toBe(100);
  });

  it('returns 0 for wildcard query with only asterisks', () => {
    expect(substringScore('*', 'hello', false, true)).toBe(0);
    expect(substringScore('**', 'hello', false, true)).toBe(0);
  });

  it('matches whole word when wholeWord is true', () => {
    const score = substringScore('test', 'this is a test', false, false, true);
    expect(score).toBeGreaterThan(0);
  });

  it('does NOT match partial word when wholeWord is true', () => {
    const score = substringScore('test', 'testing', false, false, true);
    expect(score).toBe(0);
  });

  it('falls back to substring for CJK text when wholeWord is true', () => {
    const score = substringScore('번역', '번역 메모리', false, false, true);
    expect(score).toBeGreaterThan(0);
  });
});

describe('fuzzyScore', () => {
  it('returns 100 for identical strings', () => {
    expect(fuzzyScore('hello', 'hello')).toBe(100);
  });

  it('returns high score for similar strings', () => {
    const score = fuzzyScore('hello', 'helo');
    expect(score).toBeGreaterThan(70);
  });

  it('returns low score for very different strings', () => {
    const score = fuzzyScore('hello', 'xyz');
    expect(score).toBeLessThan(30);
  });

  it('returns 0 for empty inputs', () => {
    expect(fuzzyScore('', 'hello')).toBe(0);
    expect(fuzzyScore('hello', '')).toBe(0);
  });

  it('scores reordered tokens by character-level similarity', () => {
    // Uses fuzz.ratio (Levenshtein), not token_set_ratio — reordered tokens score < 100
    const score = fuzzyScore('world hello', 'hello world');
    expect(score).toBeGreaterThan(0);
    expect(score).toBeLessThan(100);
  });

  it('scores similar reordered tokens proportionally', () => {
    const score = fuzzyScore('bar foo', 'foo bar');
    expect(score).toBeGreaterThan(0);
    expect(score).toBeLessThan(100);
  });
});

describe('search', () => {
  const entries = [
    'apple pie',
    'banana split',
    'cherry tart',
    'apple sauce',
    'grape juice',
  ];

  it('finds substring matches', () => {
    const config: SearchConfig = {
      query: 'apple',
      mode: 'substring',
      threshold: 50,
      limit: 10,
      caseSensitive: false,
      wildcards: false,
      ignoreSpaces: false,
      wholeWord: false,
    };
    const results = search(entries, config);
    expect(results.length).toBe(2);
    expect(results[0].index).toBe(0); // "apple pie"
    expect(results[1].index).toBe(3); // "apple sauce"
  });

  it('finds fuzzy matches', () => {
    const config: SearchConfig = {
      query: 'appel',
      mode: 'fuzzy',
      threshold: 30,
      limit: 10,
      caseSensitive: false,
      wildcards: false,
      ignoreSpaces: false,
      wholeWord: false,
    };
    const results = search(entries, config);
    // Should find entries with fuzzy matching
    expect(results.length).toBeGreaterThan(0);
    // The top result should be one of the apple entries (closest to "appel")
    expect([0, 3]).toContain(results[0].index);
  });

  it('returns empty for query shorter than 2 chars', () => {
    const config: SearchConfig = {
      query: 'a',
      mode: 'substring',
      threshold: 0,
      limit: 10,
      caseSensitive: false,
      wildcards: false,
      ignoreSpaces: false,
      wholeWord: false,
    };
    const results = search(entries, config);
    expect(results).toEqual([]);
  });

  it('respects limit', () => {
    const config: SearchConfig = {
      query: 'ap',
      mode: 'substring',
      threshold: 0,
      limit: 1,
      caseSensitive: false,
      wildcards: false,
      ignoreSpaces: false,
      wholeWord: false,
    };
    const results = search(entries, config);
    expect(results.length).toBeLessThanOrEqual(1);
  });

  it('handles ignoreSpaces', () => {
    const entriesWithSpaces = ['app le', 'banana'];
    const config: SearchConfig = {
      query: 'apple',
      mode: 'substring',
      threshold: 50,
      limit: 10,
      caseSensitive: false,
      wildcards: false,
      ignoreSpaces: true,
      wholeWord: false,
    };
    const results = search(entriesWithSpaces, config);
    expect(results.length).toBe(1);
    expect(results[0].index).toBe(0);
  });

  it('uses both mode (max of substring and fuzzy)', () => {
    const config: SearchConfig = {
      query: 'apple',
      mode: 'both',
      threshold: 50,
      limit: 10,
      caseSensitive: false,
      wildcards: false,
      ignoreSpaces: false,
      wholeWord: false,
    };
    const results = search(entries, config);
    // Should find at least the substring matches
    expect(results.length).toBeGreaterThanOrEqual(2);
  });

  it('sorts by score descending, then index ascending', () => {
    const config: SearchConfig = {
      query: 'apple',
      mode: 'substring',
      threshold: 0,
      limit: 10,
      caseSensitive: false,
      wildcards: false,
      ignoreSpaces: false,
      wholeWord: false,
    };
    const results = search(entries, config);
    for (let i = 1; i < results.length; i++) {
      if (results[i].score === results[i - 1].score) {
        expect(results[i].index).toBeGreaterThan(results[i - 1].index);
      } else {
        expect(results[i].score).toBeLessThan(results[i - 1].score);
      }
    }
  });
});

describe('normalizeForMatching', () => {
  it('strips inline tags', () => {
    expect(normalizeForMatching('Press <color>Start</color>')).toBe('Press Start');
  });

  it('strips variables', () => {
    expect(normalizeForMatching('{player_name} won {0} gold')).toBe('won gold');
  });

  it('collapses whitespace', () => {
    expect(normalizeForMatching('hello   world')).toBe('hello world');
  });

  it('strips trailing punctuation', () => {
    expect(normalizeForMatching('Continue...')).toBe('Continue');
    expect(normalizeForMatching('확인!')).toBe('확인');
  });

  it('handles combined normalization', () => {
    expect(normalizeForMatching('<b>{0}개</b> 획득!')).toBe('개 획득');
  });

  it('returns empty for empty input', () => {
    expect(normalizeForMatching('')).toBe('');
  });

  it('returns plain text unchanged', () => {
    expect(normalizeForMatching('plain text')).toBe('plain text');
  });
});

describe('fuzzyScore with normalization', () => {
  it('scores strings with different tags as identical', () => {
    expect(
      fuzzyScore('<color>시작하기</color>', '<Text_Yellow02>시작하기</Text_Yellow02>'),
    ).toBe(100);
  });

  it('scores strings with different variables as identical', () => {
    expect(fuzzyScore('{player_name}의 승리', '{0}의 승리')).toBe(100);
  });

  it('ignores trailing punctuation differences', () => {
    expect(fuzzyScore('계속하시겠습니까?', '계속하시겠습니까')).toBe(100);
  });
});
