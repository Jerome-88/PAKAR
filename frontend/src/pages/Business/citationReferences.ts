import type { ChatTurn } from "../../api/business";
import { readableText } from "./resultSummary";

type Citation = NonNullable<NonNullable<ChatTurn["response"]>["citations"]>[number];

// Replace only explicit, fully resolved source lists. Keep unmatched model text intact.
export function citationText(value: unknown, citations: Citation[], prefix: string) {
  return readableText(value).replace(/\(sumber:\s*([^()]+)\)/gi, (original, ids: string) => {
    const matches = ids.split(",").map(id => {
      const source = id.trim();
      const exact = citations.findIndex(c => c.id === source);
      if (exact >= 0) return exact;
      const documentMatches = citations.flatMap((c, index) => c.document_id === source ? [index] : []);
      return documentMatches.length === 1 ? documentMatches[0] : -1;
    });
    if (matches.some(index => index < 0)) return original;
    return [...new Set(matches)].map(index => `[\\[${index + 1}\\]](#${prefix}-${index + 1})`).join(" ");
  });
}
