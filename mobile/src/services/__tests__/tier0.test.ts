/**
 * Tests for Tier 0 on-device extraction.
 */
import { extractTier0 } from "../tier0";

describe("extractTier0", () => {
  // ---- Empty / edge cases ----

  it("returns empty for empty string", () => {
    const result = extractTier0("");
    expect(result.extracted_people).toEqual([]);
    expect(result.dates).toEqual([]);
    expect(result.amounts).toEqual([]);
    expect(result.phones).toEqual([]);
    expect(result.emails).toEqual([]);
  });

  it("returns empty for very short string", () => {
    const result = extractTier0("hi");
    expect(result.extracted_people).toEqual([]);
  });

  // ---- Name extraction ----

  it("extracts single capitalized name", () => {
    const result = extractTier0("Meeting with Alice tomorrow");
    expect(result.extracted_people).toContain("Alice");
  });

  it("extracts full name", () => {
    const result = extractTier0("Call from John Smith about the project");
    expect(result.extracted_people).toContain("John Smith");
  });

  it("extracts multiple names", () => {
    const result = extractTier0("Alice met Bob and Charlie for coffee");
    expect(result.extracted_people).toContain("Alice");
    expect(result.extracted_people).toContain("Bob");
    expect(result.extracted_people).toContain("Charlie");
  });

  it("filters out day names", () => {
    const result = extractTier0("Meeting on Monday and Tuesday");
    expect(result.extracted_people).not.toContain("Monday");
    expect(result.extracted_people).not.toContain("Tuesday");
  });

  it("filters out month names", () => {
    const result = extractTier0("Due in January or February");
    expect(result.extracted_people).not.toContain("January");
    expect(result.extracted_people).not.toContain("February");
  });

  it("deduplicates names", () => {
    const result = extractTier0("Alice talked to Alice again");
    const aliceCount = result.extracted_people.filter((n) => n === "Alice").length;
    expect(aliceCount).toBe(1);
  });

  // ---- Date extraction ----

  it("extracts relative dates", () => {
    const result = extractTier0("I'll do it tomorrow");
    expect(result.dates).toContain("tomorrow");
  });

  it("extracts 'next Monday' style dates", () => {
    const result = extractTier0("Let's meet next Friday");
    expect(result.dates.some((d) => d.toLowerCase().includes("friday"))).toBe(true);
  });

  it("extracts ISO dates", () => {
    const result = extractTier0("Deadline is 2024-03-15");
    expect(result.dates).toContain("2024-03-15");
  });

  it("extracts month-day dates", () => {
    const result = extractTier0("The event is on Jan 15");
    expect(result.dates.some((d) => d.includes("Jan"))).toBe(true);
  });

  it("extracts 'in N days' patterns", () => {
    const result = extractTier0("Ship this in 3 days");
    expect(result.dates.some((d) => d.includes("3 days"))).toBe(true);
  });

  // ---- Amount extraction ----

  it("extracts dollar amounts", () => {
    const result = extractTier0("The project costs $15,000");
    expect(result.amounts.length).toBeGreaterThan(0);
    expect(result.amounts[0]).toContain("15,000");
  });

  it("extracts amounts with currency words", () => {
    const result = extractTier0("Budget is 5000 dollars");
    expect(result.amounts.length).toBeGreaterThan(0);
  });

  it("extracts rupee amounts", () => {
    const result = extractTier0("Price is ₹2,500");
    expect(result.amounts.length).toBeGreaterThan(0);
  });

  // ---- Phone extraction ----

  it("extracts phone numbers", () => {
    const result = extractTier0("Call me at 555-123-4567");
    expect(result.phones.length).toBeGreaterThan(0);
  });

  it("extracts international phone numbers", () => {
    const result = extractTier0("Her number is +1 555 123 4567");
    expect(result.phones.length).toBeGreaterThan(0);
  });

  it("ignores short number sequences", () => {
    const result = extractTier0("We had 42 items");
    expect(result.phones).toEqual([]);
  });

  // ---- Email extraction ----

  it("extracts email addresses", () => {
    const result = extractTier0("Send it to alice@example.com");
    expect(result.emails).toContain("alice@example.com");
  });

  it("lowercases extracted emails", () => {
    const result = extractTier0("Email: Alice@Example.COM");
    expect(result.emails).toContain("alice@example.com");
  });

  // ---- Combined extraction ----

  it("extracts multiple entity types from one text", () => {
    const result = extractTier0(
      "Call Alice Smith at 555-123-4567 tomorrow about the $5,000 budget. Email alice@acme.com"
    );
    expect(result.extracted_people.length).toBeGreaterThan(0);
    expect(result.dates).toContain("tomorrow");
    expect(result.amounts.length).toBeGreaterThan(0);
    expect(result.phones.length).toBeGreaterThan(0);
    expect(result.emails).toContain("alice@acme.com");
  });
});
