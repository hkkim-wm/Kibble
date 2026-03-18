# Kibble Web — Design Spec

## Overview

Browser-based version of Kibble, a terminology search tool for translation professionals. Provides the same functionality as the PyQt6 desktop app but runs entirely client-side in the browser with no server required.

## Goals

- Feature parity with desktop Kibble v1.1 (excluding global hotkey Ctrl+Shift+K)
- Pure client-side: no server, no installation
- Deployable to static hosting (GitHub Pages) or openable as local file
- Same search quality: substring + fuzzy matching with highlighting

## Non-Goals

- Multi-user / shared terminology databases
- Server-side processing
- Global OS-level hotkeys (browser limitation)

## Architecture

### Project Structure

```
kibble/web/
├── src/
│   ├── core/                  # Business logic (ported from Python)
│   │   ├── parser.ts          # File parsing, column detection
│   │   ├── search.ts          # Substring + fuzzy search engine
│   │   └── session.ts         # localStorage session management
│   ├── components/
│   │   ├── App.tsx            # Main layout, state orchestration
│   │   ├── SearchPanel.tsx    # Search input + options
│   │   ├── ResultsTable.tsx   # Virtual-scrolled results table
│   │   ├── FileTabs.tsx       # File tab management
│   │   ├── DropZone.tsx       # Drag-and-drop file loading
│   │   ├── ColumnMapper.tsx   # Column config modal
│   │   └── Toast.tsx          # Notifications
│   ├── i18n/
│   │   └── translations.ts   # EN/KO translations
│   ├── workers/
│   │   └── search.worker.ts   # Web Worker for background search
│   ├── main.tsx
│   └── index.css
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
└── tailwind.config.js
```

### Tech Stack

| Concern | Library |
|---------|---------|
| UI framework | React 18 + TypeScript |
| Build | Vite 6 |
| Styling | Tailwind CSS 4 |
| xlsx parsing | SheetJS (xlsx ^0.18) |
| csv parsing | Papa Parse ^5 |
| Fuzzy search | Custom Levenshtein (fastest-levenshtein) |
| Encoding detection | jschardet ^2 |
| Virtual scroll | @tanstack/react-virtual ^3 |
| Testing | vitest ^3 |

### Desktop → Web Mapping

| Desktop (Python) | Web (TypeScript) |
|---|---|
| pandas DataFrame | SheetJS + arrays/Map |
| RapidFuzz (fuzz.ratio, token_set_ratio) | fastest-levenshtein + custom scoring |
| QThread | Web Worker (with main-thread fallback) |
| SessionManager (JSON file) | localStorage |
| chardet | TextDecoder + jschardet |
| PyQt6 widgets | React components |

## Core Logic

### File Parsing (`parser.ts`)

- **xlsx**: SheetJS, first sheet only via `sheet_to_json`. If additional sheets exist, show toast notification informing user only first sheet was loaded.
- **csv**: Papa Parse with auto delimiter detection, encoding detection
- **txt**: Tab-delimited, no header row
- **Encoding**: Browser `TextDecoder` default + `jschardet` for EUC-KR/CP949
- **LANG_PATTERNS**: Identical regex patterns from desktop (17 languages + all variants including Source, zh-Hant, zh-Hans, ES-LATAM, TW)
- **Info column patterns** (`_INFO_COL_RE`): Recognize Note, Notes, Category, Comment, Comments, Remark, Remarks, Memo, Description, 분류, 설명 — classified separately from language columns
- **Column detection**: Same logic — direct match → prefix/suffix strip → Korean content scan → fallback
- **Column ordering**: Language columns first (in file order), then info columns (Note, Category, etc.), then metadata columns last. Same `classify_column()` logic as desktop.
- **Auto column-mapper trigger**: If detected source column does not contain Korean text (scan first 10 rows), automatically open ColumnMapper dialog for manual assignment.
- **Entry limit**: 500K total across all files

### Search Engine (`search.ts`)

Direct TypeScript port of desktop search logic — not delegated to a general-purpose search library.

- **Substring**: Direct implementation with position-based scoring. Wildcard glob→regex conversion with custom scoring formula (`75 + 25 * ratio`).
- **Fuzzy**: Custom implementation using `fastest-levenshtein` for character-level Levenshtein distance. Port desktop's `fuzz.ratio` (normalized edit distance as 0-100%) and `token_set_ratio` (tokenize, sort, compare) to maintain identical scoring semantics.
- **Score normalization**: All scores on 0-100 scale (same as desktop), threshold filtering and match% display unchanged.
- **Ignore spaces**: Option to strip whitespace before comparison (port desktop `ignore_spaces` behavior).
- **Minimum query length**: 2 characters required.
- **Execution**: Runs in Web Worker to prevent UI blocking. Falls back to main-thread execution when Worker creation fails (e.g., `file://` protocol).
- **Cancellation**: New search aborts previous Worker task via message-based cancel.

### Translation Filter (Secondary Filter)

After primary search returns results, the translation filter narrows them further:
- **When searching source (KO)**: Filter by target text — only show rows where the target column contains the filter string.
- **When searching target**: Filter by source text — only show rows where the source column contains the filter string.
- Applied client-side on the result set, no re-search needed.

### Session (`session.ts`)

Stored in `localStorage` as JSON. Full schema:

```typescript
interface Session {
  file_names: string[];           // Last loaded file names (for re-load prompt)
  column_mappings: Record<string, { source: string; targets: string[] }>;
  search_settings: {
    mode: 'substring' | 'fuzzy' | 'both';
    direction: 'source' | 'target';
    case_sensitive: boolean;
    wildcards: boolean;
    ignore_spaces: boolean;
    threshold: number;            // 0-100
    limit: number;                // max results
  };
  view_mode: '3col' | 'full';
  selected_target: string;        // Language code for 3-col mode
  language: 'en' | 'ko';         // UI language
}
```

Dropped from desktop: `window_size`, `window_position` (browser manages its own window).

Does NOT persist file contents (security + storage limits). On session restore, displays message prompting user to re-load files.

## UI Components

### Layout

```
┌─────────────────────────────────────────────────────┐
│ Menu bar (File, Help)                                │
├─────────────────────────────────────────────────────┤
│ [File tabs: All | file1.xlsx | file2.csv ✕ | ...]    │
├─────────────────────────────────────────────────────┤
│ Search panel                                         │
│ [Query input] [Search] [⚙]                          │
│ [Translation filter]                                 │
│ Mode: ○Sub ○Fuzzy ○Both  Dir: ○Src ○Tgt             │
│ □Case □Wildcard □IgnoreSpaces  Threshold[━50%] [200] │
├─────────────────────────────────────────────────────┤
│ Results table (virtual scroll, word-wrap toggle)     │
│ Match% │ KO │ EN │ JP │ ... │ (File)                 │
├─────────────────────────────────────────────────────┤
│ Status bar: 🐕 animation + time              [EN/KO] │
└─────────────────────────────────────────────────────┘
```

### Component Details

| Component | Notes |
|---|---|
| **DropZone** | HTML5 Drag & Drop API + file input fallback |
| **FileTabs** | "All" tab searches across all files (shows File column in results). Per-file tabs. Horizontal scroll on overflow, ✕ button to close. |
| **SearchPanel** | Enter to search, no debounce. Includes ignore-spaces checkbox. |
| **ResultsTable** | @tanstack/react-virtual, column resize via drag, sortable headers, word-wrap toggle, double-click to copy cell |
| **ColumnMapper** | Modal dialog for manual source/target assignment. Auto-triggers when source column lacks Korean content. |
| **Toast** | CSS animation notifications (file load, extra sheets warning, errors) |
| **Highlighting** | Search term: yellow, filter: blue, corresponding translation: light background |
| **Context menu** | Custom right-click: copy row, cell, source-only, target-only |
| **Dog animation** | CSS animation replicating desktop emoji sequence |
| **Duplicate detection** | Rows where same source text has different translations across files are highlighted with a warning indicator |

### View Modes

- **3-column**: Source + selected target language + metadata
- **Full**: Source + all translation columns
- In "All" tab, an additional "File" column shows which file each row came from

### Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| Ctrl+F | Focus search input |
| Ctrl+O | Open file dialog |
| Ctrl+C | Copy selected cell |
| Escape | Clear search |

### Removed from Desktop

| Feature | Reason |
|---|---|
| Ctrl+Shift+K global hotkey | Browser cannot capture OS-level hotkeys |
| Ctrl+W close tab | Conflicts with browser tab close; replaced by ✕ button |

## Build & Deployment

### Vite Config

- `base: './'` — enables relative asset paths for static hosting and local serving
- Standard React + TypeScript template

### Build Output

- `web/dist/` — index.html + JS/CSS bundles
- Deployable to any static hosting (GitHub Pages, Netlify, etc.)
- For local use: serve via `npx serve dist` or any local HTTP server (Web Workers require HTTP, not `file://`)

### Local Use Note

Web Workers do not function under `file://` protocol due to browser same-origin policy. The app includes a main-thread fallback for search, but for full performance, use a local HTTP server (`npx serve dist`, Python `http.server`, etc.).

### Testing

- **Unit tests (vitest)**: Core logic — parser (file format handling, column detection, encoding), search (substring scoring, fuzzy scoring, wildcard, ignore-spaces, threshold filtering), session (save/restore, schema)
- **Worker tests**: Use vitest's built-in Web Worker support or mock `postMessage` interface
- **File parsing tests**: Fixture files (small xlsx/csv/txt) in `web/src/__fixtures__/`, use File API mocks
- **Port desktop test cases**: Translate desktop's 42 pytest cases to TypeScript equivalents covering the same edge cases
- **No E2E testing in v1**: Manual browser testing for UI interactions
