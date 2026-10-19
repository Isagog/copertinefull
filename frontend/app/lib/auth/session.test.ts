import { test } from "node:test";
import assert from "node:assert/strict";
import { createMagicToken, createSessionToken, redeemMagicToken, sessionEmail } from "./session.ts";

const SECRET = "x".repeat(32);
const allowedEmails = new Set(["a@b.it"]);
const config = { secret: SECRET, allowedEmails };

test("a fresh session cookie identifies its allowlisted owner", () => {
  assert.equal(sessionEmail(createSessionToken("a@b.it", SECRET), config), "a@b.it");
});

test("a session for an address dropped from the allowlist is refused", () => {
  const token = createSessionToken("gone@b.it", SECRET);
  assert.equal(sessionEmail(token, config), null);
});

test("no cookie is no session", () => {
  assert.equal(sessionEmail(undefined, config), null);
});

test("a magic token cannot be used as a session cookie", () => {
  assert.equal(sessionEmail(createMagicToken("a@b.it", SECRET), config), null);
});

test("a magic token redeems to its allowlisted owner", () => {
  assert.equal(redeemMagicToken(createMagicToken("a@b.it", SECRET), config), "a@b.it");
});

test("a session cookie cannot be redeemed as a magic link", () => {
  assert.equal(redeemMagicToken(createSessionToken("a@b.it", SECRET), config), null);
});

test("a magic token expires after its lifetime", () => {
  const issuedAt = 1_800_000_000;
  const token = createMagicToken("a@b.it", SECRET, issuedAt);
  assert.equal(redeemMagicToken(token, config, issuedAt + 15 * 60 - 1), "a@b.it");
  assert.equal(redeemMagicToken(token, config, issuedAt + 15 * 60), null);
});
