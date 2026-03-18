// ---------------------------------------------------------------------------
// Kibble Web – i18n translations (EN / KO)
// ---------------------------------------------------------------------------

export type Language = 'en' | 'ko';

/** All translation keys available in the app. */
export type TranslationKey = keyof typeof TRANSLATIONS['en'];

// ---------------------------------------------------------------------------
// Translation strings
// ---------------------------------------------------------------------------

export const TRANSLATIONS = {
  en: {
    // -- Search panel -------------------------------------------------------
    search_for: 'Search for',
    btn_search: 'Search',
    case_sensitive: 'Case sensitive',
    add_wildcards: 'Add wildcards',
    ignore_spaces: 'Ignore spaces',
    whole_word: 'Whole word',
    search_in_source: 'Search in source',
    search_in_target: 'Search in target',
    match_mode: 'Match',
    mode_both: 'Both',
    mode_substring: 'Substring',
    mode_fuzzy: 'Fuzzy',
    min_threshold: 'Threshold',
    max_results: 'Limit',
    filter_placeholder: 'Filter results…',
    total_hits: 'Total hits',

    // -- File tabs ----------------------------------------------------------
    search_all: 'Search All',

    // -- Results table ------------------------------------------------------
    col_match: 'Match %',
    col_file: 'File',
    view_3col: 'Three-column view',
    view_full: 'Source + target',
    word_wrap: 'Word wrap',
    no_results: 'No results',

    // -- Context menu -------------------------------------------------------
    copy_row: 'Copy row',
    copy_cell: 'Copy cell',
    copy_source: 'Copy source only',
    copy_target: 'Copy target only',

    // -- Drop zone ----------------------------------------------------------
    drop_files: 'Drop files here',
    drop_hint: 'Drop files here or Ctrl+O to browse',

    // -- Column mapper ------------------------------------------------------
    column_settings: 'Configure Columns',
    source_column: 'Source column',
    target_columns: 'Target columns',
    preview: 'Preview',
    btn_ok: 'OK',
    btn_cancel: 'Cancel',

    // -- Toasts & errors ----------------------------------------------------
    file_loaded: '{file} loaded ({count} entries)',
    extra_sheets: '{file} has {n} additional sheets (only first sheet loaded)',
    limit_exceeded:
      'Cannot load {file}: total entries would exceed 500K limit ({current} + {new} = {sum})',
    no_entries: 'No entries found in {file}',
    unsupported_format: 'Unsupported format. Use .xlsx, .csv, or .txt',
    search_time: 'Search completed in {time}ms',
    session_restore_hint: 'Restore last session?',

    // -- Menu ---------------------------------------------------------------
    menu_file: 'File',
    menu_open: 'Open Files…',
    menu_settings: 'Settings',
    menu_lang_toggle: 'Language: English / 한국어',
    menu_dark_mode: 'Dark Mode',
    menu_help: 'Help',
    menu_about: 'About Kibble',

    // -- About --------------------------------------------------------------
    about_title: 'About Kibble',
    about_text:
      'Kibble v{version} — Fast terminology search for Translation Memories and Terminology Bases.',

    // -- Status bar ---------------------------------------------------------
    status_ready: 'Ready',
    status_searching: 'Searching…',
    status_files: '{count} file(s) loaded',

    // -- Extra keys from desktop (kept for parity) --------------------------
    filter_target: 'Filter target',
    filter_source: 'Filter source',
    copy_success: 'Copied to clipboard',
    file_not_found: '{file} not found, skipping',
    loading: 'Loading…',
    btn_yes: 'Yes',
    btn_no: 'No',
    could_not_read: 'Could not read {file}',
    source_col: 'Source (KO)',
    meta_info: 'Meta-info',
    dup_translation: '⚠ Different translations found for same source',
    menu_exit: 'Exit',
    menu_open_folder: 'Open Folder...',
    global_hotkey: 'Ctrl+C → Ctrl+Shift+K',
    font_size: 'Font size',
  },

  ko: {
    // -- Search panel -------------------------------------------------------
    search_for: '검색어',
    btn_search: '검색',
    case_sensitive: '대소문자 구분',
    add_wildcards: '와일드카드 추가',
    ignore_spaces: '공백 무시',
    whole_word: '단어 단위',
    search_in_source: '원문에서 검색',
    search_in_target: '번역문에서 검색',
    match_mode: '일치 방식',
    mode_both: '모두',
    mode_substring: '부분 일치',
    mode_fuzzy: '유사 일치',
    min_threshold: '최소 일치율',
    max_results: '최대 결과',
    filter_placeholder: '결과 필터…',
    total_hits: '총 검색 결과',

    // -- File tabs ----------------------------------------------------------
    search_all: '전체 검색',

    // -- Results table ------------------------------------------------------
    col_match: '일치율',
    col_file: '파일',
    view_3col: '3열 보기',
    view_full: '원문 + 번역문',
    word_wrap: '줄 바꿈',
    no_results: '결과 없음',

    // -- Context menu -------------------------------------------------------
    copy_row: '행 복사',
    copy_cell: '셀 복사',
    copy_source: '원문만 복사',
    copy_target: '번역문만 복사',

    // -- Drop zone ----------------------------------------------------------
    drop_files: '파일을 끌어놓으세요',
    drop_hint: '파일을 끌어놓거나 Ctrl+O로 찾아보기',

    // -- Column mapper ------------------------------------------------------
    column_settings: '열 설정',
    source_column: '원문 열',
    target_columns: '번역문 열',
    preview: '미리 보기',
    btn_ok: '확인',
    btn_cancel: '취소',

    // -- Toasts & errors ----------------------------------------------------
    file_loaded: '{file} 로드 완료 ({count}건)',
    extra_sheets: '{file}에 {n}개의 추가 시트가 있습니다 (첫 번째 시트만 로드됨)',
    limit_exceeded:
      '{file} 로드 불가: 총 항목이 50만 제한을 초과합니다 ({current} + {new} = {sum})',
    no_entries: '{file}에서 항목을 찾을 수 없습니다',
    unsupported_format: '지원하지 않는 형식입니다. xlsx, csv, txt 파일을 사용하세요',
    search_time: '검색 완료: {time}ms',
    session_restore_hint: '이전 세션을 복원하시겠습니까?',

    // -- Menu ---------------------------------------------------------------
    menu_file: '파일',
    menu_open: '파일 열기…',
    menu_settings: '설정',
    menu_lang_toggle: '언어: English / 한국어',
    menu_dark_mode: '다크 모드',
    menu_help: '도움말',
    menu_about: 'Kibble 정보',

    // -- About --------------------------------------------------------------
    about_title: 'Kibble 정보',
    about_text:
      'Kibble v{version} — 번역 메모리(TM) 및 용어집(TB)을 위한 빠른 용어 검색 도구입니다.',

    // -- Status bar ---------------------------------------------------------
    status_ready: '준비',
    status_searching: '검색 중…',
    status_files: '{count}개 파일 로드됨',

    // -- Extra keys from desktop (kept for parity) --------------------------
    filter_target: '번역문 필터',
    filter_source: '원문 필터',
    copy_success: '클립보드에 복사됨',
    file_not_found: '{file}을(를) 찾을 수 없어 건너뜁니다',
    loading: '불러오는 중…',
    btn_yes: '예',
    btn_no: '아니오',
    could_not_read: '{file}을(를) 읽을 수 없습니다',
    source_col: '원문 (KO)',
    meta_info: '메타 정보',
    dup_translation: '⚠ 동일 원문에 다른 번역이 존재합니다',
    menu_exit: '종료',
    menu_open_folder: '폴더 열기...',
    global_hotkey: 'Ctrl+C → Ctrl+Shift+K',
    font_size: '글꼴 크기',
  },
} as const;

// ---------------------------------------------------------------------------
// t() helper
// ---------------------------------------------------------------------------

/**
 * Look up a translation string by key and language.
 *
 * - Interpolates `{placeholder}` tokens when `params` is supplied.
 * - Falls back to Korean (`ko`) if the key is missing in the requested language.
 * - Falls back to the raw key string if not found in either language.
 */
export function t(
  key: string,
  lang: Language,
  params?: Record<string, string | number>,
): string {
  const dict = (TRANSLATIONS as Record<string, Record<string, string>>)[lang];
  const fallback = TRANSLATIONS.ko as Record<string, string>;

  let text: string = dict?.[key] ?? fallback[key] ?? key;

  if (params) {
    text = text.replace(/\{(\w+)\}/g, (match, name: string) => {
      const val = params[name];
      return val !== undefined ? String(val) : match;
    });
  }

  return text;
}
