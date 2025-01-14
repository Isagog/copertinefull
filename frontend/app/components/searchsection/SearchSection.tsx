'use client';

import React, { useState } from 'react';
import { Search } from 'lucide-react';
import { useTheme } from '../../../providers/theme-provider';
import type { SearchRequest } from '@/app/types/search';

export default function SearchSection() {
  const { theme } = useTheme();
  const [searchTerm, setSearchTerm] = useState('');
  const [mode, setMode] = useState<SearchRequest['mode']>('literal');
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;

    setIsSearching(true);
    setError(null);

    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchTerm,
          mode: mode
        }),
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.error || 'Search request failed');
      }
      
      // Handle the search results here
      console.log('Search results:', data);
      
    } catch (error) {
      console.error('Search error:', error);
      setError(error instanceof Error ? error.message : 'An unexpected error occurred');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <>
      <div className="bg-red-600 h-1 w-full" />
      <div className="w-full bg-white dark:bg-black border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <form onSubmit={handleSearch} className="space-y-6">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1">
                  <label htmlFor="search" className="block text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Ricerca
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      id="search"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-200 dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                      placeholder="Inserisci il testo da cercare..."
                    />
                    <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                  </div>
                </div>
                <div className="sm:self-end">
                  <button
                    type="submit"
                    disabled={isSearching}
                    className="w-full sm:w-auto px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors duration-200 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isSearching ? 'Ricerca...' : 'Cerca'}
                  </button>
                </div>
              </div>

              {error && (
                <div className="text-red-600 text-sm mt-2">
                  {error}
                </div>
              )}

              <div className="flex items-center gap-4">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Tipo di ricerca:
                </span>
                <div className="inline-flex rounded-lg border border-gray-200 dark:border-gray-800 p-1 bg-gray-200 dark:bg-gray-800">
                  <button
                    type="button"
                    onClick={() => setMode('literal')}
                    className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors duration-200 ${
                      mode === 'literal'
                        ? 'bg-white dark:bg-black text-blue-600 dark:text-blue-400'
                        : 'text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400'
                    }`}
                  >
                    Letterale
                  </button>
                  <button
                    type="button"
                    onClick={() => setMode('fuzzy')}
                    className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors duration-200 ${
                      mode === 'fuzzy'
                        ? 'bg-white dark:bg-black text-blue-600 dark:text-blue-400'
                        : 'text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400'
                    }`}
                  >
                    Approssimata
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