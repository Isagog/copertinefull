// app/components/searchsection/SearchSection.tsx
'use client';

import React, { useState } from 'react';
import { Search, ListRestart } from 'lucide-react';
import {
  DEFAULT_OPTIONS,
  type SearchMode,
  type SearchOptions,
  type SearchScope,
} from '@app/types/search';

interface SearchSectionProps {
  onSearch: (query: string, options: SearchOptions) => void;
  onReset: () => void;
  isSearchResult: boolean;
}

interface ToggleGroupProps<T extends string> {
  label: string;
  value: T;
  options: ReadonlyArray<{ value: T; label: string; hint: string }>;
  onChange: (value: T) => void;
  disabled?: boolean;
  disabledHint?: string;
}

function ToggleGroup<T extends string>({
  label,
  value,
  options,
  onChange,
  disabled = false,
  disabledHint,
}: ToggleGroupProps<T>) {
  return (
    <div className={`flex flex-col gap-1 ${disabled ? 'opacity-50' : ''}`} title={disabled ? disabledHint : undefined}>
      <span className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {label}
      </span>
      <div className="flex rounded-lg p-1 bg-gray-100 dark:bg-gray-800 h-11 items-center" role="group" aria-label={label}>
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            disabled={disabled}
            aria-pressed={value === option.value}
            title={disabled ? disabledHint : option.hint}
            onClick={() => onChange(option.value)}
            className={`px-3 py-2 h-full rounded-md text-sm font-medium transition-all duration-200 whitespace-nowrap ${
              value === option.value
                ? 'bg-white dark:bg-gray-700 text-red-600 dark:text-red-400 shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
            } ${disabled ? 'cursor-not-allowed' : ''}`}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

const SCOPE_OPTIONS = [
  { value: 'titolo', label: 'Solo titolo', hint: 'Cerca solo nel titolo della copertina' },
  { value: 'tutto', label: 'Tutto il testo', hint: 'Cerca nel titolo e nel sommario' },
] as const satisfies ReadonlyArray<{ value: SearchScope; label: string; hint: string }>;

const MODE_OPTIONS = [
  { value: 'esatta', label: 'Esatta', hint: 'Trova il testo cosi come e stato scritto (ignora maiuscole e accenti)' },
  { value: 'varianti', label: 'Varianti', hint: 'Trova anche le varianti della parola: "guerra" trova "guerre"' },
] as const satisfies ReadonlyArray<{ value: SearchMode; label: string; hint: string }>;

const GRANULARITY_OPTIONS = [
  { value: 'parola', label: 'Parola intera', hint: '"ago" non trova "fragole"' },
  { value: 'stringa', label: 'Stringa', hint: '"ago" trova anche "fragole"' },
] as const;

const GRANULARITY_LOCKED =
  'La ricerca per varianti lavora sempre su parole intere';

export default function SearchSection({ onSearch, onReset, isSearchResult }: SearchSectionProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [options, setOptions] = useState<SearchOptions>(DEFAULT_OPTIONS);

  // Varianti is inherently word-level, so the granularity switch is locked
  // there. The user's own choice is kept in state for when they switch back.
  const granularityLocked = options.mode === 'varianti';
  const effectiveWhole = granularityLocked ? true : options.whole;

  const canSearch = searchTerm.trim().length >= 2;

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSearch) return;

    setIsSearching(true);
    try {
      await onSearch(searchTerm.trim(), { ...options, whole: effectiveWhole });
    } finally {
      setIsSearching(false);
    }
  };

  const handleReset = () => {
    setSearchTerm('');
    onReset();
  };

  const searchButtonClasses = `h-11 flex-1 sm:w-auto px-6 rounded-lg transition-all duration-200 font-medium flex items-center justify-center shadow-sm hover:shadow-md active:scale-[0.98] ${
    canSearch
      ? 'bg-red-600 hover:bg-red-700 text-white'
      : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500 cursor-not-allowed shadow-none hover:shadow-none active:scale-100'
  }`;

  const resetButtonClasses = `h-11 sm:w-auto px-4 rounded-lg transition-all duration-200 font-medium flex items-center justify-center gap-2 ${
    isSearchResult
      ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/40 cursor-pointer'
      : 'text-gray-400 dark:text-gray-500 bg-transparent cursor-not-allowed'
  }`;

  return (
    <>
      <div className="bg-red-600 h-1 w-full" />
      <div className="w-full bg-white dark:bg-black border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <form onSubmit={handleSearch} className="flex flex-col gap-4">
            {/* Query row */}
            <div className="flex flex-col sm:flex-row gap-4 items-center">
              <label htmlFor="search" className="text-lg font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">
                Cerca
              </label>
              <div className="relative flex-1 w-full">
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

            {/* Switches + actions */}
            <div className="flex flex-col lg:flex-row gap-4 lg:items-end lg:justify-between">
              <div className="flex flex-wrap gap-3">
                <ToggleGroup
                  label="Ambito"
                  value={options.scope}
                  options={SCOPE_OPTIONS}
                  onChange={(scope) => setOptions((o) => ({ ...o, scope }))}
                />
                <ToggleGroup
                  label="Corrispondenza"
                  value={options.mode}
                  options={MODE_OPTIONS}
                  onChange={(mode) => setOptions((o) => ({ ...o, mode }))}
                />
                <ToggleGroup
                  label="Granularita"
                  value={effectiveWhole ? 'parola' : 'stringa'}
                  options={GRANULARITY_OPTIONS}
                  onChange={(v) => setOptions((o) => ({ ...o, whole: v === 'parola' }))}
                  disabled={granularityLocked}
                  disabledHint={GRANULARITY_LOCKED}
                />
              </div>

              <div className="flex gap-2 items-center">
                <button type="submit" disabled={isSearching || !canSearch} className={searchButtonClasses}>
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
          </form>
        </div>
      </div>
      <div className="bg-red-600 h-1 w-full" />
    </>
  );
}
