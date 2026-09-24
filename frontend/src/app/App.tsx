import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import { KeyRound } from "lucide-react";
import { useEffect, useState } from "react";
import { createBrowserRouter, RouterProvider } from "react-router";
import { toast, Toaster } from "sonner";
import { setUnauthorizedHandler } from "@/api/client";
import { jobsStore } from "@/api/jobs";
import { keys, usePrefs } from "@/api/queries";
import { ConfirmProvider } from "@/components/confirm";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ConvertPage } from "@/pages/convert";
import { GalleryPage } from "@/pages/gallery";
import { HomePage } from "@/pages/home";
import { LoginLogoPage } from "@/pages/login-logo";
import { SequencesPage } from "@/pages/sequences";
import { SystemPage } from "@/pages/system";
import { Layout } from "./layout";
import { useApplyTheme } from "./theme";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: true, staleTime: 5_000 },
  },
});

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/crear", element: <ConvertPage /> },
      { path: "/galeria", element: <GalleryPage /> },
      { path: "/sistema", element: <SystemPage /> },
      { path: "/login", element: <LoginLogoPage /> },
      { path: "/secuencias", element: <SequencesPage /> },
      { path: "*", element: <HomePage /> },
    ],
  },
]);

// Which cached data a finished job makes stale.
const INVALIDATES: Record<string, (readonly string[])[]> = {
  convert: [keys.library],
  install: [keys.library, keys.system, keys.meta],
  activate: [keys.system, keys.meta, keys.library],
  uninstall: [keys.system, keys.meta, keys.library],
  "restore-backup": [keys.system, keys.meta],
  "reset-text": [keys.system, keys.meta],
  "login-logo": [keys.loginLogo],
  "login-logo-restore": [keys.loginLogo],
  sequence: [keys.sequences],
};

function JobsBridge() {
  const qc = useQueryClient();
  useEffect(() => {
    jobsStore.connect();
    return jobsStore.onFinish((job) => {
      for (const key of INVALIDATES[job.kind] ?? []) qc.invalidateQueries({ queryKey: key });
      qc.invalidateQueries({ queryKey: keys.meta });
      if (job.state === "succeeded") toast.success(job.title, { description: "Completado" });
      else if (job.state === "failed")
        toast.error(job.title, { description: job.error ?? "Falló", duration: 10_000 });
      else toast(job.title, { description: "Cancelado" });
    });
  }, [qc]);
  return null;
}

function Themed({ children }: { children: React.ReactNode }) {
  useApplyTheme();
  const { data: prefs } = usePrefs();
  const mode = prefs?.theme ?? "system";
  return (
    <>
      {children}
      <Toaster
        theme={mode}
        position="bottom-right"
        toastOptions={{ className: "!rounded-xl !border-border !bg-popover !text-foreground" }}
      />
    </>
  );
}

function Unauthorized() {
  return (
    <div className="grid h-full place-items-center p-8">
      <div className="max-w-sm text-center">
        <div className="mx-auto mb-4 grid size-12 place-items-center rounded-xl bg-primary-soft text-primary">
          <KeyRound className="size-6" />
        </div>
        <h1 className="text-lg font-semibold">Sesión expirada</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Por seguridad, cada arranque de Plymotion usa una clave nueva. Cierra esta ventana y
          vuelve a abrir Plymotion.
        </p>
      </div>
    </div>
  );
}

export function App() {
  const [unauthorized, setUnauthorized] = useState(false);
  useEffect(() => setUnauthorizedHandler(() => setUnauthorized(true)), []);

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={300}>
        <ConfirmProvider>
          <Themed>
            {unauthorized ? (
              <Unauthorized />
            ) : (
              <>
                <JobsBridge />
                <RouterProvider router={router} />
              </>
            )}
          </Themed>
        </ConfirmProvider>
      </TooltipProvider>
    </QueryClientProvider>
  );
}
