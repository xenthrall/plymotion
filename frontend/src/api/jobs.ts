import { useSyncExternalStore } from "react";
import type { Job } from "./client";

/**
 * Live job state from the server's single SSE stream (/api/events).
 *
 * The server sends a `snapshot` of every job on connect (and again after any
 * reconnect, so nothing is missed), then a `job` event on each state or
 * progress change and a `log` event per log line.
 */
type State = { jobs: Job[]; logs: Record<string, string[]>; connected: boolean };
type FinishListener = (job: Job) => void;

class JobsStore {
  private state: State = { jobs: [], logs: {}, connected: false };
  private listeners = new Set<() => void>();
  private finishListeners = new Set<FinishListener>();
  private source: EventSource | null = null;

  connect() {
    if (this.source) return;
    const source = new EventSource("/api/events");
    this.source = source;
    source.addEventListener("open", () => this.set({ connected: true }));
    source.addEventListener("error", () => this.set({ connected: false }));
    source.addEventListener("snapshot", (e) => {
      const { jobs } = JSON.parse((e as MessageEvent).data) as { jobs: Job[] };
      const logs: Record<string, string[]> = {};
      for (const job of jobs) logs[job.id] = this.state.logs[job.id] ?? job.log_tail;
      this.set({ jobs, logs, connected: true });
    });
    source.addEventListener("job", (e) => {
      const job = JSON.parse((e as MessageEvent).data) as Job;
      const prev = this.state.jobs.find((j) => j.id === job.id);
      const jobs = prev
        ? this.state.jobs.map((j) => (j.id === job.id ? job : j))
        : [job, ...this.state.jobs];
      this.set({ jobs });
      if (job.state !== "running" && prev?.state !== job.state) {
        this.finishListeners.forEach((listener) => listener(job));
      }
    });
    source.addEventListener("log", (e) => {
      const { job_id, line } = JSON.parse((e as MessageEvent).data) as {
        job_id: string;
        line: string;
      };
      const lines = [...(this.state.logs[job_id] ?? []), line].slice(-500);
      this.set({ logs: { ...this.state.logs, [job_id]: lines } });
    });
  }

  private set(patch: Partial<State>) {
    this.state = { ...this.state, ...patch };
    this.listeners.forEach((listener) => listener());
  }

  /** Make a job submitted by this client visible before its first SSE event arrives. */
  add(job: Job) {
    if (!this.state.jobs.some((j) => j.id === job.id)) this.set({ jobs: [job, ...this.state.jobs] });
  }

  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  onFinish(listener: FinishListener) {
    this.finishListeners.add(listener);
    return () => {
      this.finishListeners.delete(listener);
    };
  }

  getState = () => this.state;
}

export const jobsStore = new JobsStore();

/** Job kinds that run through pkexec; the server allows only one at a time ("system" lock). */
export const SYSTEM_JOB_KINDS = new Set([
  "install",
  "activate",
  "uninstall",
  "restore-backup",
  "reset-text",
  "preview",
  "login-logo",
  "login-logo-restore",
]);

export function useJobsState(): State {
  return useSyncExternalStore(jobsStore.subscribe, jobsStore.getState);
}

export function useJob(id: string | null | undefined): Job | undefined {
  const { jobs } = useJobsState();
  return id ? jobs.find((j) => j.id === id) : undefined;
}

export function useJobLogs(id: string | null | undefined): string[] {
  const { logs } = useJobsState();
  return (id && logs[id]) || [];
}

/** The running job holding the server's "system" (pkexec) lock, if any. */
export function useRunningJobs(): Job[] {
  return useJobsState().jobs.filter((j) => j.state === "running");
}
