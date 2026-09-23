/**
 * The run-create shapes the proxy must rewrite (ph. 06 §2).
 *
 *     node --test tests/
 *
 * Imports `RUN_CREATE` from the module the ROUTE imports, so this cannot
 * drift from what actually runs. The list below is the acceptance criterion
 * spelled out: "every run-create shape the UI actually issues is matched,
 * asserted by a test that lists them."
 */
import assert from "node:assert/strict";
import { test } from "node:test";

import { RUN_CREATE } from "../lib/runCreate.ts";

const STARTS_A_RUN = [
  "/threads/abc/runs",
  "/threads/abc/runs/stream",
  "/threads/abc/runs/wait",
  "/runs",
  "/runs/stream",
  "/runs/wait",
  // Real thread ids are uuids with hyphens.
  "/threads/01a0ccd4-ce0a-76d3-9429-51473669db62/runs/stream",
];

const DOES_NOT = [
  "/threads",
  "/threads/abc",
  "/threads/abc/state",
  "/threads/abc/history",
  // Acts on an EXISTING run: no context to rewrite, and no body to parse.
  "/threads/abc/runs/xyz",
  "/threads/abc/runs/xyz/join",
  "/threads/abc/runs/xyz/cancel",
  "/threads/abc/runs/xyz/stream",
  "/assistants/search",
  "/runs/batch",
  "/ok",
];

test("every shape that starts a run is rewritten", () => {
  for (const path of STARTS_A_RUN) {
    assert.equal(RUN_CREATE.test(path), true, `${path} must be rewritten`);
  }
});

test("nothing else is rewritten", () => {
  for (const path of DOES_NOT) {
    assert.equal(RUN_CREATE.test(path), false, `${path} must pass through`);
  }
});

test("the pattern is anchored at both ends", () => {
  assert.equal(RUN_CREATE.test("/x/threads/a/runs"), false);
  assert.equal(RUN_CREATE.test("/runs/stream/extra"), false);
  assert.equal(RUN_CREATE.test("prefix/runs"), false);
});

test("a thread id containing a slash cannot smuggle a path", () => {
  // `[^/]+` is what makes this true. A greedy `.+` would match
  // "/threads/a/runs/b/runs" and rewrite a body meant for a sub-resource.
  assert.equal(RUN_CREATE.test("/threads/a/b/runs"), false);
});
