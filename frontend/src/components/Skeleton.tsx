interface SkeletonProps {
  /** Number of placeholder lines. Widths cycle so the block does not look uniform. */
  lines?: number;
  testId?: string;
}

const WIDTHS = ["100%", "92%", "64%"];

/**
 * Loading placeholder for generated text.
 *
 * Marked `aria-hidden`: it is decoration, and announcing placeholder lines to a
 * screen reader would be noise. The real feedback is the `role="status"` label
 * next to it plus the `aria-live` region that receives the answer.
 */
export function Skeleton({ lines = 3, testId = "skeleton" }: SkeletonProps) {
  return (
    <div className="space-y-2" data-testid={testId} aria-hidden="true">
      {Array.from({ length: lines }, (_, index) => (
        <div
          key={index}
          className="relative h-3 overflow-hidden rounded-full bg-overlay"
          style={{ width: WIDTHS[index % WIDTHS.length] }}
        >
          <span className="animate-shimmer absolute inset-0 bg-gradient-to-r from-transparent via-ink/15 to-transparent" />
        </div>
      ))}
    </div>
  );
}
