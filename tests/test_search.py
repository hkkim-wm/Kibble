import pytest
from core.search import substring_score, fuzzy_score, search, SearchConfig, normalize_for_matching


class TestSubstringScore:
    def test_exact_match(self):
        assert substring_score("번역 메모리", "번역 메모리") == 100

    def test_substring_found(self):
        score = substring_score("번역", "번역 메모리")
        assert 75 <= score < 100

    def test_no_match(self):
        assert substring_score("없는단어", "번역 메모리") == 0

    def test_case_insensitive(self):
        score = substring_score("translation", "Translation Memory")
        assert score > 0

    def test_case_sensitive(self):
        assert substring_score("translation", "Translation Memory", case_sensitive=True) == 0

    def test_wildcard_match(self):
        score = substring_score("번역*메모리", "번역 관리 메모리", wildcards=True)
        assert score > 0

    def test_wildcard_no_match(self):
        score = substring_score("번역*용어", "번역 메모리", wildcards=True)
        assert score == 0


class TestFuzzyScore:
    def test_exact_match(self):
        assert fuzzy_score("번역 메모리", "번역 메모리") == 100

    def test_partial_overlap(self):
        score = fuzzy_score("번역 메모리 파일", "번역 메모리 관리")
        assert 50 < score < 100

    def test_no_overlap(self):
        score = fuzzy_score("완전히 다른 텍스트", "번역 메모리")
        assert score < 50


class TestSearch:
    def test_search_returns_sorted_results(self):
        entries = [
            {"text": "번역 메모리", "index": 0},
            {"text": "기계 번역", "index": 1},
            {"text": "용어집", "index": 2},
        ]
        config = SearchConfig(query="번역 메모리", mode="both", threshold=50, limit=200, case_sensitive=False, wildcards=False)
        results = search(entries, config)
        assert len(results) > 0
        assert results[0]["index"] == 0
        assert results[0]["score"] == 100
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_respects_threshold(self):
        entries = [
            {"text": "번역 메모리", "index": 0},
            {"text": "완전히 다른 것", "index": 1},
        ]
        config = SearchConfig(query="번역 메모리", mode="both", threshold=50, limit=200, case_sensitive=False, wildcards=False)
        results = search(entries, config)
        for r in results:
            assert r["score"] >= 50

    def test_search_respects_limit(self):
        entries = [{"text": f"번역 {i}", "index": i} for i in range(100)]
        config = SearchConfig(query="번역", mode="substring", threshold=0, limit=10, case_sensitive=False, wildcards=False)
        results = search(entries, config)
        assert len(results) <= 10

    def test_search_substring_only_mode(self):
        entries = [{"text": "번역 메모리", "index": 0}]
        config = SearchConfig(query="번역", mode="substring", threshold=0, limit=200, case_sensitive=False, wildcards=False)
        results = search(entries, config)
        assert len(results) == 1

    def test_search_fuzzy_only_mode(self):
        entries = [{"text": "번역 메모리", "index": 0}]
        config = SearchConfig(query="번역 메모리", mode="fuzzy", threshold=0, limit=200, case_sensitive=False, wildcards=False)
        results = search(entries, config)
        assert len(results) == 1

    def test_search_minimum_query_length(self):
        entries = [{"text": "번역", "index": 0}]
        config = SearchConfig(query="번", mode="both", threshold=0, limit=200, case_sensitive=False, wildcards=False)
        results = search(entries, config)
        assert len(results) == 0

    def test_search_empty_query(self):
        entries = [{"text": "번역", "index": 0}]
        config = SearchConfig(query="", mode="both", threshold=0, limit=200, case_sensitive=False, wildcards=False)
        results = search(entries, config)
        assert len(results) == 0


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
