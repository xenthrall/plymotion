import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, call, errorMessage, type Job, type Prefs } from "./client";
import { jobsStore } from "./jobs";

export const keys = {
  meta: ["meta"] as const,
  library: ["library"] as const,
  system: ["system-themes"] as const,
  loginLogo: ["login-logo"] as const,
  sequences: ["sequences"] as const,
  prefs: ["prefs"] as const,
};

export function useMeta() {
  return useQuery({ queryKey: keys.meta, queryFn: () => call(api.GET("/api/meta")) });
}

export function useLibrary() {
  return useQuery({ queryKey: keys.library, queryFn: () => call(api.GET("/api/library")) });
}

export function useInstalledThemes() {
  return useQuery({
    queryKey: keys.system,
    queryFn: () => call(api.GET("/api/system/themes")),
  });
}

export function useLoginLogo() {
  return useQuery({
    queryKey: keys.loginLogo,
    queryFn: () => call(api.GET("/api/login-logo")),
  });
}

export function useSequenceOutputs() {
  return useQuery({
    queryKey: keys.sequences,
    queryFn: () => call(api.GET("/api/sequences/outputs")),
  });
}

export function usePrefs() {
  return useQuery({
    queryKey: keys.prefs,
    queryFn: () => call(api.GET("/api/prefs")),
    staleTime: Infinity,
  });
}

export function useUpdatePrefs() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Partial<Prefs>) => call(api.PATCH("/api/prefs", { body: patch })),
    onMutate: (patch) => {
      const prev = qc.getQueryData<Prefs>(keys.prefs);
      if (prev) qc.setQueryData(keys.prefs, { ...prev, ...patch });
    },
    onSuccess: (prefs) => qc.setQueryData(keys.prefs, prefs),
  });
}

/**
 * Wrap a request that answers 202 with a job: registers the job in the live
 * store right away and toasts refusals (e.g. 409 while another pkexec action runs).
 */
export function useJobMutation<TVars>(start: (vars: TVars) => Promise<{ job: Job }>) {
  return useMutation({
    mutationFn: async (vars: TVars) => {
      const { job } = await start(vars);
      jobsStore.add(job);
      return job;
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
}

export async function pickFiles(kind: "video" | "image" | "images"): Promise<string[] | null> {
  try {
    const { paths } = await call(api.POST("/api/dialogs/pick", { body: { kind } }));
    return paths;
  } catch (error) {
    toast.error(errorMessage(error));
    return null;
  }
}
