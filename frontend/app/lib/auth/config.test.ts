import { test } from "node:test";
import assert from "node:assert/strict";
import { normalizeEmail, parseAllowedEmails, readAuthConfig } from "./config.ts";

const VALID_ENV = {
  AUTH_SECRET: "s".repeat(32),
  ALLOWED_EMAILS: " A@Example.it , b@example.it,,",
  APP_URL: "https://copertine.ilmanifesto.it/",
  SMTP_HOST: "smtp.example.it",
  SMTP_PORT: "465",
  SMTP_USER: "user",
  SMTP_PASS: "pass",
  SMTP_FROM: "noreply@example.it",
};

test("emails are trimmed and lower-cased", () => {
  assert.equal(normalizeEmail("  Mario.Rossi@Example.IT "), "mario.rossi@example.it");
});

test("the allowlist ignores blanks and case", () => {
  assert.deepEqual([...parseAllowedEmails(VALID_ENV.ALLOWED_EMAILS)], ["a@example.it", "b@example.it"]);
});

test("a complete environment is read", () => {
  const config = readAuthConfig(VALID_ENV);
  assert.equal(config.appUrl, "https://copertine.ilmanifesto.it");
  assert.equal(config.smtp.port, 465);
  assert.ok(config.allowedEmails.has("a@example.it"));
});

test("a short secret is refused", () => {
  assert.throws(() => readAuthConfig({ ...VALID_ENV, AUTH_SECRET: "short" }), /AUTH_SECRET/);
});

test("an empty allowlist is refused", () => {
  assert.throws(() => readAuthConfig({ ...VALID_ENV, ALLOWED_EMAILS: " , " }), /ALLOWED_EMAILS/);
});

test("each missing variable is named in the error", () => {
  for (const name of ["APP_URL", "SMTP_HOST", "SMTP_USER", "SMTP_PASS", "SMTP_FROM"]) {
    assert.throws(() => readAuthConfig({ ...VALID_ENV, [name]: "" }), new RegExp(name));
  }
});

test("a non-numeric SMTP port is refused", () => {
  assert.throws(() => readAuthConfig({ ...VALID_ENV, SMTP_PORT: "smtp" }), /SMTP_PORT/);
});
