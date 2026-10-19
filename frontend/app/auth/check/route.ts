// app/auth/check/route.ts — asked by the copertine-images nginx (auth_request)
// before it serves a cover, so the JPEGs are behind the same login as the app.
import { type NextRequest } from "next/server";
import { getAuthConfig } from "../../lib/auth/config.ts";
import { SESSION_COOKIE, sessionEmail } from "../../lib/auth/session.ts";

export function GET(request: NextRequest): Response {
  const email = sessionEmail(request.cookies.get(SESSION_COOKIE)?.value, getAuthConfig());
  return new Response(null, { status: email ? 204 : 401 });
}
