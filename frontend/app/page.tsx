// app/page.tsx
'use client';

import React from 'react';
import { ArrowUpDown } from 'lucide-react';
import CopertinaCard from './components/copertina/CopertinaCard';
import type { CopertineEntry, CopertineResponse, PaginationInfo } from './types/copertine';
import { COPERTINEPERPAGE } from '@/app/constants';

type SortField = 'date' | 'extracted_caption' | 'relevance';
type SortDirection = 'asc' | 'desc';

export default function Home() {
    const [copertine, setCopertine] = React.useState<CopertineEntry[]>([]);
    const [originalOrder, setOriginalOrder] = React.useState<CopertineEntry[]>([]);
    const [isSearchResult, setIsSearchResult] = React.useState(false);
    const [pagination, setPagination] = React.useState<PaginationInfo>({
        total: 0,
        offset: 0,
        limit: COPERTINEPERPAGE,
        hasMore: true
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
            setOriginalOrder(data.data);
            setPagination(data.pagination);
            setIsSearchResult(false);
            setSortField('date');
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load data');
        } finally {
            setIsLoading(false);
        }
    }, [pagination.limit]);

    // Effect for handling search results and reset
    React.useEffect(() => {
        const handleSearchResults = (event: CustomEvent<CopertineEntry[]>) => {
            console.log('Handling search results:', {
                resultCount: event.detail.length,
                sampleResults: event.detail.slice(0, 2)
            });
            
            setCopertine(event.detail);
            setOriginalOrder(event.detail);
            setIsSearchResult(true);
            setSortField('relevance');
            setPagination({
                total: event.detail.length,
                offset: 0,
                limit: COPERTINEPERPAGE,  // Keep the original page size
                hasMore: event.detail.length > COPERTINEPERPAGE
            });
        };
    
        const handleResetToFullList = () => {
            fetchPage(0);
        };
    
        window.addEventListener('searchResults', handleSearchResults as EventListener);
        window.addEventListener('resetToFullList', handleResetToFullList as EventListener);
    
        return () => {
            window.removeEventListener('searchResults', handleSearchResults as EventListener);
            window.removeEventListener('resetToFullList', handleResetToFullList as EventListener);
        };
    }, [fetchPage]);

    // Initial load
    React.useEffect(() => {
        fetchPage(0);
    }, [fetchPage]);

    const handleSort = (field: SortField) => {
        if (field === 'relevance' && !isSearchResult) {
            return; // Don't sort by relevance if not a search result
        }
        
        if (field === sortField) {
            setSortDirection(current => current === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDirection('desc');
        }
    };

    const sortedCopertine = React.useMemo(() => {
        // If sorting by relevance and it's a search result, return original order
        if (sortField === 'relevance' && isSearchResult) {
            return originalOrder;
        }

        return [...copertine].sort((a, b) => {
            const modifier = sortDirection === 'asc' ? 1 : -1;
            
            switch (sortField) {
                case 'date':
                    const timeA = new Date(a.isoDate).getTime();
                    const timeB = new Date(b.isoDate).getTime();
                    return (timeA - timeB) * modifier;
                case 'extracted_caption':
                    return a.extracted_caption.localeCompare(b.extracted_caption) * modifier;
                case 'relevance':
                    // This case should never be reached because of the earlier check
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
                                {error.includes('Weaviate') ? error : 'The Weaviate database is currently unavailable. Please check your connection and try again.'}
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
                        {/* Sort Controls */}
                        <div className="mb-6 bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4">
                            <div className="flex justify-between items-center">
                                <div className="flex gap-4">
                                    <button 
                                        onClick={() => handleSort('relevance')}
                                        className={`flex items-center gap-2 px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors ${
                                            !isSearchResult ? 'opacity-50 cursor-not-allowed' : ''
                                        }`}
                                        disabled={!isSearchResult}
                                    >
                                        Rilevanza {sortField === 'relevance' && <ArrowUpDown className="h-4 w-4" />}
                                    </button>
                                    <button 
                                        onClick={() => handleSort('date')}
                                        className="flex items-center gap-2 px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                                    >
                                        Data {sortField === 'date' && <ArrowUpDown className="h-4 w-4" />}
                                    </button>
                                    <button 
                                        onClick={() => handleSort('extracted_caption')}
                                        className="flex items-center gap-2 px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                                    >
                                        Didascalia {sortField === 'extracted_caption' && <ArrowUpDown className="h-4 w-4" />}
                                    </button>
                                </div>
                                
                                {/* Rest of the existing controls... */}
                            </div>
                        </div>

                        {/* Copertine Cards */}
                        <div className="space-y-6">
                            {sortedCopertine.map((copertina) => (
                                <CopertinaCard key={copertina.filename} copertina={copertina} />
                            ))}
                        </div>

                        {/* Pagination controls... */}
                    </div>
                )}
            </section>
        </div>
    );
}
