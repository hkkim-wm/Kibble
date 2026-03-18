# Kibble Web Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the Kibble desktop terminology search tool to a browser-based React app with identical functionality (minus global hotkey).

**Architecture:** Pure client-side React + TypeScript SPA. File parsing (SheetJS, Papa Parse), search (custom Levenshtein + substring), and session (localStorage) all run in-browser. Heavy search runs in a Web Worker with main-thread fallback.

**Tech Stack:** React 18, TypeScript, Vite 6, Tailwind CSS 4, SheetJS, Papa Parse, fastest-levenshtein, @tanstack/react-virtual, vitest

**Spec:** `docs/superpowers/specs/2026-03-18-kibble-web-design.md`

**Desktop source reference:** `core/parser.py`, `core/search.py`, `core/session.py`, `ui/`, `workers/`

---

## File Structure

```
kibble/web/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── src/
│   ├── main.tsx                        # React entry point
│   ├── index.css                       # Tailwind imports + global styles
│   ├── core/
│   │   ├── parser.ts                   # File parsing, column detection, LANG_PATTERNS
│   │   ├── search.ts                   # SearchConfig, substring/fuzzy scoring, search()
│   │   └── session.ts                  # localStorage session manager
│   ├── components/
│   │   ├── App.tsx                     # Main layout, state orchestration
│   │   ├── SearchPanel.tsx             # Search input, options, filter
│   │   ├── ResultsTable.tsx            # Virtual-scrolled table with highlighting
│   │   ├── FileTabs.tsx                # "All" tab + per-file tabs
│   │   ├── DropZone.tsx                # Drag-and-drop overlay
│   │   ├── ColumnMapper.tsx            # Column config modal
│   │   └── Toast.tsx                   # Toast notification
│   ├── i18n/
│   │   └── translations.ts            # EN/KO translation strings
│   ├── workers/
│   │   └── search.worker.ts           # Web Worker for background search
│   └── __fixtures__/                   # Test fixture files
│       ├── sample.xlsx
│       ├── sample.csv
│       └── sample.txt
└── tests/
    ├── parser.test.ts
    ├── search.test.ts
    ├── session.test.ts
    └── i18n.test.ts
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `web/package.json`, `web/index.html`, `web/vite.config.ts`, `web/tsconfig.json`, `web/tailwind.config.js`, `web/src/main.tsx`, `web/src/index.css`

- [ ] **Step 1: Initialize Vite project**

```bash
cd D:/VS/kibble
mkdir web && cd web
npm create vite@latest . -- --template react-ts
```

- [ ] **Step 2: Install dependencies**

```bash
npm install xlsx papaparse fastest-levenshtein @tanstack/react-virtual jschardet
npm install -D @types/papaparse tailwindcss @tailwindcss/vite
```

- [ ] **Step 3: Configure Vite for relative paths**

Update `web/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: './',
  test: {
    environment: 'jsdom',
  },
})
```

- [ ] **Step 4: Configure Tailwind**

Replace `web/src/index.css`:

```css
@import "tailwindcss";
```

- [ ] **Step 5: Create minimal App shell**

Replace `web/src/App.tsx`:

```tsx
export default function App() {
  return (
    <div className="h-screen flex flex-col bg-white text-gray-900">
      <header className="border-b px-4 py-1 text-sm">Kibble Web</header>
      <main className="flex-1 flex items-center justify-center text-gray-400">
        Drop files here to get started
      </main>
    </div>
  )
}
```

- [ ] **Step 6: Verify dev server starts**

```bash
cd D:/VS/kibble/web
npm run dev
```

Expected: Opens browser, shows "Kibble Web" header and placeholder text.

- [ ] **Step 7: Commit**

```bash
git add web/
git commit -m "feat(web): scaffold Vite + React + TypeScript + Tailwind project"
```

---

## Task 2: Core — Parser (`parser.ts`)

**Files:**
- Create: `web/src/core/parser.ts`
- Create: `web/tests/parser.test.ts`
- Create: `web/src/__fixtures__/sample.xlsx`, `sample.csv`, `sample.txt`

**Reference:** Desktop `core/parser.py` (201 lines)

- [ ] **Step 1: Create test fixture files**

Create small test files:
- `sample.xlsx`: 5 rows, columns: KO, EN, JP (use SheetJS to generate or create manually)
- `sample.csv`: Tab-delimited, columns: Korean, English, headers present
- `sample.txt`: Tab-delimited, no headers, 3 rows of KO\tEN

- [ ] **Step 2: Write failing tests for LANG_PATTERNS and normalize_column_name**

`web/tests/parser.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { normalizeColumnName, classifyColumn } from '../src/core/parser'

describe('normalizeColumnName', () => {
  it('maps exact language codes', () => {
    expect(normalizeColumnName('KO')).toBe('KO')
    expect(normalizeColumnName('EN')).toBe('EN')
    expect(normalizeColumnName('JP')).toBe('JP')
  })

  it('maps locale codes', () => {
    expect(normalizeColumnName('ko-KR')).toBe('KO')
    expect(normalizeColumnName('en-US')).toBe('EN')
    expect(normalizeColumnName('ja-JP')).toBe('JP')
    expect(normalizeColumnName('zh-TW')).toBe('CT')
    expect(normalizeColumnName('zh-CN')).toBe('CS')
  })

  it('maps full language names', () => {
    expect(normalizeColumnName('Korean')).toBe('KO')
    expect(normalizeColumnName('English')).toBe('EN')
    expect(normalizeColumnName('Japanese')).toBe('JP')
    expect(normalizeColumnName('Chinese Traditional')).toBe('CT')
    expect(normalizeColumnName('Chinese Simplified')).toBe('CS')
  })

  it('maps Korean labels', () => {
    expect(normalizeColumnName('한국어')).toBe('KO')
    expect(normalizeColumnName('영어')).toBe('EN')
    expect(normalizeColumnName('일본어')).toBe('JP')
  })

  it('maps new v1.1 patterns', () => {
    expect(normalizeColumnName('Source')).toBe('KO')
    expect(normalizeColumnName('zh-Hant')).toBe('CT')
    expect(normalizeColumnName('TW')).toBe('CT')
    expect(normalizeColumnName('zh-Hans')).toBe('CS')
    expect(normalizeColumnName('ES-LATAM')).toBe('ES')
    expect(normalizeColumnName('Spanish (Latin America)')).toBe('ES')
  })

  it('strips Target_ prefix', () => {
    expect(normalizeColumnName('Target_EN')).toBe('EN')
    expect(normalizeColumnName('Target_JA')).toBe('JP')
    expect(normalizeColumnName('tgt_French')).toBe('FR')
  })

  it('returns original for unknown columns', () => {
    expect(normalizeColumnName('Notes')).toBe('Notes')
    expect(normalizeColumnName('Category')).toBe('Category')
  })
})

describe('classifyColumn', () => {
  it('classifies language columns as 0', () => {
    expect(classifyColumn('KO')).toBe(0)
    expect(classifyColumn('EN')).toBe(0)
  })

  it('classifies info columns as 1', () => {
    expect(classifyColumn('Note')).toBe(1)
    expect(classifyColumn('notes')).toBe(1)
    expect(classifyColumn('분류')).toBe(1)
    expect(classifyColumn('Category')).toBe(1)
  })

  it('classifies unknown columns as 2', () => {
    expect(classifyColumn('ID')).toBe(0)  // ID = Indonesian
    expect(classifyColumn('random')).toBe(2)
  })
})
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd D:/VS/kibble/web
npx vitest run tests/parser.test.ts
```

Expected: FAIL — module not found.

- [ ] **Step 4: Implement LANG_PATTERNS, normalizeColumnName, classifyColumn**

`web/src/core/parser.ts`:

```typescript
// Port of desktop core/parser.py — LANG_PATTERNS, column detection, file parsing

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
}

const LANG_CODES = new Set(Object.keys(LANG_PATTERNS))

const INFO_COL_RE = /^(note|notes|분류|category|comment|comments|remark|remarks|memo|description|설명)$/i

const COL_PREFIXES = /^(target|tgt|source|src|lang|translation|trans)[_\-\s.:]+/i
const COL_SUFFIXES = /[_\-\s.:](target|tgt|source|src|lang|translation|trans)$/i

const HANGUL_RE = /[\uAC00-\uD7AF]/

export const MAX_ENTRIES = 500_000

export function normalizeColumnName(colName: string): string {
  const stripped = colName.trim()

  for (const [code, pattern] of Object.entries(LANG_PATTERNS)) {
    if (pattern.test(stripped)) return code
  }

  let cleaned = stripped.replace(COL_PREFIXES, '')
  cleaned = cleaned.replace(COL_SUFFIXES, '').trim()
  if (cleaned && cleaned !== stripped) {
    for (const [code, pattern] of Object.entries(LANG_PATTERNS)) {
      if (pattern.test(cleaned)) return code
    }
  }

  return stripped
}

export function classifyColumn(normName: string): number {
  if (LANG_CODES.has(normName)) return 0
  if (INFO_COL_RE.test(normName)) return 1
  return 2
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
npx vitest run tests/parser.test.ts
```

Expected: All PASS.

- [ ] **Step 6: Write failing tests for file parsing and column detection**

Add to `web/tests/parser.test.ts`:

```typescript
import { detectColumns, parseFile, checkEntryLimit } from '../src/core/parser'

describe('detectColumns', () => {
  it('detects KO source from headers', () => {
    const data = [
      { KO: '테스트', EN: 'test', JP: 'テスト' },
    ]
    const columns = ['KO', 'EN', 'JP']
    const { source, targets } = detectColumns(data, columns)
    expect(source).toBe('KO')
    expect(targets).toContain('EN')
    expect(targets).toContain('JP')
    expect(targets).not.toContain('KO')
  })

  it('detects Korean content when no language headers', () => {
    const data = [
      { col1: '안녕하세요', col2: 'hello' },
      { col1: '감사합니다', col2: 'thank you' },
    ]
    const columns = ['col1', 'col2']
    const { source, targets } = detectColumns(data, columns)
    expect(source).toBe('col1')
    expect(targets).toEqual(['col2'])
  })

  it('falls back to first column', () => {
    const data = [{ A: 'abc', B: 'def' }]
    const columns = ['A', 'B']
    const { source, targets } = detectColumns(data, columns)
    expect(source).toBe('A')
    expect(targets).toEqual(['B'])
  })
})

describe('checkEntryLimit', () => {
  it('passes within limit', () => {
    expect(() => checkEntryLimit(100, 200, 'test.xlsx')).not.toThrow()
  })

  it('throws when exceeding limit', () => {
    expect(() => checkEntryLimit(499_999, 2, 'test.xlsx')).toThrow(/500K/)
  })
})
```

- [ ] **Step 7: Run tests to verify they fail**

```bash
npx vitest run tests/parser.test.ts
```

- [ ] **Step 8: Implement parseFile, detectColumns, checkEntryLimit**

Add to `web/src/core/parser.ts`:

```typescript
import * as XLSX from 'xlsx'
import Papa from 'papaparse'
import jschardet from 'jschardet'

export interface ParsedFile {
  data: Record<string, string>[]
  columns: string[]
  extraSheets: number
  sourceFile: string
}

export interface ColumnDetection {
  source: string
  targets: string[]
}

export async function parseFile(file: File): Promise<ParsedFile> {
  const ext = file.name.split('.').pop()?.toLowerCase()

  if (ext === 'xlsx') {
    return parseXlsx(file)
  } else if (ext === 'csv' || ext === 'txt') {
    return parseDelimited(file, ext === 'txt')
  }
  throw new Error(`Unsupported format: .${ext}. Use .xlsx, .csv, or .txt`)
}

async function parseXlsx(file: File): Promise<ParsedFile> {
  const buffer = await file.arrayBuffer()
  const workbook = XLSX.read(buffer, { type: 'array' })
  const sheetName = workbook.SheetNames[0]
  const sheet = workbook.Sheets[sheetName]
  const data = XLSX.utils.sheet_to_json<Record<string, string>>(sheet, { defval: '', raw: false })

  if (data.length === 0) throw new Error(`No entries found in ${file.name}`)

  const columns = Object.keys(data[0] || {})
  return {
    data,
    columns: columns.map(String),
    extraSheets: workbook.SheetNames.length - 1,
    sourceFile: file.name,
  }
}

async function parseDelimited(file: File, noHeader: boolean): Promise<ParsedFile> {
  const buffer = await file.arrayBuffer()
  const uint8 = new Uint8Array(buffer)

  // Detect encoding using jschardet (handles Korean EUC-KR/CP949 well)
  const binaryStr = Array.from(uint8).map(b => String.fromCharCode(b)).join('')
  const detected = jschardet.detect(binaryStr)
  const encoding = detected?.encoding?.toLowerCase() ?? 'utf-8'

  let decoderName = 'utf-8'
  if (encoding.includes('euc-kr') || encoding.includes('cp949') || encoding === 'euc-kr') {
    decoderName = 'euc-kr'
  } else if (encoding.includes('shift_jis') || encoding.includes('sjis')) {
    decoderName = 'shift-jis'
  } else if (encoding.includes('euc-jp')) {
    decoderName = 'euc-jp'
  } else if (encoding.includes('iso-8859') || encoding === 'ascii') {
    decoderName = 'utf-8'
  }

  let text: string
  try {
    text = new TextDecoder(decoderName, { fatal: true }).decode(uint8)
  } catch {
    // Fallback chain: utf-8 → euc-kr → latin-1
    try {
      text = new TextDecoder('utf-8', { fatal: true }).decode(uint8)
    } catch {
      try {
        text = new TextDecoder('euc-kr', { fatal: true }).decode(uint8)
      } catch {
        text = new TextDecoder('iso-8859-1').decode(uint8)
      }
    }
  }

  const result = Papa.parse<Record<string, string>>(text, {
    header: !noHeader,
    skipEmptyLines: true,
    dynamicTyping: false,
  })

  const data = result.data.filter((row: any) => {
    const values = Object.values(row)
    return values.some(v => v !== '' && v !== null && v !== undefined)
  })

  if (data.length === 0) throw new Error(`No entries found in ${file.name}`)

  const columns = noHeader
    ? Object.keys(data[0] || {})
    : (result.meta.fields || Object.keys(data[0] || {}))

  return {
    data: data as Record<string, string>[],
    columns: columns.map(String),
    extraSheets: 0,
    sourceFile: file.name,
  }
}

export function detectColumns(
  data: Record<string, string>[],
  columns: string[],
): ColumnDetection {
  // 1. Check for explicit KO pattern in headers
  let source: string | null = null
  for (const col of columns) {
    for (const [code, pattern] of Object.entries(LANG_PATTERNS)) {
      if (pattern.test(col.trim())) {
        if (code === 'KO') { source = col; break }
      }
    }
    if (source) break
  }

  if (source) {
    return { source, targets: columns.filter(c => c !== source) }
  }

  // 2. Scan for Korean content
  const scanRows = Math.min(10, data.length)
  for (const col of columns) {
    let count = 0
    for (let i = 0; i < scanRows; i++) {
      const val = data[i]?.[col] ?? ''
      if (HANGUL_RE.test(val)) count++
    }
    if (count > 0) {
      return { source: col, targets: columns.filter(c => c !== col) }
    }
  }

  // 3. Fallback: first column
  return {
    source: columns[0],
    targets: columns.slice(1),
  }
}

export function checkEntryLimit(currentTotal: number, newCount: number, fileName: string): void {
  if (currentTotal + newCount > MAX_ENTRIES) {
    throw new Error(
      `Cannot load ${fileName}: total entries would exceed 500K limit ` +
      `(${currentTotal} + ${newCount} = ${currentTotal + newCount})`
    )
  }
}
```

- [ ] **Step 9: Run tests to verify they pass**

```bash
npx vitest run tests/parser.test.ts
```

Expected: All PASS.

- [ ] **Step 10: Commit**

```bash
git add web/src/core/parser.ts web/tests/parser.test.ts
git commit -m "feat(web): implement file parser with LANG_PATTERNS and column detection"
```

---

## Task 3: Core — Search Engine (`search.ts`)

**Files:**
- Create: `web/src/core/search.ts`
- Create: `web/tests/search.test.ts`

**Reference:** Desktop `core/search.py` (174 lines)

- [ ] **Step 1: Write failing tests**

`web/tests/search.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import {
  SearchConfig,
  substringScore,
  fuzzyScore,
  search,
} from '../src/core/search'

describe('substringScore', () => {
  it('returns 100 for exact match', () => {
    expect(substringScore('hello', 'hello', false, false)).toBe(100)
  })

  it('returns partial score for substring match', () => {
    const score = substringScore('test', 'this is a test string', false, false)
    expect(score).toBeGreaterThan(75)
    expect(score).toBeLessThanOrEqual(100)
  })

  it('returns 0 for no match', () => {
    expect(substringScore('xyz', 'hello world', false, false)).toBe(0)
  })

  it('respects case sensitivity', () => {
    expect(substringScore('Hello', 'hello', true, false)).toBe(0)
    expect(substringScore('Hello', 'hello', false, false)).toBe(100)
  })

  it('handles wildcard patterns', () => {
    const score = substringScore('te*ng', 'testing', false, true)
    expect(score).toBeGreaterThan(0)
  })

  it('wildcard non-match returns 0', () => {
    expect(substringScore('te*xyz', 'testing', false, true)).toBe(0)
  })
})

describe('fuzzyScore', () => {
  it('returns 100 for identical strings', () => {
    expect(fuzzyScore('hello', 'hello')).toBe(100)
  })

  it('returns high score for similar strings', () => {
    const score = fuzzyScore('hello', 'helo')
    expect(score).toBeGreaterThan(70)
  })

  it('returns low score for different strings', () => {
    const score = fuzzyScore('hello', 'world')
    expect(score).toBeLessThan(50)
  })
})

describe('search', () => {
  const entries = [
    { KO: '번역 메모리', EN: 'Translation Memory' },
    { KO: '용어집', EN: 'Glossary' },
    { KO: '번역 품질', EN: 'Translation Quality' },
    { KO: '메모리 관리', EN: 'Memory Management' },
  ]

  it('finds substring matches', () => {
    const config: SearchConfig = {
      query: '번역',
      mode: 'substring',
      threshold: 50,
      limit: 200,
      caseSensitive: false,
      wildcards: false,
      ignoreSpaces: false,
    }
    const results = search(entries, 'KO', config)
    expect(results.length).toBe(2)
    expect(results[0].score).toBeGreaterThanOrEqual(config.threshold)
  })

  it('finds fuzzy matches', () => {
    const config: SearchConfig = {
      query: '번역메모리',
      mode: 'fuzzy',
      threshold: 50,
      limit: 200,
      caseSensitive: false,
      wildcards: false,
      ignoreSpaces: false,
    }
    const results = search(entries, 'KO', config)
    expect(results.length).toBeGreaterThan(0)
  })

  it('respects minimum query length', () => {
    const config: SearchConfig = {
      query: '번',
      mode: 'substring',
      threshold: 50,
      limit: 200,
      caseSensitive: false,
      wildcards: false,
      ignoreSpaces: false,
    }
    const results = search(entries, 'KO', config)
    expect(results.length).toBe(0)
  })

  it('respects limit', () => {
    const config: SearchConfig = {
      query: '번역',
      mode: 'substring',
      threshold: 0,
      limit: 1,
      caseSensitive: false,
      wildcards: false,
      ignoreSpaces: false,
    }
    const results = search(entries, 'KO', config)
    expect(results.length).toBeLessThanOrEqual(1)
  })

  it('handles ignore spaces', () => {
    const config: SearchConfig = {
      query: '번역메모리',
      mode: 'substring',
      threshold: 50,
      limit: 200,
      caseSensitive: false,
      wildcards: false,
      ignoreSpaces: true,
    }
    const results = search(entries, 'KO', config)
    expect(results.length).toBeGreaterThan(0)  // matches "번역 메모리"
  })

  it('both mode takes max of substring and fuzzy', () => {
    const config: SearchConfig = {
      query: '번역',
      mode: 'both',
      threshold: 50,
      limit: 200,
      caseSensitive: false,
      wildcards: false,
      ignoreSpaces: false,
    }
    const results = search(entries, 'KO', config)
    expect(results.length).toBeGreaterThan(0)
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx vitest run tests/search.test.ts
```

- [ ] **Step 3: Implement search engine**

`web/src/core/search.ts`:

```typescript
import { distance } from 'fastest-levenshtein'

export interface SearchConfig {
  query: string
  mode: 'substring' | 'fuzzy' | 'both'
  threshold: number
  limit: number
  caseSensitive: boolean
  wildcards: boolean
  ignoreSpaces: boolean
}

export interface SearchResult {
  index: number
  score: number
}

function globToRegex(pattern: string): string {
  const parts = pattern.split('*')
  return parts.map(p => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('.*')
}

export function substringScore(
  query: string,
  text: string,
  caseSensitive: boolean,
  wildcards: boolean,
): number {
  if (!text) return 0

  let q = query
  let t = text
  if (!caseSensitive) {
    q = q.toLowerCase()
    t = t.toLowerCase()
  }

  if (wildcards) {
    // Match desktop behavior: wrap with *...* if no * present
    const globQ = q.includes('*') ? q : `*${q}*`
    const regex = new RegExp(globToRegex(globQ), caseSensitive ? '' : 'i')
    const match = regex.exec(text)
    if (!match) return 0
    const ratio = query.replace(/\*/g, '').length / text.length
    return Math.min(100, Math.round(75 + 25 * ratio))
  }

  if (t === q) return 100

  const idx = t.indexOf(q)
  if (idx === -1) return 0

  const ratio = q.length / t.length
  return Math.min(100, Math.round(75 + 25 * ratio))
}

/**
 * Levenshtein ratio — equivalent to RapidFuzz fuzz.ratio.
 * Formula: (1 - distance / maxLen) * 100, rounded.
 */
function levenshteinRatio(a: string, b: string): number {
  if (a === b) return 100
  const maxLen = Math.max(a.length, b.length)
  if (maxLen === 0) return 100
  return Math.round((1 - distance(a, b) / maxLen) * 100)
}

/**
 * Token set ratio — equivalent to RapidFuzz fuzz.token_set_ratio.
 * Tokenizes, sorts, and compares intersection + remainder strings.
 * Takes the max ratio across combinations.
 */
function tokenSetRatio(a: string, b: string): number {
  const tokensA = new Set(a.toLowerCase().split(/\s+/).filter(Boolean))
  const tokensB = new Set(b.toLowerCase().split(/\s+/).filter(Boolean))

  const intersection = [...tokensA].filter(t => tokensB.has(t)).sort()
  const diffAB = [...tokensA].filter(t => !tokensB.has(t)).sort()
  const diffBA = [...tokensB].filter(t => !tokensA.has(t)).sort()

  const sorted_sect = intersection.join(' ')
  const combined_a = [sorted_sect, ...diffAB].filter(Boolean).join(' ')
  const combined_b = [sorted_sect, ...diffBA].filter(Boolean).join(' ')

  return Math.max(
    levenshteinRatio(sorted_sect, combined_a),
    levenshteinRatio(sorted_sect, combined_b),
    levenshteinRatio(combined_a, combined_b),
  )
}

export function fuzzyScore(query: string, text: string): number {
  if (!text || !query) return 0
  return Math.max(
    levenshteinRatio(query.toLowerCase(), text.toLowerCase()),
    tokenSetRatio(query, text),
  )
}

export function search(
  entries: Record<string, string>[],
  searchColumn: string,
  config: SearchConfig,
): SearchResult[] {
  if (config.query.length < 2) return []

  const results: SearchResult[] = []
  const stripSpaces = config.ignoreSpaces
  const query = stripSpaces ? config.query.replace(/\s+/g, '') : config.query

  for (let i = 0; i < entries.length; i++) {
    let text = entries[i][searchColumn] ?? ''
    if (stripSpaces) text = text.replace(/\s+/g, '')

    let score = 0

    if (config.mode === 'substring' || config.mode === 'both') {
      score = substringScore(query, text, config.caseSensitive, config.wildcards)
    }

    if (config.mode === 'fuzzy' || config.mode === 'both') {
      const fScore = fuzzyScore(query, text)
      score = Math.max(score, fScore)
    }

    if (score >= config.threshold) {
      results.push({ index: i, score })
    }
  }

  results.sort((a, b) => b.score - a.score || a.index - b.index)
  return results.slice(0, config.limit)
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run tests/search.test.ts
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/core/search.ts web/tests/search.test.ts
git commit -m "feat(web): implement search engine with substring, fuzzy, and combined modes"
```

---

## Task 4: Core — Session Manager (`session.ts`)

**Files:**
- Create: `web/src/core/session.ts`
- Create: `web/tests/session.test.ts`

**Reference:** Desktop `core/session.py` (77 lines)

- [ ] **Step 1: Write failing tests**

`web/tests/session.test.ts`:

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { SessionManager, Session } from '../src/core/session'

describe('SessionManager', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('returns defaults when no session saved', () => {
    const session = SessionManager.load()
    expect(session.language).toBe('ko')
    expect(session.search_settings.mode).toBe('both')
    expect(session.search_settings.threshold).toBe(50)
    expect(session.search_settings.limit).toBe(200)
  })

  it('saves and loads session', () => {
    const session = SessionManager.load()
    session.language = 'en'
    session.search_settings.threshold = 70
    SessionManager.save(session)

    const loaded = SessionManager.load()
    expect(loaded.language).toBe('en')
    expect(loaded.search_settings.threshold).toBe(70)
  })

  it('merges partial data with defaults', () => {
    localStorage.setItem('kibble_session', JSON.stringify({ language: 'en' }))
    const session = SessionManager.load()
    expect(session.language).toBe('en')
    expect(session.search_settings.mode).toBe('both')  // default preserved
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx vitest run tests/session.test.ts
```

- [ ] **Step 3: Implement session manager**

`web/src/core/session.ts`:

```typescript
export interface Session {
  file_names: string[]
  column_mappings: Record<string, { source: string; targets: string[] }>
  search_settings: {
    mode: 'substring' | 'fuzzy' | 'both'
    direction: 'source' | 'target'
    case_sensitive: boolean
    wildcards: boolean
    ignore_spaces: boolean
    threshold: number
    limit: number
  }
  view_mode: '3col' | 'full'
  selected_target: string
  language: 'en' | 'ko'
}

const DEFAULT_SESSION: Session = {
  file_names: [],
  column_mappings: {},
  search_settings: {
    mode: 'both',
    direction: 'source',
    case_sensitive: false,
    wildcards: false,
    ignore_spaces: false,
    threshold: 50,
    limit: 200,
  },
  view_mode: '3col',
  selected_target: 'EN',
  language: 'ko',
}

const STORAGE_KEY = 'kibble_session'

function deepMerge(defaults: any, partial: any): any {
  if (!partial || typeof partial !== 'object') return defaults
  const result = { ...defaults }
  for (const key of Object.keys(defaults)) {
    if (key in partial) {
      if (typeof defaults[key] === 'object' && !Array.isArray(defaults[key])) {
        result[key] = deepMerge(defaults[key], partial[key])
      } else {
        result[key] = partial[key]
      }
    }
  }
  return result
}

export const SessionManager = {
  load(): Session {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return { ...DEFAULT_SESSION, search_settings: { ...DEFAULT_SESSION.search_settings } }
      const parsed = JSON.parse(raw)
      return deepMerge(DEFAULT_SESSION, parsed)
    } catch {
      return { ...DEFAULT_SESSION, search_settings: { ...DEFAULT_SESSION.search_settings } }
    }
  },

  save(session: Session): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
    } catch {
      // localStorage full or unavailable — silently ignore
    }
  },
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx vitest run tests/session.test.ts
```

- [ ] **Step 5: Commit**

```bash
git add web/src/core/session.ts web/tests/session.test.ts
git commit -m "feat(web): implement session manager with localStorage persistence"
```

---

## Task 5: i18n Translations

**Files:**
- Create: `web/src/i18n/translations.ts`

**Reference:** Desktop `ui/i18n.py` (167 lines, 80+ keys)

- [ ] **Step 1: Implement translations**

`web/src/i18n/translations.ts`:

```typescript
const TRANSLATIONS: Record<string, Record<string, string>> = {
  en: {
    // Search panel
    search_for: 'Search for',
    btn_search: 'Search',
    case_sensitive: 'Case sensitive',
    add_wildcards: 'Wildcards',
    ignore_spaces: 'Ignore spaces',
    search_in_source: 'Source',
    search_in_target: 'Target',
    match_mode: 'Mode',
    mode_both: 'Both',
    mode_substring: 'Substring',
    mode_fuzzy: 'Fuzzy',
    min_threshold: 'Min match %',
    max_results: 'Max results',
    filter_placeholder: 'Filter translations...',
    total_hits: 'Total: {count}',

    // File tabs
    search_all: 'Search All',

    // Results table
    col_match: 'Match %',
    col_file: 'File',
    view_3col: '3 columns',
    view_full: 'All columns',
    word_wrap: 'Word wrap',
    no_results: 'No results found',

    // Context menu
    copy_row: 'Copy row',
    copy_cell: 'Copy cell',
    copy_source: 'Copy source only',
    copy_target: 'Copy target only',

    // Drop zone
    drop_files: 'Drop files here or click to open',
    drop_hint: 'Supports .xlsx, .csv, .txt',

    // Column mapper
    column_settings: 'Column Settings',
    source_column: 'Source column',
    target_columns: 'Target columns',
    preview: 'Preview',
    btn_ok: 'OK',
    btn_cancel: 'Cancel',

    // Toasts & errors
    file_loaded: '{file} loaded ({count} entries)',
    extra_sheets: '{file} has {count} extra sheets (only first sheet loaded)',
    limit_exceeded: 'Cannot load {file}: total entries would exceed 500K limit ({current} + {new} = {sum})',
    no_entries: 'No entries found in {file}',
    unsupported_format: 'Unsupported format. Use .xlsx, .csv, or .txt',
    search_time: 'Search completed in {time}s',
    session_restore_hint: 'Previously loaded files need to be re-opened',

    // Menu
    menu_file: 'File',
    menu_open: 'Open...',
    menu_help: 'Help',
    menu_about: 'About',

    // About
    about_title: 'About Kibble Web',
    about_text: 'Kibble Web v{version} — Terminology search tool for translators',

    // Status
    status_ready: 'Ready',
    status_searching: 'Searching...',
    status_files: '{count} files, {entries} entries',
  },
  ko: {
    search_for: '검색어',
    btn_search: '검색',
    case_sensitive: '대소문자 구분',
    add_wildcards: '와일드카드',
    ignore_spaces: '공백 무시',
    search_in_source: '원문',
    search_in_target: '번역문',
    match_mode: '일치 방식',
    mode_both: '모두',
    mode_substring: '부분 일치',
    mode_fuzzy: '유사 일치',
    min_threshold: '최소 일치율',
    max_results: '최대 결과',
    filter_placeholder: '번역문 필터...',
    total_hits: '총 {count}건',

    search_all: '전체 검색',

    col_match: '일치율',
    col_file: '파일',
    view_3col: '3열 보기',
    view_full: '전체 보기',
    word_wrap: '줄 바꿈',
    no_results: '검색 결과가 없습니다',

    copy_row: '행 복사',
    copy_cell: '셀 복사',
    copy_source: '원문만 복사',
    copy_target: '번역문만 복사',

    drop_files: '파일을 여기에 드롭하거나 클릭하여 열기',
    drop_hint: '.xlsx, .csv, .txt 지원',

    column_settings: '열 설정',
    source_column: '원문 열',
    target_columns: '번역문 열',
    preview: '미리보기',
    btn_ok: '확인',
    btn_cancel: '취소',

    file_loaded: '{file} 로드 완료 ({count}건)',
    extra_sheets: '{file}에 {count}개의 추가 시트가 있습니다 (첫 번째 시트만 로드)',
    limit_exceeded: '{file}을(를) 로드할 수 없습니다: 총 항목 수가 500K 제한을 초과합니다 ({current} + {new} = {sum})',
    no_entries: '{file}에 항목이 없습니다',
    unsupported_format: '지원하지 않는 형식입니다. .xlsx, .csv, .txt를 사용하세요',
    search_time: '검색 완료: {time}초',
    session_restore_hint: '이전에 로드한 파일을 다시 열어주세요',

    menu_file: '파일',
    menu_open: '열기...',
    menu_help: '도움말',
    menu_about: '정보',

    about_title: 'Kibble Web 정보',
    about_text: 'Kibble Web v{version} — 번역가를 위한 용어 검색 도구',

    status_ready: '준비',
    status_searching: '검색 중...',
    status_files: '{count}개 파일, {entries}건',
  },
}

export type Language = 'en' | 'ko'

export function t(key: string, lang: Language = 'ko', params?: Record<string, string | number>): string {
  const str = TRANSLATIONS[lang]?.[key] ?? TRANSLATIONS.ko[key] ?? key
  if (!params) return str
  return str.replace(/\{(\w+)\}/g, (_, k) => String(params[k] ?? `{${k}}`))
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/i18n/translations.ts
git commit -m "feat(web): add EN/KO translation strings (80+ keys)"
```

---

## Task 6: Web Worker — Search Worker

**Files:**
- Create: `web/src/workers/search.worker.ts`

**Reference:** Desktop `workers/search_worker.py` (31 lines)

- [ ] **Step 1: Implement search worker**

`web/src/workers/search.worker.ts`:

```typescript
import { search, SearchConfig, SearchResult } from '../core/search'

interface SearchMessage {
  type: 'search'
  entries: Record<string, string>[]
  searchColumn: string
  config: SearchConfig
  id: number
}

self.onmessage = (e: MessageEvent<SearchMessage>) => {
  const { entries, searchColumn, config, id } = e.data

  try {
    const results = search(entries, searchColumn, config)
    self.postMessage({ type: 'result', results, id })
  } catch (err) {
    self.postMessage({ type: 'error', error: String(err), id })
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/workers/search.worker.ts
git commit -m "feat(web): add Web Worker for background search execution"
```

---

## Task 7: Component — Toast

**Files:**
- Create: `web/src/components/Toast.tsx`

- [ ] **Step 1: Implement Toast component**

`web/src/components/Toast.tsx`:

```tsx
import { useEffect, useState } from 'react'

interface ToastItem {
  id: number
  message: string
}

let toastId = 0
let toastListener: ((msg: string) => void) | null = null

export function showToast(message: string) {
  toastListener?.(message)
}

export default function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  useEffect(() => {
    toastListener = (message: string) => {
      const id = ++toastId
      setToasts(prev => [...prev, { id, message }])
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id))
      }, 4000)
    }
    return () => { toastListener = null }
  }, [])

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2">
      {toasts.map(t => (
        <div
          key={t.id}
          className="bg-gray-800 text-white px-4 py-2 rounded-lg shadow-lg text-sm animate-fade-in"
        >
          {t.message}
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/Toast.tsx
git commit -m "feat(web): add Toast notification component"
```

---

## Task 8: Component — DropZone

**Files:**
- Create: `web/src/components/DropZone.tsx`

- [ ] **Step 1: Implement DropZone**

`web/src/components/DropZone.tsx`:

```tsx
import { useCallback, useRef, useState, useEffect } from 'react'
import { t, Language } from '../i18n/translations'

const VALID_EXTENSIONS = new Set(['xlsx', 'csv', 'txt'])

interface DropZoneProps {
  onFilesDropped: (files: File[]) => void
  lang: Language
  hasFiles: boolean
}

export default function DropZone({ onFilesDropped, lang, hasFiles }: DropZoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback((fileList: FileList | null) => {
    if (!fileList) return
    const valid: File[] = []
    for (const f of Array.from(fileList)) {
      const ext = f.name.split('.').pop()?.toLowerCase() ?? ''
      if (VALID_EXTENSIONS.has(ext)) valid.push(f)
    }
    if (valid.length > 0) onFilesDropped(valid)
  }, [onFilesDropped])

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const onDragLeave = useCallback(() => setIsDragging(false), [])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  // Window-level drag detection when files are already loaded
  useEffect(() => {
    if (!hasFiles) return
    let dragCounter = 0
    const onEnter = (e: DragEvent) => { e.preventDefault(); dragCounter++; setIsDragging(true) }
    const onLeave = () => { dragCounter--; if (dragCounter <= 0) { dragCounter = 0; setIsDragging(false) } }
    const onOver = (e: DragEvent) => e.preventDefault()
    const onDropWindow = (e: DragEvent) => { e.preventDefault(); dragCounter = 0; setIsDragging(false); handleFiles(e.dataTransfer?.files ?? null) }
    window.addEventListener('dragenter', onEnter)
    window.addEventListener('dragleave', onLeave)
    window.addEventListener('dragover', onOver)
    window.addEventListener('drop', onDropWindow)
    return () => {
      window.removeEventListener('dragenter', onEnter)
      window.removeEventListener('dragleave', onLeave)
      window.removeEventListener('dragover', onOver)
      window.removeEventListener('drop', onDropWindow)
    }
  }, [hasFiles, handleFiles])

  // When files are loaded, this becomes a full-window drag overlay
  if (hasFiles) {
    return (
      <>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept=".xlsx,.csv,.txt"
          multiple
          onChange={e => handleFiles(e.target.files)}
        />
        {isDragging && (
          <div
            className="fixed inset-0 z-40 bg-blue-500/20 border-4 border-dashed border-blue-500 flex items-center justify-center"
          >
            <p className="text-blue-700 text-xl font-semibold">{t('drop_files', lang)}</p>
          </div>
        )}
      </>
    )
  }

  return (
    <div
      className={`flex-1 flex flex-col items-center justify-center cursor-pointer border-2 border-dashed rounded-lg m-8 transition-colors ${
        isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
      }`}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept=".xlsx,.csv,.txt"
        multiple
        onChange={e => handleFiles(e.target.files)}
      />
      <p className="text-gray-500 text-lg">{t('drop_files', lang)}</p>
      <p className="text-gray-400 text-sm mt-1">{t('drop_hint', lang)}</p>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/DropZone.tsx
git commit -m "feat(web): add DropZone component with drag-and-drop and file input"
```

---

## Task 9: Component — FileTabs

**Files:**
- Create: `web/src/components/FileTabs.tsx`

- [ ] **Step 1: Implement FileTabs**

`web/src/components/FileTabs.tsx`:

```tsx
import { t, Language } from '../i18n/translations'

interface FileTabsProps {
  files: { path: string; name: string }[]
  activeTab: string  // "all" or file path
  onTabChange: (tab: string) => void
  onFileClose: (path: string) => void
  onConfigure: () => void
  lang: Language
}

export default function FileTabs({
  files, activeTab, onTabChange, onFileClose, onConfigure, lang,
}: FileTabsProps) {
  if (files.length === 0) return null

  return (
    <div className="flex items-center border-b bg-gray-50 overflow-x-auto">
      <button
        className={`px-4 py-1.5 text-sm whitespace-nowrap border-b-2 transition-colors ${
          activeTab === 'all'
            ? 'border-blue-500 text-blue-600 bg-white'
            : 'border-transparent text-gray-600 hover:text-gray-800'
        }`}
        onClick={() => onTabChange('all')}
      >
        {t('search_all', lang)}
      </button>
      {files.map(f => (
        <div
          key={f.path}
          className={`flex items-center gap-1 px-3 py-1.5 text-sm whitespace-nowrap border-b-2 cursor-pointer transition-colors ${
            activeTab === f.path
              ? 'border-blue-500 text-blue-600 bg-white'
              : 'border-transparent text-gray-600 hover:text-gray-800'
          }`}
          onClick={() => onTabChange(f.path)}
        >
          <span>{f.name}</span>
          <button
            className="ml-1 text-gray-400 hover:text-red-500 text-xs"
            onClick={e => { e.stopPropagation(); onFileClose(f.path) }}
            title="Close"
          >
            ✕
          </button>
        </div>
      ))}
      <button
        className="ml-auto px-3 py-1.5 text-gray-500 hover:text-gray-700"
        onClick={onConfigure}
        title={t('column_settings', lang)}
      >
        ⚙
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/FileTabs.tsx
git commit -m "feat(web): add FileTabs with All tab and close buttons"
```

---

## Task 10: Component — SearchPanel

**Files:**
- Create: `web/src/components/SearchPanel.tsx`

**Reference:** Desktop `ui/search_panel.py` (192 lines)

- [ ] **Step 1: Implement SearchPanel**

`web/src/components/SearchPanel.tsx`:

```tsx
import { useState, useRef, useEffect, useCallback } from 'react'
import { SearchConfig } from '../core/search'
import { t, Language } from '../i18n/translations'

interface SearchPanelProps {
  onSearch: (config: SearchConfig, direction: 'source' | 'target') => void
  onFilterChange: (filter: string) => void
  totalHits: number
  lang: Language
  initialConfig?: Partial<SearchConfig & { direction: string }>
}

export default function SearchPanel({
  onSearch, onFilterChange, totalHits, lang, initialConfig,
}: SearchPanelProps) {
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('')
  const [mode, setMode] = useState<'both' | 'substring' | 'fuzzy'>(initialConfig?.mode ?? 'both')
  const [direction, setDirection] = useState<'source' | 'target'>(
    (initialConfig as any)?.direction ?? 'source'
  )
  const [caseSensitive, setCaseSensitive] = useState(initialConfig?.caseSensitive ?? false)
  const [wildcards, setWildcards] = useState(initialConfig?.wildcards ?? false)
  const [ignoreSpaces, setIgnoreSpaces] = useState(initialConfig?.ignoreSpaces ?? false)
  const [threshold, setThreshold] = useState(initialConfig?.threshold ?? 50)
  const [limit, setLimit] = useState(initialConfig?.limit ?? 200)
  const inputRef = useRef<HTMLInputElement>(null)

  const doSearch = useCallback(() => {
    onSearch({
      query,
      mode,
      threshold,
      limit,
      caseSensitive,
      wildcards,
      ignoreSpaces,
    }, direction)
  }, [query, mode, threshold, limit, caseSensitive, wildcards, ignoreSpaces, direction, onSearch])

  // Ctrl+F focus
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'f') {
        e.preventDefault()
        inputRef.current?.focus()
        inputRef.current?.select()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') doSearch()
    if (e.key === 'Escape') { setQuery(''); setFilter('') }
  }

  return (
    <div className="border-b px-4 py-2 space-y-2">
      {/* Row 1: Search input + button */}
      <div className="flex gap-2">
        <input
          ref={inputRef}
          className="flex-1 border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          placeholder={t('search_for', lang)}
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <button
          className="px-4 py-1.5 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 transition-colors"
          onClick={doSearch}
        >
          {t('btn_search', lang)}
        </button>
      </div>

      {/* Row 2: Filter */}
      <input
        className="w-full border rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        placeholder={t('filter_placeholder', lang)}
        value={filter}
        onChange={e => { setFilter(e.target.value); onFilterChange(e.target.value) }}
        onKeyDown={e => { if (e.key === 'Enter') onFilterChange(filter) }}
      />

      {/* Row 3: Options */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
        {/* Direction */}
        <div className="flex gap-2">
          <label className="flex items-center gap-1 cursor-pointer">
            <input
              type="radio" name="direction" checked={direction === 'source'}
              onChange={() => setDirection('source')}
            />
            {t('search_in_source', lang)}
          </label>
          <label className="flex items-center gap-1 cursor-pointer">
            <input
              type="radio" name="direction" checked={direction === 'target'}
              onChange={() => setDirection('target')}
            />
            {t('search_in_target', lang)}
          </label>
        </div>

        <span className="text-gray-300">|</span>

        {/* Mode */}
        <select
          className="border rounded px-2 py-0.5 text-sm"
          value={mode}
          onChange={e => setMode(e.target.value as any)}
        >
          <option value="both">{t('mode_both', lang)}</option>
          <option value="substring">{t('mode_substring', lang)}</option>
          <option value="fuzzy">{t('mode_fuzzy', lang)}</option>
        </select>

        <span className="text-gray-300">|</span>

        {/* Checkboxes */}
        <label className="flex items-center gap-1 cursor-pointer">
          <input type="checkbox" checked={caseSensitive} onChange={e => setCaseSensitive(e.target.checked)} />
          {t('case_sensitive', lang)}
        </label>
        <label className="flex items-center gap-1 cursor-pointer">
          <input type="checkbox" checked={wildcards} onChange={e => setWildcards(e.target.checked)} />
          {t('add_wildcards', lang)}
        </label>
        <label className="flex items-center gap-1 cursor-pointer">
          <input type="checkbox" checked={ignoreSpaces} onChange={e => setIgnoreSpaces(e.target.checked)} />
          {t('ignore_spaces', lang)}
        </label>

        <span className="text-gray-300">|</span>

        {/* Threshold */}
        <label className="flex items-center gap-1">
          {t('min_threshold', lang)}
          <input
            type="range" min={0} max={100} value={threshold}
            onChange={e => setThreshold(Number(e.target.value))}
            className="w-20"
          />
          <span className="w-8 text-right">{threshold}%</span>
        </label>

        {/* Limit */}
        <label className="flex items-center gap-1">
          {t('max_results', lang)}
          <input
            type="number" min={10} max={1000} step={10} value={limit}
            onChange={e => setLimit(Number(e.target.value))}
            className="border rounded px-2 py-0.5 w-16 text-sm"
          />
        </label>

        {/* Total hits */}
        <span className="text-gray-500 ml-auto">
          {t('total_hits', lang, { count: totalHits })}
        </span>
      </div>
    </div>
  )
}
```

The `direction` is passed alongside `SearchConfig` in the `onSearch` callback for App to use when selecting the search column.

- [ ] **Step 2: Commit**

```bash
git add web/src/components/SearchPanel.tsx
git commit -m "feat(web): add SearchPanel with all search options"
```

---

## Task 11: Component — ResultsTable

**Files:**
- Create: `web/src/components/ResultsTable.tsx`

**Reference:** Desktop `ui/results_table.py` (471 lines)

- [ ] **Step 1: Implement ResultsTable with virtual scrolling, highlighting, context menu**

`web/src/components/ResultsTable.tsx`:

Full implementation below. Key features: virtual scrolling, highlighting, sorting, column resize, context menu, view modes.

`web/src/components/ResultsTable.tsx`:

```tsx
import { useState, useRef, useCallback, useMemo, useEffect, ReactNode } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { t, Language } from '../i18n/translations'

export interface DisplayRow {
  score: number
  isDuplicate: boolean
  dupLangs: string[]
  data: Record<string, string>
  fileSource?: string
}

interface ResultsTableProps {
  results: DisplayRow[]
  columns: string[]
  searchQuery: string
  filterQuery: string
  searchDirection: 'source' | 'target'
  sourceColumn: string
  targetLanguages: string[]
  viewMode: '3col' | 'full'
  selectedTarget: string
  onViewModeChange: (mode: '3col' | 'full') => void
  onSelectedTargetChange: (lang: string) => void
  lang: Language
}

// Highlight helper: returns JSX fragments with colored spans
function highlightText(text: string, searchQuery: string, filterQuery: string, isSearchCol: boolean, isTargetTint: boolean): ReactNode {
  if (!text) return text
  const parts: { text: string; type: 'normal' | 'search' | 'filter' }[] = []
  let remaining = text

  // Build regex for search and filter terms
  const patterns: { regex: RegExp; type: 'search' | 'filter' }[] = []
  if (searchQuery && isSearchCol) {
    try {
      const escaped = searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      patterns.push({ regex: new RegExp(`(${escaped})`, 'gi'), type: 'search' })
    } catch { /* invalid regex */ }
  }
  if (filterQuery) {
    try {
      const escaped = filterQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      patterns.push({ regex: new RegExp(`(${escaped})`, 'gi'), type: 'filter' })
    } catch { /* invalid regex */ }
  }

  if (patterns.length === 0) {
    return isTargetTint
      ? <span className="bg-yellow-50">{text}</span>
      : text
  }

  // Simple approach: split by first matching pattern
  const allRegex = patterns.map(p => `(${p.regex.source})`).join('|')
  const combined = new RegExp(allRegex, 'gi')
  const segments = text.split(combined).filter(Boolean)

  const result = segments.map((seg, i) => {
    if (!seg) return null
    for (const p of patterns) {
      if (p.regex.test(seg)) {
        p.regex.lastIndex = 0
        const bg = p.type === 'search' ? 'bg-yellow-300' : 'bg-blue-200'
        return <span key={i} className={bg}>{seg}</span>
      }
    }
    return <span key={i} className={isTargetTint ? 'bg-yellow-50' : ''}>{seg}</span>
  })

  return <>{result}</>
}

export default function ResultsTable({
  results, columns, searchQuery, filterQuery, searchDirection,
  sourceColumn, targetLanguages, viewMode, selectedTarget,
  onViewModeChange, onSelectedTargetChange, lang,
}: ResultsTableProps) {
  const [sortCol, setSortCol] = useState<string | null>(null)
  const [sortAsc, setSortAsc] = useState(true)
  const [wordWrap, setWordWrap] = useState(false)
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; row: DisplayRow; col: string } | null>(null)
  const parentRef = useRef<HTMLDivElement>(null)

  // Determine visible columns based on view mode
  const visibleColumns = useMemo(() => {
    if (viewMode === 'full') return columns
    // 3-col: source + selected target + info/meta columns
    const target = selectedTarget || targetLanguages[0] || ''
    return columns.filter(c => c === sourceColumn || c === target || !targetLanguages.includes(c))
  }, [viewMode, columns, sourceColumn, selectedTarget, targetLanguages])

  // Sort results
  const sortedResults = useMemo(() => {
    if (!sortCol) return results
    const sorted = [...results]
    sorted.sort((a, b) => {
      if (sortCol === '%') {
        return sortAsc ? a.score - b.score : b.score - a.score
      }
      const va = a.data[sortCol] ?? ''
      const vb = b.data[sortCol] ?? ''
      return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va)
    })
    return sorted
  }, [results, sortCol, sortAsc])

  const virtualizer = useVirtualizer({
    count: sortedResults.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => wordWrap ? 60 : 32,
    overscan: 20,
  })

  const handleSort = (col: string) => {
    if (sortCol === col) setSortAsc(!sortAsc)
    else { setSortCol(col); setSortAsc(true) }
  }

  const copyToClipboard = (text: string) => navigator.clipboard.writeText(text)

  const onDoubleClick = (row: DisplayRow, col: string) => {
    copyToClipboard(row.data[col] ?? '')
  }

  const onContextMenu = (e: React.MouseEvent, row: DisplayRow, col: string) => {
    e.preventDefault()
    setContextMenu({ x: e.clientX, y: e.clientY, row, col })
  }

  // Close context menu on click outside
  useEffect(() => {
    const handler = () => setContextMenu(null)
    window.addEventListener('click', handler)
    return () => window.removeEventListener('click', handler)
  }, [])

  // Ctrl+C handler
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'c' && contextMenu) {
        copyToClipboard(contextMenu.row.data[contextMenu.col] ?? '')
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [contextMenu])

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Toolbar */}
      <div className="flex items-center gap-4 px-4 py-1 border-b text-sm bg-gray-50">
        <label className="flex items-center gap-1 cursor-pointer">
          <input type="radio" checked={viewMode === '3col'} onChange={() => onViewModeChange('3col')} />
          {t('view_3col', lang)}
        </label>
        <label className="flex items-center gap-1 cursor-pointer">
          <input type="radio" checked={viewMode === 'full'} onChange={() => onViewModeChange('full')} />
          {t('view_full', lang)}
        </label>
        {viewMode === '3col' && targetLanguages.length > 0 && (
          <select
            className="border rounded px-2 py-0.5 text-sm"
            value={selectedTarget}
            onChange={e => onSelectedTargetChange(e.target.value)}
          >
            {targetLanguages.map(l => <option key={l} value={l}>{l}</option>)}
          </select>
        )}
        <label className="flex items-center gap-1 cursor-pointer ml-auto">
          <input type="checkbox" checked={wordWrap} onChange={e => setWordWrap(e.target.checked)} />
          {t('word_wrap', lang)}
        </label>
      </div>

      {/* Table */}
      {sortedResults.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-gray-400">
          {t('no_results', lang)}
        </div>
      ) : (
        <div ref={parentRef} className="flex-1 overflow-auto">
          {/* Header */}
          <div className="sticky top-0 z-10 flex bg-gray-100 border-b text-sm font-medium">
            <div
              className="w-16 flex-shrink-0 px-2 py-1 cursor-pointer select-none border-r"
              onClick={() => handleSort('%')}
            >
              {t('col_match', lang)} {sortCol === '%' ? (sortAsc ? '▲' : '▼') : ''}
            </div>
            {visibleColumns.map(col => (
              <div
                key={col}
                className="flex-1 min-w-[120px] px-2 py-1 cursor-pointer select-none border-r truncate"
                onClick={() => handleSort(col)}
              >
                {col} {sortCol === col ? (sortAsc ? '▲' : '▼') : ''}
              </div>
            ))}
          </div>

          {/* Virtual rows */}
          <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
            {virtualizer.getVirtualItems().map(virtualRow => {
              const row = sortedResults[virtualRow.index]
              const isSearchSource = searchDirection === 'source'
              const rowBg = row.isDuplicate ? 'bg-orange-50' : ''

              return (
                <div
                  key={virtualRow.key}
                  className={`absolute left-0 right-0 flex border-b text-sm ${rowBg}`}
                  style={{
                    top: virtualRow.start,
                    height: virtualRow.size,
                  }}
                >
                  {/* Score column */}
                  <div className="w-16 flex-shrink-0 px-2 py-1 border-r text-right">
                    {row.isDuplicate ? '⚠' : ''}{row.score}%
                  </div>
                  {/* Data columns */}
                  {visibleColumns.map(col => {
                    const text = row.data[col] ?? ''
                    const isSource = col === sourceColumn
                    const isTarget = targetLanguages.includes(col)
                    const isSearchCol = (isSearchSource && isSource) || (!isSearchSource && isTarget)
                    const isTargetTint = searchQuery && ((isSearchSource && isTarget) || (!isSearchSource && isSource))

                    return (
                      <div
                        key={col}
                        className={`flex-1 min-w-[120px] px-2 py-1 border-r ${
                          wordWrap ? 'whitespace-pre-wrap break-words' : 'truncate'
                        }`}
                        onDoubleClick={() => onDoubleClick(row, col)}
                        onContextMenu={e => onContextMenu(e, row, col)}
                      >
                        {highlightText(text, searchQuery, filterQuery, isSearchCol, !!isTargetTint)}
                      </div>
                    )
                  })}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Context menu */}
      {contextMenu && (
        <div
          className="fixed z-50 bg-white border rounded shadow-lg py-1 text-sm"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          <button className="w-full px-4 py-1 text-left hover:bg-gray-100" onClick={() => {
            copyToClipboard(visibleColumns.map(c => contextMenu.row.data[c] ?? '').join('\t'))
            setContextMenu(null)
          }}>{t('copy_row', lang)}</button>
          <button className="w-full px-4 py-1 text-left hover:bg-gray-100" onClick={() => {
            copyToClipboard(contextMenu.row.data[contextMenu.col] ?? '')
            setContextMenu(null)
          }}>{t('copy_cell', lang)}</button>
          <button className="w-full px-4 py-1 text-left hover:bg-gray-100" onClick={() => {
            copyToClipboard(contextMenu.row.data[sourceColumn] ?? '')
            setContextMenu(null)
          }}>{t('copy_source', lang)}</button>
          <button className="w-full px-4 py-1 text-left hover:bg-gray-100" onClick={() => {
            const targetCol = selectedTarget || targetLanguages[0] || ''
            copyToClipboard(contextMenu.row.data[targetCol] ?? '')
            setContextMenu(null)
          }}>{t('copy_target', lang)}</button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/ResultsTable.tsx
git commit -m "feat(web): add ResultsTable with virtual scroll, highlighting, and context menu"
```

---

## Task 12: Component — ColumnMapper

**Files:**
- Create: `web/src/components/ColumnMapper.tsx`

**Reference:** Desktop `ui/column_mapper.py` (92 lines)

- [ ] **Step 1: Implement ColumnMapper modal**

`web/src/components/ColumnMapper.tsx`:

```tsx
import { useState } from 'react'
import { t, Language } from '../i18n/translations'

interface ColumnMapperProps {
  columns: string[]
  currentSource: string
  currentTargets: string[]
  previewData: Record<string, string>[]  // first 5 rows
  onConfirm: (source: string, targets: string[]) => void
  onCancel: () => void
  lang: Language
}

export default function ColumnMapper({
  columns, currentSource, currentTargets, previewData, onConfirm, onCancel, lang,
}: ColumnMapperProps) {
  const [source, setSource] = useState(currentSource)
  const [targets, setTargets] = useState<Set<string>>(new Set(currentTargets))

  const toggleTarget = (col: string) => {
    const next = new Set(targets)
    if (next.has(col)) next.delete(col)
    else next.add(col)
    setTargets(next)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-[600px] max-h-[80vh] overflow-auto p-6">
        <h2 className="text-lg font-semibold mb-4">{t('column_settings', lang)}</h2>

        {/* Source column */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">{t('source_column', lang)}</label>
          <select
            className="w-full border rounded px-3 py-1.5 text-sm"
            value={source}
            onChange={e => setSource(e.target.value)}
          >
            {columns.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        {/* Target columns */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">{t('target_columns', lang)}</label>
          <div className="flex flex-wrap gap-2">
            {columns.filter(c => c !== source).map(c => (
              <label key={c} className="flex items-center gap-1 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={targets.has(c)}
                  onChange={() => toggleTarget(c)}
                />
                {c}
              </label>
            ))}
          </div>
        </div>

        {/* Preview */}
        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">{t('preview', lang)}</label>
          <div className="border rounded overflow-auto max-h-40">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-gray-50">
                  {columns.map(c => (
                    <th key={c} className="px-2 py-1 text-left border-b">{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewData.slice(0, 5).map((row, i) => (
                  <tr key={i}>
                    {columns.map(c => (
                      <td key={c} className="px-2 py-1 border-b truncate max-w-[150px]">
                        {row[c] ?? ''}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Buttons */}
        <div className="flex justify-end gap-2">
          <button
            className="px-4 py-1.5 border rounded text-sm hover:bg-gray-50"
            onClick={onCancel}
          >
            {t('btn_cancel', lang)}
          </button>
          <button
            className="px-4 py-1.5 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
            onClick={() => onConfirm(source, Array.from(targets))}
          >
            {t('btn_ok', lang)}
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/components/ColumnMapper.tsx
git commit -m "feat(web): add ColumnMapper modal with source/target selection and preview"
```

---

## Task 13: Component — App (Main Orchestrator)

**Files:**
- Create: `web/src/components/App.tsx`
- Modify: `web/src/main.tsx`

**Reference:** Desktop `ui/main_window.py` (745 lines)

This is the central component that wires everything together. Key responsibilities:

- [ ] **Step 1: Implement full App component**

`web/src/components/App.tsx`:

```tsx
import { useState, useCallback, useRef, useEffect, useMemo } from 'react'
import { parseFile, detectColumns, checkEntryLimit, normalizeColumnName, classifyColumn, ParsedFile, ColumnDetection } from '../core/parser'
import { SearchConfig, SearchResult, search } from '../core/search'
import { SessionManager, Session } from '../core/session'
import { t, Language } from '../i18n/translations'
import SearchPanel from './SearchPanel'
import { DisplayRow } from './ResultsTable'
import ResultsTable from './ResultsTable'
import FileTabs from './FileTabs'
import DropZone from './DropZone'
import ColumnMapper from './ColumnMapper'
import ToastContainer, { showToast } from './Toast'

interface LoadedFile {
  data: Record<string, string>[]
  columns: string[]
  source: string
  targets: string[]
  name: string
}

const DOG_FRAMES = [
  '🐕 •        ', '🐕  •       ', '🐕   •      ', '🐕    •     ',
  '🐕     •    ', '🐕      •   ', '🐕       •  ', '🐕        • ',
  '🐕       •  ', '🐕      •   ', '🐕     •    ', '🐕    •     ',
  '🐕   •      ', '🐕  •       ',
]

const APP_VERSION = '1.0'

export default function App() {
  // Session
  const [session, setSession] = useState<Session>(() => SessionManager.load())
  const lang = session.language

  // Files
  const [loadedFiles, setLoadedFiles] = useState<Map<string, LoadedFile>>(new Map())
  const [activeTab, setActiveTab] = useState<string>('all')
  const [totalEntries, setTotalEntries] = useState(0)

  // Search
  const [searchResults, setSearchResults] = useState<DisplayRow[]>([])
  const [totalHits, setTotalHits] = useState(0)
  const [isSearching, setIsSearching] = useState(false)
  const [searchTime, setSearchTime] = useState(0)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterQuery, setFilterQuery] = useState('')
  const [searchDirection, setSearchDirection] = useState<'source' | 'target'>('source')

  // UI state
  const [showColumnMapper, setShowColumnMapper] = useState<string | null>(null)  // file path or null
  const [showAbout, setShowAbout] = useState(false)
  const [dogFrame, setDogFrame] = useState(0)
  const dogTimerRef = useRef<number | null>(null)
  const workerRef = useRef<Worker | null>(null)
  const searchIdRef = useRef(0)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const searchStartTime = useRef<number>(0)
  const processResultsRef = useRef<(results: SearchResult[]) => void>(() => {})

  // Dog animation
  useEffect(() => {
    if (isSearching) {
      dogTimerRef.current = window.setInterval(() => {
        setDogFrame(f => (f + 1) % DOG_FRAMES.length)
      }, 150)
    } else if (dogTimerRef.current) {
      clearInterval(dogTimerRef.current)
      dogTimerRef.current = null
    }
    return () => { if (dogTimerRef.current) clearInterval(dogTimerRef.current) }
  }, [isSearching])

  // Save session on change
  useEffect(() => {
    SessionManager.save(session)
  }, [session])

  // Ctrl+O handler
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'o') {
        e.preventDefault()
        fileInputRef.current?.click()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // Initialize Web Worker
  useEffect(() => {
    try {
      workerRef.current = new Worker(
        new URL('../workers/search.worker.ts', import.meta.url),
        { type: 'module' }
      )
      workerRef.current.onmessage = (e) => {
        const { type, results, id } = e.data
        if (id !== searchIdRef.current) return  // stale result
        if (type === 'result') {
          processResultsRef.current(results)
        }
        setIsSearching(false)
      }
    } catch {
      // Worker failed (e.g., file:// protocol) — will use main thread fallback
      workerRef.current = null
    }
    return () => workerRef.current?.terminate()
  }, [])

  // Get ordered target columns across all files
  const getOrderedTargets = useCallback((): string[] => {
    const langCols = new Map<string, number>()
    const infoCols = new Map<string, number>()
    const metaCols = new Map<string, number>()
    let order = 0

    for (const file of loadedFiles.values()) {
      for (const col of file.targets) {
        const norm = normalizeColumnName(col)
        const cls = classifyColumn(norm)
        const target = cls === 0 ? langCols : cls === 1 ? infoCols : metaCols
        if (!target.has(norm)) target.set(norm, order++)
      }
    }

    const sorted = (m: Map<string, number>) =>
      [...m.entries()].sort((a, b) => a[1] - b[1]).map(e => e[0])

    return [...sorted(langCols), ...sorted(infoCols), ...sorted(metaCols)]
  }, [loadedFiles])

  const orderedTargets = useMemo(() => getOrderedTargets(), [getOrderedTargets])
  const langTargets = useMemo(() => orderedTargets.filter(c => classifyColumn(c) === 0), [orderedTargets])

  // Build search data for the active tab
  const buildSearchData = useCallback((direction: 'source' | 'target'): { entries: Record<string, string>[]; searchColumn: string; fileSources: string[] } => {
    const files = activeTab === 'all'
      ? [...loadedFiles.values()]
      : loadedFiles.has(activeTab) ? [loadedFiles.get(activeTab)!] : []

    const entries: Record<string, string>[] = []
    const fileSources: string[] = []

    for (const file of files) {
      const sourceNorm = normalizeColumnName(file.source)
      for (const row of file.data) {
        const normalized: Record<string, string> = {}
        for (const col of file.columns) {
          normalized[normalizeColumnName(col)] = row[col] ?? ''
        }
        normalized['__source_file'] = file.name
        entries.push(normalized)
        fileSources.push(file.name)
      }
    }

    const sourceCol = files[0] ? normalizeColumnName(files[0].source) : 'KO'
    const searchColumn = direction === 'source'
      ? sourceCol
      : (session.selected_target || langTargets[0] || sourceCol)

    return { entries, searchColumn, fileSources }
  }, [activeTab, loadedFiles, session.selected_target, langTargets])

  // Process search results into display rows
  const processSearchResults = useCallback((results: SearchResult[]) => {
    const { entries } = buildSearchData(searchDirection)
    const sourceCol = [...loadedFiles.values()][0]
      ? normalizeColumnName([...loadedFiles.values()][0].source)
      : 'KO'

    // Detect duplicates: same source text, different translations
    const sourceMap = new Map<string, Set<string>>()
    for (const r of results) {
      const entry = entries[r.index]
      if (!entry) continue
      const srcText = entry[sourceCol] ?? ''
      if (!sourceMap.has(srcText)) sourceMap.set(srcText, new Set())
      for (const lang of langTargets) {
        const val = entry[lang]
        if (val) sourceMap.get(srcText)!.add(`${lang}:${val}`)
      }
    }

    const dupSources = new Set<string>()
    for (const [src, translations] of sourceMap) {
      // Check if same language has different values
      const byLang = new Map<string, Set<string>>()
      for (const t of translations) {
        const [lang, val] = [t.split(':')[0], t.slice(t.indexOf(':') + 1)]
        if (!byLang.has(lang)) byLang.set(lang, new Set())
        byLang.get(lang)!.add(val)
      }
      for (const [, vals] of byLang) {
        if (vals.size > 1) { dupSources.add(src); break }
      }
    }

    const displayRows: DisplayRow[] = results.map(r => {
      const entry = entries[r.index] ?? {}
      const srcText = entry[sourceCol] ?? ''
      const isDuplicate = dupSources.has(srcText)
      return {
        score: r.score,
        isDuplicate,
        dupLangs: [],
        data: entry,
        fileSource: entry['__source_file'],
      }
    })

    // Apply secondary filter
    let filtered = displayRows
    if (filterQuery.trim()) {
      const ft = filterQuery.trim().toLowerCase()
      filtered = displayRows.filter(row => {
        // When searching source, filter by target text; vice versa
        if (searchDirection === 'source') {
          return langTargets.some(l => (row.data[l] ?? '').toLowerCase().includes(ft))
        } else {
          return (row.data[sourceCol] ?? '').toLowerCase().includes(ft)
        }
      })
    }

    setSearchResults(filtered)
    setTotalHits(results.length)
    setSearchTime((performance.now() - (searchStartTime.current ?? 0)) / 1000)
  }, [buildSearchData, searchDirection, filterQuery, loadedFiles, langTargets])

  // Keep ref in sync so Worker onmessage always calls latest version
  processResultsRef.current = processSearchResults

  // Handle search
  const handleSearch = useCallback((config: SearchConfig, direction: 'source' | 'target') => {
    setSearchQuery(config.query)
    setSearchDirection(direction)
    setIsSearching(true)
    searchStartTime.current = performance.now()
    const id = ++searchIdRef.current

    const { entries, searchColumn } = buildSearchData(direction)

    if (workerRef.current) {
      workerRef.current.postMessage({ type: 'search', entries, searchColumn, config, id })
    } else {
      // Main thread fallback
      const results = search(entries, searchColumn, config)
      processSearchResults(results)
      setIsSearching(false)
    }
  }, [buildSearchData, processSearchResults])

  // Handle file loading
  const handleFilesDropped = useCallback(async (files: File[]) => {
    for (const file of files) {
      try {
        const ext = file.name.split('.').pop()?.toLowerCase()
        if (!['xlsx', 'csv', 'txt'].includes(ext ?? '')) {
          showToast(t('unsupported_format', lang))
          continue
        }

        const parsed = await parseFile(file)
        checkEntryLimit(totalEntries, parsed.data.length, file.name)

        const { source, targets } = detectColumns(parsed.data, parsed.columns)

        // Check if source column has Korean content
        const hasKorean = parsed.data.slice(0, 10).some(row =>
          /[\uAC00-\uD7AF]/.test(row[source] ?? '')
        )

        const path = file.name + '_' + Date.now()
        const loaded: LoadedFile = {
          data: parsed.data,
          columns: parsed.columns,
          source,
          targets,
          name: file.name,
        }

        setLoadedFiles(prev => new Map(prev).set(path, loaded))
        setTotalEntries(prev => prev + parsed.data.length)
        showToast(t('file_loaded', lang, { file: file.name, count: parsed.data.length }))

        if (parsed.extraSheets > 0) {
          showToast(t('extra_sheets', lang, { file: file.name, count: parsed.extraSheets }))
        }

        // Auto-open column mapper if no Korean detected
        if (!hasKorean) {
          setShowColumnMapper(path)
        }
      } catch (e: any) {
        showToast(e.message || String(e))
      }
    }
  }, [lang, totalEntries])

  const handleFileClose = useCallback((path: string) => {
    setLoadedFiles(prev => {
      const next = new Map(prev)
      const file = next.get(path)
      if (file) setTotalEntries(t => t - file.data.length)
      next.delete(path)
      return next
    })
    if (activeTab === path) setActiveTab('all')
  }, [activeTab])

  const handleColumnConfirm = useCallback((source: string, targets: string[]) => {
    if (!showColumnMapper) return
    setLoadedFiles(prev => {
      const next = new Map(prev)
      const file = next.get(showColumnMapper)
      if (file) next.set(showColumnMapper, { ...file, source, targets })
      return next
    })
    setShowColumnMapper(null)
  }, [showColumnMapper])

  const fileList = useMemo(() =>
    [...loadedFiles.entries()].map(([path, f]) => ({ path, name: f.name })),
    [loadedFiles]
  )

  const hasFiles = loadedFiles.size > 0

  // Columns for display
  const displayColumns = useMemo(() => {
    const sourceCol = [...loadedFiles.values()][0]
      ? normalizeColumnName([...loadedFiles.values()][0].source)
      : 'KO'
    const cols = [sourceCol, ...orderedTargets.filter(c => c !== sourceCol)]
    if (activeTab === 'all' && loadedFiles.size > 1) cols.push('__source_file')
    return cols
  }, [loadedFiles, orderedTargets, activeTab])

  return (
    <div className="h-screen flex flex-col bg-white text-gray-900">
      {/* Menu bar */}
      <div className="flex items-center border-b px-2 py-0.5 text-sm bg-gray-50">
        <div className="relative group">
          <button className="px-2 py-0.5 hover:bg-gray-200 rounded">{t('menu_file', lang)}</button>
          <div className="absolute left-0 top-full hidden group-hover:block bg-white border rounded shadow-lg z-20">
            <button className="block w-full px-4 py-1.5 text-left hover:bg-gray-100 whitespace-nowrap"
              onClick={() => fileInputRef.current?.click()}>
              {t('menu_open', lang)} <span className="text-gray-400 ml-4">Ctrl+O</span>
            </button>
          </div>
        </div>
        <div className="relative group">
          <button className="px-2 py-0.5 hover:bg-gray-200 rounded">{t('menu_help', lang)}</button>
          <div className="absolute left-0 top-full hidden group-hover:block bg-white border rounded shadow-lg z-20">
            <button className="block w-full px-4 py-1.5 text-left hover:bg-gray-100 whitespace-nowrap"
              onClick={() => setShowAbout(true)}>
              {t('menu_about', lang)}
            </button>
          </div>
        </div>
      </div>

      {/* File input (hidden) */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept=".xlsx,.csv,.txt"
        multiple
        onChange={e => {
          if (e.target.files) handleFilesDropped(Array.from(e.target.files))
          e.target.value = ''
        }}
      />

      {/* File tabs */}
      {hasFiles && (
        <FileTabs
          files={fileList}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onFileClose={handleFileClose}
          onConfigure={() => {
            const firstFile = [...loadedFiles.keys()][0]
            if (firstFile) setShowColumnMapper(firstFile)
          }}
          lang={lang}
        />
      )}

      {/* Search panel */}
      {hasFiles && (
        <SearchPanel
          onSearch={handleSearch}
          onFilterChange={setFilterQuery}
          totalHits={totalHits}
          lang={lang}
          initialConfig={session.search_settings}
        />
      )}

      {/* Main content */}
      {hasFiles ? (
        <ResultsTable
          results={searchResults}
          columns={displayColumns}
          searchQuery={searchQuery}
          filterQuery={filterQuery}
          searchDirection={searchDirection}
          sourceColumn={displayColumns[0] || 'KO'}
          targetLanguages={langTargets}
          viewMode={session.view_mode}
          selectedTarget={session.selected_target}
          onViewModeChange={mode => setSession(s => ({ ...s, view_mode: mode }))}
          onSelectedTargetChange={tgt => setSession(s => ({ ...s, selected_target: tgt }))}
          lang={lang}
        />
      ) : (
        <DropZone onFilesDropped={handleFilesDropped} lang={lang} hasFiles={false} />
      )}

      {/* DropZone overlay for drag when files exist */}
      {hasFiles && <DropZone onFilesDropped={handleFilesDropped} lang={lang} hasFiles={true} />}

      {/* Status bar */}
      <div className="flex items-center justify-between border-t px-4 py-1 text-xs bg-gray-50">
        <div className="font-mono">
          {isSearching
            ? DOG_FRAMES[dogFrame]
            : searchTime > 0
              ? t('search_time', lang, { time: searchTime.toFixed(2) })
              : t('status_ready', lang)
          }
        </div>
        <div className="flex items-center gap-4">
          {hasFiles && (
            <span>{t('status_files', lang, { count: loadedFiles.size, entries: totalEntries })}</span>
          )}
          <button
            className="px-2 py-0.5 border rounded text-xs hover:bg-gray-100"
            onClick={() => setSession(s => ({ ...s, language: s.language === 'ko' ? 'en' : 'ko' }))}
          >
            {lang === 'ko' ? 'EN' : 'KO'}
          </button>
        </div>
      </div>

      {/* Column Mapper Modal */}
      {showColumnMapper && loadedFiles.has(showColumnMapper) && (() => {
        const file = loadedFiles.get(showColumnMapper)!
        return (
          <ColumnMapper
            columns={file.columns}
            currentSource={file.source}
            currentTargets={file.targets}
            previewData={file.data.slice(0, 5)}
            onConfirm={handleColumnConfirm}
            onCancel={() => setShowColumnMapper(null)}
            lang={lang}
          />
        )
      })()}

      {/* About Modal */}
      {showAbout && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={() => setShowAbout(false)}>
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-sm" onClick={e => e.stopPropagation()}>
            <h2 className="text-lg font-semibold mb-2">{t('about_title', lang)}</h2>
            <p className="text-sm text-gray-600">{t('about_text', lang, { version: APP_VERSION })}</p>
            <button className="mt-4 px-4 py-1.5 bg-blue-500 text-white rounded text-sm"
              onClick={() => setShowAbout(false)}>{t('btn_ok', lang)}</button>
          </div>
        </div>
      )}

      <ToastContainer />
    </div>
  )
}
```

- [ ] **Step 2: Wire entry point**

- [ ] **Step 4: Update main.tsx entry point**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './components/App'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
```

- [ ] **Step 5: Verify the full app works end-to-end**

```bash
cd D:/VS/kibble/web
npm run dev
```

Test manually:
1. Drag an xlsx file → loads, shows tabs
2. Search a term → results appear with highlighting
3. Toggle view modes, sort columns
4. Switch EN/KO language
5. Right-click → copy options work

- [ ] **Step 6: Commit**

```bash
git add web/src/components/App.tsx web/src/main.tsx
git commit -m "feat(web): implement App orchestrator with full search workflow"
```

---

## Task 14: Build Configuration & Local Serving

**Files:**
- Modify: `web/vite.config.ts`
- Modify: `web/package.json`

- [ ] **Step 1: Add build and preview scripts**

Verify `package.json` has:
```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  }
}
```

- [ ] **Step 2: Test production build**

```bash
cd D:/VS/kibble/web
npm run build
npx serve dist
```

Expected: Opens at localhost, full app works from built static files.

- [ ] **Step 3: Verify Web Worker fallback**

Open `dist/index.html` directly in browser via `file://`. Search should still work (falls back to main thread). May show console warning about Worker.

- [ ] **Step 4: Commit**

```bash
git add web/vite.config.ts web/package.json
git commit -m "feat(web): configure build for static deployment with relative paths"
```

---

## Task 15: Additional Tests (i18n, Worker)

**Files:**
- Create: `web/tests/i18n.test.ts`

- [ ] **Step 1: Write i18n tests**

`web/tests/i18n.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { t } from '../src/i18n/translations'

describe('t (translation)', () => {
  it('returns Korean by default', () => {
    expect(t('btn_search', 'ko')).toBe('검색')
  })

  it('returns English translation', () => {
    expect(t('btn_search', 'en')).toBe('Search')
  })

  it('interpolates parameters', () => {
    expect(t('file_loaded', 'en', { file: 'test.xlsx', count: 100 }))
      .toBe('test.xlsx loaded (100 entries)')
  })

  it('falls back to key for missing translation', () => {
    expect(t('nonexistent_key', 'en')).toBe('nonexistent_key')
  })

  it('falls back to Korean for unknown language', () => {
    expect(t('btn_search', 'fr' as any)).toBe('검색')
  })
})
```

- [ ] **Step 2: Run i18n tests**

```bash
npx vitest run tests/i18n.test.ts
```

- [ ] **Step 3: Add token_set_ratio tests to search.test.ts**

Add to `web/tests/search.test.ts`:

```typescript
describe('fuzzyScore (token_set_ratio)', () => {
  it('handles reordered tokens', () => {
    const score = fuzzyScore('translation memory', 'memory translation')
    expect(score).toBe(100)  // same tokens, different order
  })

  it('handles partial token overlap', () => {
    const score = fuzzyScore('translation memory tool', 'memory tool')
    expect(score).toBeGreaterThan(70)
  })
})
```

- [ ] **Step 4: Commit**

```bash
git add web/tests/i18n.test.ts web/tests/search.test.ts
git commit -m "test(web): add i18n and fuzzy token_set_ratio tests"
```

---

## Task 16: Final Testing & Polish

- [ ] **Step 1: Run all unit tests**

```bash
cd D:/VS/kibble/web
npx vitest run
```

Expected: All tests pass.

- [ ] **Step 2: Manual testing checklist**

- [ ] Load xlsx, csv, txt files
- [ ] Column auto-detection works
- [ ] Column mapper opens when source is non-Korean
- [ ] Extra sheets notification shown
- [ ] Search all modes: substring, fuzzy, both
- [ ] Ignore spaces works
- [ ] Wildcard patterns work
- [ ] Case sensitivity works
- [ ] Translation filter works
- [ ] 3-col and full view modes
- [ ] Column sorting
- [ ] Word wrap toggle
- [ ] Double-click copy
- [ ] Right-click context menu
- [ ] EN/KO language toggle
- [ ] Session persists across page reload
- [ ] Dog animation during search
- [ ] "All" tab merges files
- [ ] Duplicate translation warning
- [ ] 500K limit check

- [ ] **Step 3: Fix any issues found**

- [ ] **Step 4: Final commit**

```bash
git add -A web/
git commit -m "feat(web): complete Kibble Web v1.0 with full feature parity"
```
