// middleware.ts — every page and /api route requires a valid session cookie.
//
// Pages without one redirect to /login; the API answers 401. If the auth
// environment is incomplete nobody gets in (503) rather than everybody.
// The cover JPEGs are served by the separate copertine-images nginx, which asks
// /auth/check itself.
import { NextResponse, type NextRequest } from "next/server";
import { getAuthConfig, type AuthConfig } from "./app/lib/auth/config.ts";
import { SESSION_COOKIE, sessionEmail } from "./app/lib/auth/session.ts";

function loadConfig(): AuthConfig | null {
  try {
    return getAuthConfig();
  } catch (error: unknown) {
    console.error("Login is not configured:", error);
    return null;
  }
}

export function middleware(request: NextRequest): NextResponse {
  const config = loadConfig();
  if (!config) return new NextResponse("Servizio non disponibile", { status: 503 });

  if (sessionEmail(request.cookies.get(SESSION_COOKIE)?.value, config)) return NextResponse.next();

  if (request.nextUrl.pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "Non autenticato" }, { status: 401 });
  }
  return NextResponse.redirect(`${config.appUrl}/login`);
}

export const config = {
  // node:crypto is used to check the cookie, so this cannot run on the edge runtime.
  runtime: "nodejs",
  // Open: the login page and its endpoints, Next's build assets, and the
  // root-level files in public/ the login page itself shows (logo, favicon).
  matcher: ["/((?!login|auth/|_next/static|_next/image|favicon\\.ico|[^/]+\\.(?:svg|png)$).*)"],
};
