// app/components/header/Header.tsx
'use client';

import { Moon, Sun } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { useTheme } from '../../../providers/theme-provider';

export default function Header() {
  const { theme, setTheme } = useTheme();

  return (
    <>
      <header className="w-full bg-white dark:bg-black border-b border-gray-200 dark:border-gray-800">
        <div className="container mx-auto px-4">
          <div className="h-20 flex items-center justify-between">
            {/* Empty div to maintain centering */}
            <div className="w-10"></div>
            
            {/* Central logo */}
            <Link href="/" className="flex items-center justify-center">
              <Image
                src="/copertine/manifesto_logo.svg"
                alt="Il Manifesto"
                width={300}
                height={50}
                className="dark:invert"
                priority
              />
              <span className="sr-only">Il Manifesto</span>
            </Link>
            
            {/* Theme toggle */}
            <button
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="w-10 h-10 p-2 rounded-lg bg-gray-200 dark:bg-gray-800"
              aria-label="Cambia tema"
            >
              {theme === 'dark' ? (
                <Sun className="w-full h-full text-yellow-500" />
              ) : (
                <Moon className="w-full h-full text-gray-700" />
              )}
            </button>
          </div>
        </div>
      </header>
      {/* Red line under header */}
      <div className="w-full h-1 bg-red-600"></div>
    </>
  );
}