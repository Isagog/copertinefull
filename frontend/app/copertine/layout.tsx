import { Suspense } from "react";
import { SignedIn, SignedOut, SignInButton } from "@clerk/nextjs";
import Header from "../components/header/Header";
import SearchSection from "../components/searchsection/SearchSection";

export default function CopertineLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <SignedIn>
        <Header />
        <SearchSection />
        <main>
          <Suspense
            fallback={
              <div className="min-h-[calc(100vh-176px)] flex flex-col items-center justify-center">
                <div className="animate-pulse text-blue-700 text-lg">
                  Caricamento...
                </div>
              </div>
            }
          >
            {children}
          </Suspense>
        </main>
      </SignedIn>
      <SignedOut>
        <div className="min-h-screen flex flex-col items-center justify-center">
          <div className="text-center mb-4">
            <h1 className="text-2xl font-bold mb-2">Accesso Richiesto</h1>
            <p className="text-gray-600 mb-4">Per favore, effettua l'accesso per visualizzare le copertine.</p>
            <SignInButton mode="modal">
              <button className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                Accedi
              </button>
            </SignInButton>
          </div>
        </div>
      </SignedOut>
    </>
  );
}
