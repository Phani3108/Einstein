/**
 * Tier 0 — On-device regex extraction.
 *
 * Runs immediately on captured events BEFORE sync.
 * Extracts: person names, dates, phone numbers, monetary amounts, emails.
 * Lightweight — no ML, no network, pure regex.
 */

// ---- Name Extraction ----
// Matches capitalized word pairs: "Alice Smith", "Dr. Jones"
const NAME_PATTERN =
  /(?:(?:Dr|Mr|Mrs|Ms|Prof)\.?\s+)?([A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){0,2})/g;

// Common false positives to filter out
const NAME_BLOCKLIST = new Set([
  "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
  "The", "This", "That", "These", "Those", "What", "When", "Where", "Which",
  "Google", "Apple", "Amazon", "Microsoft", "Facebook", "Instagram",
  "WhatsApp", "Telegram", "Signal", "Slack", "Discord",
  "New York", "San Francisco", "Los Angeles",
  "Good Morning", "Happy Birthday", "Thank You",
]);

// ---- Date Extraction ----
const DATE_PATTERNS = [
  // "tomorrow", "today", "yesterday"
  /\b(today|tomorrow|yesterday)\b/gi,
  // "next Monday", "last Friday"
  /\b(next|last|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b/gi,
  // "Jan 15", "March 3rd"
  /\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?\b/gi,
  // "2024-01-15", "01/15/2024"
  /\b\d{4}-\d{2}-\d{2}\b/g,
  /\b\d{1,2}\/\d{1,2}\/\d{2,4}\b/g,
  // "in 3 days", "2 weeks from now"
  /\bin\s+\d+\s+(?:day|week|month|hour)s?\b/gi,
];

// ---- Amount Extraction ----
const AMOUNT_PATTERN =
  /(?:\$|USD|EUR|GBP|INR|Rs\.?|₹|€|£)\s?\d[\d,]*(?:\.\d{1,2})?|\b\d[\d,]*(?:\.\d{1,2})?\s*(?:dollars?|USD|EUR|rupees?|INR)\b/gi;

// ---- Phone Number ----
const PHONE_PATTERN =
  /(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}\b/g;

// ---- Email ----
const EMAIL_PATTERN = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;

// ---- Public API ----

export interface Tier0Result {
  extracted_people: string[];
  dates: string[];
  amounts: string[];
  phones: string[];
  emails: string[];
}

/**
 * Run all Tier 0 extractors on raw text.
 * Returns structured data to attach to a ContextEvent.
 */
export function extractTier0(text: string): Tier0Result {
  if (!text || text.length < 3) {
    return { extracted_people: [], dates: [], amounts: [], phones: [], emails: [] };
  }

  return {
    extracted_people: extractNames(text),
    dates: extractDates(text),
    amounts: extractAmounts(text),
    phones: extractPhones(text),
    emails: extractEmails(text),
  };
}

function extractNames(text: string): string[] {
  const matches: string[] = [];
  let m: RegExpExecArray | null;

  // Reset regex state
  NAME_PATTERN.lastIndex = 0;
  while ((m = NAME_PATTERN.exec(text)) !== null) {
    const name = m[0].trim();
    // At least 2 chars, not in blocklist
    if (name.length >= 2 && !NAME_BLOCKLIST.has(name) && !NAME_BLOCKLIST.has(name.split(" ")[0])) {
      matches.push(name);
    }
  }

  return [...new Set(matches)];
}

function extractDates(text: string): string[] {
  const results: string[] = [];
  for (const pattern of DATE_PATTERNS) {
    pattern.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = pattern.exec(text)) !== null) {
      results.push(m[0].trim());
    }
  }
  return [...new Set(results)];
}

function extractAmounts(text: string): string[] {
  AMOUNT_PATTERN.lastIndex = 0;
  const matches = text.match(AMOUNT_PATTERN);
  return matches ? [...new Set(matches.map((a) => a.trim()))] : [];
}

function extractPhones(text: string): string[] {
  PHONE_PATTERN.lastIndex = 0;
  const matches = text.match(PHONE_PATTERN);
  // Filter out numbers that are too short (likely not phone numbers)
  return matches
    ? [...new Set(matches.map((p) => p.trim()).filter((p) => p.replace(/\D/g, "").length >= 7))]
    : [];
}

function extractEmails(text: string): string[] {
  EMAIL_PATTERN.lastIndex = 0;
  const matches = text.match(EMAIL_PATTERN);
  return matches ? [...new Set(matches.map((e) => e.toLowerCase().trim()))] : [];
}
