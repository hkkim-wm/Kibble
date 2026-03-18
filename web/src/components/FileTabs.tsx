import { t, type Language } from '../i18n/translations'

interface FileTabInfo {
  name: string
  id: string
}

interface FileTabsProps {
  files: FileTabInfo[]
  activeTab: string
  onTabChange: (tabId: string) => void
  onFileClose: (fileId: string) => void
  onConfigure: () => void
  lang: Language
  darkMode?: boolean
}

const SEARCH_ALL_ID = '__search_all__'

export { SEARCH_ALL_ID }

export default function FileTabs({
  files,
  activeTab,
  onTabChange,
  onFileClose,
  onConfigure,
  lang,
  darkMode = false,
}: FileTabsProps) {
  return (
    <div className={`flex items-center border-b overflow-x-auto ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-gray-50'}`}>
      {/* Search All tab (pinned) */}
      <button
        className={`shrink-0 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
          activeTab === SEARCH_ALL_ID
            ? darkMode ? 'border-blue-400 bg-gray-900 text-blue-400' : 'border-blue-500 bg-white text-blue-700'
            : darkMode ? 'border-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-700' : 'border-transparent text-gray-600 hover:text-gray-800 hover:bg-gray-100'
        }`}
        onClick={() => onTabChange(SEARCH_ALL_ID)}
      >
        {t('search_all', lang)}
      </button>

      {/* Per-file tabs */}
      {files.map(file => (
        <div
          key={file.id}
          className={`shrink-0 flex items-center border-b-2 transition-colors ${
            activeTab === file.id
              ? darkMode ? 'border-blue-400 bg-gray-900' : 'border-blue-500 bg-white'
              : darkMode ? 'border-transparent hover:bg-gray-700' : 'border-transparent hover:bg-gray-100'
          }`}
        >
          <button
            className={`px-3 py-2 text-sm ${
              activeTab === file.id
                ? darkMode ? 'text-blue-400 font-medium' : 'text-blue-700 font-medium'
                : darkMode ? 'text-gray-400' : 'text-gray-600'
            }`}
            onClick={() => onTabChange(file.id)}
          >
            {file.name}
          </button>
          <button
            className="px-1.5 py-1 text-gray-400 hover:text-red-500 text-xs"
            onClick={e => { e.stopPropagation(); onFileClose(file.id) }}
            title="Close"
          >
            ✕
          </button>
        </div>
      ))}

      {/* Gear button */}
      <button
        className={`shrink-0 ml-auto px-3 py-2 text-base ${darkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'}`}
        onClick={onConfigure}
        title={t('column_settings', lang)}
      >
        ⚙
      </button>
    </div>
  )
}
