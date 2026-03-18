/**
 * Core parser — TypeScript port of desktop `core/parser.py`.
 *
 * Handles file parsing (xlsx / csv / txt), column normalisation,
 * language detection and entry-limit checking.
 */

import * as XLSX from "xlsx";
import Papa from "papaparse";
import jschardet from "jschardet";

/* ------------------------------------------------------------------ */
/*  Language patterns                                                   */
/* ------------------------------------------------------------------ */

export const LANG_PATTERNS: Record<string, RegExp> = {
  KO: /^(KO|Korean|한국어|ko-KR|kor|Source)$/i,
  EN: /^(EN|English|영어|en-US|en-GB|eng)$/i,
  JP: /^(JP|JA|Japanese|일본어|ja-JP|jpn)$/i,
  CT: /^(CT|CHT|zh-TW|zh-Hant|TW|Chinese[\s_-]?Traditional|Chinese[\s_-]?\(?\s*Taiwan\s*\)?|중국어[\s_-]?번체|繁體中文)$/i,
  CS: /^(CS|CHS|zh-CN|zh-Hans|Chinese[\s_-]?Simplified|Chinese[\s_-]?\(?\s*PRC\s*\)?|중국어[\s_-]?간체|简体中文)$/i,
  ZH: /^(ZH|Chinese|중국어|zho)$/i,
  DE: /^(DE|German|독일어|de-DE|deu)$/i,
  FR: /^(FR|French|프랑스어|fr-FR|fra)$/i,
  ES: /^(ES|Spanish|스페인어|es-ES|spa|ES-LATAM|Spanish[\s_-]?\(?\s*Latin\s*America\s*\)?)$/i,
  PT: /^(PT|Portuguese|Portuguese[\s_-]?\(?\s*Brazil\s*\)?|포르투갈어|pt-BR|pt-PT|por)$/i,
  IT: /^(IT|Italian|이탈리아어|it-IT|ita)$/i,
  RU: /^(RU|Russian|러시아어|ru-RU|rus)$/i,
  TH: /^(TH|Thai|태국어|th-TH|tha)$/i,
  VI: /^(VI|Vietnamese|베트남어|vi-VN|vie)$/i,
  ID: /^(ID|Indonesian|인도네시아어|id-ID|ind)$/i,
  AR: /^(AR|Arabic|아랍어|ar-SA|ara)$/i,
  TR: /^(TR|Turkish|터키어|tr-TR|tur)$/i,
};

const _INFO_COL_RE =
  /^(note|notes|분류|category|comment|comments|remark|remarks|memo|description|설명)$/i;

const _LANG_CODES = new Set(Object.keys(LANG_PATTERNS));

const _COL_PREFIXES =
  /^(target|tgt|source|src|lang|translation|trans)[_\-\s.:]+/i;
const _COL_SUFFIXES =
  /[_\-\s.:](target|tgt|source|src|lang|translation|trans)$/i;

const HANGUL_RE = /[\uAC00-\uD7AF]/;

const MAX_ENTRIES = 500_000;

/* ------------------------------------------------------------------ */
/*  Column helpers                                                     */
/* ------------------------------------------------------------------ */

/**
 * Normalize a column header to a standard language code.
 *
 * "Target_EN" → "EN", "English" → "EN", "영어" → "EN",
 * "ja-JP" → "JP", "tgt_French" → "FR".
 *
 * Returns the original (trimmed) name unchanged if no pattern matches.
 */
export function normalizeColumnName(colName: string): string {
  const colStripped = String(colName).trim();

  // Direct match
  for (const [langCode, pattern] of Object.entries(LANG_PATTERNS)) {
    if (pattern.test(colStripped)) return langCode;
  }

  // Strip common prefixes / suffixes and retry
  let cleaned = colStripped.replace(_COL_PREFIXES, "");
  cleaned = cleaned.replace(_COL_SUFFIXES, "").trim();

  if (cleaned && cleaned !== colStripped) {
    for (const [langCode, pattern] of Object.entries(LANG_PATTERNS)) {
      if (pattern.test(cleaned)) return langCode;
    }
  }

  return colStripped;
}

/**
 * Classify a normalized column name for display ordering.
 *
 * 0 — language column (known code)
 * 1 — info column (note, category, comment …)
 * 2 — metadata / non-translation column
 */
export function classifyColumn(normName: string): 0 | 1 | 2 {
  if (_LANG_CODES.has(normName)) return 0;
  if (_INFO_COL_RE.test(normName)) return 1;
  return 2;
}

/* ------------------------------------------------------------------ */
/*  Encoding detection                                                 */
/* ------------------------------------------------------------------ */

function detectEncoding(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer).slice(0, 100_000);
  const result = jschardet.detect(
    // jschardet wants a binary string
    Array.from(bytes)
      .map((b) => String.fromCharCode(b))
      .join(""),
  );
  const encoding = result.encoding ?? "utf-8";
  const encLower = encoding.toLowerCase().replace(/-/g, "");
  if (encLower === "ascii" || encLower === "utf8") return "utf-8";
  return encoding;
}

function decodeBuffer(buffer: ArrayBuffer, encoding: string): string {
  try {
    const decoder = new TextDecoder(encoding);
    return decoder.decode(buffer);
  } catch {
    // Fallback chain
    for (const fb of ["utf-8", "euc-kr", "iso-8859-1"]) {
      try {
        return new TextDecoder(fb).decode(buffer);
      } catch {
        continue;
      }
    }
    // Last resort — latin1 never throws
    return new TextDecoder("iso-8859-1").decode(buffer);
  }
}

/* ------------------------------------------------------------------ */
/*  File parsing                                                       */
/* ------------------------------------------------------------------ */

export interface ParseResult {
  /** Array of row objects (column → value). */
  data: Record<string, string>[];
  /** Ordered column names. */
  columns: string[];
  /** Number of additional sheets (xlsx only, else 0). */
  extraSheets: number;
  /** Original file name. */
  sourceFile: string;
}

/**
 * Parse an uploaded File (xlsx / csv / txt) and return structured data.
 */
export async function parseFile(file: File): Promise<ParseResult> {
  const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  const buffer = await file.arrayBuffer();

  if (ext === ".xlsx") {
    return parseXlsx(buffer, file.name);
  } else if (ext === ".csv" || ext === ".txt") {
    return parseCsvTxt(buffer, ext, file.name);
  }

  throw new Error(
    `Unsupported format: ${ext}. Use .xlsx, .csv, or .txt`,
  );
}

function parseXlsx(buffer: ArrayBuffer, fileName: string): ParseResult {
  let workbook: XLSX.WorkBook;
  try {
    workbook = XLSX.read(buffer, { type: "array" });
  } catch (e) {
    throw new Error(
      `Could not read ${fileName}: ${e instanceof Error ? e.message : e}`,
    );
  }

  const sheetName = workbook.SheetNames[0];
  const sheet = workbook.Sheets[sheetName];
  const rows: Record<string, string>[] = XLSX.utils.sheet_to_json(sheet, {
    defval: "",
    raw: false,
  });

  if (rows.length === 0) {
    throw new Error(`No entries found in ${fileName}`);
  }

  const columns = Object.keys(rows[0]);

  // Drop all-empty rows
  const data = rows.filter((row) =>
    columns.some((c) => row[c] !== undefined && String(row[c]).trim() !== ""),
  );

  if (data.length === 0) {
    throw new Error(`No entries found in ${fileName}`);
  }

  return {
    data,
    columns,
    extraSheets: workbook.SheetNames.length - 1,
    sourceFile: fileName,
  };
}

function parseCsvTxt(
  buffer: ArrayBuffer,
  ext: string,
  fileName: string,
): ParseResult {
  const encoding = detectEncoding(buffer);
  const text = decodeBuffer(buffer, encoding);

  const hasHeader = ext !== ".txt";

  const parsed = Papa.parse<Record<string, string>>(text, {
    header: hasHeader,
    delimiter: "", // auto-detect
    skipEmptyLines: "greedy",
    dynamicTyping: false,
  });

  if (parsed.data.length === 0) {
    throw new Error(`No entries found in ${fileName}`);
  }

  let columns: string[];
  let data: Record<string, string>[];

  if (hasHeader) {
    columns = parsed.meta.fields ?? Object.keys(parsed.data[0]);
    data = parsed.data;
  } else {
    // txt — no header; generate Col0, Col1, …
    const firstRow = parsed.data[0];
    const nCols = Object.keys(firstRow).length;
    columns = Array.from({ length: nCols }, (_, i) => `Col${i}`);

    // Papa with header:false gives arrays disguised as objects keyed "0","1",…
    data = (parsed.data as unknown as string[][]).map((row) => {
      const obj: Record<string, string> = {};
      columns.forEach((c, i) => {
        obj[c] = row[i] ?? "";
      });
      return obj;
    });
  }

  // Drop all-empty rows
  data = data.filter((row) =>
    columns.some((c) => row[c] !== undefined && String(row[c]).trim() !== ""),
  );

  if (data.length === 0) {
    throw new Error(`No entries found in ${fileName}`);
  }

  return { data, columns, extraSheets: 0, sourceFile: fileName };
}

/* ------------------------------------------------------------------ */
/*  Column detection                                                   */
/* ------------------------------------------------------------------ */

export interface ColumnDetection {
  source: string;
  targets: string[];
}

/**
 * Detect source (Korean) column and target columns.
 *
 * 1. Check language patterns — if KO matches, that's the source.
 * 2. Scan first 10 rows for Hangul content.
 * 3. Fall back to first column.
 */
export function detectColumns(
  data: Record<string, string>[],
  columns: string[],
): ColumnDetection {
  let source: string | null = null;

  // 1. Header-based detection
  for (const col of columns) {
    const colStripped = String(col).trim();
    for (const [langCode, pattern] of Object.entries(LANG_PATTERNS)) {
      if (pattern.test(colStripped)) {
        if (langCode === "KO") {
          source = col;
        }
        break;
      }
    }
  }

  if (source !== null) {
    return { source, targets: columns.filter((c) => c !== source) };
  }

  // 2. Content scan for Hangul
  const scanRows = Math.min(10, data.length);
  const koreanCounts: Record<string, number> = {};

  for (const col of columns) {
    let count = 0;
    for (let i = 0; i < scanRows; i++) {
      const val = data[i]?.[col];
      if (val != null && HANGUL_RE.test(String(val))) {
        count++;
      }
    }
    if (count > 0) {
      koreanCounts[col] = count;
    }
  }

  if (Object.keys(koreanCounts).length > 0) {
    // Pick the first column (in original order) that has Korean
    for (const col of columns) {
      if (col in koreanCounts) {
        source = col;
        break;
      }
    }
    return { source: source!, targets: columns.filter((c) => c !== source) };
  }

  // 3. Fallback — first column
  source = columns[0];
  return {
    source,
    targets: columns.length > 1 ? columns.slice(1) : [],
  };
}

/* ------------------------------------------------------------------ */
/*  Entry limit                                                        */
/* ------------------------------------------------------------------ */

/**
 * Throw if adding `newCount` entries to `currentTotal` would exceed 500K.
 */
export function checkEntryLimit(
  currentTotal: number,
  newCount: number,
  fileName: string,
): void {
  if (currentTotal + newCount > MAX_ENTRIES) {
    throw new Error(
      `Cannot load ${fileName}: total entries would exceed 500K limit ` +
        `(${currentTotal} + ${newCount} = ${currentTotal + newCount})`,
    );
  }
}
