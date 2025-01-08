// app/layout.tsx
import type { Metadata } from "next";
import { Inter as FontSans } from "next/font/google";
import { Suspense } from "react";

import Header from "./components/header/Header";
import { ThemeProvider } from "../providers/theme-provider";
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
        <link rel="preload" href="/manifesto_logo.svg" as="image" />
      </head>
      <body className="antialiased">
        <ThemeProvider defaultTheme="light">
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