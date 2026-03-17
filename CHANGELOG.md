# Changelog

## v1.1 — 2026-03-17

### New Features
- **Menu bar** — Added File menu (Open Files, Exit) and Help menu (About Kibble) with full EN/KO translations. The About dialog shows supported formats, keyboard shortcuts, and usage tips.

### Improvements
- **Cross-file column merging** — When searching across multiple files, columns referring to the same language are merged into a single column regardless of naming differences (e.g., "Target_EN", "English", "영어" all merge into "EN"). Supported for all 17 language codes.
- **Chinese Traditional/Simplified split** — Chinese (Taiwan) and Chinese (PRC) are now recognized as separate targets: CT (CHT, zh-TW, Chinese Traditional, Target_CT) and CS (CHS, zh-CN, Chinese Simplified, Target_CS).
- **Column ordering** — Translation columns appear first (preserving original file order), followed by relevant info columns (Note, 분류), then metadata columns (#, 상태, 비고, Table, Status, Date, etc.) pushed to the back.
- **Inconsistency detection** — The duplicate translation warning now only compares language columns, ignoring metadata and info columns. Empty cells from files missing a language are also ignored. Only the specific language cell(s) with conflicting translations are highlighted red, not the entire row.

### Bug Fixes
- **Crash fix for mixed file search** — Fixed crash when searching "All" across xlsx and csv files with different column structures. NaN values from mismatched columns are now handled correctly.
- **Column order preservation** — Search results now maintain the original column order from loaded files instead of sorting alphabetically.
- **Search worker race condition** — Old search worker signals are disconnected before starting a new search, preventing stale results from corrupting the display.

## v1.0 — 2026-03-16

- Initial release.
