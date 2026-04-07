# Fuzzy Search Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `normalize_for_matching()` from l10n-LLM's QA pipeline to Kibble's fuzzy search, so inline tags (`<color>`), variables (`{0}`), and trailing punctuation don't pollute fuzzy similarity scores.

**Architecture:** Add a normalization layer that strips tags/variables/punctuation and collapses whitespace before fuzzy comparison. Normalization applies only to the fuzzy scoring path — substring matching is unaffected (users expect literal matches). Both desktop (Python) and web (TypeScript) get the same normalization logic. Original text is preserved for display; only the scoring comparison uses normalized text.

**Tech Stack:** Python (RapidFuzz), TypeScript (fastest-levenshtein) — no new dependencies.

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Modify | `core/search.py` | Add `normalize_for_matching()`, apply it in `fuzzy_score()` and `search_vectorized()` fuzzy path |
| Modify | `web/src/core/search.ts` | Add `normalizeForMatching()`, apply it in `fuzzyScore()` and `search()` fuzzy path |
| Modify | `tests/test_search.py` | Add normalization tests for desktop |
| Modify | `web/tests/search.test.ts` | Add normalization tests for web |

---

### Task 1: Desktop — Add normalization and tests

**Files:**
- Modify: `core/search.py:1-10` (add regex constants), `core/search.py:56-63` (modify `fuzzy_score`), `core/search.py:157-169` (modify `search_vectorized` fuzzy path)
- Modify: `tests/test_search.py` (add normalization test class)

**Reference:** The normalization logic comes from `D:\VS\l10n-LLM\QA\scripts\qa_input.py:9-27`.

- [ ] **Step 1: Write failing tests for normalization**

Add to `tests/test_search.py`:

```python
from core.search import normalize_for_matching


class TestNormalizeForMatching:
    def test_strips_inline_tags(self):
        assert normalize_for_matching("Press <color>Start</color>") == "Press Start"

    def test_strips_variables(self):
        assert normalize_for_matching("{player_name} won {0} gold") == "won gold"

    def test_collapses_whitespace(self):
        assert normalize_for_matching("hello   world") == "hello world"

    def test_strips_trailing_punctuation(self):
        assert normalize_for_matching("Continue...") == "Continue"
        assert normalize_for_matching("확인!") == "확인"

    def test_combined_normalization(self):
        assert normalize_for_matching("<b>{0}개</b> 획득!") == "개 획득"

    def test_empty_and_plain(self):
        assert normalize_for_matching("") == ""
        assert normalize_for_matching("plain text") == "plain text"


class TestFuzzyScoreWithNormalization:
    def test_tags_dont_inflate_score(self):
        """Two strings identical except for different tags should score high."""
        score = fuzzy_score(
            "<color>시작하기</color>",
            "<Text_Yellow02>시작하기</Text_Yellow02>",
        )
        assert score == 100

    def test_variables_dont_deflate_score(self):
        """Strings differing only in variable names should score high."""
        score = fuzzy_score("{player_name}의 승리", "{0}의 승리")
        assert score == 100

    def test_trailing_punctuation_ignored(self):
        score = fuzzy_score("계속하시겠습니까?", "계속하시겠습니까")
        assert score == 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd D:/VS/kibble && .venv/Scripts/python -m pytest tests/test_search.py::TestNormalizeForMatching tests/test_search.py::TestFuzzyScoreWithNormalization -v`
Expected: FAIL — `normalize_for_matching` not found, fuzzy tests fail because tags/variables affect scoring.

- [ ] **Step 3: Add `normalize_for_matching` to `core/search.py`**

Add after the existing imports at the top of `core/search.py` (after line 4):

```python
# --- Normalization for fuzzy matching (ported from l10n-LLM QA pipeline) ---
_INLINE_TAG_RE = re.compile(r'<[^>]+>')       # <color>, <Text_Yellow02>, </>
_VARIABLE_RE = re.compile(r'\{[^}]+\}')        # {0}, {player_name}
_MULTI_SPACE_RE = re.compile(r'\s+')


def normalize_for_matching(text: str) -> str:
    """Normalize text for fuzzy comparison.

    Strips inline tags, variables, collapses whitespace, and strips
    trailing punctuation. Only used for similarity scoring — original
    text is preserved for display.
    """
    t = _INLINE_TAG_RE.sub('', text)
    t = _VARIABLE_RE.sub('', t)
    t = _MULTI_SPACE_RE.sub(' ', t)
    t = t.strip().rstrip('.,!?;:~…')
    return t
```

- [ ] **Step 4: Apply normalization in `fuzzy_score()`**

Replace the `fuzzy_score` function (lines 56-63):

```python
def fuzzy_score(query: str, text: str) -> int:
    if not query or not text:
        return 0
    nq = normalize_for_matching(query)
    nt = normalize_for_matching(text)
    if not nq or not nt:
        return 0
    return int(fuzz.ratio(nq, nt))
```

- [ ] **Step 5: Apply normalization in `search_vectorized()` fuzzy path**

In the fuzzy matching section of `search_vectorized()` (around lines 157-169), normalize the texts before fuzzy comparison. Replace:

```python
    # --- Fuzzy matching (RapidFuzz batch API) ---
    if config.mode in ("fuzzy", "both"):
        texts_list = texts_normalized.tolist()
        fuzzy_results = process.extract(
            query_normalized,
            texts_list,
            scorer=fuzz.ratio,
            limit=None,
            score_cutoff=max(config.threshold, 1),  # Skip below threshold early
        )
        for text, score, idx in fuzzy_results:
            if score > scores[idx]:
                scores[idx] = score
```

With:

```python
    # --- Fuzzy matching (RapidFuzz batch API) ---
    if config.mode in ("fuzzy", "both"):
        # Normalize texts for fuzzy comparison (strip tags, variables, punctuation)
        fuzzy_texts = texts_normalized.apply(normalize_for_matching).tolist()
        fuzzy_query = normalize_for_matching(query_normalized)
        if fuzzy_query:  # skip if normalization empties the query
            fuzzy_results = process.extract(
                fuzzy_query,
                fuzzy_texts,
                scorer=fuzz.ratio,
                limit=None,
                score_cutoff=max(config.threshold, 1),
            )
            for text, score, idx in fuzzy_results:
                if score > scores[idx]:
                    scores[idx] = score
```

- [ ] **Step 6: Run all search tests**

Run: `cd D:/VS/kibble && .venv/Scripts/python -m pytest tests/test_search.py -v`
Expected: ALL PASS (new normalization tests + existing tests unchanged).

- [ ] **Step 7: Commit**

```bash
cd D:/VS/kibble
git add core/search.py tests/test_search.py
git commit -m "feat(search): add normalize_for_matching to desktop fuzzy scoring

Port normalization from l10n-LLM QA pipeline. Strips inline tags,
variables, trailing punctuation before fuzzy comparison so markup
doesn't pollute similarity scores."
```

---

### Task 2: Web — Add normalization and tests

**Files:**
- Modify: `web/src/core/search.ts:1-5` (add regex constants), `web/src/core/search.ts:89-106` (modify fuzzy functions)
- Modify: `web/tests/search.test.ts` (add normalization test suite)

- [ ] **Step 1: Write failing tests for normalization**

Add to `web/tests/search.test.ts` — after the existing imports, add `normalizeForMatching` to the import list:

```typescript
import {
  substringScore,
  fuzzyScore,
  search,
  normalizeForMatching,
  SearchConfig,
  SearchResult,
} from '../src/core/search';
```

Then add these test suites before the closing of the file:

```typescript
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd D:/VS/kibble/web && npx vitest run tests/search.test.ts`
Expected: FAIL — `normalizeForMatching` is not exported, fuzzy tests fail.

- [ ] **Step 3: Add `normalizeForMatching` to `web/src/core/search.ts`**

Add after the existing imports (after line 1) in `web/src/core/search.ts`:

```typescript
// --- Normalization for fuzzy matching (ported from l10n-LLM QA pipeline) ---
const INLINE_TAG_RE = /<[^>]+>/g;      // <color>, <Text_Yellow02>, </>
const VARIABLE_RE = /\{[^}]+\}/g;       // {0}, {player_name}
const MULTI_SPACE_RE = /\s+/g;
const TRAILING_PUNCT_RE = /[.,!?;:~…]+$/;

export function normalizeForMatching(text: string): string {
  let t = text.replace(INLINE_TAG_RE, '');
  t = t.replace(VARIABLE_RE, '');
  t = t.replace(MULTI_SPACE_RE, ' ');
  t = t.trim().replace(TRAILING_PUNCT_RE, '');
  return t;
}
```

- [ ] **Step 4: Apply normalization in `fuzzyScore()`**

Replace the `fuzzyScore` function:

```typescript
export function fuzzyScore(query: string, text: string): number {
  if (!query || !text) return 0;
  const nq = normalizeForMatching(query).toLowerCase();
  const nt = normalizeForMatching(text).toLowerCase();
  if (!nq || !nt) return 0;
  return levenshteinRatio(nq, nt);
}
```

- [ ] **Step 5: Run all search tests**

Run: `cd D:/VS/kibble/web && npx vitest run tests/search.test.ts`
Expected: ALL PASS.

- [ ] **Step 6: Commit**

```bash
cd D:/VS/kibble
git add web/src/core/search.ts web/tests/search.test.ts
git commit -m "feat(web/search): add normalizeForMatching to web fuzzy scoring

Port normalization from l10n-LLM QA pipeline (TypeScript version).
Strips inline tags, variables, trailing punctuation before fuzzy
comparison so markup doesn't pollute similarity scores."
```

---

### Task 3: Verify no regressions across both platforms

- [ ] **Step 1: Run full desktop test suite**

Run: `cd D:/VS/kibble && .venv/Scripts/python -m pytest tests/ -v`
Expected: ALL PASS (42 tests).

- [ ] **Step 2: Run full web test suite**

Run: `cd D:/VS/kibble/web && npx vitest run`
Expected: ALL PASS (68 tests).

- [ ] **Step 3: Manual smoke test — verify normalization doesn't break substring search**

Substring search should NOT normalize (users typing `<color>` as a query should find literal `<color>` in text). Verify by checking that `substringScore("<color>", "<color>test")` still returns > 0 on both platforms. This is already covered by the architecture (normalization is only in the fuzzy path), but confirm no accidental leakage.

- [ ] **Step 4: Commit if any fixes were needed, otherwise done**
