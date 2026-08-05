export interface WikiResultsHost {
  innerHTML: string;
}

export interface WikiResultsDocument {
  querySelector(selector: string): WikiResultsHost | null;
}

/** Mount already-rendered Wiki markup without coupling the search model to DOM APIs. */
export function mountWikiResults(documentLike: WikiResultsDocument, markup: string): boolean {
  const host = documentLike.querySelector("#wiki-results");
  if (!host) return false;
  host.innerHTML = markup;
  return true;
}
