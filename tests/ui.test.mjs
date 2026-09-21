import test from "node:test";
import assert from "node:assert/strict";
import {
  date,
  age,
  isFresh,
  proposalStatus,
  csv,
  esc,
  money,
  number,
} from "../src/optionlab/web/core.mjs";

test("UTC storage and freshness boundaries do not treat stale data as tradable", () => {
  const now = Date.parse("2026-09-21T04:30:00Z");
  assert.equal(date("2026-09-21T04:30:00").getTime(), now);
  assert.equal(isFresh("2026-09-21T04:29:00Z", 60, now), true);
  assert.equal(isFresh("2026-09-21T04:28:59Z", 60, now), false);
  assert.equal(isFresh("2026-09-21T04:30:06Z", 60, now), false);
  assert.equal(isFresh(null, 60, now), false);
  assert.equal(age("2026-09-20T04:30:00Z", now), "1d ago");
});
test("proposal expiry is evaluated locally without rewriting filled records", () => {
  const now = Date.parse("2026-09-21T04:30:00Z");
  const proposal = { status: "PROPOSED", expires_at: "2026-09-21T04:30:00Z" };
  assert.equal(proposalStatus(proposal, now), "expired");
  assert.equal(proposalStatus(proposal, now - 1), "pending");
  assert.equal(
    proposalStatus({ ...proposal, status: "FILLED" }, now),
    "filled",
  );
});
test("untrusted records are escaped and spreadsheet formulas neutralized", () => {
  assert.equal(
    esc('<img src="x" onerror=alert(1)>'),
    "&lt;img src=&quot;x&quot; onerror=alert(1)&gt;",
  );
  assert.equal(
    csv([['=HYPERLINK("x")', "@SUM(1)", "-10", "a,b"]]),
    '"\'=HYPERLINK(""x"")","\'@SUM(1)","\'-10","a,b"',
  );
});
test("missing numeric values are not presented as zero or NaN", () => {
  assert.equal(money(null), "—");
  assert.equal(number(undefined), "—");
  assert.equal(number(NaN), "—");
  assert.equal(number("0"), "0.00");
});
