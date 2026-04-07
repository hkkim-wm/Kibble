import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process

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


@dataclass
class SearchConfig:
    query: str
    mode: str  # "substring", "fuzzy", "both"
    threshold: int  # 0-100
    limit: int  # max results
    case_sensitive: bool
    wildcards: bool
    ignore_spaces: bool = False
    whole_word: bool = False


def _glob_to_regex(pattern: str) -> str:
    parts = pattern.split("*")
    escaped = [re.escape(p) for p in parts]
    return ".*".join(escaped)


def substring_score(query: str, text: str, case_sensitive: bool = False, wildcards: bool = False) -> int:
    if not query or not text:
        return 0
    q = query if case_sensitive else query.lower()
    t = text if case_sensitive else text.lower()

    if wildcards:
        glob_q = q if "*" in q else f"*{q}*"
        regex_pattern = _glob_to_regex(glob_q)
        flags = 0 if case_sensitive else re.IGNORECASE
        if re.search(regex_pattern, t, flags):
            q_clean = q.replace("*", "")
            if not q_clean:
                return 0
            if q_clean == t:
                return 100
            ratio = len(q_clean) / len(t)
            return int(75 + 25 * ratio)
        return 0

    if q == t:
        return 100
    if q in t:
        ratio = len(q) / len(t)
        return int(75 + 25 * ratio)
    return 0


def fuzzy_score(query: str, text: str) -> int:
    if not query or not text:
        return 0
    nq = normalize_for_matching(query)
    nt = normalize_for_matching(text)
    if not nq or not nt:
        return 0
    return int(fuzz.ratio(nq, nt))


def search_vectorized(texts: pd.Series, config: SearchConfig) -> pd.DataFrame:
    """Vectorized search using pandas str operations and RapidFuzz batch API.

    Args:
        texts: pandas Series of strings to search against.
        config: Search configuration.

    Returns:
        DataFrame with columns ["index", "score"], sorted by score descending,
        limited to config.limit rows. "index" corresponds to the position in texts.
    """
    if len(config.query) < 2 or len(texts) == 0:
        return pd.DataFrame(columns=["index", "score"])

    n = len(texts)
    # Fill NaN with empty string for safe operations
    texts_clean = texts.fillna("").astype(str)
    scores = np.zeros(n, dtype=np.float32)

    # --- Whitespace normalization ---
    # When ignore_spaces is on, strip all whitespace from both query and texts
    # for matching purposes. Original texts are preserved for display.
    if config.ignore_spaces:
        texts_normalized = texts_clean.str.replace(r"\s+", "", regex=True)
        query_normalized = re.sub(r"\s+", "", config.query)
    else:
        texts_normalized = texts_clean
        query_normalized = config.query

    # --- Substring matching (vectorized with pandas) ---
    if config.mode in ("substring", "both"):
        query = query_normalized
        case = config.case_sensitive

        if config.wildcards:
            # Build regex pattern from glob
            glob_q = query if "*" in query else f"*{query}*"
            regex_pat = _glob_to_regex(glob_q)
            mask = texts_normalized.str.contains(regex_pat, case=case, regex=True, na=False)
            q_clean = query.replace("*", "")
            if q_clean:
                matched_texts = texts_normalized[mask]
                q_len = len(q_clean)
                q_lower = q_clean if case else q_clean.lower()
                t_lower = matched_texts if case else matched_texts.str.lower()
                is_exact = t_lower == q_lower
                lengths = matched_texts.str.len().replace(0, 1)
                ratio_scores = 75 + 25 * (q_len / lengths)
                sub_scores = np.where(is_exact, 100, ratio_scores)
                scores[mask.values] = np.maximum(scores[mask.values], sub_scores)
        elif config.whole_word:
            # Whole-word matching: use word boundaries for Latin/non-CJK text,
            # fall back to normal substring for CJK text
            _CJK_RE = re.compile(r'[\uAC00-\uD7AF\u3000-\u9FFF]')
            if _CJK_RE.search(query):
                # CJK text: fall back to normal substring
                mask = texts_normalized.str.contains(
                    re.escape(query), case=case, regex=True, na=False
                )
            else:
                # Latin/non-CJK: use word boundary regex
                word_pattern = r'\b' + re.escape(query) + r'\b'
                mask = texts_normalized.str.contains(
                    word_pattern, case=case, regex=True, na=False
                )
            if mask.any():
                matched_texts = texts_normalized[mask]
                q_len = len(query)
                q_compare = query if case else query.lower()
                t_compare = matched_texts if case else matched_texts.str.lower()
                is_exact = t_compare == q_compare
                lengths = matched_texts.str.len().replace(0, 1)
                ratio_scores = 75 + 25 * (q_len / lengths)
                sub_scores = np.where(is_exact, 100, ratio_scores)
                scores[mask.values] = np.maximum(scores[mask.values], sub_scores)
        else:
            # Simple substring containment
            mask = texts_normalized.str.contains(
                re.escape(query), case=case, regex=True, na=False
            )
            if mask.any():
                matched_texts = texts_normalized[mask]
                q_len = len(query)
                q_compare = query if case else query.lower()
                t_compare = matched_texts if case else matched_texts.str.lower()
                is_exact = t_compare == q_compare
                lengths = matched_texts.str.len().replace(0, 1)
                ratio_scores = 75 + 25 * (q_len / lengths)
                sub_scores = np.where(is_exact, 100, ratio_scores)
                scores[mask.values] = np.maximum(scores[mask.values], sub_scores)

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

    # Filter by threshold
    mask = scores >= config.threshold
    indices = np.where(mask)[0]
    matched_scores = scores[indices]

    # Sort by score descending, then by original index ascending (stable file order for ties)
    sort_order = np.lexsort((indices, -matched_scores))
    indices = indices[sort_order]
    matched_scores = matched_scores[sort_order]

    # Apply limit
    indices = indices[:config.limit]
    matched_scores = matched_scores[:config.limit]

    return pd.DataFrame({
        "index": indices.astype(int),
        "score": matched_scores.astype(int),
    })


def search(entries: List[Dict[str, Any]], config: SearchConfig) -> List[Dict[str, Any]]:
    """Legacy entry-point: wraps search_vectorized for backward compatibility."""
    if len(config.query) < 2:
        return []
    texts = pd.Series([e["text"] for e in entries])
    result_df = search_vectorized(texts, config)
    return [
        {"index": int(row["index"]), "score": int(row["score"])}
        for _, row in result_df.iterrows()
    ]
