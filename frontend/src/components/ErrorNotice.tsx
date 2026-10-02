import { ApiError } from "../api/client";

interface ErrorNoticeProps {
  error: unknown;
  onRetry?: () => void;
}

const FRIENDLY: Record<string, string> = {
  ResourceNotFound: "We could not find that title in the catalogue.",
  InvalidInput: "That search is not valid. Try a longer query.",
  ExternalServiceError: "The TV catalogue is not answering right now.",
  ProviderUnavailable: "The insight service is unavailable. Everything else still works.",
};

/** Turns an `ApiError` code into something a human can act on. */
export function ErrorNotice({ error, onRetry }: ErrorNoticeProps) {
  const code = error instanceof ApiError ? error.code : "UnexpectedError";
  const detail = error instanceof Error ? error.message : String(error);

  return (
    <div
      role="alert"
      className="rounded-lg border border-red-500/40 bg-red-500/10 p-4 text-sm"
    >
      <p className="font-medium text-red-700 dark:text-red-200">{FRIENDLY[code] ?? "Something went wrong."}</p>
      <p className="mt-1 text-red-700/80 dark:text-red-700 dark:text-red-300/80">{detail}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-md border border-red-400/40 px-3 py-1 text-red-100 hover:bg-red-500/20"
        >
          Try again
        </button>
      ) : null}
    </div>
  );
}
