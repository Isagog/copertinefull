// app/page.tsx
"use client";

import React from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import CopertinaCard from "../components/copertina/CopertinaCard";
import PaginationControls from "../components/PaginationControls";
import type {
  CopertineEntry,
  CopertineResponse,
  PaginationInfo,
} from "../types/copertine";
import { PAGINATION } from "@/app/lib/config/constants";

type SortField = "date" | "extracted_caption" | "relevance";
type SortDirection = "asc" | "desc";

export default function Home() {
  // State declarations
  const [copertine, setCopertine] = React.useState<CopertineEntry[]>([]);
  const [originalOrder, setOriginalOrder] = React.useState<CopertineEntry[]>(
    []
  );
  const [isSearchResult, setIsSearchResult] = React.useState(false);
  const [pagination, setPagination] = React.useState<PaginationInfo>({
    total: 0,
    offset: 0,
    limit: PAGINATION.ITEMS_PER_PAGE,
    hasMore: true,
  });
  const [sortField, setSortField] = React.useState<SortField>("date");
  const [sortDirection, setSortDirection] =
    React.useState<SortDirection>("desc");
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  // Fetch page data
  const fetchPage = React.useCallback(async (offset: number) => {
    try {
        setIsLoading(true);
        console.log(`Fetching page with offset ${offset}`);

        // Explicitly construct the URL using window.location.origin
        const baseUrl = window.location.origin;
        const url = `${baseUrl}/copertine/api/copertine?offset=${offset}&limit=${pagination.limit}`;
        console.log('Requesting URL:', url);
        
        const response = await fetch(url);
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Error response:', errorText);
            throw new Error(`Failed to fetch data: ${response.status} ${errorText}`);
        }
        
        const data: CopertineResponse = await response.json();
        console.log('Received data:', data);
        
        if (!data.data || !Array.isArray(data.data)) {
            throw new Error('Invalid data format received');
        }

        setCopertine(data.data);
        setOriginalOrder(data.data);
        setPagination(data.pagination);
        setIsSearchResult(false);
        setSortField('date');
        setError(null);
    } catch (err) {
        console.error('Fetch error:', err);
        setError(err instanceof Error ? err.message : 'Failed to load data');
        setCopertine([]);
        setOriginalOrder([]);
        setPagination({
            total: 0,
            offset: 0,
            limit: PAGINATION.ITEMS_PER_PAGE,
            hasMore: false
        });
    } finally {
        setIsLoading(false);
    }
}, [pagination.limit]);

  // Handle search results and reset
  React.useEffect(() => {
    const handleSearchResults = (event: CustomEvent<CopertineEntry[]>) => {
      console.log("Handling search results:", {
        resultCount: event.detail.length,
        sampleResults: event.detail.slice(0, 2),
      });

      setCopertine(event.detail);
      setOriginalOrder(event.detail);
      setIsSearchResult(true);
      setSortField("relevance");
      setPagination({
        total: event.detail.length,
        offset: 0,
        limit: PAGINATION.ITEMS_PER_PAGE,
        hasMore: event.detail.length > PAGINATION.ITEMS_PER_PAGE,
      });
    };

    const handleResetToFullList = () => {
      fetchPage(0);
    };

    window.addEventListener(
      "searchResults",
      handleSearchResults as EventListener
    );
    window.addEventListener(
      "resetToFullList",
      handleResetToFullList as EventListener
    );

    return () => {
      window.removeEventListener(
        "searchResults",
        handleSearchResults as EventListener
      );
      window.removeEventListener(
        "resetToFullList",
        handleResetToFullList as EventListener
      );
    };
  }, [fetchPage]);

  // Initial load
  React.useEffect(() => {
    fetchPage(0);
  }, [fetchPage]);

  // Sort handling
  const handleSort = (field: SortField) => {
    if (field === "relevance") {
      if (!isSearchResult) return; // Don't sort by relevance if not a search result
      setSortField("relevance");
      setSortDirection("desc"); // Always desc for relevance
      return;
    }

    if (field === sortField) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  // Sort copertine based on current field and direction
  const sortedCopertine = React.useMemo(() => {
    if (sortField === "relevance" && isSearchResult) {
      return originalOrder;
    }

    return [...copertine].sort((a, b) => {
      const modifier = sortDirection === "asc" ? 1 : -1;

      switch (sortField) {
        case "date":
          const timeA = new Date(a.isoDate).getTime();
          const timeB = new Date(b.isoDate).getTime();
          return (timeA - timeB) * modifier;
        case "extracted_caption":
          return (
            a.extracted_caption.localeCompare(b.extracted_caption) * modifier
          );
        case "relevance":
          return 0;
        default:
          return 0;
      }
    });
  }, [copertine, sortField, sortDirection, originalOrder, isSearchResult]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <section className="max-w-4xl mx-auto px-4 py-6">
        {error ? (
          <div className="flex flex-col items-center justify-center min-h-[400px]">
            <div className="max-w-lg text-center space-y-4">
              <div className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                Unable to Connect to Database
              </div>
              <div className="text-gray-600 dark:text-gray-400">
                {error.includes("Weaviate")
                  ? error
                  : "The Weaviate database is currently unavailable. Please check your connection and try again."}
              </div>
            </div>
          </div>
        ) : isLoading ? (
          <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
            <div className="relative w-16 h-16">
              <div className="absolute top-0 left-0 w-full h-full border-4 border-gray-200 dark:border-gray-700 rounded-full"></div>
              <div className="absolute top-0 left-0 w-full h-full border-4 border-blue-500 dark:border-blue-400 rounded-full animate-spin border-t-transparent"></div>
            </div>
            <div className="text-lg text-gray-600 dark:text-gray-400">
              Caricamento copertine...
            </div>
          </div>
        ) : (
          <div>
            {/* Combined Sort and Pagination Controls */}
            <div className="mb-6 bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4">
              {/* Pagination Controls - Now shown for both search and normal results */}
              <PaginationControls
                currentPage={
                  Math.floor(pagination.offset / pagination.limit) + 1
                }
                totalPages={Math.ceil(pagination.total / pagination.limit)}
                totalItems={pagination.total}
                onPageChange={(newPage) => {
                  const newOffset = (newPage - 1) * pagination.limit;
                  fetchPage(newOffset);
                }}
                isLoading={isLoading}
              />

              {/* Sort Controls */}
              <div className="flex gap-4 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => handleSort("date")}
                  className={`flex items-center gap-2 px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-blue-100 dark:hover:bg-gray-700 rounded-md transition-colors ${
                    sortField === "date" ? "bg-blue-100 dark:bg-gray-700" : ""
                  }`}
                >
                  Data
                  <div className="flex flex-col">
                    <ChevronUp
                      className={`h-3 w-3 -mb-1 ${
                        sortField === "date" && sortDirection === "asc"
                          ? "text-blue-600 dark:text-blue-400"
                          : "text-gray-400"
                      }`}
                    />
                    <ChevronDown
                      className={`h-3 w-3 ${
                        sortField === "date" && sortDirection === "desc"
                          ? "text-blue-600 dark:text-blue-400"
                          : "text-gray-400"
                      }`}
                    />
                  </div>
                </button>
                <button
                  onClick={() => handleSort("extracted_caption")}
                  className={`flex items-center gap-2 px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-blue-100 dark:hover:bg-gray-700 rounded-md transition-colors ${
                    sortField === "extracted_caption"
                      ? "bg-blue-100 dark:bg-gray-700"
                      : ""
                  }`}
                >
                  Titolo
                  <div className="flex flex-col">
                    <ChevronUp
                      className={`h-3 w-3 -mb-1 ${
                        sortField === "extracted_caption" &&
                        sortDirection === "asc"
                          ? "text-blue-600 dark:text-blue-400"
                          : "text-gray-400"
                      }`}
                    />
                    <ChevronDown
                      className={`h-3 w-3 ${
                        sortField === "extracted_caption" &&
                        sortDirection === "desc"
                          ? "text-blue-600 dark:text-blue-400"
                          : "text-gray-400"
                      }`}
                    />
                  </div>
                </button>
                {isSearchResult && (
                  <button
                    onClick={() => {
                      setSortField("relevance");
                      setSortDirection("desc");
                    }}
                    className={`px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-blue-100 dark:hover:bg-gray-700 rounded-md transition-colors ${
                      sortField === "relevance"
                        ? "bg-blue-100 dark:bg-gray-700"
                        : ""
                    }`}
                  >
                    Rilevanza
                  </button>
                )}
              </div>
            </div>

            {/* Copertine Cards */}
            <div className="space-y-6">
              {sortedCopertine.map((copertina) => (
                <CopertinaCard key={copertina.filename} copertina={copertina} />
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
