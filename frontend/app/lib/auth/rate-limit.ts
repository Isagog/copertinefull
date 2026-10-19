// app/lib/auth/rate-limit.ts
//
// One hit per key per window, in process memory. Enough to stop the login form
// from being used to flood an allowlisted inbox; the app runs as one container.

export type RateLimiter = (key: string, nowMs?: number) => boolean;

export function createRateLimiter(windowMs: number): RateLimiter {
  const lastHit = new Map<string, number>();

  return (key, nowMs = Date.now()) => {
    const previous = lastHit.get(key);
    if (previous !== undefined && nowMs - previous < windowMs) return false;
    lastHit.set(key, nowMs);
    return true;
  };
}
