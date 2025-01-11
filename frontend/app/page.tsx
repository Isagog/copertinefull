// app/page.tsx
'use client';

import React from 'react';
import { ArrowUpDown, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import CopertinaCard from './components/copertina/CopertinaCard';
import type { CopertineEntry, CopertineResponse, PaginationInfo } from './types/copertine';
import { COPERTINEPERPAGE } from '@/app/constants';

type SortField = 'date' | 'extracted_caption';
type SortDirection = 'asc' | 'desc';

const LoadingSpinner = () => (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <div className="relative w-16 h-16">
            <div className="absolute top-0 left-0 w-full h-full border-4 border-gray-200 dark:border-gray-700 rounded-full"></div>
            <div className="absolute top-0 left-0 w-full h-full border-4 border-blue-500 dark:border-blue-400 rounded-full animate-spin border-t-transparent"></div>
        </div>
        <div className="text-lg text-gray-600 dark:text-gray-400">
            Caricamento copertine...
        </div>
    </div>
);

export default function Home() {
    const [copertine, setCopertine] = React.useState<CopertineEntry[]>([]);
    const [pagination, setPagination] = React.useState<PaginationInfo>({
        total: 0,
        offset: 0,
        limit: COPERTINEPERPAGE,
        hasMore: false
    });
    const [sortField, setSortField] = React.useState<SortField>('date');
    const [sortDirection, setSortDirection] = React.useState<SortDirection>('desc');
    const [isLoading, setIsLoading] = React.useState(true);
    const [error, setError] = React.useState<string | null>(null);

    const fetchPage = React.useCallback(async (offset: number) => {
        try {
            setIsLoading(true);
            const response = await fetch(`/api/copertine?offset=${offset}&limit=${pagination.limit}`);
            if (!response.ok) throw new Error('Failed to fetch data');
            const data: CopertineResponse = await response.json();
            setCopertine(data.data);
            setPagination(data.pagination);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load data');
        } finally {
            setIsLoading(false);
        }
    }, [pagination.limit]);

    React.useEffect(() => {
        fetchPage(0);
    }, [fetchPage]);

    const handleSort = (field: SortField) => {
        if (field === sortField) {
            setSortDirection(current => current === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDirection('desc');
        }
    };

    const sortedCopertine = React.useMemo(() => {
        return [...copertine].sort((a, b) => {
            const modifier = sortDirection === 'asc' ? 1 : -1;
            
            if (sortField === 'date') {
                const timeA = new Date(a.isoDate).getTime();
                const timeB = new Date(b.isoDate).getTime();
                return (timeA - timeB) * modifier;
            }
            
            return a[sortField].localeCompare(b[sortField]) * modifier;
        });
    }, [copertine, sortField, sortDirection]);

    const handlePageChange = (newOffset: number) => {
        fetchPage(newOffset);
    };

    const goToFirst = () => handlePageChange(0);
    const goToLast = () => handlePageChange(Math.floor(pagination.total / pagination.limit) * pagination.limit);
    const goToNext = () => handlePageChange(pagination.offset + pagination.limit);
    const goToPrevious = () => handlePageChange(Math.max(0, pagination.offset - pagination.limit));

    const totalPages = pagination.total > 0 ? Math.ceil(pagination.total / pagination.limit) : 1;
    const currentPage = pagination.total > 0 ? Math.floor(pagination.offset / pagination.limit) + 1 : 0;

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
            <section className="container mx-auto px-4 py-6">
                {error ? (
                    <div className="flex flex-col items-center justify-center min-h-[400px]">
                        <div className="max-w-lg text-center space-y-4">
                            <div className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                                Unable to Connect to Database
                            </div>
                            <div className="text-gray-600 dark:text-gray-400">
                                {error.includes('Weaviate') ? error : 'The Weaviate database is currently unavailable. Please check your connection and try again.'}
                            </div>
                        </div>
                    </div>
                ) : isLoading ? (
                    <LoadingSpinner />
                ) : (
                    <div>
                        {/* Sort Controls */}
                        <div className="flex justify-between items-center mb-6 p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
                            {/* ... your existing sort controls ... */}
                            
                            {/* Pagination Info */}
                            <div className="text-sm text-gray-600 dark:text-gray-400">
                                {pagination.total > 0 && 
                                    `Showing ${pagination.offset + 1}-${Math.min(pagination.offset + pagination.limit, pagination.total)} of ${pagination.total}`
                                }
                            </div>
                        </div>

                        {/* Cards Grid */}
                        <div className="space-y-6">
                            {sortedCopertine.map((copertina: CopertineEntry) => (
                                <CopertinaCard key={copertina.filename} copertina={copertina} />
                            ))}
                        </div>

                        {/* Pagination Controls */}
                        <div className="flex justify-center items-center gap-4 mt-8 p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm">
                            <button
                                onClick={goToFirst}
                                disabled={pagination.offset === 0}
                                className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                                aria-label="First page"
                            >
                                <ChevronsLeft className="h-5 w-5" />
                            </button>
                            <button
                                onClick={goToPrevious}
                                disabled={pagination.offset === 0}
                                className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                                aria-label="Previous page"
                            >
                                <ChevronLeft className="h-5 w-5" />
                            </button>
                            
                            <span className="text-gray-600 dark:text-gray-400">
                                {pagination.total > 0 ? `Page ${currentPage} of ${totalPages}` : 'No results'}
                            </span>

                            <button
                                onClick={goToNext}
                                disabled={!pagination.hasMore}
                                className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                                aria-label="Next page"
                            >
                                <ChevronRight className="h-5 w-5" />
                            </button>
                            <button
                                onClick={goToLast}
                                disabled={!pagination.hasMore}
                                className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
                                aria-label="Last page"
                            >
                                <ChevronsRight className="h-5 w-5" />
                            </button>
                        </div>
                    </div>
                )}
            </section>
        </div>
    );
}