import { useCallback, useEffect, useRef, useState } from 'react'
import type { SearchConfig } from '../core/search'
import { t, type Language } from '../i18n/translations'

export interface SearchPanelProps {
  onSearch: (config: SearchConfig, direction: 'source' | 'target') => void
  onFilterChange: (filter: string) => void
  totalHits: number
  lang: Language
  initialConfig?: Partial<SearchConfig & { direction: string }>
  darkMode?: boolean
}

const DEFAULT_CONFIG: SearchConfig = {
  query: '',
  mode: 'both',
  threshold: 60,
  limit: 200,
  caseSensitive: false,
  wildcards: false,
  ignoreSpaces: false,
  wholeWord: false,
}

export default function SearchPanel({
  onSearch,
  onFilterChange,
  totalHits,
  lang,
  initialConfig,
  darkMode = false,
}: SearchPanelProps) {
  const [query, setQuery] = useState(initialConfig?.query ?? DEFAULT_CONFIG.query)
  const [filter, setFilter] = useState('')
  const [direction, setDirection] = useState<'source' | 'target'>(
    (initialConfig?.direction as 'source' | 'target') ?? 'source',
  )
  const [mode, setMode] = useState<SearchConfig['mode']>(
    initialConfig?.mode ?? DEFAULT_CONFIG.mode,
  )
  const [caseSensitive, setCaseSensitive] = useState(
    initialConfig?.caseSensitive ?? DEFAULT_CONFIG.caseSensitive,
  )
  const [wildcards, setWildcards] = useState(
    initialConfig?.wildcards ?? DEFAULT_CONFIG.wildcards,
  )
  const [ignoreSpaces, setIgnoreSpaces] = useState(
    initialConfig?.ignoreSpaces ?? DEFAULT_CONFIG.ignoreSpaces,
  )
  const [wholeWord, setWholeWord] = useState(
    initialConfig?.wholeWord ?? DEFAULT_CONFIG.wholeWord,
  )
  const [threshold, setThreshold] = useState(
    initialConfig?.threshold ?? DEFAULT_CONFIG.threshold,
  )
  const [limit, setLimit] = useState(
    initialConfig?.limit ?? DEFAULT_CONFIG.limit,
  )

  const searchInputRef = useRef<HTMLInputElement>(null)

  const triggerSearch = useCallback(() => {
    if (!query.trim()) return
    const config: SearchConfig = {
      query: query.trim(),
      mode,
      threshold,
      limit,
      caseSensitive,
      wildcards,
      ignoreSpaces,
      wholeWord,
    }
    onSearch(config, direction)
  }, [query, mode, threshold, limit, caseSensitive, wildcards, ignoreSpaces, wholeWord, direction, onSearch])

  // Ctrl+F focuses search input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'f') {
        e.preventDefault()
        searchInputRef.current?.focus()
        searchInputRef.current?.select()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      triggerSearch()
    } else if (e.key === 'Escape') {
      setQuery('')
      setFilter('')
      onFilterChange('')
    }
  }

  const handleFilterKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      onFilterChange(filter)
    } else if (e.key === 'Escape') {
      setFilter('')
      onFilterChange('')
    }
  }

  const handleLimitChange = (value: string) => {
    const n = parseInt(value, 10)
    if (!isNaN(n)) {
      setLimit(Math.max(10, Math.min(1000, n)))
    }
  }

  const labelClass = `text-xs select-none ${darkMode ? 'text-gray-400' : 'text-gray-500'}`
  const inputClass = darkMode
    ? 'border border-gray-600 bg-gray-800 text-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400'
    : 'border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400'
  const checkboxLabelClass = `flex items-center gap-1 text-xs select-none cursor-pointer ${darkMode ? 'text-gray-300' : 'text-gray-700'}`

  return (
    <div className={`flex flex-col gap-2 px-3 py-2 border-b ${darkMode ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'}`}>
      {/* Row 1: Search input + button */}
      <div className="flex items-center gap-2">
        <input
          ref={searchInputRef}
          type="text"
          className={`${inputClass} flex-1`}
          placeholder={t('search_for', lang)}
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleSearchKeyDown}
        />
        <button
          type="button"
          className="px-3 py-1 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400 whitespace-nowrap"
          onClick={triggerSearch}
        >
          {t('btn_search', lang)}
        </button>
      </div>

      {/* Row 2: Translation filter */}
      <input
        type="text"
        className={`${inputClass} w-full`}
        placeholder={t('filter_placeholder', lang)}
        value={filter}
        onChange={e => setFilter(e.target.value)}
        onKeyDown={handleFilterKeyDown}
      />

      {/* Row 3: Options */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        {/* Direction radios */}
        <fieldset className="flex items-center gap-2">
          <label className={checkboxLabelClass}>
            <input
              type="radio"
              name="direction"
              className="accent-blue-600"
              checked={direction === 'source'}
              onChange={() => setDirection('source')}
            />
            {t('search_in_source', lang)}
          </label>
          <label className={checkboxLabelClass}>
            <input
              type="radio"
              name="direction"
              className="accent-blue-600"
              checked={direction === 'target'}
              onChange={() => setDirection('target')}
            />
            {t('search_in_target', lang)}
          </label>
        </fieldset>

        {/* Separator */}
        <div className={`w-px h-4 ${darkMode ? 'bg-gray-600' : 'bg-gray-300'}`} />

        {/* Mode dropdown */}
        <label className="flex items-center gap-1">
          <span className={labelClass}>{t('match_mode', lang)}</span>
          <select
            className={`${inputClass} py-0.5`}
            value={mode}
            onChange={e => setMode(e.target.value as SearchConfig['mode'])}
          >
            <option value="both">{t('mode_both', lang)}</option>
            <option value="substring">{t('mode_substring', lang)}</option>
            <option value="fuzzy">{t('mode_fuzzy', lang)}</option>
          </select>
        </label>

        {/* Separator */}
        <div className={`w-px h-4 ${darkMode ? 'bg-gray-600' : 'bg-gray-300'}`} />

        {/* Checkboxes */}
        <label className={checkboxLabelClass}>
          <input
            type="checkbox"
            className="accent-blue-600"
            checked={caseSensitive}
            onChange={e => setCaseSensitive(e.target.checked)}
          />
          {t('case_sensitive', lang)}
        </label>
        <label className={checkboxLabelClass}>
          <input
            type="checkbox"
            className="accent-blue-600"
            checked={wildcards}
            onChange={e => setWildcards(e.target.checked)}
          />
          {t('add_wildcards', lang)}
        </label>
        <label className={checkboxLabelClass}>
          <input
            type="checkbox"
            className="accent-blue-600"
            checked={ignoreSpaces}
            onChange={e => setIgnoreSpaces(e.target.checked)}
          />
          {t('ignore_spaces', lang)}
        </label>
        <label className={checkboxLabelClass}>
          <input
            type="checkbox"
            className="accent-blue-600"
            checked={wholeWord}
            onChange={e => setWholeWord(e.target.checked)}
          />
          {t('whole_word', lang)}
        </label>

        {/* Separator */}
        <div className={`w-px h-4 ${darkMode ? 'bg-gray-600' : 'bg-gray-300'}`} />

        {/* Threshold slider */}
        <label className="flex items-center gap-1">
          <span className={labelClass}>{t('min_threshold', lang)}</span>
          <input
            type="range"
            className="w-20 h-4 accent-blue-600"
            min={0}
            max={100}
            value={threshold}
            onChange={e => setThreshold(Number(e.target.value))}
          />
          <span className={`text-xs w-7 text-right tabular-nums ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>{threshold}</span>
        </label>

        {/* Max results input */}
        <label className="flex items-center gap-1">
          <span className={labelClass}>{t('max_results', lang)}</span>
          <input
            type="number"
            className={`${inputClass} w-16 py-0.5 text-right tabular-nums`}
            min={10}
            max={1000}
            value={limit}
            onChange={e => handleLimitChange(e.target.value)}
          />
        </label>

        {/* Separator */}
        <div className={`w-px h-4 ${darkMode ? 'bg-gray-600' : 'bg-gray-300'}`} />

        {/* Total hits */}
        <span className={`text-xs tabular-nums ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          {t('total_hits', lang)}: <span className={`font-medium ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>{totalHits}</span>
        </span>
      </div>
    </div>
  )
}
