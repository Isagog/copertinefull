// app/components/header/Header.tsx
'use client';

import { LogOut, Moon, Sun } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTheme } from '../../../providers/theme-provider';

export default function Header() {
  const { theme, setTheme } = useTheme();
  const pathname = usePathname();

  return (
    <>
      <header className="w-full bg-white dark:bg-black border-b border-gray-200 dark:border-gray-800">
        <div className="container mx-auto px-4">
          <div className="h-20 flex items-center justify-between">
            {/* Empty div to maintain centering: as wide as the buttons on the right */}
            <div className={pathname === '/login' ? 'w-10' : 'w-[5.5rem]'}></div>
            
            {/* Central logo */}
            <Link href="/" className="flex items-center justify-center">
              <Image
                src="/manifesto_logo.svg"
                alt="Il Manifesto"
                width={300}
                height={50}
                className="dark:invert"
                priority
              />
              <span className="sr-only">Il Manifesto</span>
            </Link>
            
            <div className="flex items-center gap-2">
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

              {/* Logout — every page but /login is behind the session cookie */}
              {pathname !== '/login' && (
                <form method="post" action="/auth/logout">
                  <button
                    type="submit"
                    className="w-10 h-10 p-2 rounded-lg bg-gray-200 dark:bg-gray-800"
                    aria-label="Esci"
                    title="Esci"
                  >
                    <LogOut className="w-full h-full text-gray-700 dark:text-gray-300" />
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      </header>
      {/* Red line under header */}
      <div className="w-full h-1 bg-red-600"></div>
    </>
  );
}