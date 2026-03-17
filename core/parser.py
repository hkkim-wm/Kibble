import os
import re
from typing import Tuple, List

import chardet
import pandas as pd

LANG_PATTERNS = {
    "KO": re.compile(r"^(KO|Korean|한국어|ko-KR|kor)$", re.IGNORECASE),
    "EN": re.compile(r"^(EN|English|영어|en-US|en-GB|eng)$", re.IGNORECASE),
    "JP": re.compile(r"^(JP|JA|Japanese|일본어|ja-JP|jpn)$", re.IGNORECASE),
    # Chinese Traditional (Taiwan) and Simplified (PRC) as separate targets
    "CT": re.compile(r"^(CT|CHT|zh-TW|Chinese[\s_\-]?Traditional|Chinese[\s_\-]?\(?\s*Taiwan\s*\)?|중국어[\s_\-]?번체|繁體中文)$", re.IGNORECASE),
    "CS": re.compile(r"^(CS|CHS|zh-CN|Chinese[\s_\-]?Simplified|Chinese[\s_\-]?\(?\s*PRC\s*\)?|중국어[\s_\-]?간체|简体中文)$", re.IGNORECASE),
    "ZH": re.compile(r"^(ZH|Chinese|중국어|zho)$", re.IGNORECASE),
    "DE": re.compile(r"^(DE|German|독일어|de-DE|deu)$", re.IGNORECASE),
    "FR": re.compile(r"^(FR|French|프랑스어|fr-FR|fra)$", re.IGNORECASE),
    "ES": re.compile(r"^(ES|Spanish|스페인어|es-ES|spa)$", re.IGNORECASE),
    "PT": re.compile(r"^(PT|Portuguese|Portuguese[\s_\-]?\(?\s*Brazil\s*\)?|포르투갈어|pt-BR|pt-PT|por)$", re.IGNORECASE),
    "IT": re.compile(r"^(IT|Italian|이탈리아어|it-IT|ita)$", re.IGNORECASE),
    "RU": re.compile(r"^(RU|Russian|러시아어|ru-RU|rus)$", re.IGNORECASE),
    "TH": re.compile(r"^(TH|Thai|태국어|th-TH|tha)$", re.IGNORECASE),
    "VI": re.compile(r"^(VI|Vietnamese|베트남어|vi-VN|vie)$", re.IGNORECASE),
    "ID": re.compile(r"^(ID|Indonesian|인도네시아어|id-ID|ind)$", re.IGNORECASE),
    "AR": re.compile(r"^(AR|Arabic|아랍어|ar-SA|ara)$", re.IGNORECASE),
    "TR": re.compile(r"^(TR|Turkish|터키어|tr-TR|tur)$", re.IGNORECASE),
}

# Columns that contain relevant supplementary info (shown after translations)
_INFO_COL_RE = re.compile(
    r"^(note|notes|분류|category|comment|comments|remark|remarks|memo|description|설명)$",
    re.IGNORECASE,
)

# All recognized language codes (for classification)
_LANG_CODES = set(LANG_PATTERNS.keys())

# Common prefixes/suffixes stripped before matching language patterns
_COL_PREFIXES = re.compile(
    r"^(target|tgt|source|src|lang|translation|trans)[_\-\s.:]+",
    re.IGNORECASE,
)
_COL_SUFFIXES = re.compile(
    r"[_\-\s.:](target|tgt|source|src|lang|translation|trans)$",
    re.IGNORECASE,
)

HANGUL_RE = re.compile(r"[\uAC00-\uD7AF]")
MAX_ENTRIES = 500_000


def normalize_column_name(col_name: str) -> str:
    """Normalize a column name to a standard language code.

    Examples: "Target_EN" → "EN", "English" → "EN", "영어" → "EN",
              "ja-JP" → "JP", "tgt_French" → "FR".
    Returns the original name unchanged if no language pattern matches.
    """
    col_stripped = str(col_name).strip()

    # Try direct match first
    for lang_code, pattern in LANG_PATTERNS.items():
        if pattern.match(col_stripped):
            return lang_code

    # Strip common prefixes/suffixes and retry
    cleaned = _COL_PREFIXES.sub("", col_stripped)
    cleaned = _COL_SUFFIXES.sub("", cleaned).strip()
    if cleaned and cleaned != col_stripped:
        for lang_code, pattern in LANG_PATTERNS.items():
            if pattern.match(cleaned):
                return lang_code

    return col_stripped


def classify_column(norm_name: str) -> int:
    """Classify a normalized column name for display ordering.

    Returns:
        0 — translation column (known language code)
        1 — relevant info column (Note, 분류, etc.)
        2 — metadata / non-translation column (pushed to back)
    """
    if norm_name in _LANG_CODES:
        return 0
    if _INFO_COL_RE.match(norm_name):
        return 1
    return 2


def detect_encoding(file_path: str) -> str:
    with open(file_path, "rb") as f:
        raw = f.read(100_000)
    result = chardet.detect(raw)
    encoding = result.get("encoding", "utf-8") or "utf-8"
    enc_lower = encoding.lower().replace("-", "")
    if enc_lower in ("ascii", "utf8"):
        return "utf-8"
    return encoding


def _detect_delimiter(file_path: str, encoding: str) -> str:
    with open(file_path, "r", encoding=encoding, errors="replace") as f:
        sample = f.read(8192)
    counts = {"\t": sample.count("\t"), ",": sample.count(","), ";": sample.count(";")}
    if counts["\t"] > 0:
        return "\t"
    return max(counts, key=counts.get)


def parse_file(file_path: str) -> pd.DataFrame:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".xlsx":
        try:
            df = pd.read_excel(file_path, sheet_name=0, dtype=str)
        except Exception as e:
            raise ValueError(f"Could not read {os.path.basename(file_path)}: {e}")
        xls = pd.ExcelFile(file_path)
        df.attrs["extra_sheets"] = len(xls.sheet_names) - 1
        df.attrs["sheet_names"] = xls.sheet_names

    elif ext in (".csv", ".txt"):
        encoding = detect_encoding(file_path)
        delimiter = _detect_delimiter(file_path, encoding)
        # For .txt files, assume no header row
        header_arg = None if ext == ".txt" else "infer"
        try:
            df = pd.read_csv(file_path, sep=delimiter, encoding=encoding, dtype=str,
                             on_bad_lines="skip", header=header_arg)
        except pd.errors.EmptyDataError:
            raise ValueError(f"No entries found in {os.path.basename(file_path)}")
        except Exception:
            for fallback_enc in ["utf-8", "euc-kr", "cp949", "latin-1"]:
                try:
                    df = pd.read_csv(file_path, sep=delimiter, encoding=fallback_enc, dtype=str,
                                     on_bad_lines="skip", header=header_arg)
                    break
                except pd.errors.EmptyDataError:
                    raise ValueError(f"No entries found in {os.path.basename(file_path)}")
                except Exception:
                    continue
            else:
                raise ValueError(f"Could not read {os.path.basename(file_path)}")
    else:
        raise ValueError(f"Unsupported format: {ext}. Use .xlsx, .csv, or .txt")

    df = df.dropna(how="all").reset_index(drop=True)
    if len(df) == 0:
        raise ValueError(f"No entries found in {os.path.basename(file_path)}")
    df.attrs["source_file"] = os.path.basename(file_path)
    return df


def detect_columns(df: pd.DataFrame) -> Tuple[str, List[str]]:
    columns = list(df.columns)
    source = None

    for col in columns:
        col_stripped = str(col).strip()
        for lang_code, pattern in LANG_PATTERNS.items():
            if pattern.match(col_stripped):
                if lang_code == "KO":
                    source = col
                break

    if source is not None:
        targets = [c for c in columns if c != source]
        return source, targets

    scan_rows = min(10, len(df))
    korean_counts = {}
    for col in columns:
        count = 0
        for i in range(scan_rows):
            val = str(df.iloc[i][col]) if pd.notna(df.iloc[i][col]) else ""
            if HANGUL_RE.search(val):
                count += 1
        if count > 0:
            korean_counts[col] = count

    if korean_counts:
        for col in columns:
            if col in korean_counts:
                source = col
                break
        targets = [c for c in columns if c != source]
        return source, targets

    source = columns[0]
    targets = columns[1:] if len(columns) > 1 else []
    return source, targets


def check_entry_limit(current_total: int, new_count: int, file_name: str) -> None:
    if current_total + new_count > MAX_ENTRIES:
        raise ValueError(
            f"Cannot load {file_name}: total entries would exceed 500K limit "
            f"({current_total} + {new_count} = {current_total + new_count})"
        )
