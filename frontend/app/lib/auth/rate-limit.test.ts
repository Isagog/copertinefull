import { test } from "node:test";
import assert from "node:assert/strict";
import { createRateLimiter } from "./rate-limit.ts";

test("a key is allowed once per window", () => {
  const allow = createRateLimiter(60_000);
  assert.equal(allow("a", 0), true);
  assert.equal(allow("a", 59_999), false);
  assert.equal(allow("a", 60_000), true);
});

test("keys are limited independently", () => {
  const allow = createRateLimiter(60_000);
  assert.equal(allow("a", 0), true);
  assert.equal(allow("b", 0), true);
});
