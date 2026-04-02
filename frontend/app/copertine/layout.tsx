import { Suspense } from "react";
import Header from "../components/header/Header";

export default function CopertineLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <Header />
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
    </>
  );
}
