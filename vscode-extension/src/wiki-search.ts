export interface WikiSearchDocument {
  path: string;
  title: string;
  type: string;
  bodyPreview: string;
  status?: string;
  verifiedBy?: string;
  parseErrors?: readonly string[];
}

export interface WikiSearchState {
  draftQuery: string;
  appliedQuery: string;
  type: string;
  showAll: boolean;
}

export interface WikiSearchModelOptions {
  pageLimit?: number;
}

interface IndexedWikiSearchDocument {
  document: WikiSearchDocument;
  haystack: string;
}

export class WikiSearchModel {
  private readonly pageLimit: number;
  private documents: IndexedWikiSearchDocument[] = [];
  private currentState: WikiSearchState = {
    draftQuery: "",
    appliedQuery: "",
    type: "all",
    showAll: false
  };

  public constructor(
    documents: readonly WikiSearchDocument[] = [],
    options: WikiSearchModelOptions = {}
  ) {
    this.pageLimit = Math.max(1, Math.floor(options.pageLimit ?? 12));
    this.updateDocuments(documents);
  }

  public get state(): WikiSearchState {
    return { ...this.currentState };
  }

  public updateDocuments(documents: readonly WikiSearchDocument[]): WikiSearchState {
    this.documents = documents.map((document) => ({
      document,
      haystack: [document.title, document.path, document.bodyPreview].join(" ").toLowerCase()
    }));
    return this.state;
  }

  public updateDraft(value: string): WikiSearchState {
    this.currentState = { ...this.currentState, draftQuery: value };
    return this.state;
  }

  public submit(): WikiSearchState {
    this.currentState = {
      ...this.currentState,
      appliedQuery: this.currentState.draftQuery.trim(),
      showAll: false
    };
    return this.state;
  }

  public setType(value: string): WikiSearchState {
    this.currentState = {
      ...this.currentState,
      type: value || "all",
      showAll: false
    };
    return this.state;
  }

  public setShowAll(value: boolean): WikiSearchState {
    this.currentState = { ...this.currentState, showAll: value };
    return this.state;
  }

  public filter(): WikiSearchDocument[] {
    const query = this.currentState.appliedQuery.toLowerCase();
    return this.documents
      .filter(({ document, haystack }) => {
        const matchesType = this.currentState.type === "all" || document.type === this.currentState.type;
        return matchesType && (!query || haystack.includes(query));
      })
      .map(({ document }) => document);
  }

  public visiblePages(): WikiSearchDocument[] {
    const filtered = this.filter();
    return this.currentState.showAll ? filtered : filtered.slice(0, this.pageLimit);
  }
}
