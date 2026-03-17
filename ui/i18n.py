TRANSLATIONS = {
    "en": {
        "search_for": "Search for",
        "btn_search": "Search",
        "case_sensitive": "Case sensitive",
        "add_wildcards": "Add wildcards",
        "search_in_source": "Search in source",
        "search_in_target": "Search in target",
        "filter_target": "Filter target",
        "filter_source": "Filter source",
        "match_mode": "Match",
        "mode_substring": "Substring",
        "mode_fuzzy": "Fuzzy",
        "mode_both": "Both",
        "threshold": "Threshold",
        "limit": "Limit",
        "total_hits": "Total hits",
        "search_all": "Search All",
        "three_col_view": "Three-column view",
        "source_target_view": "Source + target",
        "drop_hint": "Drop files here or Ctrl+O to browse",
        "configure_columns": "Configure Columns",
        "restore_session": "Restore last session?",
        "copy_success": "Copied to clipboard",
        "limit_exceeded": "Cannot load {file}: total entries would exceed 500K limit ({current} + {new} = {sum})",
        "no_entries": "No entries found in {file}",
        "unsupported_format": "Unsupported format. Use .xlsx, .csv, or .txt",
        "file_not_found": "{file} not found, skipping",
        "loading": "Loading...",
        "extra_sheets": "{file} has {n} additional sheets (only first sheet loaded)",
        "btn_yes": "Yes",
        "btn_no": "No",
        "copy_row": "Copy row",
        "copy_cell": "Copy cell",
        "copy_source_only": "Copy source only",
        "copy_target_only": "Copy target only",
        "could_not_read": "Could not read {file}",
        "match_pct": "Match %",
        "source_col": "Source (KO)",
        "meta_info": "Meta-info",
        "word_wrap": "Word wrap",
        "global_hotkey": "Ctrl+C → Ctrl+Shift+K",
    },
    "ko": {
        "search_for": "검색어",
        "btn_search": "검색",
        "case_sensitive": "대소문자 구분",
        "add_wildcards": "와일드카드 추가",
        "search_in_source": "원문에서 검색",
        "search_in_target": "번역문에서 검색",
        "filter_target": "번역문 필터",
        "filter_source": "원문 필터",
        "match_mode": "일치 방식",
        "mode_substring": "부분 일치",
        "mode_fuzzy": "유사 일치",
        "mode_both": "모두",
        "threshold": "최소 일치율",
        "limit": "최대 결과",
        "total_hits": "총 검색 결과",
        "search_all": "전체 검색",
        "three_col_view": "3열 보기",
        "source_target_view": "원문 + 번역문",
        "drop_hint": "파일을 끌어놓거나 Ctrl+O로 찾아보기",
        "configure_columns": "열 설정",
        "restore_session": "이전 세션을 복원하시겠습니까?",
        "copy_success": "클립보드에 복사됨",
        "limit_exceeded": "{file} 로드 불가: 총 항목이 50만 제한을 초과합니다 ({current} + {new} = {sum})",
        "no_entries": "{file}에서 항목을 찾을 수 없습니다",
        "unsupported_format": "지원하지 않는 형식입니다. xlsx, csv, txt 파일을 사용하세요",
        "file_not_found": "{file}을(를) 찾을 수 없어 건너뜁니다",
        "loading": "불러오는 중...",
        "extra_sheets": "{file}에 {n}개의 추가 시트가 있습니다 (첫 번째 시트만 로드됨)",
        "btn_yes": "예",
        "btn_no": "아니오",
        "copy_row": "행 복사",
        "copy_cell": "셀 복사",
        "copy_source_only": "원문만 복사",
        "copy_target_only": "번역문만 복사",
        "could_not_read": "{file}을(를) 읽을 수 없습니다",
        "match_pct": "일치율",
        "source_col": "원문 (KO)",
        "meta_info": "메타 정보",
        "word_wrap": "줄 바꿈",
        "global_hotkey": "Ctrl+C → Ctrl+Shift+K",
    },
}


class I18n:
    """Internationalization helper with EN/KO support."""

    def __init__(self, language: str = "ko"):
        self.language = language

    def set_language(self, language: str) -> None:
        self.language = language

    def t(self, key: str, **kwargs) -> str:
        """Get translated string. Supports {placeholder} formatting."""
        strings = TRANSLATIONS.get(self.language, TRANSLATIONS["ko"])
        text = strings.get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass
        return text
