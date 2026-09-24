import { Activity, ChevronDown, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { useState } from "react";
import { api, call, errorMessage, type Job } from "@/api/client";
import { useJobsState } from "@/api/jobs";
import { JobLog, JobProgress } from "@/components/job-status";
import { Button } from "@/components/ui/button";
import { cn, formatRelative } from "@/lib/utils";
import { toast } from "sonner";

function JobRow({ job }: { job: Job }) {
  const [open, setOpen] = useState(job.state === "running");
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="flex items-start justify-between gap-2">
        <button
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
          onClick={() => setOpen((o) => !o)}
        >
          <ChevronDown
            className={cn(
              "size-3.5 shrink-0 text-muted-foreground transition-transform",
              !open && "-rotate-90",
            )}
          />
          <span className="truncate text-sm font-medium">{job.title}</span>
        </button>
        <span className="shrink-0 text-[11px] text-muted-foreground">
          {formatRelative(job.created_at)}
        </span>
      </div>
      <div className="mt-2 pl-5">
        <JobProgress job={job} />
        {open && <JobLog jobId={job.id} className="mt-2" />}
        {job.cancellable && (
          <Button
            variant="destructive-ghost"
            size="sm"
            className="mt-2 -ml-2"
            onClick={() =>
              call(api.DELETE("/api/jobs/{job_id}", { params: { path: { job_id: job.id } } })).catch(
                (e) => toast.error(errorMessage(e)),
              )
            }
          >
            Cancelar
          </Button>
        )}
      </div>
    </div>
  );
}

export function ActivityButton() {
  const { jobs, connected } = useJobsState();
  const running = jobs.filter((j) => j.state === "running").length;
  return (
    <DialogPrimitive.Root>
      <DialogPrimitive.Trigger asChild>
        <Button variant="ghost" size="sm" className="relative gap-2">
          <Activity className={cn(running > 0 && "text-primary")} />
          <span className="hidden sm:inline">Actividad</span>
          {running > 0 && (
            <span className="grid size-4.5 place-items-center rounded-full bg-primary text-[10px] font-semibold text-primary-foreground">
              {running}
            </span>
          )}
          {!connected && <span className="size-1.5 rounded-full bg-warning" title="Reconectando" />}
        </Button>
      </DialogPrimitive.Trigger>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40 data-[state=open]:animate-[fade-in_150ms]" />
        <DialogPrimitive.Content className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l bg-background shadow-2xl outline-none data-[state=open]:animate-[sheet-in_220ms_cubic-bezier(0.2,0.9,0.3,1)]">
          <div className="flex items-center justify-between border-b px-5 py-4">
            <div>
              <DialogPrimitive.Title className="font-semibold">Actividad</DialogPrimitive.Title>
              <DialogPrimitive.Description className="text-xs text-muted-foreground">
                Tareas de esta sesión, en vivo.
              </DialogPrimitive.Description>
            </div>
            <DialogPrimitive.Close asChild>
              <Button variant="ghost" size="icon-sm" aria-label="Cerrar">
                <X />
              </Button>
            </DialogPrimitive.Close>
          </div>
          <div className="flex-1 space-y-2 overflow-y-auto p-4">
            <AnimatePresence initial={false}>
              {jobs.map((job) => (
                <motion.div
                  key={job.id}
                  layout
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <JobRow job={job} />
                </motion.div>
              ))}
            </AnimatePresence>
            {jobs.length === 0 && (
              <p className="py-12 text-center text-sm text-muted-foreground">
                Aún no hay tareas en esta sesión.
              </p>
            )}
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
