export type SemanticRole = "identifier" | "measure" | "timestamp" | "category" | "free_text" | "unknown";
export type ReviewPriority = "routine" | "inspect" | "resolve";

export interface TypedDecision<T extends string> {
  label: T;
  confidence: number;
  probabilities: Record<T, number>;
}

export interface LayaCsvReview {
  schema_version: "1.0";
  generated_at: string;
  source: { name: string; profile_schema_version: string; aggregate_sha256: string };
  engine: { name: "Laya"; runtime: string; model: string };
  policy: { mode: "shadow"; confidence_threshold: number; low_confidence_action: "review" };
  privacy: { raw_values_sent: false; input: string };
  columns: Array<{
    index: number;
    name: string;
    semantic_role: TypedDecision<SemanticRole>;
    review_priority: TypedDecision<ReviewPriority>;
    gate: "accepted" | "review";
  }>;
}
