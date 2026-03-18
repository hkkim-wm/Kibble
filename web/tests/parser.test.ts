import { describe, it, expect } from "vitest";
import {
  normalizeColumnName,
  classifyColumn,
  detectColumns,
  checkEntryLimit,
  LANG_PATTERNS,
} from "../src/core/parser";

/* ------------------------------------------------------------------ */
/*  normalizeColumnName                                                */
/* ------------------------------------------------------------------ */
describe("normalizeColumnName", () => {
  it("maps exact language codes", () => {
    expect(normalizeColumnName("KO")).toBe("KO");
    expect(normalizeColumnName("EN")).toBe("EN");
    expect(normalizeColumnName("JP")).toBe("JP");
    expect(normalizeColumnName("CT")).toBe("CT");
    expect(normalizeColumnName("CS")).toBe("CS");
    expect(normalizeColumnName("ZH")).toBe("ZH");
    expect(normalizeColumnName("DE")).toBe("DE");
    expect(normalizeColumnName("FR")).toBe("FR");
    expect(normalizeColumnName("ES")).toBe("ES");
    expect(normalizeColumnName("PT")).toBe("PT");
    expect(normalizeColumnName("IT")).toBe("IT");
    expect(normalizeColumnName("RU")).toBe("RU");
    expect(normalizeColumnName("TH")).toBe("TH");
    expect(normalizeColumnName("VI")).toBe("VI");
    expect(normalizeColumnName("ID")).toBe("ID");
    expect(normalizeColumnName("AR")).toBe("AR");
    expect(normalizeColumnName("TR")).toBe("TR");
  });

  it("maps locale codes to standard codes", () => {
    expect(normalizeColumnName("ko-KR")).toBe("KO");
    expect(normalizeColumnName("en-US")).toBe("EN");
    expect(normalizeColumnName("en-GB")).toBe("EN");
    expect(normalizeColumnName("ja-JP")).toBe("JP");
    expect(normalizeColumnName("zh-TW")).toBe("CT");
    expect(normalizeColumnName("zh-Hant")).toBe("CT");
    expect(normalizeColumnName("zh-CN")).toBe("CS");
    expect(normalizeColumnName("zh-Hans")).toBe("CS");
    expect(normalizeColumnName("de-DE")).toBe("DE");
    expect(normalizeColumnName("fr-FR")).toBe("FR");
    expect(normalizeColumnName("es-ES")).toBe("ES");
    expect(normalizeColumnName("pt-BR")).toBe("PT");
    expect(normalizeColumnName("pt-PT")).toBe("PT");
    expect(normalizeColumnName("it-IT")).toBe("IT");
    expect(normalizeColumnName("ru-RU")).toBe("RU");
    expect(normalizeColumnName("th-TH")).toBe("TH");
    expect(normalizeColumnName("vi-VN")).toBe("VI");
    expect(normalizeColumnName("id-ID")).toBe("ID");
    expect(normalizeColumnName("ar-SA")).toBe("AR");
    expect(normalizeColumnName("tr-TR")).toBe("TR");
  });

  it("maps full language names (English)", () => {
    expect(normalizeColumnName("Korean")).toBe("KO");
    expect(normalizeColumnName("English")).toBe("EN");
    expect(normalizeColumnName("Japanese")).toBe("JP");
    expect(normalizeColumnName("German")).toBe("DE");
    expect(normalizeColumnName("French")).toBe("FR");
    expect(normalizeColumnName("Spanish")).toBe("ES");
    expect(normalizeColumnName("Portuguese")).toBe("PT");
    expect(normalizeColumnName("Italian")).toBe("IT");
    expect(normalizeColumnName("Russian")).toBe("RU");
    expect(normalizeColumnName("Thai")).toBe("TH");
    expect(normalizeColumnName("Vietnamese")).toBe("VI");
    expect(normalizeColumnName("Indonesian")).toBe("ID");
    expect(normalizeColumnName("Arabic")).toBe("AR");
    expect(normalizeColumnName("Turkish")).toBe("TR");
  });

  it("maps Korean labels", () => {
    expect(normalizeColumnName("한국어")).toBe("KO");
    expect(normalizeColumnName("영어")).toBe("EN");
    expect(normalizeColumnName("일본어")).toBe("JP");
    expect(normalizeColumnName("중국어 번체")).toBe("CT");
    expect(normalizeColumnName("중국어 간체")).toBe("CS");
    expect(normalizeColumnName("중국어")).toBe("ZH");
    expect(normalizeColumnName("독일어")).toBe("DE");
    expect(normalizeColumnName("프랑스어")).toBe("FR");
    expect(normalizeColumnName("스페인어")).toBe("ES");
    expect(normalizeColumnName("포르투갈어")).toBe("PT");
    expect(normalizeColumnName("이탈리아어")).toBe("IT");
    expect(normalizeColumnName("러시아어")).toBe("RU");
    expect(normalizeColumnName("태국어")).toBe("TH");
    expect(normalizeColumnName("베트남어")).toBe("VI");
    expect(normalizeColumnName("인도네시아어")).toBe("ID");
    expect(normalizeColumnName("아랍어")).toBe("AR");
    expect(normalizeColumnName("터키어")).toBe("TR");
  });

  it("maps v1.1 patterns (Chinese variants, ES-LATAM, etc.)", () => {
    expect(normalizeColumnName("CHT")).toBe("CT");
    expect(normalizeColumnName("CHS")).toBe("CS");
    expect(normalizeColumnName("Chinese Traditional")).toBe("CT");
    expect(normalizeColumnName("Chinese Simplified")).toBe("CS");
    expect(normalizeColumnName("Chinese (Taiwan)")).toBe("CT");
    expect(normalizeColumnName("Chinese (PRC)")).toBe("CS");
    expect(normalizeColumnName("繁體中文")).toBe("CT");
    expect(normalizeColumnName("简体中文")).toBe("CS");
    expect(normalizeColumnName("ES-LATAM")).toBe("ES");
    expect(normalizeColumnName("Spanish (Latin America)")).toBe("ES");
    expect(normalizeColumnName("Portuguese (Brazil)")).toBe("PT");
    expect(normalizeColumnName("Source")).toBe("KO");
    expect(normalizeColumnName("JA")).toBe("JP");
  });

  it("is case-insensitive", () => {
    expect(normalizeColumnName("ko")).toBe("KO");
    expect(normalizeColumnName("english")).toBe("EN");
    expect(normalizeColumnName("JAPANESE")).toBe("JP");
    expect(normalizeColumnName("chinese traditional")).toBe("CT");
  });

  it("strips common prefixes and retries", () => {
    expect(normalizeColumnName("target_EN")).toBe("EN");
    expect(normalizeColumnName("tgt_FR")).toBe("FR");
    expect(normalizeColumnName("src_KO")).toBe("KO");
    expect(normalizeColumnName("source_Korean")).toBe("KO");
    expect(normalizeColumnName("translation_JP")).toBe("JP");
    expect(normalizeColumnName("trans_DE")).toBe("DE");
    expect(normalizeColumnName("lang_ES")).toBe("ES");
  });

  it("strips common suffixes and retries", () => {
    expect(normalizeColumnName("EN_target")).toBe("EN");
    expect(normalizeColumnName("FR_tgt")).toBe("FR");
    expect(normalizeColumnName("KO_source")).toBe("KO");
    expect(normalizeColumnName("JP_translation")).toBe("JP");
  });

  it("returns original name for unknown columns", () => {
    expect(normalizeColumnName("ID_NUMBER")).toBe("ID_NUMBER");
    expect(normalizeColumnName("random_col")).toBe("random_col");
    expect(normalizeColumnName("foo")).toBe("foo");
  });

  it("trims whitespace", () => {
    expect(normalizeColumnName("  EN  ")).toBe("EN");
    expect(normalizeColumnName(" Korean ")).toBe("KO");
  });
});

/* ------------------------------------------------------------------ */
/*  classifyColumn                                                     */
/* ------------------------------------------------------------------ */
describe("classifyColumn", () => {
  it("classifies language columns as 0", () => {
    expect(classifyColumn("KO")).toBe(0);
    expect(classifyColumn("EN")).toBe(0);
    expect(classifyColumn("JP")).toBe(0);
    expect(classifyColumn("CT")).toBe(0);
    expect(classifyColumn("CS")).toBe(0);
    expect(classifyColumn("ZH")).toBe(0);
    expect(classifyColumn("DE")).toBe(0);
    expect(classifyColumn("FR")).toBe(0);
    expect(classifyColumn("ES")).toBe(0);
    expect(classifyColumn("PT")).toBe(0);
    expect(classifyColumn("IT")).toBe(0);
    expect(classifyColumn("RU")).toBe(0);
    expect(classifyColumn("TH")).toBe(0);
    expect(classifyColumn("VI")).toBe(0);
    expect(classifyColumn("ID")).toBe(0);
    expect(classifyColumn("AR")).toBe(0);
    expect(classifyColumn("TR")).toBe(0);
  });

  it("classifies info columns as 1", () => {
    expect(classifyColumn("note")).toBe(1);
    expect(classifyColumn("Notes")).toBe(1);
    expect(classifyColumn("분류")).toBe(1);
    expect(classifyColumn("category")).toBe(1);
    expect(classifyColumn("comment")).toBe(1);
    expect(classifyColumn("comments")).toBe(1);
    expect(classifyColumn("remark")).toBe(1);
    expect(classifyColumn("remarks")).toBe(1);
    expect(classifyColumn("memo")).toBe(1);
    expect(classifyColumn("description")).toBe(1);
    expect(classifyColumn("설명")).toBe(1);
  });

  it("classifies metadata/unknown columns as 2", () => {
    expect(classifyColumn("ID_NUMBER")).toBe(2);
    expect(classifyColumn("random_col")).toBe(2);
    expect(classifyColumn("index")).toBe(2);
    expect(classifyColumn("timestamp")).toBe(2);
  });
});

/* ------------------------------------------------------------------ */
/*  detectColumns                                                      */
/* ------------------------------------------------------------------ */
describe("detectColumns", () => {
  it("detects Korean source column from known headers", () => {
    const data = [
      { KO: "안녕", EN: "Hello", JP: "こんにちは" },
      { KO: "세계", EN: "World", JP: "世界" },
    ];
    const columns = ["KO", "EN", "JP"];
    const result = detectColumns(data, columns);
    expect(result.source).toBe("KO");
    expect(result.targets).toEqual(["EN", "JP"]);
  });

  it("detects Korean source from 'Source' header", () => {
    const data = [
      { Source: "안녕", EN: "Hello" },
    ];
    const columns = ["Source", "EN"];
    const result = detectColumns(data, columns);
    expect(result.source).toBe("Source");
    expect(result.targets).toEqual(["EN"]);
  });

  it("detects Korean content when no header matches KO", () => {
    const data = [
      { col1: "안녕하세요", col2: "Hello" },
      { col1: "감사합니다", col2: "Thank you" },
      { col1: "좋은 아침", col2: "Good morning" },
    ];
    const columns = ["col1", "col2"];
    const result = detectColumns(data, columns);
    expect(result.source).toBe("col1");
    expect(result.targets).toEqual(["col2"]);
  });

  it("falls back to first column when no Korean detected", () => {
    const data = [
      { col1: "Hello", col2: "Hola" },
      { col1: "World", col2: "Mundo" },
    ];
    const columns = ["col1", "col2"];
    const result = detectColumns(data, columns);
    expect(result.source).toBe("col1");
    expect(result.targets).toEqual(["col2"]);
  });

  it("handles single-column data", () => {
    const data = [{ col1: "Hello" }];
    const columns = ["col1"];
    const result = detectColumns(data, columns);
    expect(result.source).toBe("col1");
    expect(result.targets).toEqual([]);
  });
});

/* ------------------------------------------------------------------ */
/*  checkEntryLimit                                                    */
/* ------------------------------------------------------------------ */
describe("checkEntryLimit", () => {
  it("does not throw when within limit", () => {
    expect(() => checkEntryLimit(100_000, 100_000, "test.xlsx")).not.toThrow();
    expect(() => checkEntryLimit(0, 500_000, "test.xlsx")).not.toThrow();
  });

  it("throws when exceeding 500K limit", () => {
    expect(() => checkEntryLimit(400_000, 200_000, "test.xlsx")).toThrow(
      /500K/
    );
    expect(() => checkEntryLimit(500_000, 1, "big.csv")).toThrow(/500K/);
  });

  it("includes file name in error message", () => {
    expect(() => checkEntryLimit(400_000, 200_000, "my_file.xlsx")).toThrow(
      /my_file\.xlsx/
    );
  });
});

/* ------------------------------------------------------------------ */
/*  LANG_PATTERNS exported                                             */
/* ------------------------------------------------------------------ */
describe("LANG_PATTERNS", () => {
  it("covers all 17 language codes", () => {
    const expected = [
      "KO", "EN", "JP", "CT", "CS", "ZH", "DE", "FR", "ES",
      "PT", "IT", "RU", "TH", "VI", "ID", "AR", "TR",
    ];
    for (const code of expected) {
      expect(LANG_PATTERNS).toHaveProperty(code);
    }
  });
});
