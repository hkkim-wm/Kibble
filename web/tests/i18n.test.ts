import { describe, it, expect } from "vitest";
import { t, TRANSLATIONS } from "../src/i18n/translations";

/* ------------------------------------------------------------------ */
/*  t() – Korean (default language)                                    */
/* ------------------------------------------------------------------ */
describe("t() returns Korean translation by default", () => {
  it("returns Korean for simple keys", () => {
    expect(t("btn_search", "ko")).toBe("검색");
    expect(t("status_ready", "ko")).toBe("준비");
    expect(t("no_results", "ko")).toBe("결과 없음");
  });

  it("returns Korean for all defined keys", () => {
    const koKeys = Object.keys(TRANSLATIONS.ko);
    for (const key of koKeys) {
      const result = t(key, "ko");
      expect(result).toBe((TRANSLATIONS.ko as Record<string, string>)[key]);
    }
  });
});

/* ------------------------------------------------------------------ */
/*  t() – English                                                      */
/* ------------------------------------------------------------------ */
describe("t() returns English translation", () => {
  it("returns English for simple keys", () => {
    expect(t("btn_search", "en")).toBe("Search");
    expect(t("status_ready", "en")).toBe("Ready");
    expect(t("no_results", "en")).toBe("No results");
  });

  it("returns English for all defined keys", () => {
    const enKeys = Object.keys(TRANSLATIONS.en);
    for (const key of enKeys) {
      const result = t(key, "en");
      expect(result).toBe((TRANSLATIONS.en as Record<string, string>)[key]);
    }
  });
});

/* ------------------------------------------------------------------ */
/*  t() – placeholder interpolation                                    */
/* ------------------------------------------------------------------ */
describe("t() interpolates {placeholder} parameters", () => {
  it("replaces a single placeholder", () => {
    expect(t("search_time", "en", { time: 42 })).toBe(
      "Search completed in 42ms",
    );
    expect(t("search_time", "ko", { time: 150 })).toBe("검색 완료: 150ms");
  });

  it("replaces multiple placeholders", () => {
    expect(t("file_loaded", "en", { file: "data.xlsx", count: 100 })).toBe(
      "data.xlsx loaded (100 entries)",
    );
    expect(t("file_loaded", "ko", { file: "data.xlsx", count: 100 })).toBe(
      "data.xlsx 로드 완료 (100건)",
    );
  });

  it("replaces many placeholders in one string", () => {
    const result = t("limit_exceeded", "en", {
      file: "big.csv",
      current: 400000,
      new: 200000,
      sum: 600000,
    });
    expect(result).toBe(
      "Cannot load big.csv: total entries would exceed 500K limit (400000 + 200000 = 600000)",
    );
  });

  it("leaves unmatched placeholders intact", () => {
    // Only supply 'file', omit 'count'
    const result = t("file_loaded", "en", { file: "test.csv" });
    expect(result).toBe("test.csv loaded ({count} entries)");
  });

  it("works without params on a template string (placeholders stay)", () => {
    const result = t("file_loaded", "en");
    expect(result).toBe("{file} loaded ({count} entries)");
  });
});

/* ------------------------------------------------------------------ */
/*  t() – missing key fallback                                         */
/* ------------------------------------------------------------------ */
describe("t() falls back to key for missing translation", () => {
  it("returns the raw key when not found in either language", () => {
    expect(t("totally_nonexistent_key", "en")).toBe("totally_nonexistent_key");
    expect(t("totally_nonexistent_key", "ko")).toBe("totally_nonexistent_key");
  });

  it("returns the raw key even with params supplied", () => {
    const result = t("missing_key", "en", { x: 1 });
    expect(result).toBe("missing_key");
  });
});

/* ------------------------------------------------------------------ */
/*  t() – unknown language falls back to Korean                        */
/* ------------------------------------------------------------------ */
describe("t() falls back to Korean for unknown language", () => {
  it("returns Korean value when language is not en or ko", () => {
    // Force an unknown language code through the type system
    const result = t("btn_search", "fr" as any);
    expect(result).toBe("검색");
  });

  it("returns Korean value with interpolation for unknown language", () => {
    const result = t("file_loaded", "ja" as any, {
      file: "test.txt",
      count: 50,
    });
    expect(result).toBe("test.txt 로드 완료 (50건)");
  });

  it("falls back to key if missing in both ko and unknown language", () => {
    const result = t("no_such_key", "de" as any);
    expect(result).toBe("no_such_key");
  });
});
