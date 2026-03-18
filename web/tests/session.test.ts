import { describe, it, expect, beforeEach } from 'vitest'
import { DEFAULT_SESSION, SessionManager, type Session } from '../src/core/session'

const STORAGE_KEY = 'kibble_session'

beforeEach(() => {
  localStorage.clear()
})

describe('SessionManager.load', () => {
  it('returns defaults when no session is stored', () => {
    const session = SessionManager.load()
    expect(session).toEqual(DEFAULT_SESSION)
  })

  it('returns defaults when stored value is invalid JSON', () => {
    localStorage.setItem(STORAGE_KEY, '{bad json')
    const session = SessionManager.load()
    expect(session).toEqual(DEFAULT_SESSION)
  })
})

describe('SessionManager.save / load round-trip', () => {
  it('saves and loads a full session', () => {
    const custom: Session = {
      ...DEFAULT_SESSION,
      file_names: ['test.csv'],
      view_mode: 'full',
      language: 'en',
    }
    SessionManager.save(custom)
    const loaded = SessionManager.load()
    expect(loaded).toEqual(custom)
  })
})

describe('deep merge with defaults', () => {
  it('fills missing top-level keys from defaults', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ file_names: ['a.csv'] }))
    const session = SessionManager.load()
    expect(session.file_names).toEqual(['a.csv'])
    expect(session.search_settings).toEqual(DEFAULT_SESSION.search_settings)
    expect(session.view_mode).toBe('3col')
    expect(session.language).toBe('ko')
  })

  it('deep-merges nested search_settings', () => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        search_settings: { mode: 'fuzzy', threshold: 80 },
      }),
    )
    const session = SessionManager.load()
    expect(session.search_settings.mode).toBe('fuzzy')
    expect(session.search_settings.threshold).toBe(80)
    // defaults preserved for missing nested keys
    expect(session.search_settings.direction).toBe('source')
    expect(session.search_settings.case_sensitive).toBe(false)
    expect(session.search_settings.limit).toBe(200)
  })

  it('deep-merges column_mappings', () => {
    const partial = {
      column_mappings: {
        'file.csv': { source: 'KO', targets: ['EN'] },
      },
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(partial))
    const session = SessionManager.load()
    expect(session.column_mappings).toEqual(partial.column_mappings)
    // other defaults intact
    expect(session.file_names).toEqual([])
  })
})
