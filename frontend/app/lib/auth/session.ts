// app/lib/auth/session.ts
//
// The two tokens of the login flow. The magic link is short-lived and only
// ever redeemed for a session; the session lives in an httpOnly cookie.
// Both re-check the allowlist, so removing an address from ALLOWED_EMAILS and
// redeploying locks that person out at their next request.
import type { AuthConfig } from "./config.ts";
import { signToken, verifyToken } from "./token.ts";

export const SESSION_COOKIE = "cop_session";
export const SESSION_TTL_SECONDS = 30 * 24 * 60 * 60;
export const MAGIC_TTL_SECONDS = 15 * 60;

type TokenConfig = Pick<AuthConfig, "secret" | "allowedEmails">;

const nowInSeconds = (): number => Math.floor(Date.now() / 1000);

export function createMagicToken(email: string, secret: string, now: number = nowInSeconds()): string {
  return signToken({ sub: email, kind: "magic", exp: now + MAGIC_TTL_SECONDS }, secret);
}

export function createSessionToken(email: string, secret: string, now: number = nowInSeconds()): string {
  return signToken({ sub: email, kind: "session", exp: now + SESSION_TTL_SECONDS }, secret);
}

function allowed(email: string | null, config: TokenConfig): string | null {
  return email !== null && config.allowedEmails.has(email) ? email : null;
}

export function redeemMagicToken(token: string, config: TokenConfig, now: number = nowInSeconds()): string | null {
  return allowed(verifyToken(token, config.secret, "magic", now), config);
}

export function sessionEmail(cookie: string | undefined, config: TokenConfig, now: number = nowInSeconds()): string | null {
  if (!cookie) return null;
  return allowed(verifyToken(cookie, config.secret, "session", now), config);
}
