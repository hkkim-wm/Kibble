# Kibble 🐕

용어 검색 도구 — 번역 메모리(TM) 및 용어집(TB) 파일에서 용어를 빠르게 검색합니다.

**두 가지 버전**으로 제공됩니다:
- **데스크톱** — Windows 포터블 exe (PyQt6)
- **웹** — 브라우저에서 바로 사용: https://hkkim-wm.github.io/Kibble/

## 기능

- **파일 지원**: xlsx, csv, txt 파일 로드 (드래그 앤 드롭, Ctrl+O, 폴더 일괄 로드)
- **검색 방식**: 부분 일치(Substring) + 유사 일치(Fuzzy) + 단어 단위(Whole Word)
- **원문/번역문 검색**: 원문(한국어) 또는 번역문(대상 언어)에서 검색 선택 가능
- **번역문 필터**: 검색 결과를 번역문 텍스트로 추가 필터링
- **다국어 지원**: 한국어 원문 → 영어, 일본어, 중국어(번체/간체) 등 17개 언어
- **열 자동 감지**: 언어 코드 헤더 인식 또는 한글 콘텐츠 기반 자동 열 매핑
- **열 수동 설정**: ⚙ 버튼으로 원문/번역문 열을 직접 지정 가능
- **파일 간 열 병합**: 다른 파일의 "English"와 "EN"을 동일 열로 자동 통합
- **검색 결과 하이라이트**: 검색어는 노란색, 필터 텍스트는 파란색으로 강조 표시
- **보기 모드**: 3열 보기(원문 + 선택 언어 + 메타) 또는 전체 번역문 보기
- **일치율 표시**: 검색 결과에 일치율(%) 열 표시
- **열 정렬/너비 조절**: 열 헤더 클릭으로 정렬, 경계 드래그로 너비 조절
- **글꼴 크기 조절**: S/M/L/XL 선택 가능
- **다크 모드**: 설정 메뉴에서 전환 가능
- **세션 저장**: 파일, 검색 설정, 다크 모드, 글꼴 크기 등 자동 저장/복원
- **EN/KO UI**: 설정 메뉴에서 영어/한국어 인터페이스 전환
- **전역 단축키** (데스크톱만): Ctrl+C로 복사 후 `Ctrl+Shift+K`로 외부 앱에서 바로 검색
- **포터블**: 데스크톱은 단일 exe, 웹은 URL 접속만으로 사용

## 사용법

### 파일 로드
1. 파일을 창에 드래그 앤 드롭하거나 `Ctrl+O`로 파일을 엽니다.
2. **파일 > 폴더 열기**로 폴더 내 모든 xlsx/csv/txt를 일괄 로드할 수 있습니다.
3. 열이 자동으로 감지됩니다. 잘못된 경우 ⚙ 버튼으로 수정하세요.

### 검색
1. 검색어를 입력하고 `Enter` 키를 누릅니다.
2. 검색 방향을 선택합니다:
   - **원문에서 검색**: 한국어 원문 열에서 검색
   - **번역문에서 검색**: 대상 언어 열에서 검색
3. "번역문 필터"로 결과를 추가로 필터링할 수 있습니다.

### 검색 옵션
- **일치 방식**: 부분 일치 / 유사 일치 / 모두
- **단어 단위**: 단어 경계 기준 매칭 (CJK는 부분 일치로 자동 전환)
- **대소문자 구분**: 영문 대소문자 구분 여부
- **와일드카드**: `*`를 와일드카드로 사용
- **공백 무시**: 공백을 무시하고 검색
- **최소 일치율**: 슬라이더로 조절 (기본: 50%)
- **최대 결과**: 표시할 최대 결과 수 (기본: 200)

### 단축키 (데스크톱)

| 단축키 | 기능 |
|--------|------|
| `Ctrl+F` | 검색창 포커스 |
| `Ctrl+O` | 파일 열기 |
| `Ctrl+C` | 선택한 셀 복사 |
| `Ctrl+W` | 현재 파일 탭 닫기 |
| `Escape` | 검색창 초기화 |
| `Ctrl+Shift+K` | 외부 앱에서 클립보드 텍스트로 검색 |

### 결과 조작
- **더블 클릭**: 셀 텍스트를 클립보드에 복사
- **우클릭**: 행 복사, 셀 복사, 원문만 복사, 번역문만 복사
- **열 헤더 클릭**: 해당 열로 정렬
- **열 경계 드래그**: 열 너비 조절

## 기술 스택

### 데스크톱 (PyQt6)

| 구성 요소 | 기술 |
|-----------|------|
| 런타임 | Python 3.11+ |
| GUI | PyQt6 |
| 파일 파싱 | pandas + openpyxl |
| 유사 검색 | RapidFuzz |
| 인코딩 감지 | chardet |
| 패키징 | PyInstaller |

### 웹 (React)

| 구성 요소 | 기술 |
|-----------|------|
| 프레임워크 | React 18 + TypeScript |
| 빌드 | Vite 7 |
| 스타일링 | Tailwind CSS 4 |
| xlsx 파싱 | SheetJS |
| csv 파싱 | Papa Parse |
| 유사 검색 | fastest-levenshtein |
| 가상 스크롤 | @tanstack/react-virtual |
| 인코딩 감지 | jschardet |
| 호스팅 | GitHub Pages |

## 빌드

### 데스크톱

```bash
cd kibble
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
```

```bash
# 테스트
.venv/Scripts/python -m pytest tests/ -v

# 실행 (개발 모드)
.venv/Scripts/python main.py

# exe 빌드
.venv/Scripts/pip install pyinstaller
.venv/Scripts/pyinstaller Kibble.spec
```

빌드 결과: `dist/Kibble.exe` (약 70MB, 포터블)

### 웹

```bash
cd kibble/web
npm install
```

```bash
# 테스트
npx vitest run

# 개발 서버
npm run dev

# 프로덕션 빌드
npm run build
```

빌드 결과: `web/dist/` (index.html + assets/)

> GitHub Pages에 배포: `gh-pages` 브랜치에 `dist/` 폴더 내용을 push합니다.

## 파일 구조

```
kibble/
├── main.py                 # 데스크톱 진입점
├── core/
│   ├── parser.py           # 파일 파싱 (xlsx, csv, txt)
│   ├── search.py           # 검색 엔진 (부분 일치 + 유사 일치 + 단어 단위)
│   └── session.py          # 세션 저장/복원
├── ui/
│   ├── main_window.py      # 메인 윈도우
│   ├── search_panel.py     # 검색 패널
│   ├── results_table.py    # 결과 테이블 + 하이라이트
│   ├── file_tabs.py        # 파일 탭
│   ├── drop_zone.py        # 드래그 앤 드롭 + 토스트 알림
│   ├── column_mapper.py    # 열 설정 다이얼로그
│   └── i18n.py             # EN/KO 번역
├── workers/
│   ├── parse_worker.py     # 파일 파싱 백그라운드 워커
│   └── search_worker.py    # 검색 백그라운드 워커
├── assets/
│   └── icon.ico            # 앱 아이콘
├── tests/                  # 데스크톱 테스트 (42개)
├── Kibble.spec             # PyInstaller 빌드 설정
├── requirements.txt        # Python 의존성
└── web/                    # 웹 버전
    ├── src/
    │   ├── core/           # 파서, 검색, 세션 (TS 포팅)
    │   ├── components/     # React 컴포넌트
    │   ├── i18n/           # EN/KO 번역
    │   └── workers/        # Web Worker
    ├── tests/              # 웹 테스트 (68개)
    └── dist/               # 빌드 결과
```

## 제한 사항

- 최대 총 항목 수: 500,000 (파일 합산)
- xlsx 파일은 첫 번째 시트만 로드
- 검색어 최소 길이: 2자

## 라이선스

내부 사용 전용
