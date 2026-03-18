import { useEffect, useRef, useState } from 'react'
import { t, type Language } from '../i18n/translations'

interface DropZoneProps {
  onFilesDropped: (files: File[]) => void
  lang: Language
  hasFiles: boolean
  darkMode?: boolean
}

const VALID_EXTENSIONS = ['xlsx', 'csv', 'txt']

function filterValidFiles(files: FileList | null): File[] {
  if (!files) return []
  return Array.from(files).filter(f => {
    const ext = f.name.split('.').pop()?.toLowerCase() ?? ''
    return VALID_EXTENSIONS.includes(ext)
  })
}

export default function DropZone({ onFilesDropped, lang, hasFiles, darkMode = false }: DropZoneProps) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const dirInputRef = useRef<HTMLInputElement>(null)
  const dragCounter = useRef(0)

  // Window-level drag listeners when files are already loaded
  useEffect(() => {
    if (!hasFiles) return

    const handleDragEnter = (e: DragEvent) => {
      e.preventDefault()
      dragCounter.current++
      if (dragCounter.current === 1) setDragging(true)
    }
    const handleDragLeave = (e: DragEvent) => {
      e.preventDefault()
      dragCounter.current--
      if (dragCounter.current === 0) setDragging(false)
    }
    const handleDragOver = (e: DragEvent) => {
      e.preventDefault()
    }
    const handleDrop = (e: DragEvent) => {
      e.preventDefault()
      dragCounter.current = 0
      setDragging(false)
      const valid = filterValidFiles(e.dataTransfer?.files ?? null)
      if (valid.length > 0) onFilesDropped(valid)
    }

    window.addEventListener('dragenter', handleDragEnter)
    window.addEventListener('dragleave', handleDragLeave)
    window.addEventListener('dragover', handleDragOver)
    window.addEventListener('drop', handleDrop)
    return () => {
      window.removeEventListener('dragenter', handleDragEnter)
      window.removeEventListener('dragleave', handleDragLeave)
      window.removeEventListener('dragover', handleDragOver)
      window.removeEventListener('drop', handleDrop)
    }
  }, [hasFiles, onFilesDropped])

  // Full-area drop zone (no files loaded yet)
  if (!hasFiles) {
    return (
      <div
        className={`flex-1 flex flex-col items-center justify-center border-2 border-dashed rounded-xl m-4 cursor-pointer transition-colors ${
          dragging
            ? darkMode ? 'border-blue-400 bg-blue-950' : 'border-blue-500 bg-blue-50'
            : darkMode ? 'border-gray-600 bg-gray-800' : 'border-gray-300 bg-gray-50'
        }`}
        onDragEnter={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={e => { e.preventDefault(); setDragging(false) }}
        onDragOver={e => e.preventDefault()}
        onDrop={e => {
          e.preventDefault()
          setDragging(false)
          const valid = filterValidFiles(e.dataTransfer.files)
          if (valid.length > 0) onFilesDropped(valid)
        }}
        onClick={() => inputRef.current?.click()}
      >
        <p className={`text-lg font-medium ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>{t('drop_files', lang)}</p>
        <p className={`text-sm mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>{t('drop_hint', lang)}</p>
        <div className="flex gap-3 mt-3">
          <button
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700"
            onClick={e => { e.stopPropagation(); inputRef.current?.click() }}
          >
            {t('menu_open', lang)}
          </button>
          <button
            className="px-4 py-2 text-sm font-medium text-blue-600 bg-white border border-blue-600 rounded hover:bg-blue-50"
            onClick={e => { e.stopPropagation(); dirInputRef.current?.click() }}
          >
            {t('menu_open_folder', lang)}
          </button>
        </div>
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          multiple
          accept=".xlsx,.csv,.txt"
          onChange={e => {
            const valid = filterValidFiles(e.target.files)
            if (valid.length > 0) onFilesDropped(valid)
          }}
        />
        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
        <input
          ref={dirInputRef}
          type="file"
          className="hidden"
          {...({ webkitdirectory: '' } as any)}
          onChange={e => {
            const valid = filterValidFiles(e.target.files)
            if (valid.length > 0) onFilesDropped(valid)
            e.target.value = ''
          }}
        />
      </div>
    )
  }

  // Overlay shown when dragging over window with files already loaded
  if (!dragging) return null
  return (
    <div className="fixed inset-0 z-40 bg-blue-500/20 flex items-center justify-center pointer-events-none">
      <div className="bg-white px-8 py-6 rounded-xl shadow-2xl border-2 border-blue-500 text-blue-700 text-lg font-medium">
        {t('drop_files', lang)}
      </div>
    </div>
  )
}
