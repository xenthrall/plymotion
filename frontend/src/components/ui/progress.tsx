import { cn } from "@/lib/utils";

/** `value` null = indeterminate (e.g. waiting on the pkexec password prompt). */
export function Progress({ value, className }: { value: number | null; className?: string }) {
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value ?? undefined}
      className={cn("relative h-1.5 w-full overflow-hidden rounded-full bg-muted", className)}
    >
      {value === null ? (
        <div className="absolute inset-y-0 w-full origin-left animate-indeterminate rounded-full bg-primary" />
      ) : (
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-300 ease-out"
          style={{ width: `${Math.max(0, Math.min(value, 100))}%` }}
        />
      )}
    </div>
  );
}
