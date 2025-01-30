'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ChevronUp, ChevronDown } from "lucide-react";
import CopertinaCard from "@app/components/copertina/CopertinaCard";
import PaginationControls from "@app/components/PaginationControls";
import type { CopertineEntry } from "@app/types/copertine";
import { PAGINATION } from "@app/lib/config/constants";
import { useCopertine } from '../hooks/useCopertine';
import { useAuth } from '@app/hooks/useAuth';

type SortField = "date" | "extracted_caption" | "relevance";
type SortDirection = "asc" | "desc";

export default function CopertineList() {
  console.log('[CopertineList] Component rendering');
  
  const router = useRouter();
  const searchParams = useSearchParams();
  const page = Number(searchParams.get('page')) || 1;
  const offset = (page - 1) * PAGINATION.ITEMS_PER_PAGE;

  const [sortField, setSortField] = useState<SortField>("date");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [currentSearchTerm, setCurrentSearchTerm] = useState<string>('');

  console.log('[CopertineList] Fetching data with:', { page, offset });
  const { data, error, isLoading } = useCopertine({
    offset,
    limit: PAGINATION.ITEMS_PER_PAGE,
  });

  // Handle sort
  const handleSort = (field: SortField) => {
    if (field === "relevance" && !currentSearchTerm) return;

    if (field === sortField) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  // Sort copertine
  const sortedCopertine = [...(data?.data || [])].sort((a, b) => {
    const modifier = sortDirection === "asc" ? 1 : -1;

    switch (sortField) {
      case "date":
        return (new Date(a.isoDate).getTime() - new Date(b.isoDate).getTime()) * modifier;
      case "extracted_caption":
        return a.extracted_caption.localeCompare(b.extracted_caption) * modifier;
      default:
        return 0;
    }
  });

  const { isAuthenticated } = useAuth();
  console.log('[CopertineList] Auth state:', { isAuthenticated });

  // Let AuthProvider handle loading state
  // Let middleware handle redirects

  if (error) {
    console.log('[CopertineList] Error state:', error);
    console.log('[CopertineList] Rendering error state');
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col items-center justify-center">
        <div className="max-w-lg text-center space-y-4">
          <div className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Unable to Connect to Database
          </div>
          <div className="text-gray-600 dark:text-gray-400">
            {error.includes("Weaviate")
              ? error
              : "The database is currently unavailable. Please try again later."}
          </div>
        </div>
      </div>
    );
  }

  console.log('[CopertineList] Rendering main content:', { 
    hasData: !!data, 
    dataLength: data?.data?.length,
    isLoading 
  });

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4">
      <div className="max-w-7xl mx-auto">
      {/* Sort Controls */}
      <div className="mb-6 bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4">
        {/* Pagination Controls */}
        {data && (
          <PaginationControls
            currentPage={page}
            totalPages={Math.ceil(data.pagination.total / PAGINATION.ITEMS_PER_PAGE)}
            totalItems={data.pagination.total}
            onPageChange={(newPage) => {
              const params = new URLSearchParams(searchParams);
              params.set('page', newPage.toString());
              router.push(`/copertine?${params.toString()}`);
            }}
            isLoading={isLoading}
          />
        )}

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
        </div>
      </div>

      {/* Copertine Cards */}
      <div className="space-y-6">
        {sortedCopertine.map((copertina) => (
          <CopertinaCard 
            key={copertina.filename} 
            copertina={copertina} 
            searchTerm={currentSearchTerm}
          />
        ))}
      </div>
      </div>
    </div>
  );
}
