// app/lib/auth/config.ts
//
// Everything the magic-link login needs, read from the environment once and
// validated up front. A missing or weak value is a deployment error: callers
// fail closed (nobody gets in) rather than open.

const MIN_SECRET_LENGTH = 32;

export interface SmtpConfig {
  host: string;
  port: number;
  user: string;
  pass: string;
  from: string;
}

export interface AuthConfig {
  secret: string;
  allowedEmails: ReadonlySet<string>;
  /** Public origin used to build the emailed link and redirects, no trailing slash. */
  appUrl: string;
  smtp: SmtpConfig;
}

type Env = Readonly<Record<string, string | undefined>>;

export function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

export function parseAllowedEmails(raw: string | undefined): ReadonlySet<string> {
  return new Set(
    (raw ?? "")
      .split(",")
      .map(normalizeEmail)
      .filter((email) => email.length > 0),
  );
}

function required(env: Env, name: string): string {
  const value = env[name]?.trim();
  if (!value) throw new Error(`${name} is not set`);
  return value;
}

export function readAuthConfig(env: Env): AuthConfig {
  const secret = required(env, "AUTH_SECRET");
  if (secret.length < MIN_SECRET_LENGTH) {
    throw new Error(`AUTH_SECRET must be at least ${MIN_SECRET_LENGTH} characters`);
  }

  const allowedEmails = parseAllowedEmails(env.ALLOWED_EMAILS);
  if (allowedEmails.size === 0) throw new Error("ALLOWED_EMAILS lists no address");

  const port = Number(env.SMTP_PORT ?? "465");
  if (!Number.isInteger(port) || port <= 0) throw new Error("SMTP_PORT is not a port number");

  return {
    secret,
    allowedEmails,
    appUrl: required(env, "APP_URL").replace(/\/+$/, ""),
    smtp: {
      host: required(env, "SMTP_HOST"),
      port,
      user: required(env, "SMTP_USER"),
      pass: required(env, "SMTP_PASS"),
      from: required(env, "SMTP_FROM"),
    },
  };
}

let cached: AuthConfig | undefined;

/** The process-wide config; throws (every time) until the environment is valid. */
export function getAuthConfig(): AuthConfig {
  cached ??= readAuthConfig(process.env);
  return cached;
}
