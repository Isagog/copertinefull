"use client";

import React from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import CopertinaCard from "../components/copertina/CopertinaCard";
import PaginationControls from "../components/PaginationControls";
import SearchSection from "../components/searchsection/SearchSection";
import type { CopertineEntry, CopertineResponse, PaginationInfo } from "../types/copertine";
import {
  DEFAULT_CRITERIA,
  criteriaToQueryString,
  supportsRelevance,
  type SearchCriteria,
  type SearchOptions,
  type SortField,
} from "../types/search";
import { PAGINATION } from "@/app/lib/config/constants";

const EMPTY_PAGINATION: PaginationInfo = {
  total: 0,
  offset: 0,
  limit: PAGINATION.ITEMS_PER_PAGE,
  hasMore: false,
};

export default function Home() {
  const [copertine, setCopertine] = React.useState<CopertineEntry[]>([]);
  const [criteria, setCriteria] = React.useState<SearchCriteria>(DEFAULT_CRITERIA);
  const [pagination, setPagination] = React.useState<PaginationInfo>({
    ...EMPTY_PAGINATION,
    hasMore: true,
  });
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  /**
   * The single fetch path. Every navigation — search, sort, paging — goes
   * through here with a complete criteria object, so paging can no longer
   * drop the active query the way the old separate browse/search calls did.
   */
  const fetchResults = React.useCallback(async (next: SearchCriteria) => {
    try {
      setIsLoading(true);
      setError(null);
      setCriteria(next);

      const url = `/api/copertine?${criteriaToQueryString(next, PAGINATION.ITEMS_PER_PAGE)}`;
      const response = await fetch(url);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to fetch data: ${response.status} ${errorText}`);
      }

      const data: CopertineResponse = await response.json();
      if (!data.data || !Array.isArray(data.data)) {
        throw new Error("Invalid data format received");
      }

      setCopertine(data.data);
      setPagination(data.pagination);

      if (data.data.length === 0 && next.q) {
        setError(`Nessun risultato trovato per "${next.q}"`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
      setCopertine([]);
      setPagination(EMPTY_PAGINATION);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleSearch = React.useCallback(
    (query: string, options: SearchOptions) => {
      const next: SearchCriteria = {
        ...options,
        q: query,
        // Relevance is the useful default where a rank exists.
        sort: options.mode === "varianti" ? "rilevanza" : "data",
        dir: "desc",
        offset: 0,
      };
      return fetchResults(next);
    },
    [fetchResults],
  );

  const handleReset = React.useCallback(() => fetchResults(DEFAULT_CRITERIA), [fetchResults]);

  // Ordering happens in SQL over the whole result set, not just the loaded
  // page, so changing it refetches from offset 0.
  const handleSort = React.useCallback(
    (field: SortField) => {
      const dir =
        field === "rilevanza"
          ? "desc"
          : criteria.sort === field && criteria.dir === "desc"
            ? "asc"
            : "desc";
      fetchResults({ ...criteria, sort: field, dir, offset: 0 });
    },
    [criteria, fetchResults],
  );

  const handlePageChange = React.useCallback(
    (newPage: number) => {
      fetchResults({ ...criteria, offset: (newPage - 1) * PAGINATION.ITEMS_PER_PAGE });
    },
    [criteria, fetchResults],
  );

  // Initial load
  React.useEffect(() => {
    fetchResults(DEFAULT_CRITERIA);
  }, [fetchResults]);

  const isSearchResult = criteria.q !== "";
  const showRelevance = supportsRelevance(criteria);

  const sortButtonClasses = (field: SortField) =>
    `flex items-center gap-2 px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-blue-100 dark:hover:bg-gray-700 rounded-md transition-colors ${
      criteria.sort === field ? "bg-blue-100 dark:bg-gray-700" : ""
    }`;

  const chevrons = (field: SortField) => (
    <div className="flex flex-col">
      <ChevronUp
        className={`h-3 w-3 -mb-1 ${
          criteria.sort === field && criteria.dir === "asc"
            ? "text-blue-600 dark:text-blue-400"
            : "text-gray-400"
        }`}
      />
      <ChevronDown
        className={`h-3 w-3 ${
          criteria.sort === field && criteria.dir === "desc"
            ? "text-blue-600 dark:text-blue-400"
            : "text-gray-400"
        }`}
      />
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <SearchSection onSearch={handleSearch} onReset={handleReset} isSearchResult={isSearchResult} />

      <section className="max-w-4xl mx-auto px-4 py-6">
        {error && !isLoading ? (
          <div className="flex flex-col items-center justify-center min-h-[400px]">
            <div className="max-w-lg text-center space-y-4">
              <div className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                {isSearchResult ? "Nessun risultato" : "Impossibile caricare i dati"}
              </div>
              <div className="text-gray-600 dark:text-gray-400">{error}</div>
            </div>
          </div>
        ) : isLoading ? (
          <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
            <div className="relative w-16 h-16">
              <div className="absolute top-0 left-0 w-full h-full border-4 border-gray-200 dark:border-gray-700 rounded-full"></div>
              <div className="absolute top-0 left-0 w-full h-full border-4 border-blue-500 dark:border-blue-400 rounded-full animate-spin border-t-transparent"></div>
            </div>
            <div className="text-lg text-gray-600 dark:text-gray-400">Caricamento copertine...</div>
          </div>
        ) : (
          <div>
            <div className="mb-6 bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4">
              <PaginationControls
                currentPage={Math.floor(pagination.offset / pagination.limit) + 1}
                totalPages={Math.ceil(pagination.total / pagination.limit)}
                totalItems={pagination.total}
                onPageChange={handlePageChange}
                isLoading={isLoading}
              />

              <div className="flex gap-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button onClick={() => handleSort("data")} className={sortButtonClasses("data")}>
                  Data
                  {chevrons("data")}
                </button>
                <button onClick={() => handleSort("titolo")} className={sortButtonClasses("titolo")}>
                  Titolo
                  {chevrons("titolo")}
                </button>
                {showRelevance && (
                  <button
                    onClick={() => handleSort("rilevanza")}
                    className={sortButtonClasses("rilevanza")}
                  >
                    Rilevanza
                  </button>
                )}
              </div>
            </div>

            <div className="space-y-6">
              {copertine.map((copertina) => (
                <CopertinaCard
                  key={copertina.filename}
                  copertina={copertina}
                  searchTerm={criteria.q}
                  matchWholeWord={criteria.whole}
                  scope={criteria.scope}
                />
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
