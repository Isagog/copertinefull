import { test } from "node:test";
import assert from "node:assert/strict";
import { signToken, verifyToken } from "./token.ts";

const SECRET = "x".repeat(32);
const NOW = 1_800_000_000;

test("a signed token verifies and yields its subject", () => {
  const token = signToken({ sub: "a@b.it", kind: "session", exp: NOW + 60 }, SECRET);
  assert.equal(verifyToken(token, SECRET, "session", NOW), "a@b.it");
});

test("an expired token is rejected", () => {
  const token = signToken({ sub: "a@b.it", kind: "session", exp: NOW }, SECRET);
  assert.equal(verifyToken(token, SECRET, "session", NOW), null);
});

test("a token of the other kind is rejected", () => {
  const magic = signToken({ sub: "a@b.it", kind: "magic", exp: NOW + 60 }, SECRET);
  assert.equal(verifyToken(magic, SECRET, "session", NOW), null);
});

test("a token signed with another secret is rejected", () => {
  const token = signToken({ sub: "a@b.it", kind: "session", exp: NOW + 60 }, "y".repeat(32));
  assert.equal(verifyToken(token, SECRET, "session", NOW), null);
});

test("a token whose payload was altered is rejected", () => {
  const token = signToken({ sub: "a@b.it", kind: "session", exp: NOW + 60 }, SECRET);
  const [, sig] = token.split(".");
  const forged = Buffer.from(JSON.stringify({ sub: "evil@x.it", kind: "session", exp: NOW + 60 }))
    .toString("base64url");
  assert.equal(verifyToken(`${forged}.${sig}`, SECRET, "session", NOW), null);
});

test("malformed input is rejected without throwing", () => {
  for (const bad of ["", "abc", "a.b.c", ".", "!!!.???", "e30.AAAA"]) {
    assert.equal(verifyToken(bad, SECRET, "session", NOW), null, bad);
  }
});
