// app/components/searchsection/SearchSection.tsx
'use client';

import React, { useState } from 'react';
import { Search, ListRestart } from 'lucide-react';

export type SearchMode = 'esatta' | 'varianti';

interface SearchSectionProps {
  onSearch: (query: string, mode: SearchMode) => void;
  onReset: () => void;
  isSearchResult: boolean;
}

export default function SearchSection({ onSearch, onReset, isSearchResult }: SearchSectionProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchMode, setSearchMode] = useState<SearchMode>('esatta');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim() || searchTerm.trim().length < 2) return;

    setIsSearching(true);
    try {
      await onSearch(searchTerm.trim(), searchMode);
    } finally {
      setIsSearching(false);
    }
  };

  const handleReset = () => {
    setSearchTerm('');
    onReset();
  };

  const searchButtonClasses = `h-12 flex-1 sm:w-auto px-6 rounded-lg transition-all duration-200 font-medium flex items-center justify-center shadow-sm hover:shadow-md active:scale-[0.98] ${
    searchTerm.trim().length >= 2
      ? "bg-red-600 hover:bg-red-700 text-white"
      : "bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 cursor-not-allowed shadow-none hover:shadow-none active:scale-100"
  }`;

  const resetButtonClasses = `h-12 sm:w-auto px-4 rounded-lg transition-all duration-200 font-medium flex items-center justify-center gap-2 ${
    isSearchResult
      ? "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/40 cursor-pointer"
      : "text-gray-400 dark:text-gray-500 bg-transparent cursor-not-allowed"
  }`;

  return (
    <>
      <div className="bg-red-600 h-1 w-full" />
      <div className="w-full bg-white dark:bg-black border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <form onSubmit={handleSearch} className="space-y-6">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col sm:flex-row gap-4 items-center">
                <div className="flex-1 flex items-center gap-4">
                  <label htmlFor="search" className="text-lg font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">
                    Cerca
                  </label>
                  <div className="relative flex-1">
                    <input
                      type="text"
                      id="search"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full px-4 py-2 h-10 rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      placeholder="Inserisci il testo da cercare..."
                    />
                    <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                  </div>
                </div>
                <div className="sm:self-auto flex gap-2 items-center">
                  {/* Mode toggle */}
                  <div className="flex rounded-lg p-1 bg-gray-100 dark:bg-gray-800 h-12 items-center">
                    {(['esatta', 'varianti'] as SearchMode[]).map((mode) => (
                      <button
                        key={mode}
                        type="button"
                        onClick={() => setSearchMode(mode)}
                        className={`px-4 py-2 h-full rounded-md text-sm font-medium transition-all duration-200 ${
                          searchMode === mode
                            ? 'bg-white dark:bg-gray-700 text-red-600 dark:text-red-400 shadow-sm'
                            : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
                        }`}
                      >
                        {mode.charAt(0).toUpperCase() + mode.slice(1)}
                      </button>
                    ))}
                  </div>

                  <button
                    type="submit"
                    disabled={isSearching || searchTerm.trim().length < 2}
                    className={searchButtonClasses}
                  >
                    {isSearching ? 'Ricerca...' : 'Cerca'}
                  </button>
                  <button
                    type="button"
                    onClick={handleReset}
                    disabled={!isSearchResult}
                    className={resetButtonClasses}
                    title="Torna alla lista completa"
                  >
                    <ListRestart className="w-4 h-4" />
                    <span className="hidden sm:inline">Lista completa</span>
                    <span className="sm:hidden">Reset</span>
                  </button>
                </div>
              </div>
            </div>
          </form>
        </div>
      </div>
      <div className="bg-red-600 h-1 w-full" />
    </>
  );
}
