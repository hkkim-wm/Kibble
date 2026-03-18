import { useState, useEffect } from 'react'
import { t, type Language } from '../i18n/translations'

interface ColumnMapperProps {
  columns: string[]
  currentSource: string
  currentTargets: string[]
  previewData: Record<string, string>[] // first 5 rows
  onConfirm: (source: string, targets: string[]) => void
  onCancel: () => void
  lang: Language
  darkMode?: boolean
}

export default function ColumnMapper({
  columns,
  currentSource,
  currentTargets,
  previewData,
  onConfirm,
  onCancel,
  lang,
  darkMode = false,
}: ColumnMapperProps) {
  const [source, setSource] = useState(currentSource)
  const [targets, setTargets] = useState<string[]>(currentTargets)

  // When source changes, remove it from targets
  useEffect(() => {
    setTargets(prev => prev.filter(col => col !== source))
  }, [source])

  function handleTargetToggle(col: string) {
    setTargets(prev =>
      prev.includes(col) ? prev.filter(c => c !== col) : [...prev, col],
    )
  }

  function handleConfirm() {
    onConfirm(source, targets)
  }

  // Close on backdrop click
  function handleBackdropClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onCancel()
  }

  // Close on Escape
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onCancel])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={handleBackdropClick}
    >
      <div className={`rounded-lg shadow-xl w-full max-w-[600px] max-h-[80vh] flex flex-col mx-4 ${darkMode ? 'bg-gray-800 text-gray-200' : 'bg-white'}`}>
        {/* Title */}
        <div className={`px-6 py-4 border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <h2 className={`text-lg font-semibold ${darkMode ? 'text-gray-100' : 'text-gray-900'}`}>
            {t('column_settings', lang)}
          </h2>
        </div>

        {/* Body – scrollable */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-5">
          {/* Source column */}
          <div>
            <label className={`block text-sm font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {t('source_column', lang)}
            </label>
            <select
              className={`w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${darkMode ? 'border-gray-600 bg-gray-700 text-gray-200' : 'border-gray-300'}`}
              value={source}
              onChange={e => setSource(e.target.value)}
            >
              {columns.map(col => (
                <option key={col} value={col}>
                  {col}
                </option>
              ))}
            </select>
          </div>

          {/* Target columns */}
          <div>
            <label className={`block text-sm font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {t('target_columns', lang)}
            </label>
            <div className="space-y-1">
              {columns.map(col => {
                const isSource = col === source
                return (
                  <label
                    key={col}
                    className={`flex items-center gap-2 text-sm ${
                      isSource
                        ? darkMode ? 'text-gray-600' : 'text-gray-400'
                        : darkMode ? 'text-gray-300' : 'text-gray-700'
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="rounded border-gray-300"
                      checked={!isSource && targets.includes(col)}
                      disabled={isSource}
                      onChange={() => handleTargetToggle(col)}
                    />
                    {col}
                  </label>
                )
              })}
            </div>
          </div>

          {/* Preview table */}
          {previewData.length > 0 && (
            <div>
              <label className={`block text-sm font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                {t('preview', lang)}
              </label>
              <div className={`overflow-x-auto border rounded ${darkMode ? 'border-gray-600' : 'border-gray-200'}`}>
                <table className="min-w-full text-xs">
                  <thead>
                    <tr className={darkMode ? 'bg-gray-700' : 'bg-gray-50'}>
                      {columns.map(col => (
                        <th
                          key={col}
                          className={`px-3 py-2 text-left font-medium whitespace-nowrap ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewData.map((row, i) => (
                      <tr
                        key={i}
                        className={i % 2 === 0 ? (darkMode ? 'bg-gray-800' : 'bg-white') : (darkMode ? 'bg-gray-700' : 'bg-gray-50')}
                      >
                        {columns.map(col => (
                          <td
                            key={col}
                            className={`px-3 py-1.5 whitespace-nowrap max-w-[200px] truncate ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}
                          >
                            {row[col] ?? ''}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Footer buttons */}
        <div className={`px-6 py-3 border-t flex justify-end gap-3 ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <button
            type="button"
            className={`px-4 py-2 text-sm font-medium border rounded ${darkMode ? 'text-gray-300 bg-gray-700 border-gray-600 hover:bg-gray-600' : 'text-gray-700 bg-white border-gray-300 hover:bg-gray-50'}`}
            onClick={onCancel}
          >
            {t('btn_cancel', lang)}
          </button>
          <button
            type="button"
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600
                       rounded hover:bg-blue-700"
            onClick={handleConfirm}
          >
            {t('btn_ok', lang)}
          </button>
        </div>
      </div>
    </div>
  )
}
