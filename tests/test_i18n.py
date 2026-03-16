from ui.i18n import I18n


class TestI18n:
    def test_default_language_is_ko(self):
        i18n = I18n()
        assert i18n.language == "ko"

    def test_get_ko_string(self):
        i18n = I18n(language="ko")
        assert i18n.t("btn_search") == "검색"

    def test_get_en_string(self):
        i18n = I18n(language="en")
        assert i18n.t("btn_search") == "Search"

    def test_switch_language(self):
        i18n = I18n(language="ko")
        assert i18n.t("btn_search") == "검색"
        i18n.set_language("en")
        assert i18n.t("btn_search") == "Search"

    def test_missing_key_returns_key(self):
        i18n = I18n()
        assert i18n.t("nonexistent_key") == "nonexistent_key"

    def test_format_placeholders(self):
        i18n = I18n(language="en")
        result = i18n.t("no_entries", file="test.xlsx")
        assert "test.xlsx" in result
