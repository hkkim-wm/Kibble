import os
import sys
import pytest
import pandas as pd

# Add project root to sys.path so tests can import core/ui/workers modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def sample_xlsx(tmp_path):
    """Create a sample xlsx with KO/EN/JP columns."""
    path = tmp_path / "test.xlsx"
    df = pd.DataFrame({
        "KO": ["번역 메모리", "기계 번역", "용어집"],
        "EN": ["Translation Memory", "Machine Translation", "Glossary"],
        "JP": ["翻訳メモリ", "機械翻訳", "用語集"],
    })
    df.to_excel(path, index=False)
    return path


@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample tab-delimited CSV with KO/EN columns."""
    path = tmp_path / "test.csv"
    df = pd.DataFrame({
        "Korean": ["번역 메모리", "기계 번역"],
        "English": ["Translation Memory", "Machine Translation"],
    })
    df.to_csv(path, index=False, sep="\t")
    return path


@pytest.fixture
def sample_txt(tmp_path):
    """Create a sample tab-delimited TXT without headers."""
    path = tmp_path / "test.txt"
    content = "번역 메모리\tTranslation Memory\n기계 번역\tMachine Translation\n"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def sample_euckr_csv(tmp_path):
    """Create a CSV encoded in EUC-KR."""
    path = tmp_path / "euckr.csv"
    df = pd.DataFrame({
        "KO": ["번역 메모리", "기계 번역"],
        "EN": ["Translation Memory", "Machine Translation"],
    })
    df.to_csv(path, index=False, encoding="euc-kr")
    return path


@pytest.fixture
def large_xlsx(tmp_path):
    """Create a large xlsx for limit testing (1000 rows)."""
    path = tmp_path / "large.xlsx"
    df = pd.DataFrame({
        "KO": [f"용어_{i}" for i in range(1000)],
        "EN": [f"Term_{i}" for i in range(1000)],
    })
    df.to_excel(path, index=False)
    return path
