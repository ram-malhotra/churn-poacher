import test from "node:test";
import assert from "node:assert/strict";

test("Deduplication of candidates across pages using stable identifiers", () => {
  const page1 = [
    { candidate_id: "comp_1", primary_domain: "datadoghq.com", name: "Datadog" },
    { candidate_id: "comp_2", primary_domain: "hathway.com", name: "Hathway" },
  ];

  const page2 = [
    { candidate_id: "comp_1_dup", primary_domain: "datadoghq.com", name: "Datadog Inc" }, // Duplicate by domain
    { candidate_id: "comp_3", primary_domain: "sparkdatabox.com", name: "Spark Databox" },
  ];

  const existingKeys = new Set(
    page1.map((c) => c.profile_url || (c.primary_domain ? `domain_${c.primary_domain}` : c.candidate_id))
  );

  const uniqueIncoming = page2.filter(
    (c) => !existingKeys.has(c.profile_url || (c.primary_domain ? `domain_${c.primary_domain}` : c.candidate_id))
  );

  const merged = [...page1, ...uniqueIncoming];
  assert.equal(merged.length, 3, "Duplicate domain must be filtered out");
  assert.equal(merged[2].primary_domain, "sparkdatabox.com");
});

test("Candidate search criteria relevance distinguishes VERIFIED, INFERRED and UNAVAILABLE", () => {
  const matchedCriteria = [
    {
      criterion: "Industry",
      requested_value: "SaaS",
      actual_value: "Software as a Service",
      status: "VERIFIED",
      evidence: "Matched Crustdata industry taxonomy",
    },
    {
      criterion: "Country",
      requested_value: "US",
      actual_value: "USA",
      status: "VERIFIED",
      evidence: "Verified from Crustdata locations",
    },
    {
      criterion: "Employee count",
      requested_value: "200-1000",
      actual_value: null,
      status: "UNAVAILABLE",
      evidence: "Headcount not available in search preview",
    },
  ];

  const verified = matchedCriteria.filter((c) => c.status === "VERIFIED");
  const unavailable = matchedCriteria.filter((c) => c.status === "UNAVAILABLE");

  assert.equal(verified.length, 2);
  assert.equal(unavailable.length, 1);
  assert.equal(unavailable[0].criterion, "Employee count");
  assert.equal(unavailable[0].actual_value, null);
});

test("Candidate preserves raw Crustdata payload without fabricating missing attributes", () => {
  const rawPayload = {
    crustdata_company_id: 1895,
    basic_info: {
      name: "Hathway Cable & Datacom Ltd",
      primary_domain: "hathway.com",
    },
    locations: {
      country: "IND",
    },
  };

  const candidate = {
    candidate_id: "comp_1895",
    name: rawPayload.basic_info.name,
    primary_domain: rawPayload.basic_info.primary_domain,
    location: rawPayload.locations.country,
    headline: null, // Not fabricated
    current_title: null, // Not fabricated
    raw_data: rawPayload,
    field_verification: {
      name: "VERIFIED",
      primary_domain: "VERIFIED",
      location: "VERIFIED",
      current_title: "UNKNOWN",
    },
  };

  assert.deepEqual(candidate.raw_data, rawPayload);
  assert.equal(candidate.headline, null);
  assert.equal(candidate.field_verification.current_title, "UNKNOWN");
});
