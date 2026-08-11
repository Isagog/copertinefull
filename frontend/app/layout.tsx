// app/layout.tsx
import type { Metadata } from "next";
import { Inter as FontSans } from "next/font/google";
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
        {/* Served by Next from `public/`, i.e. at the ROOT — not under
            /copertine/. That prefix worked only on mema3, where an nginx
            `alias` mapped /copertine/ onto frontend/public/ because the app
            shared a vhost with a dozen other services. On its own host there
            is no such alias and the prefixed path 404s. */}
        <link rel="preload" href="/manifesto_logo.svg" as="image" />
      </head>
      <body className="antialiased">
        <ThemeProvider defaultTheme="light">
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}