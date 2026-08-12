// app/layout.tsx
import { Suspense } from "react";
import type { Metadata } from "next";
import { Inter as FontSans } from "next/font/google";
import { ThemeProvider } from "../providers/theme-provider";
import Header from "./components/header/Header";
import "./globals.css";

const fontSans = FontSans({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Il Manifesto - Copertine",
  description: "Archivio delle copertine de Il Manifesto",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="it" className={fontSans.variable}>
      <head>
        {/* Served by Next from `public/`, i.e. at the ROOT — not under
            /copertine/. That prefix worked only on mema3, where an nginx
            `alias` mapped /copertine/ onto frontend/public/ because the app
            shared a vhost with a dozen other services. On its own host there
            is no such alias and the prefixed path 404s. */}
        <link rel="preload" href="/manifesto_logo.svg" as="image" />
      </head>
      <body className="antialiased">
        <ThemeProvider defaultTheme="light">
          {/* Header and the Suspense boundary used to live in a nested
              app/copertine/layout.tsx. The archive now owns `/` outright, so
              there is no nested segment left to hold them and they belong
              here. The boundary is load-bearing, not decoration: the page is
              a client component that reads searchParams, which Next requires
              to be wrapped in Suspense or the build fails. */}
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
        </ThemeProvider>
      </body>
    </html>
  );
}