// app/auth/logout/route.ts — POST target of the logout button in the header.
import { NextResponse } from "next/server";
import { getAuthConfig } from "../../lib/auth/config.ts";
import { SESSION_COOKIE } from "../../lib/auth/session.ts";

export function POST(): NextResponse {
  const response = NextResponse.redirect(`${getAuthConfig().appUrl}/login`, 303);
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
