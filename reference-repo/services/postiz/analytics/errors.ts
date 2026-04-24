export type AnalyticsErrorCode =
  | "not_found"
  | "upstream_unavailable";

export class AnalyticsServiceError extends Error {
  constructor(
    public readonly code: AnalyticsErrorCode,
    message: string,
    public readonly cause?: unknown
  ) {
    super(message);
    this.name = "AnalyticsServiceError";
  }
}

export function isAnalyticsServiceError(
  error: unknown
): error is AnalyticsServiceError {
  return error instanceof AnalyticsServiceError;
}
