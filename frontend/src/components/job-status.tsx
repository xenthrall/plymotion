import { CheckCircle2, CircleX, Loader2, Ban } from "lucide-react";
import { useEffect, useRef } from "react";
import type { Job } from "@/api/client";
import { useJobLogs } from "@/api/jobs";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

export function JobStateIcon({ job, className }: { job: Job; className?: string }) {
  const cls = cn("size-4 shrink-0", className);
  switch (job.state) {
    case "running":
      return <Loader2 className={cn(cls, "animate-spin text-primary")} />;
    case "succeeded":
      return <CheckCircle2 className={cn(cls, "text-success")} />;
    case "failed":
      return <CircleX className={cn(cls, "text-destructive")} />;
    default:
      return <Ban className={cn(cls, "text-muted-foreground")} />;
  }
}

export function JobProgress({ job }: { job: Job }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3 text-[13px]">
        <span className="flex min-w-0 items-center gap-2">
          <JobStateIcon job={job} />
          <span className="truncate">{job.error ?? job.stage ?? "En cola"}</span>
        </span>
        {job.state === "running" && job.progress !== null && (
          <span className="font-mono text-xs text-muted-foreground tabular-nums">
            {Math.round(job.progress)}%
          </span>
        )}
      </div>
      {job.state === "running" && <Progress value={job.progress} />}
    </div>
  );
}

export function JobLog({ jobId, className }: { jobId: string; className?: string }) {
  const lines = useJobLogs(jobId);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight });
  }, [lines.length]);
  if (lines.length === 0) return null;
  return (
    <div
      ref={ref}
      className={cn(
        "max-h-40 overflow-y-auto rounded-lg bg-stage p-3 font-mono text-[11.5px] leading-relaxed text-white/70",
        className,
      )}
    >
      {lines.map((line, i) => (
        <div key={i} className={cn(line.startsWith("ERROR") && "text-red-400")}>
          <span className="mr-2 text-white/25 select-none">›</span>
          {line}
        </div>
      ))}
    </div>
  );
}
