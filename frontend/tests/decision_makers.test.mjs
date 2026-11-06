import test from "node:test";
import assert from "node:assert/strict";
import { formatDecisionMaker } from "../src/lib/utils.ts";

test("formatDecisionMaker - object with role and department", () => {
  const dm = { role: "VP of Engineering", department: "Engineering" };
  assert.strictEqual(formatDecisionMaker(dm), "VP of Engineering · Engineering");
});

test("formatDecisionMaker - object with role only", () => {
  const dm = { role: "Head of Infrastructure" };
  assert.strictEqual(formatDecisionMaker(dm), "Head of Infrastructure");
});

test("formatDecisionMaker - object with department only", () => {
  const dm = { department: "Operations" };
  assert.strictEqual(formatDecisionMaker(dm), "Operations");
});

test("formatDecisionMaker - object with title and department (alias for role)", () => {
  const dm = { title: "Director of Platform", department: "Cloud Architecture" };
  assert.strictEqual(formatDecisionMaker(dm), "Director of Platform · Cloud Architecture");
});

test("formatDecisionMaker - object with name, role, and department", () => {
  const dm = {
    name: "Alice Smith",
    role: "VP Engineering",
    department: "Technology",
  };
  assert.strictEqual(formatDecisionMaker(dm), "Alice Smith (VP Engineering · Technology)");
});

test("formatDecisionMaker - object with name and role", () => {
  const dm = { name: "Bob Jones", role: "CTO" };
  assert.strictEqual(formatDecisionMaker(dm), "Bob Jones (CTO)");
});

test("formatDecisionMaker - object with name only", () => {
  const dm = { name: "Charlie Brown" };
  assert.strictEqual(formatDecisionMaker(dm), "Charlie Brown");
});

test("formatDecisionMaker - backward compatibility with string entries", () => {
  assert.strictEqual(formatDecisionMaker("CTO"), "CTO");
  assert.strictEqual(formatDecisionMaker("Head of DevOps"), "Head of DevOps");
  assert.strictEqual(formatDecisionMaker("  VP of Product  "), "VP of Product");
});

test("formatDecisionMaker - safe handling of null, undefined, and empty string", () => {
  assert.strictEqual(formatDecisionMaker(null), null);
  assert.strictEqual(formatDecisionMaker(undefined), null);
  assert.strictEqual(formatDecisionMaker(""), null);
  assert.strictEqual(formatDecisionMaker("   "), null);
});

test("formatDecisionMaker - safe handling of empty object and objects with null/undefined values", () => {
  assert.strictEqual(formatDecisionMaker({}), null);
  assert.strictEqual(
    formatDecisionMaker({ role: null, department: undefined, name: "" }),
    null
  );
  assert.strictEqual(formatDecisionMaker({ role: "   ", department: "" }), null);
});

test("formatDecisionMaker - malformed object with alternative string key", () => {
  const dm = { custom_role: "Staff Site Reliability Engineer" };
  assert.strictEqual(formatDecisionMaker(dm), "Staff Site Reliability Engineer");
});

test("formatDecisionMaker - malformed object with no usable string values", () => {
  const dm = { count: 42, active: true, metadata: null };
  assert.strictEqual(formatDecisionMaker(dm), null);
});

test("formatDecisionMaker - simulated list mapping in Company Dossier", () => {
  const rawDecisionMakers = [
    { role: "VP of Engineering", department: "Engineering" },
    "CTO",
    { role: "Head of Infrastructure", department: "Operations" },
    {},
    null,
    "",
    { name: "Sarah Connor", title: "Chief Information Security Officer" },
  ];

  const renderedBadges = rawDecisionMakers
    .map((dm) => formatDecisionMaker(dm))
    .filter((label) => Boolean(label));

  assert.deepStrictEqual(renderedBadges, [
    "VP of Engineering · Engineering",
    "CTO",
    "Head of Infrastructure · Operations",
    "Sarah Connor (Chief Information Security Officer)",
  ]);
});
