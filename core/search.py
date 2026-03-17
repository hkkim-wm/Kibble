import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process


@dataclass
class SearchConfig:
    query: str
    mode: str  # "substring", "fuzzy", "both"
    threshold: int  # 0-100
    limit: int  # max results
    case_sensitive: bool
    wildcards: bool


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
    # Use fuzz.ratio for strict full-string similarity.
    # WRatio/token_set_ratio inflate scores when strings share
    # even a single common token (e.g. "및") due to partial matching.
    # fuzz.ratio compares entire strings honestly.
    return int(fuzz.ratio(query, text))


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

    # --- Substring matching (vectorized with pandas) ---
    if config.mode in ("substring", "both"):
        query = config.query
        case = config.case_sensitive

        if config.wildcards:
            # Build regex pattern from glob
            glob_q = query if "*" in query else f"*{query}*"
            regex_pat = _glob_to_regex(glob_q)
            mask = texts_clean.str.contains(regex_pat, case=case, regex=True, na=False)
            q_clean = query.replace("*", "")
            if q_clean:
                matched_texts = texts_clean[mask]
                q_len = len(q_clean)
                # Exact match = 100, otherwise 75 + 25 * ratio
                q_lower = q_clean if case else q_clean.lower()
                t_lower = matched_texts if case else matched_texts.str.lower()
                is_exact = t_lower == q_lower
                lengths = matched_texts.str.len().replace(0, 1)
                ratio_scores = 75 + 25 * (q_len / lengths)
                sub_scores = np.where(is_exact, 100, ratio_scores)
                scores[mask.values] = np.maximum(scores[mask.values], sub_scores)
        else:
            # Simple substring containment
            mask = texts_clean.str.contains(
                re.escape(query), case=case, regex=True, na=False
            )
            if mask.any():
                matched_texts = texts_clean[mask]
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
        texts_list = texts_clean.tolist()
        fuzzy_results = process.extract(
            config.query,
            texts_list,
            scorer=fuzz.ratio,
            limit=None,
            score_cutoff=max(config.threshold, 1),  # Skip below threshold early
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
