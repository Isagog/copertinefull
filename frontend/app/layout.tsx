// app/layout.tsx
import type { Metadata } from "next";
import { Inter as FontSans } from "next/font/google";
import { ClerkProvider, SignInButton, SignedIn, SignedOut, UserButton } from "@clerk/nextjs";
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
        <link rel="preload" href="/copertine/manifesto_logo.svg" as="image" />
      </head>
      <body className="antialiased">
        <ClerkProvider>
          <ThemeProvider defaultTheme="light">
            <header className="flex justify-end p-4">
              <SignedOut>
                <SignInButton />
              </SignedOut>
              <SignedIn>
                <UserButton afterSignOutUrl="/" />
              </SignedIn>
            </header>
            {children}
          </ThemeProvider>
        </ClerkProvider>
      </body>
    </html>
  );
}
