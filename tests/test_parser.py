import pandas as pd
import pytest
from core.parser import parse_file, detect_columns, detect_encoding, check_entry_limit


class TestParseFile:
    def test_parse_xlsx(self, sample_xlsx):
        df = parse_file(str(sample_xlsx))
        assert len(df) == 3
        assert "KO" in df.columns
        assert "EN" in df.columns
        assert "JP" in df.columns

    def test_parse_csv_tab_delimited(self, sample_csv):
        df = parse_file(str(sample_csv))
        assert len(df) == 2
        assert "Korean" in df.columns

    def test_parse_txt(self, sample_txt):
        df = parse_file(str(sample_txt))
        assert len(df) == 2
        assert df.shape[1] >= 2

    def test_parse_unsupported_format(self, tmp_path):
        path = tmp_path / "test.docx"
        path.write_text("dummy")
        with pytest.raises(ValueError, match="Unsupported"):
            parse_file(str(path))

    def test_parse_empty_file(self, tmp_path):
        path = tmp_path / "empty.csv"
        path.write_text("")
        with pytest.raises(ValueError, match="No entries"):
            parse_file(str(path))

    def test_parse_euckr_encoding(self, sample_euckr_csv):
        df = parse_file(str(sample_euckr_csv))
        assert len(df) == 2
        assert "번역 메모리" in df.iloc[0].values


class TestDetectColumns:
    def test_detect_known_headers(self, sample_xlsx):
        df = parse_file(str(sample_xlsx))
        source, targets = detect_columns(df)
        assert source == "KO"
        assert "EN" in targets
        assert "JP" in targets

    def test_detect_by_korean_content(self, sample_txt):
        df = parse_file(str(sample_txt))
        source, targets = detect_columns(df)
        assert source == df.columns[0]
        assert len(targets) >= 1

    def test_detect_with_no_korean(self, tmp_path):
        path = tmp_path / "no_ko.csv"
        df = pd.DataFrame({"A": ["hello", "world"], "B": ["foo", "bar"]})
        df.to_csv(path, index=False)
        parsed = parse_file(str(path))
        source, targets = detect_columns(parsed)
        assert source == "A"


class TestCheckEntryLimit:
    def test_within_limit(self):
        check_entry_limit(400_000, 50_000, "test.xlsx")

    def test_exceeds_limit(self):
        with pytest.raises(ValueError, match="500K limit"):
            check_entry_limit(400_000, 200_000, "test.xlsx")

    def test_exact_limit(self):
        check_entry_limit(400_000, 100_000, "test.xlsx")


class TestDetectEncoding:
    def test_detect_utf8(self, sample_csv):
        encoding = detect_encoding(str(sample_csv))
        assert encoding.lower().replace("-", "") in ("utf8", "ascii", "utf-8")

    def test_detect_euckr(self, sample_euckr_csv):
        encoding = detect_encoding(str(sample_euckr_csv))
        assert encoding.lower().replace("-", "") in ("euckr", "cp949", "euc-kr")
