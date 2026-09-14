import { isProblemDetails } from "../types/problemDetails";

export function getErrorMessage(error: unknown): string {
  if (isProblemDetails(error)) {
    if (error.invalid_params && error.invalid_params.length > 0) {
      const details = error.invalid_params.map((p) => `${p.name}: ${p.reason}`).join(", ");
      return `${error.title} (${details})`;
    }
    return error.detail || error.title;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "予期せぬエラーが発生しました";
}
