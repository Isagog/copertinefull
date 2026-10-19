// app/login/page.tsx — a plain HTML form; works without client-side JS.
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Accesso - Copertine" };

interface LoginPageProps {
  searchParams: Promise<{ sent?: string; error?: string }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const { sent, error } = await searchParams;

  return (
    <div className="min-h-[calc(100vh-176px)] flex items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-lg border border-gray-200 dark:border-gray-800 p-8 shadow-sm">
        <h1 className="mb-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
          Archivio delle copertine
        </h1>

        {sent ? (
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Se l&apos;indirizzo è abilitato, riceverai a breve un&apos;email con il link di
            accesso. Il link vale 15 minuti.
          </p>
        ) : (
          <>
            <p className="mb-6 text-sm text-gray-600 dark:text-gray-400">
              Inserisci la tua email: ti invieremo un link per accedere.
            </p>
            {error && (
              <p className="mb-4 text-sm text-red-600 dark:text-red-400">
                Link non valido o scaduto. Richiedine uno nuovo.
              </p>
            )}
            <form method="post" action="/auth/login" className="flex flex-col gap-3">
              <input
                type="email"
                name="email"
                required
                autoComplete="email"
                maxLength={254}
                placeholder="nome@esempio.it"
                aria-label="Email"
                className="h-11 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-3 text-sm"
              />
              <button
                type="submit"
                className="h-11 rounded-lg bg-red-600 text-sm font-medium text-white hover:bg-red-700"
              >
                Invia link di accesso
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
