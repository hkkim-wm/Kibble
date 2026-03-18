import { useCallback, useMemo, useRef, useState } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { t, type Language } from '../i18n/translations'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

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
  darkMode?: boolean
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type SortDir = 'asc' | 'desc'

/** Highlight `term` inside `text`. Returns React nodes. */
function highlightText(
  text: string,
  term: string,
  className: string,
): React.ReactNode {
  if (!term) return text
  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escaped})`, 'gi')
  const parts = text.split(regex)
  if (parts.length === 1) return text
  return parts.map((part, i) =>
    regex.test(part) ? (
      <mark key={i} className={className}>
        {part}
      </mark>
    ) : (
      part
    ),
  )
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ResultsTable({
  results,
  columns,
  searchQuery,
  filterQuery,
  searchDirection,
  sourceColumn,
  targetLanguages,
  viewMode,
  selectedTarget,
  onViewModeChange,
  onSelectedTargetChange,
  lang,
  darkMode = false,
}: ResultsTableProps) {
  // -- Local state ----------------------------------------------------------
  const [sortCol, setSortCol] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [wordWrap, setWordWrap] = useState(false)
  const [ctxMenu, setCtxMenu] = useState<{
    x: number
    y: number
    row: DisplayRow
    cellValue: string
  } | null>(null)
  const [colWidths, setColWidths] = useState<Record<string, number>>({})
  const [fontSize, setFontSize] = useState<number>(14)

  const parentRef = useRef<HTMLDivElement>(null)
  const resizingRef = useRef<{ col: string; startX: number; startW: number } | null>(null)

  // -- Visible columns ------------------------------------------------------
  const visibleColumns = useMemo(() => {
    if (viewMode === 'full') return columns
    // 3-col: source + selected target + non-language columns
    return columns.filter(
      col =>
        col === sourceColumn ||
        col === selectedTarget ||
        !targetLanguages.includes(col),
    )
  }, [columns, viewMode, sourceColumn, selectedTarget, targetLanguages])

  // -- Sorting --------------------------------------------------------------
  const sortedResults = useMemo(() => {
    if (!sortCol) return results
    const arr = [...results]
    const dir = sortDir === 'asc' ? 1 : -1
    if (sortCol === '__score') {
      arr.sort((a, b) => (a.score - b.score) * dir)
    } else {
      arr.sort((a, b) => {
        const av = a.data[sortCol] ?? ''
        const bv = b.data[sortCol] ?? ''
        return av.localeCompare(bv) * dir
      })
    }
    return arr
  }, [results, sortCol, sortDir])

  const handleHeaderClick = useCallback(
    (col: string) => {
      if (sortCol === col) {
        setSortDir(d => (d === 'asc' ? 'desc' : 'asc'))
      } else {
        setSortCol(col)
        setSortDir(col === '__score' ? 'desc' : 'asc')
      }
    },
    [sortCol],
  )

  // -- Virtual scrolling ----------------------------------------------------
  const virtualizer = useVirtualizer({
    count: sortedResults.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 36,
    overscan: 20,
  })

  // -- Column resize ---------------------------------------------------------
  const handleResizeStart = useCallback((e: React.MouseEvent, col: string) => {
    e.preventDefault()
    e.stopPropagation()
    const startX = e.clientX
    const startW = colWidths[col] ?? 150

    resizingRef.current = { col, startX, startW }

    const onMouseMove = (ev: MouseEvent) => {
      if (!resizingRef.current) return
      const delta = ev.clientX - resizingRef.current.startX
      const newWidth = Math.max(60, resizingRef.current.startW + delta)
      setColWidths(prev => ({ ...prev, [resizingRef.current!.col]: newWidth }))
    }
    const onMouseUp = () => {
      resizingRef.current = null
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }
    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }, [colWidths])

  // -- Double-click: copy cell ----------------------------------------------
  const handleDoubleClick = useCallback((_e: React.MouseEvent, text: string) => {
    navigator.clipboard.writeText(text)
  }, [])

  // -- Context menu ---------------------------------------------------------
  const handleContextMenu = useCallback(
    (e: React.MouseEvent, row: DisplayRow, cellValue: string) => {
      e.preventDefault()
      setCtxMenu({ x: e.clientX, y: e.clientY, row, cellValue })
    },
    [],
  )

  const closeCtx = useCallback(() => setCtxMenu(null), [])

  const copyToClipboard = useCallback(
    (text: string) => {
      navigator.clipboard.writeText(text)
      closeCtx()
    },
    [closeCtx],
  )

  // -- Determine target column for "copy target" ----------------------------
  const effectiveTarget = viewMode === '3col' ? selectedTarget : targetLanguages[0] ?? ''

  // -- Sort arrow -----------------------------------------------------------
  const sortArrow = (col: string) => {
    if (sortCol !== col) return null
    return sortDir === 'asc' ? ' ▲' : ' ▼'
  }

  // -- Render ---------------------------------------------------------------
  if (results.length === 0) {
    return (
      <div className={`flex-1 flex items-center justify-center text-sm ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
        {t('no_results', lang)}
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-h-0" onClick={closeCtx}>
      {/* Toolbar */}
      <div className={`flex items-center gap-4 px-3 py-1.5 border-b text-sm shrink-0 ${darkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-50'}`}>
        {/* View mode radios */}
        <label className="flex items-center gap-1 cursor-pointer">
          <input
            type="radio"
            name="viewMode"
            checked={viewMode === '3col'}
            onChange={() => onViewModeChange('3col')}
            className="accent-blue-600"
          />
          {t('view_3col', lang)}
        </label>
        <label className="flex items-center gap-1 cursor-pointer">
          <input
            type="radio"
            name="viewMode"
            checked={viewMode === 'full'}
            onChange={() => onViewModeChange('full')}
            className="accent-blue-600"
          />
          {t('view_full', lang)}
        </label>

        {/* Target language selector (3-col only) */}
        {viewMode === '3col' && targetLanguages.length > 1 && (
          <select
            value={selectedTarget}
            onChange={e => onSelectedTargetChange(e.target.value)}
            className={`border rounded px-1.5 py-0.5 text-sm ${darkMode ? 'border-gray-600 bg-gray-700 text-gray-200' : 'border-gray-300'}`}
          >
            {targetLanguages.map(tl => (
              <option key={tl} value={tl}>
                {tl}
              </option>
            ))}
          </select>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Word wrap */}
        <label className="flex items-center gap-1 cursor-pointer">
          <input
            type="checkbox"
            checked={wordWrap}
            onChange={e => setWordWrap(e.target.checked)}
            className="accent-blue-600"
          />
          {t('word_wrap', lang)}
        </label>

        {/* Font size */}
        <div className="flex items-center gap-1">
          <span className="text-xs text-gray-500">{t('font_size', lang)}</span>
          {([['S', 12], ['M', 14], ['L', 16], ['XL', 18]] as const).map(([label, size]) => (
            <button
              key={label}
              className={`px-1.5 py-0.5 text-xs rounded border ${
                fontSize === size
                  ? 'bg-blue-600 text-white border-blue-600'
                  : darkMode
                    ? 'bg-gray-700 text-gray-300 border-gray-600 hover:bg-gray-600'
                    : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-100'
              }`}
              onClick={() => setFontSize(size)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Scrollable table area (horizontal + vertical) */}
      <div ref={parentRef} className="flex-1 overflow-auto min-h-0">
        {/* Inner container with min-width to enable horizontal scroll */}
        <div style={{ minWidth: 64 + visibleColumns.reduce((sum, col) => sum + (colWidths[col] ?? 200), 0) }}>
          {/* Table header — sticky */}
          <div className={`flex border-b text-xs font-semibold sticky top-0 z-10 ${darkMode ? 'border-gray-600 bg-gray-800 text-gray-400' : 'border-gray-300 bg-gray-100 text-gray-600'}`}>
            {/* Score column */}
            <div
              className={`w-16 shrink-0 px-2 py-2 text-right cursor-pointer select-none ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-200'}`}
              onClick={() => handleHeaderClick('__score')}
            >
              {t('col_match', lang)}
              {sortArrow('__score')}
            </div>
            {/* Data columns */}
            {visibleColumns.map(col => (
              <div
                key={col}
                className={`relative px-2 py-2 cursor-pointer select-none truncate shrink-0 border-l ${darkMode ? 'hover:bg-gray-700 border-gray-700' : 'hover:bg-gray-200 border-gray-200'}`}
                style={{ width: colWidths[col] ?? 200 }}
                onClick={() => handleHeaderClick(col)}
              >
                {col}
                {sortArrow(col)}
                {/* Resize handle */}
                <div
                  className="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-blue-400/50"
                  onMouseDown={e => handleResizeStart(e, col)}
                />
              </div>
            ))}
          </div>

          {/* Virtualised body */}
          <div
            className="relative"
            style={{ height: virtualizer.getTotalSize() }}
          >
          {virtualizer.getVirtualItems().map(vRow => {
            const row = sortedResults[vRow.index]
            const isSearchSource = searchDirection === 'source'
            const searchCol = isSearchSource ? sourceColumn : effectiveTarget
            const highlightCol = isSearchSource ? effectiveTarget : sourceColumn

            return (
              <div
                key={vRow.index}
                data-index={vRow.index}
                ref={virtualizer.measureElement}
                className={`absolute left-0 w-full flex border-b text-sm ${
                  darkMode
                    ? `border-gray-800 ${row.isDuplicate ? 'bg-orange-950' : vRow.index % 2 === 0 ? 'bg-gray-900' : 'bg-gray-850'}`
                    : `border-gray-100 ${row.isDuplicate ? 'bg-orange-50' : vRow.index % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}`
                }`}
                style={{ top: vRow.start }}
              >
                {/* Score */}
                <div
                  className="w-16 shrink-0 px-2 py-1.5 text-right tabular-nums"
                  style={{ fontSize }}
                  onDoubleClick={e => handleDoubleClick(e, String(row.score))}
                  onContextMenu={e => handleContextMenu(e, row, String(row.score))}
                >
                  {row.isDuplicate && (
                    <span title={t('dup_translation', lang)}>⚠</span>
                  )}
                  {row.score}%
                </div>

                {/* Data cells */}
                {visibleColumns.map(col => {
                  const value = row.data[col] ?? ''
                  const isTarget = targetLanguages.includes(col)
                  const tintBg =
                    searchQuery && isTarget && col !== searchCol
                      ? darkMode ? ' bg-yellow-900/30' : ' bg-yellow-50'
                      : ''

                  const searchHlClass = darkMode
                    ? 'bg-yellow-700 text-white rounded-sm'
                    : 'bg-yellow-300 rounded-sm'
                  const filterHlClass = darkMode
                    ? 'bg-blue-800 text-white rounded-sm'
                    : 'bg-blue-200 rounded-sm'

                  let content: React.ReactNode = value
                  if (col === searchCol && searchQuery) {
                    content = highlightText(value, searchQuery, searchHlClass)
                  } else if (col === highlightCol && filterQuery) {
                    content = highlightText(value, filterQuery, filterHlClass)
                  } else if (filterQuery) {
                    content = highlightText(value, filterQuery, filterHlClass)
                  }

                  return (
                    <div
                      key={col}
                      className={`shrink-0 px-2 py-1.5 border-l ${darkMode ? 'border-gray-800' : 'border-gray-100'}${tintBg}${
                        wordWrap ? ' whitespace-pre-wrap break-words' : ' truncate'
                      }`}
                      style={{ width: colWidths[col] ?? 200, fontSize }}
                      onDoubleClick={e => handleDoubleClick(e, value)}
                      onContextMenu={e => handleContextMenu(e, row, value)}
                    >
                      {content}
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
        </div>{/* end inner min-width container */}
      </div>{/* end scrollable area */}

      {/* Context menu */}
      {ctxMenu && (
        <div
          className={`fixed z-50 border rounded shadow-lg py-1 text-sm min-w-[160px] ${darkMode ? 'bg-gray-800 border-gray-600 text-gray-200' : 'bg-white border-gray-300'}`}
          style={{ left: ctxMenu.x, top: ctxMenu.y }}
        >
          <button
            className={`w-full text-left px-3 py-1 ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-blue-50'}`}
            onClick={() => {
              const rowText = visibleColumns.map(c => ctxMenu.row.data[c] ?? '').join('\t')
              copyToClipboard(rowText)
            }}
          >
            {t('copy_row', lang)}
          </button>
          <button
            className={`w-full text-left px-3 py-1 ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-blue-50'}`}
            onClick={() => copyToClipboard(ctxMenu.cellValue)}
          >
            {t('copy_cell', lang)}
          </button>
          <button
            className={`w-full text-left px-3 py-1 ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-blue-50'}`}
            onClick={() => copyToClipboard(ctxMenu.row.data[sourceColumn] ?? '')}
          >
            {t('copy_source', lang)}
          </button>
          <button
            className={`w-full text-left px-3 py-1 ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-blue-50'}`}
            onClick={() => copyToClipboard(ctxMenu.row.data[effectiveTarget] ?? '')}
          >
            {t('copy_target', lang)}
          </button>
        </div>
      )}
    </div>
  )
}
