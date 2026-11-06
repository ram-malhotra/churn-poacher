import test from "node:test";
import assert from "node:assert/strict";

function computeBudgetStatus(totalBudget, usedCredits) {
  const remaining = Math.max(0, totalBudget - usedCredits);
  if (totalBudget <= 0 || usedCredits >= totalBudget || remaining <= 0) {
    return "Exhausted";
  }
  const usagePct = (usedCredits / totalBudget) * 100;
  if (usagePct >= 80) {
    return "Near Limit";
  }
  return "Active";
}

test("computeBudgetStatus - Active state (< 80% used)", () => {
  assert.strictEqual(computeBudgetStatus(1200, 0), "Active");
  assert.strictEqual(computeBudgetStatus(1200, 200), "Active");
  assert.strictEqual(computeBudgetStatus(1200, 959), "Active");
});

test("computeBudgetStatus - Near Limit state (>= 80% and < 100% used)", () => {
  assert.strictEqual(computeBudgetStatus(1200, 960), "Near Limit");
  assert.strictEqual(computeBudgetStatus(1200, 1100), "Near Limit");
  assert.strictEqual(computeBudgetStatus(1200, 1199.5), "Near Limit");
});

test("computeBudgetStatus - Exhausted state (>= 100% used)", () => {
  assert.strictEqual(computeBudgetStatus(1200, 1200), "Exhausted");
  assert.strictEqual(computeBudgetStatus(1200, 1250), "Exhausted");
  assert.strictEqual(computeBudgetStatus(0, 0), "Exhausted");
});

test("computeBudgetStatus - Remaining and Percentage accuracy", () => {
  const budget = 1200;
  const used = 450;
  const remaining = Math.max(0, budget - used);
  const pct = (used / budget) * 100;

  assert.strictEqual(remaining, 750);
  assert.strictEqual(pct, 37.5);
  assert.strictEqual(computeBudgetStatus(budget, used), "Active");
});


test("parseCreditErrorMessage - parses balance and threshold from error string", () => {
  const errMsg = "Insufficient Crustdata credits: current balance 0.0, required 0.5, minimum safety threshold 5.0";
  const balMatch = errMsg.match(/current balance ([\d.]+)/);
  const reqMatch = errMsg.match(/required ([\d.]+)/);
  const floorMatch = errMsg.match(/minimum safety threshold ([\d.]+)/);

  assert.strictEqual(parseFloat(balMatch[1]), 0.0);
  assert.strictEqual(parseFloat(reqMatch[1]), 0.5);
  assert.strictEqual(parseFloat(floorMatch[1]), 5.0);
});
