interface ProgressBarProps {
  value: number;
  label: string;
  className?: string;
}

/** Accessible progress bar used for whole-series and per-season progress. */
export function ProgressBar({ value, label, className = "" }: ProgressBarProps) {
  const percent = Math.round(Math.min(Math.max(value, 0), 1) * 100);

  return (
    <div className={className}>
      <div
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        className="h-2 w-full overflow-hidden rounded-full bg-card-hover"
      >
        <div
          className="h-full rounded-full bg-accent transition-[width] duration-300"
          style={{ width: `${percent}%` }}
        />
      </div>
      <p className="mt-1 text-xs text-muted">{percent}% watched</p>
    </div>
  );
}
