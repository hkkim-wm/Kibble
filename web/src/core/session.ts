export interface Session {
  file_names: string[]
  column_mappings: Record<string, { source: string; targets: string[] }>
  search_settings: {
    mode: 'substring' | 'fuzzy' | 'both'
    direction: 'source' | 'target'
    case_sensitive: boolean
    wildcards: boolean
    ignore_spaces: boolean
    whole_word: boolean
    threshold: number // 0-100
    limit: number // max results
  }
  view_mode: '3col' | 'full'
  selected_target: string // language code for 3-col mode
  language: 'en' | 'ko'
  dark_mode: boolean
}

export const DEFAULT_SESSION: Session = {
  file_names: [],
  column_mappings: {},
  search_settings: {
    mode: 'both',
    direction: 'source',
    case_sensitive: false,
    wildcards: false,
    ignore_spaces: false,
    whole_word: false,
    threshold: 50,
    limit: 200,
  },
  view_mode: '3col',
  selected_target: 'EN',
  language: 'ko',
  dark_mode: false,
}

const STORAGE_KEY = 'kibble_session'

function deepMerge(defaults: Record<string, unknown>, partial: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, unknown> = { ...defaults }
  for (const key of Object.keys(partial)) {
    const defaultVal = defaults[key]
    const partialVal = partial[key]
    if (
      defaultVal !== null &&
      partialVal !== null &&
      typeof defaultVal === 'object' &&
      typeof partialVal === 'object' &&
      !Array.isArray(defaultVal) &&
      !Array.isArray(partialVal)
    ) {
      result[key] = deepMerge(
        defaultVal as Record<string, unknown>,
        partialVal as Record<string, unknown>,
      )
    } else {
      result[key] = partialVal
    }
  }
  return result
}

export const SessionManager = {
  load(): Session {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw === null) return { ...DEFAULT_SESSION, search_settings: { ...DEFAULT_SESSION.search_settings } }
      const data = JSON.parse(raw)
      return deepMerge(
        DEFAULT_SESSION as unknown as Record<string, unknown>,
        data as Record<string, unknown>,
      ) as unknown as Session
    } catch {
      return { ...DEFAULT_SESSION, search_settings: { ...DEFAULT_SESSION.search_settings } }
    }
  },

  save(session: Session): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  },
}
