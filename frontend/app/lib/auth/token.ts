// app/lib/auth/token.ts
//
// Stateless signed tokens: base64url(JSON claims) + "." + base64url(HMAC-SHA256).
// The same format carries both the emailed magic link and the session cookie;
// `kind` keeps one from being replayed as the other.
import { createHmac, timingSafeEqual } from "node:crypto";

export type TokenKind = "magic" | "session";

export interface TokenClaims {
  sub: string;
  kind: TokenKind;
  /** Expiry, seconds since the epoch. */
  exp: number;
}

function sign(payload: string, secret: string): Buffer {
  return createHmac("sha256", secret).update(payload).digest();
}

export function signToken(claims: TokenClaims, secret: string): string {
  const payload = Buffer.from(JSON.stringify(claims)).toString("base64url");
  return `${payload}.${sign(payload, secret).toString("base64url")}`;
}

function parseClaims(payload: string): TokenClaims | null {
  try {
    const claims: unknown = JSON.parse(Buffer.from(payload, "base64url").toString("utf8"));
    if (typeof claims !== "object" || claims === null) return null;
    const { sub, kind, exp } = claims as Record<string, unknown>;
    if (typeof sub !== "string" || !sub) return null;
    if (kind !== "magic" && kind !== "session") return null;
    if (typeof exp !== "number") return null;
    return { sub, kind, exp };
  } catch {
    return null;
  }
}

/** Returns the token's subject, or null if it is forged, malformed, expired or of the wrong kind. */
export function verifyToken(
  token: string,
  secret: string,
  kind: TokenKind,
  nowSeconds: number = Math.floor(Date.now() / 1000),
): string | null {
  const parts = token.split(".");
  if (parts.length !== 2) return null;
  const [payload, signature] = parts;

  const expected = sign(payload, secret);
  const given = Buffer.from(signature, "base64url");
  if (given.length !== expected.length || !timingSafeEqual(given, expected)) return null;

  const claims = parseClaims(payload);
  if (!claims || claims.kind !== kind || claims.exp <= nowSeconds) return null;
  return claims.sub;
}
