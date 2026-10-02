import { useState } from "react";
import type { SubmitEvent } from "react";

interface CommentFormProps {
  onSubmit: (text: string) => Promise<unknown>;
  placeholder?: string;
}

const MAX_LENGTH = 2000;

export function CommentForm({ onSubmit, placeholder = "Share your take…" }: CommentFormProps) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmed = text.trim();

  // `FormEvent` is deprecated in the React 19 types ("it doesn't actually exist");
  // a form submit is a `SubmitEvent`, which is also what the `onSubmit` prop uses.
  async function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!trimmed || busy) return;

    setBusy(true);
    setError(null);
    try {
      await onSubmit(trimmed);
      setText("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not post the comment.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <label htmlFor="comment" className="sr-only">
        Your comment
      </label>
      <textarea
        id="comment"
        value={text}
        maxLength={MAX_LENGTH}
        onChange={(event) => setText(event.target.value)}
        placeholder={placeholder}
        rows={3}
        className="w-full resize-y rounded-lg border border-line bg-surface px-3 py-2 text-sm placeholder:text-muted focus:border-accent focus:outline-none"
      />
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs text-muted">
          {trimmed.length}/{MAX_LENGTH}
        </span>
        <button
          type="submit"
          disabled={!trimmed || busy}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-soft disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? "Posting…" : "Post comment"}
        </button>
      </div>
      {error ? (
        <p role="alert" className="text-xs text-red-700 dark:text-red-300">
          {error}
        </p>
      ) : null}
    </form>
  );
}
