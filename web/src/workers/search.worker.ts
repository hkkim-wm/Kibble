import { search } from '../core/search';
import type { SearchConfig, SearchResult } from '../core/search';

interface SearchMessage {
  type: 'search';
  entries: string[];
  config: SearchConfig;
  id: number;
}

interface SearchResultMessage {
  type: 'result';
  results: SearchResult[];
  id: number;
}

interface SearchErrorMessage {
  type: 'error';
  error: string;
  id: number;
}

export type SearchWorkerResponse = SearchResultMessage | SearchErrorMessage;

self.onmessage = (e: MessageEvent<SearchMessage>) => {
  const { entries, config, id } = e.data;

  try {
    const results = search(entries, config);
    self.postMessage({ type: 'result', results, id } satisfies SearchResultMessage);
  } catch (err) {
    self.postMessage({
      type: 'error',
      error: err instanceof Error ? err.message : String(err),
      id,
    } satisfies SearchErrorMessage);
  }
};
