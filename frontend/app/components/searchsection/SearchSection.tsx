// app/components/searchsection/SearchSection.tsx
'use client';

import React, { useState } from 'react';
import { Search } from 'lucide-react';

interface SearchSectionProps {
  onSearch: (query: string) => void;
  onReset: () => void;
  isSearchResult: boolean;
}

export default function SearchSection({ onSearch, onReset, isSearchResult }: SearchSectionProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim() || searchTerm.trim().length < 2) return;

    setIsSearching(true);
    try {
      await onSearch(searchTerm.trim());
    } finally {
      setIsSearching(false);
    }
  };

  const handleReset = () => {
    setSearchTerm('');
    onReset();
  };

  // Base button classes
  const baseButtonClasses = "h-12 flex-1 sm:w-auto px-6 rounded-lg transition-colors duration-200 font-medium flex items-center justify-center";

  // Active button style (dark)
  const activeButtonClasses = "bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200";

  // Inactive button style (light)
  const inactiveButtonClasses = "bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 cursor-not-allowed";

  // Primary button style (blue)
  const primaryButtonClasses = "bg-blue-500 hover:bg-blue-600 text-white";

  const searchButtonClasses = `${baseButtonClasses} ${
    searchTerm.trim().length >= 2
      ? primaryButtonClasses
      : inactiveButtonClasses
  }`;

  const resetButtonClasses = `${baseButtonClasses} ${
    isSearchResult
      ? primaryButtonClasses
      : inactiveButtonClasses
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
                <div className="sm:self-auto flex gap-2">
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
                  >
                    Lista completa
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
