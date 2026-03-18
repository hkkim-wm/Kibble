import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { parseFile, detectColumns, checkEntryLimit, classifyColumn, normalizeColumnName } from '../core/parser'
import type { SearchConfig, SearchResult } from '../core/search'
import { search } from '../core/search'
import { SessionManager } from '../core/session'
import type { Session } from '../core/session'
import { t } from '../i18n/translations'
import type { Language } from '../i18n/translations'

import ToastContainer, { showToast } from './Toast'
import DropZone from './DropZone'
import FileTabs, { SEARCH_ALL_ID } from './FileTabs'
import SearchPanel from './SearchPanel'
import ResultsTable from './ResultsTable'
import type { DisplayRow } from './ResultsTable'
import ColumnMapper from './ColumnMapper'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LoadedFile {
  data: Record<string, string>[]
  columns: string[]
  source: string
  targets: string[]
  name: string
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const APP_VERSION = '1.0.0'

const HANGUL_RE = /[\uAC00-\uD7AF]/

// ---------------------------------------------------------------------------
// App Component
// ---------------------------------------------------------------------------

export default function App() {
  // -- Session & language ---------------------------------------------------
  const [session, setSession] = useState<Session>(() => SessionManager.load())
  const [lang, setLang] = useState<Language>(session.language)

  // -- Files ----------------------------------------------------------------
  const [loadedFiles, setLoadedFiles] = useState<Map<string, LoadedFile>>(new Map())
  const [activeTab, setActiveTab] = useState<string>(SEARCH_ALL_ID)

  // -- Column mapper --------------------------------------------------------
  const [mapperFileId, setMapperFileId] = useState<string | null>(null)

  // -- Search state ---------------------------------------------------------
  const [results, setResults] = useState<DisplayRow[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [filterQuery, setFilterQuery] = useState('')
  const [searchDirection, setSearchDirection] = useState<'source' | 'target'>(
    session.search_settings.direction,
  )
  const [isSearching, setIsSearching] = useState(false)
  const [searchTime, setSearchTime] = useState<number | null>(null)
  const [, setTotalHits] = useState(0)

  // -- View mode ------------------------------------------------------------
  const [viewMode, setViewMode] = useState<'3col' | 'full'>(session.view_mode)
  const [selectedTarget, setSelectedTarget] = useState(session.selected_target)

  // -- Dark mode ------------------------------------------------------------
  const [darkMode, setDarkMode] = useState(session.dark_mode)

  // -- About modal ----------------------------------------------------------
  const [showAbout, setShowAbout] = useState(false)

  // -- Search panel resize --------------------------------------------------
  const [searchPanelHeight, setSearchPanelHeight] = useState<number | null>(null)
  const searchPanelRef = useRef<HTMLDivElement>(null)

  // -- Worker ---------------------------------------------------------------
  const workerRef = useRef<Worker | null>(null)
  const searchIdRef = useRef(0)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const dirInputRef = useRef<HTMLInputElement>(null)

  // Ref to avoid stale closures in worker onmessage
  const processResultsRef = useRef<(results: SearchResult[], startTime: number) => void>(() => {})

  // -- Derived state --------------------------------------------------------
  const entryCount = useMemo(
    () => Array.from(loadedFiles.values()).reduce((sum, f) => sum + f.data.length, 0),
    [loadedFiles],
  )

  const fileTabInfos = useMemo(
    () => Array.from(loadedFiles.entries()).map(([id, f]) => ({ id, name: f.name })),
    [loadedFiles],
  )

  // Get the active file's source column (normalized, or 'KO')
  const activeSourceColumn = useMemo(() => {
    if (activeTab !== SEARCH_ALL_ID && loadedFiles.has(activeTab)) {
      return normalizeColumnName(loadedFiles.get(activeTab)!.source)
    }
    const first = loadedFiles.values().next()
    if (!first.done) return normalizeColumnName(first.value.source)
    return 'KO'
  }, [loadedFiles, activeTab])

  // Collect all target columns across files, normalized and merged by language code
  const orderedTargets = useMemo(() => {
    const seen = new Map<string, number>() // normalized name → insertion order
    let order = 0
    for (const f of loadedFiles.values()) {
      for (const tgt of f.targets) {
        const norm = normalizeColumnName(tgt)
        if (!seen.has(norm)) seen.set(norm, order++)
      }
    }
    const targets = Array.from(seen.keys())
    targets.sort((a, b) => {
      const ca = classifyColumn(a)
      const cb = classifyColumn(b)
      if (ca !== cb) return ca - cb
      return (seen.get(a) ?? 0) - (seen.get(b) ?? 0)
    })
    return targets
  }, [loadedFiles])

  // All columns for ResultsTable (source + ordered targets)
  const allColumns = useMemo(() => {
    return [activeSourceColumn, ...orderedTargets]
  }, [activeSourceColumn, orderedTargets])

  // -- Session persistence --------------------------------------------------
  useEffect(() => {
    const updated: Session = {
      ...session,
      language: lang,
      view_mode: viewMode,
      selected_target: selectedTarget,
      dark_mode: darkMode,
      search_settings: {
        ...session.search_settings,
        direction: searchDirection,
      },
      file_names: Array.from(loadedFiles.values()).map(f => f.name),
      column_mappings: Object.fromEntries(
        Array.from(loadedFiles.entries()).map(([id, f]) => [
          id,
          { source: f.source, targets: f.targets },
        ]),
      ),
    }
    setSession(updated)
    SessionManager.save(updated)
  }, [lang, viewMode, selectedTarget, searchDirection, darkMode, loadedFiles])

  // -- Worker setup ---------------------------------------------------------
  useEffect(() => {
    try {
      const worker = new Worker(
        new URL('../workers/search.worker.ts', import.meta.url),
        { type: 'module' },
      )
      workerRef.current = worker

      worker.onmessage = (e: MessageEvent) => {
        const data = e.data
        if (data.type === 'result') {
          processResultsRef.current(data.results, data.id)
        } else if (data.type === 'error') {
          setIsSearching(false)
          showToast(data.error)
        }
      }

      return () => worker.terminate()
    } catch {
      // Worker not supported — fallback to main thread
      workerRef.current = null
    }
  }, [])

  // -- Build search entries helper ------------------------------------------
  const buildSearchEntries = useCallback(
    (direction: 'source' | 'target'): { entries: string[]; indexMap: { fileId: string; rowIdx: number }[] } => {
      const entries: string[] = []
      const indexMap: { fileId: string; rowIdx: number }[] = []

      const filesToSearch =
        activeTab === SEARCH_ALL_ID
          ? Array.from(loadedFiles.entries())
          : loadedFiles.has(activeTab)
            ? [[activeTab, loadedFiles.get(activeTab)!] as [string, LoadedFile]]
            : []

      for (const [fileId, file] of filesToSearch) {
        const searchCol =
          direction === 'source'
            ? file.source
            : file.targets[0] ?? file.source

        for (let i = 0; i < file.data.length; i++) {
          entries.push(file.data[i][searchCol] ?? '')
          indexMap.push({ fileId, rowIdx: i })
        }
      }

      return { entries, indexMap }
    },
    [loadedFiles, activeTab],
  )

  // -- Process search results -----------------------------------------------
  const processResults = useCallback(
    (
      searchResults: SearchResult[],
      startTime: number,
      config: SearchConfig,
      direction: 'source' | 'target',
      indexMap: { fileId: string; rowIdx: number }[],
    ) => {
      const elapsed = Date.now() - startTime

      // Map results back to DisplayRows with normalized column keys
      const displayRows: DisplayRow[] = []
      for (const sr of searchResults) {
        const { fileId, rowIdx } = indexMap[sr.index]
        const file = loadedFiles.get(fileId)
        if (!file) continue

        // Normalize column names so "English" and "EN" merge into "EN"
        const normalizedData: Record<string, string> = {}
        for (const col of file.columns) {
          const norm = normalizeColumnName(col)
          normalizedData[norm] = file.data[rowIdx][col] ?? ''
        }

        displayRows.push({
          score: sr.score,
          isDuplicate: false,
          dupLangs: [],
          data: normalizedData,
          fileSource: file.name,
        })
      }

      // Detect duplicates: same source text, different translations
      const sourceCol = (() => {
        const first = loadedFiles.values().next()
        return first.done ? 'KO' : normalizeColumnName(first.value.source)
      })()

      const sourceGroups = new Map<string, DisplayRow[]>()
      for (const row of displayRows) {
        const srcText = row.data[sourceCol] ?? ''
        if (!srcText) continue
        if (!sourceGroups.has(srcText)) sourceGroups.set(srcText, [])
        sourceGroups.get(srcText)!.push(row)
      }

      for (const [, group] of sourceGroups) {
        if (group.length < 2) continue
        // Check if any target column has differing values
        const targetCols = orderedTargets.filter(
          c => classifyColumn(normalizeColumnName(c)) === 0,
        )
        for (const tCol of targetCols) {
          const vals = new Set(group.map(r => (r.data[tCol] ?? '').trim()).filter(Boolean))
          if (vals.size > 1) {
            for (const row of group) {
              row.isDuplicate = true
              if (!row.dupLangs.includes(tCol)) row.dupLangs.push(tCol)
            }
          }
        }
      }

      setResults(displayRows)
      setTotalHits(displayRows.length)
      setSearchTime(elapsed)
      setSearchQuery(config.query)
      setSearchDirection(direction)
      setIsSearching(false)

      showToast(t('search_time', lang, { time: elapsed }))
    },
    [loadedFiles, orderedTargets, lang],
  )

  // -- Search handler -------------------------------------------------------
  const handleSearch = useCallback(
    (config: SearchConfig, direction: 'source' | 'target') => {
      if (loadedFiles.size === 0) return

      setIsSearching(true)
      setSearchTime(null)

      const { entries, indexMap } = buildSearchEntries(direction)
      const startTime = Date.now()
      const currentSearchId = ++searchIdRef.current

      // Update the ref for worker callback
      processResultsRef.current = (workerResults: SearchResult[]) => {
        processResults(workerResults, startTime, config, direction, indexMap)
      }

      // Update session search settings
      setSession(prev => ({
        ...prev,
        search_settings: {
          ...prev.search_settings,
          mode: config.mode,
          direction,
          case_sensitive: config.caseSensitive,
          wildcards: config.wildcards,
          ignore_spaces: config.ignoreSpaces,
          threshold: config.threshold,
          limit: config.limit,
        },
      }))

      if (workerRef.current) {
        workerRef.current.postMessage({
          type: 'search',
          entries,
          config,
          id: currentSearchId,
        })
      } else {
        // Main thread fallback
        try {
          const searchResults = search(entries, config)
          processResults(searchResults, startTime, config, direction, indexMap)
        } catch (err) {
          setIsSearching(false)
          showToast(err instanceof Error ? err.message : String(err))
        }
      }
    },
    [loadedFiles, buildSearchEntries, processResults],
  )

  // -- Filter handler -------------------------------------------------------
  const handleFilterChange = useCallback((filter: string) => {
    setFilterQuery(filter)
  }, [])

  // -- File loading ---------------------------------------------------------
  const handleFilesDropped = useCallback(
    async (files: File[]) => {
      for (const file of files) {
        try {
          const result = await parseFile(file)

          // Check entry limit
          checkEntryLimit(entryCount, result.data.length, file.name)

          // Detect columns
          const detection = detectColumns(result.data, result.columns)

          // Generate unique key
          const fileId = `${file.name}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`

          const loadedFile: LoadedFile = {
            data: result.data,
            columns: result.columns,
            source: detection.source,
            targets: detection.targets,
            name: file.name,
          }

          setLoadedFiles(prev => {
            const next = new Map(prev)
            next.set(fileId, loadedFile)
            return next
          })

          // Toast: file loaded
          showToast(
            t('file_loaded', lang, {
              file: file.name,
              count: result.data.length,
            }),
          )

          // Toast: extra sheets warning
          if (result.extraSheets > 0) {
            showToast(
              t('extra_sheets', lang, {
                file: file.name,
                n: result.extraSheets,
              }),
            )
          }

          // Check for Korean content in source column — open mapper if none
          const hasKorean = result.data
            .slice(0, 10)
            .some(row => HANGUL_RE.test(row[detection.source] ?? ''))

          if (!hasKorean) {
            setMapperFileId(fileId)
          }
        } catch (err) {
          showToast(err instanceof Error ? err.message : String(err))
        }
      }
    },
    [entryCount, lang],
  )

  // -- File close -----------------------------------------------------------
  const handleFileClose = useCallback(
    (fileId: string) => {
      setLoadedFiles(prev => {
        const next = new Map(prev)
        next.delete(fileId)
        return next
      })
      if (activeTab === fileId) setActiveTab(SEARCH_ALL_ID)
      // Clear results if no files remain
      setLoadedFiles(prev => {
        if (prev.size === 0) {
          setResults([])
          setTotalHits(0)
          setSearchQuery('')
          setFilterQuery('')
          setSearchTime(null)
        }
        return prev
      })
    },
    [activeTab],
  )

  // -- Column mapper --------------------------------------------------------
  const handleConfigure = useCallback(() => {
    // Open mapper for active file, or first file
    const targetId =
      activeTab !== SEARCH_ALL_ID && loadedFiles.has(activeTab)
        ? activeTab
        : loadedFiles.keys().next().value ?? null
    if (targetId) setMapperFileId(targetId)
  }, [activeTab, loadedFiles])

  const handleMapperConfirm = useCallback(
    (source: string, targets: string[]) => {
      if (!mapperFileId) return
      setLoadedFiles(prev => {
        const next = new Map(prev)
        const file = next.get(mapperFileId)
        if (file) {
          next.set(mapperFileId, { ...file, source, targets })
        }
        return next
      })
      setMapperFileId(null)
    },
    [mapperFileId],
  )

  const handleMapperCancel = useCallback(() => {
    setMapperFileId(null)
  }, [])

  // -- View mode / target ---------------------------------------------------
  const handleViewModeChange = useCallback((mode: '3col' | 'full') => {
    setViewMode(mode)
  }, [])

  const handleSelectedTargetChange = useCallback((target: string) => {
    setSelectedTarget(target)
  }, [])

  // -- Search panel resize handler ------------------------------------------
  const startResize = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    const startY = e.clientY
    const startH = searchPanelHeight ?? searchPanelRef.current?.offsetHeight ?? 150

    const onMove = (ev: MouseEvent) => {
      const delta = ev.clientY - startY
      setSearchPanelHeight(Math.max(80, Math.min(400, startH + delta)))
    }
    const onUp = () => {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [searchPanelHeight])

  // -- Language toggle ------------------------------------------------------
  const toggleLang = useCallback(() => {
    setLang(prev => (prev === 'en' ? 'ko' : 'en'))
  }, [])

  // -- Keyboard shortcuts ---------------------------------------------------
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'o') {
        e.preventDefault()
        fileInputRef.current?.click()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // -- File input handler ---------------------------------------------------
  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (files && files.length > 0) {
        handleFilesDropped(Array.from(files))
      }
      // Reset input so the same file can be selected again
      e.target.value = ''
    },
    [handleFilesDropped],
  )

  const handleDirInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (files && files.length > 0) {
        const validExts = ['xlsx', 'csv', 'txt']
        const valid = Array.from(files).filter(f => {
          const ext = f.name.split('.').pop()?.toLowerCase() ?? ''
          return validExts.includes(ext)
        })
        if (valid.length > 0) handleFilesDropped(valid)
      }
      e.target.value = ''
    },
    [handleFilesDropped],
  )

  // -- Menu state -----------------------------------------------------------
  const [openMenu, setOpenMenu] = useState<string | null>(null)

  const handleMenuClick = useCallback((menu: string) => {
    setOpenMenu(prev => (prev === menu ? null : menu))
  }, [])

  const closeMenus = useCallback(() => setOpenMenu(null), [])

  // -- Status bar text ------------------------------------------------------
  const statusLeft = useMemo(() => {
    if (isSearching) return t('status_searching', lang)
    if (searchTime !== null) return t('search_time', lang, { time: searchTime })
    return t('drop_hint', lang)
  }, [isSearching, searchTime, lang])

  // -- Column mapper data ---------------------------------------------------
  const mapperFile = mapperFileId ? loadedFiles.get(mapperFileId) : null

  // -- Initial search config from session -----------------------------------
  const initialSearchConfig = useMemo(
    () => ({
      mode: session.search_settings.mode,
      threshold: session.search_settings.threshold,
      limit: session.search_settings.limit,
      caseSensitive: session.search_settings.case_sensitive,
      wildcards: session.search_settings.wildcards,
      ignoreSpaces: session.search_settings.ignore_spaces,
      direction: session.search_settings.direction,
    }),
    [], // Only use initial session values
  )

  // -- Filtered results (apply filterQuery on target columns) ---------------
  const filteredResults = useMemo(() => {
    if (!filterQuery) return results
    const filterLower = filterQuery.toLowerCase()
    return results.filter(row => {
      // Check all target columns for filter match
      for (const col of orderedTargets) {
        const val = (row.data[col] ?? '').toLowerCase()
        if (val.includes(filterLower)) return true
      }
      return false
    })
  }, [results, filterQuery, orderedTargets])

  // -- Render ---------------------------------------------------------------
  const hasFiles = loadedFiles.size > 0

  return (
    <div className={`h-screen flex flex-col select-none ${darkMode ? 'bg-gray-900 text-gray-200' : 'bg-white text-gray-900'}`} onClick={closeMenus}>
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        multiple
        accept=".xlsx,.csv,.txt"
        onChange={handleFileInputChange}
      />
      {/* Hidden directory input */}
      {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
      <input
        ref={dirInputRef}
        type="file"
        className="hidden"
        {...({ webkitdirectory: '' } as any)}
        onChange={handleDirInputChange}
      />

      {/* Menu bar */}
      <div className={`flex items-center border-b text-sm shrink-0 relative ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-gray-50'}`}>
        {/* File menu */}
        <div className="relative">
          <button
            className={`px-3 py-1.5 ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-200'} ${openMenu === 'file' ? (darkMode ? 'bg-gray-700' : 'bg-gray-200') : ''}`}
            onClick={e => { e.stopPropagation(); handleMenuClick('file') }}
          >
            {t('menu_file', lang)}
          </button>
          {openMenu === 'file' && (
            <div className={`absolute left-0 top-full z-50 border rounded shadow-lg py-1 min-w-[180px] ${darkMode ? 'bg-gray-800 border-gray-600' : 'bg-white border-gray-300'}`}>
              <button
                className={`w-full text-left px-3 py-1.5 flex justify-between ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-blue-50'}`}
                onClick={() => {
                  fileInputRef.current?.click()
                  closeMenus()
                }}
              >
                <span>{t('menu_open', lang)}</span>
                <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>Ctrl+O</span>
              </button>
              <button
                className={`w-full text-left px-3 py-1.5 ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-blue-50'}`}
                onClick={() => {
                  dirInputRef.current?.click()
                  closeMenus()
                }}
              >
                {t('menu_open_folder', lang)}
              </button>
            </div>
          )}
        </div>

        {/* Settings menu */}
        <div className="relative">
          <button
            className={`px-3 py-1.5 hover:bg-gray-200 ${darkMode ? 'hover:bg-gray-700' : ''} ${openMenu === 'settings' ? (darkMode ? 'bg-gray-700' : 'bg-gray-200') : ''}`}
            onClick={e => { e.stopPropagation(); handleMenuClick('settings') }}
          >
            {t('menu_settings', lang)}
          </button>
          {openMenu === 'settings' && (
            <div className={`absolute left-0 top-full z-50 border rounded shadow-lg py-1 min-w-[220px] ${darkMode ? 'bg-gray-800 border-gray-600' : 'bg-white border-gray-300'}`}>
              <button
                className={`w-full text-left px-3 py-1.5 ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-blue-50'}`}
                onClick={() => {
                  toggleLang()
                  closeMenus()
                }}
              >
                {t('menu_lang_toggle', lang)}
              </button>
              <label
                className={`flex items-center gap-2 w-full px-3 py-1.5 cursor-pointer ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-blue-50'}`}
                onClick={e => e.stopPropagation()}
              >
                <input
                  type="checkbox"
                  checked={darkMode}
                  onChange={e => setDarkMode(e.target.checked)}
                  className="accent-blue-600"
                />
                {t('menu_dark_mode', lang)}
              </label>
              <div className={`my-1 border-t ${darkMode ? 'border-gray-600' : 'border-gray-200'}`} />
              <button
                className={`w-full text-left px-3 py-1.5 ${darkMode ? 'hover:bg-gray-700' : 'hover:bg-blue-50'}`}
                onClick={() => {
                  setShowAbout(true)
                  closeMenus()
                }}
              >
                {t('menu_about', lang)}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Main content */}
      {!hasFiles ? (
        <DropZone onFilesDropped={handleFilesDropped} lang={lang} hasFiles={false} darkMode={darkMode} />
      ) : (
        <>
          {/* File tabs */}
          <FileTabs
            files={fileTabInfos}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            onFileClose={handleFileClose}
            onConfigure={handleConfigure}
            lang={lang}
            darkMode={darkMode}
          />

          {/* Search panel */}
          <div
            ref={searchPanelRef}
            style={searchPanelHeight ? { height: searchPanelHeight, overflow: 'hidden' } : undefined}
            className="shrink-0"
          >
            <SearchPanel
              onSearch={handleSearch}
              onFilterChange={handleFilterChange}
              totalHits={filteredResults.length}
              lang={lang}
              initialConfig={initialSearchConfig}
              darkMode={darkMode}
            />
          </div>

          {/* Resize divider */}
          <div
            className={`h-1 hover:bg-blue-400 cursor-row-resize shrink-0 ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}
            onMouseDown={startResize}
          />

          {/* Results table */}
          <ResultsTable
            results={filteredResults}
            columns={allColumns}
            searchQuery={searchQuery}
            filterQuery={filterQuery}
            searchDirection={searchDirection}
            sourceColumn={activeSourceColumn}
            targetLanguages={orderedTargets}
            viewMode={viewMode}
            selectedTarget={selectedTarget}
            onViewModeChange={handleViewModeChange}
            onSelectedTargetChange={handleSelectedTargetChange}
            lang={lang}
            darkMode={darkMode}
          />

          {/* DropZone overlay (for drag-and-drop when files are loaded) */}
          <DropZone onFilesDropped={handleFilesDropped} lang={lang} hasFiles={true} darkMode={darkMode} />
        </>
      )}

      {/* Status bar */}
      <div className={`flex items-center justify-between border-t px-3 py-1 text-xs shrink-0 ${darkMode ? 'bg-gray-800 border-gray-700 text-gray-400' : 'bg-gray-50 text-gray-500'}`}>
        <span className="font-mono whitespace-pre">{statusLeft}</span>
        <span>
          {searchTime !== null && t('search_time', lang, { time: searchTime })}
        </span>
      </div>

      {/* Toast container */}
      <ToastContainer />

      {/* Column mapper modal */}
      {mapperFile && mapperFileId && (
        <ColumnMapper
          columns={mapperFile.columns}
          currentSource={mapperFile.source}
          currentTargets={mapperFile.targets}
          previewData={mapperFile.data.slice(0, 5)}
          onConfirm={handleMapperConfirm}
          onCancel={handleMapperCancel}
          lang={lang}
          darkMode={darkMode}
        />
      )}

      {/* About modal */}
      {showAbout && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setShowAbout(false)}
        >
          <div
            className={`rounded-lg shadow-xl p-6 max-w-sm mx-4 ${darkMode ? 'bg-gray-800 text-gray-200' : 'bg-white'}`}
            onClick={e => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold mb-2">{t('about_title', lang)}</h2>
            <p className={`text-sm mb-4 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              {t('about_text', lang, { version: APP_VERSION })}
            </p>
            <div className="text-right">
              <button
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700"
                onClick={() => setShowAbout(false)}
              >
                {t('btn_ok', lang)}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
