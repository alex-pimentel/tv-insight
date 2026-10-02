interface SpinnerProps {
  label?: string;
  /** `sm` fits inside a button; `md` is the page level indicator. */
  size?: "sm" | "md";
  /** `onAccent` inverts the ring so it stays visible on the accent button. */
  tone?: "default" | "onAccent";
}

const RING_BY_TONE = {
  default: "border-line border-t-accent",
  onAccent: "border-white/30 border-t-white",
} as const;

export function Spinner({
  label = "Loading",
  size = "md",
  tone = "default",
}: SpinnerProps) {
  const box = size === "sm" ? "h-3.5 w-3.5" : "h-4 w-4";

  return (
    <span className="inline-flex items-center gap-2" role="status">
      <span
        aria-hidden="true"
        className={`animate-spin rounded-full border-2 ${box} ${RING_BY_TONE[tone]}`}
      />
      <span className={size === "sm" ? "text-xs" : "text-sm"}>{label}</span>
    </span>
  );
}
