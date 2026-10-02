import type { Comment } from "../api/types";

interface CommentListProps {
  comments: Comment[];
  emptyMessage?: string;
}

function formatDate(iso: string): string {
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? iso : parsed.toLocaleString();
}

export function CommentList({ comments, emptyMessage = "No comments yet." }: CommentListProps) {
  if (comments.length === 0) {
    return (
      <p className="text-sm text-muted" data-testid="comments-empty">
        {emptyMessage}
      </p>
    );
  }

  return (
    <ul className="space-y-3" data-testid="comment-list">
      {comments.map((comment) => (
        <li
          key={comment.id}
          data-testid="comment-item"
          className="rounded-lg border border-line bg-card p-3"
        >
          <p className="text-sm">{comment.text}</p>
          <p className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-muted">
            {comment.mine ? (
              <span className="rounded-full bg-accent/20 px-2 py-0.5 text-accent-soft">you</span>
            ) : null}
            {comment.episode_code ? <span>{comment.episode_code}</span> : null}
            <time dateTime={comment.created_at}>{formatDate(comment.created_at)}</time>
          </p>
        </li>
      ))}
    </ul>
  );
}
