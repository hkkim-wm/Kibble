import re
from dataclasses import dataclass
from typing import List, Dict, Any

from rapidfuzz import fuzz


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
    return int(fuzz.token_set_ratio(query, text))


def search(entries: List[Dict[str, Any]], config: SearchConfig) -> List[Dict[str, Any]]:
    if len(config.query) < 2:
        return []
    results = []
    for entry in entries:
        text = entry["text"]
        score = 0
        if config.mode in ("substring", "both"):
            s = substring_score(config.query, text, case_sensitive=config.case_sensitive, wildcards=config.wildcards)
            score = max(score, s)
        if config.mode in ("fuzzy", "both"):
            f = fuzzy_score(config.query, text)
            score = max(score, f)
        if score >= config.threshold:
            results.append({"index": entry["index"], "score": score})
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:config.limit]
