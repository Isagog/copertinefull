// app/auth/verify/route.ts — the link in the email lands here.
import { NextResponse, type NextRequest } from "next/server";
import { getAuthConfig } from "../../lib/auth/config.ts";
import {
  createSessionToken,
  redeemMagicToken,
  SESSION_COOKIE,
  SESSION_TTL_SECONDS,
} from "../../lib/auth/session.ts";

export function GET(request: NextRequest): NextResponse {
  const config = getAuthConfig();
  const email = redeemMagicToken(request.nextUrl.searchParams.get("token") ?? "", config);
  if (!email) return NextResponse.redirect(`${config.appUrl}/login?error=link`, 303);

  const response = NextResponse.redirect(`${config.appUrl}/`, 303);
  response.cookies.set(SESSION_COOKIE, createSessionToken(email, config.secret), {
    httpOnly: true,
    secure: config.appUrl.startsWith("https://"),
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_TTL_SECONDS,
  });
  return response;
}
