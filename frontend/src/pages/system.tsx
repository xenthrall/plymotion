import {
  ArchiveRestore,
  CheckCircle2,
  LifeBuoy,
  MonitorPlay,
  MoreHorizontal,
  Play,
  Power,
  ShieldCheck,
  Sparkles,
  Trash2,
  Type,
} from "lucide-react";
import { useState } from "react";
import { api, call, type InstalledTheme } from "@/api/client";
import { SYSTEM_JOB_KINDS, useRunningJobs } from "@/api/jobs";
import { useInstalledThemes, useJobMutation } from "@/api/queries";
import { BootSimulator } from "@/components/boot-simulator";
import { useConfirm } from "@/components/confirm";
import { JobProgress } from "@/components/job-status";
import { Page, PageHeader } from "@/components/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

function ThemeRow({
  theme,
  busy,
  onSimulate,
}: {
  theme: InstalledTheme;
  busy: boolean;
  onSimulate: () => void;
}) {
  const confirm = useConfirm();
  const path = { params: { path: { dir_name: theme.dir_name } } };
  const activate = useJobMutation(() =>
    call(api.POST("/api/system/themes/{dir_name}/activate", path)),
  );
  const uninstall = useJobMutation(() => call(api.DELETE("/api/system/themes/{dir_name}", path)));
  const restore = useJobMutation(() =>
    call(api.POST("/api/system/restore-backup", { body: { theme: theme.dir_name } })),
  );
  const isText = theme.dir_name === "text";

  return (
    <div
      className={cn(
        "flex items-center gap-4 rounded-xl border bg-card p-3 pr-4 transition-colors",
        theme.is_default && "border-primary/40 bg-primary-soft/40",
      )}
    >
      <button
        className="relative grid h-16 w-28 shrink-0 place-items-center overflow-hidden rounded-lg bg-stage disabled:cursor-default"
        onClick={onSimulate}
        disabled={!theme.frame_url_template}
        aria-label={`Simular ${theme.name}`}
      >
        {theme.thumbnail_url ? (
          <img src={theme.thumbnail_url} alt="" className="size-full object-contain p-1.5" />
        ) : isText ? (
          <Type className="size-5 text-white/40" />
        ) : (
          <MonitorPlay className="size-5 text-white/40" />
        )}
      </button>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium">{theme.name}</span>
          {theme.is_default && (
            <Badge variant="success">
              <CheckCircle2 /> Activo
            </Badge>
          )}
          {theme.is_plymotion && <Badge>Plymotion</Badge>}
          {theme.has_backup && <Badge variant="outline">Backup</Badge>}
          {theme.is_plymotion && theme.watermark_url && <Badge variant="secondary">Logo</Badge>}
        </div>
        <p className="mt-0.5 truncate text-xs text-muted-foreground">
          {theme.description || theme.dir_name}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-1">
        {!theme.is_default && (
          <Button
            size="sm"
            variant="secondary"
            disabled={busy}
            onClick={async () => {
              const ok = await confirm({
                title: `Activar «${theme.name}»`,
                description:
                  "Pasa a ser la animación de arranque y se regenera el initramfs (tarda unos segundos).",
                confirmLabel: "Activar",
                privileged: true,
              });
              if (ok) activate.mutate(undefined);
            }}
          >
            <Power /> Activar
          </Button>
        )}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label="Más acciones">
              <MoreHorizontal />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem disabled={!theme.frame_url_template} onSelect={onSimulate}>
              <MonitorPlay /> Simular arranque
            </DropdownMenuItem>
            <DropdownMenuItem
              disabled={!theme.has_backup || busy}
              onSelect={async () => {
                const ok = await confirm({
                  title: "Restaurar backup",
                  description: `Vuelve a la versión de «${theme.name}» que había antes de la última instalación.`,
                  confirmLabel: "Restaurar",
                  privileged: true,
                });
                if (ok) restore.mutate(undefined);
              }}
            >
              <ArchiveRestore /> Restaurar backup
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              destructive
              disabled={isText || busy}
              onSelect={async () => {
                const ok = await confirm({
                  title: `Desinstalar «${theme.name}»`,
                  description: theme.is_default
                    ? "Es el tema activo: el arranque volverá primero al modo texto y después se borrará."
                    : "Se borra del sistema. Si lo generaste con Plymotion, sigue en tu galería.",
                  confirmLabel: "Desinstalar",
                  destructive: true,
                  privileged: true,
                });
                if (ok) uninstall.mutate(undefined);
              }}
            >
              <Trash2 /> Desinstalar
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}

export function SystemPage() {
  const { data: themes, isLoading } = useInstalledThemes();
  const running = useRunningJobs().filter((j) => SYSTEM_JOB_KINDS.has(j.kind));
  const busy = running.length > 0;
  const confirm = useConfirm();
  const [simulated, setSimulated] = useState<InstalledTheme | null>(null);
  const preview = useJobMutation(() =>
    call(api.POST("/api/system/preview", { body: { seconds: 6 } })),
  );
  const resetText = useJobMutation(() => call(api.POST("/api/system/reset-text")));

  return (
    <Page>
      <PageHeader
        title="Sistema"
        description="Temas instalados en /usr/share/plymouth/themes. Solo uno está activo en el arranque."
        actions={
          <Button
            disabled={busy}
            onClick={async () => {
              const ok = await confirm({
                title: "Probar el tema activo",
                description:
                  "Muestra el splash de arranque real en pantalla durante 6 segundos, sin reiniciar.",
                confirmLabel: "Probar ahora",
                privileged: true,
              });
              if (ok) preview.mutate(undefined);
            }}
          >
            <Play /> Probar en vivo
          </Button>
        }
      />

      {running.map((job) => (
        <Card key={job.id} className="mb-5 border-primary/30">
          <CardContent className="space-y-1.5 pt-5">
            <div className="text-sm font-medium">{job.title}</div>
            <JobProgress job={job} />
          </CardContent>
        </Card>
      ))}

      <div className="grid items-start gap-5 lg:grid-cols-[1fr_320px]">
        <div className="space-y-2.5">
          {isLoading
            ? Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-[88px] rounded-xl" />)
            : themes?.map((theme) => (
                <ThemeRow
                  key={theme.dir_name}
                  theme={theme}
                  busy={busy}
                  onSimulate={() => setSimulated(theme)}
                />
              ))}
        </div>

        <div className="space-y-5 lg:sticky lg:top-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShieldCheck className="size-4 text-success" /> Siempre recuperable
              </CardTitle>
              <CardDescription>
                Un tema roto nunca impide arrancar: Plymouth cae al modo texto y el sistema
                continúa.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                className="w-full"
                disabled={busy}
                onClick={async () => {
                  const ok = await confirm({
                    title: "Volver a modo texto",
                    description:
                      "El arranque usará el tema de texto de Plymouth. Tus temas siguen instalados y puedes reactivarlos cuando quieras.",
                    confirmLabel: "Volver a modo texto",
                    privileged: true,
                  });
                  if (ok) resetText.mutate(undefined);
                }}
              >
                <Type /> Volver a modo texto
              </Button>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LifeBuoy className="size-4 text-primary" /> Si no puedes arrancar
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-[13px] text-muted-foreground">
              <p>
                En GRUB pulsa <span className="font-mono text-foreground">e</span> y añade al final
                de la línea del kernel:
              </p>
              <pre className="rounded-md bg-stage px-3 py-2 font-mono text-xs text-white/80">
                plymouth.enable=0
              </pre>
              <p>O desde una TTY (Ctrl+Alt+F3):</p>
              <pre className="rounded-md bg-stage px-3 py-2 font-mono text-[11px] leading-relaxed break-all whitespace-pre-wrap text-white/80">
                {"sudo update-alternatives --set default.plymouth \\\n  /usr/share/plymouth/themes/text/text.plymouth\nsudo update-initramfs -u -k all"}
              </pre>
            </CardContent>
          </Card>
          <Card className="bg-muted/30">
            <CardContent className="flex gap-3 pt-5 text-[13px] text-muted-foreground">
              <Sparkles className="mt-0.5 size-4 shrink-0 text-primary" />
              Activar o desinstalar regenera el initramfs de todos los kernels, así el cambio
              aplica al próximo arranque aunque haya un kernel nuevo.
            </CardContent>
          </Card>
        </div>
      </div>

      {simulated?.frame_url_template && (
        <BootSimulator
          open
          onOpenChange={(open) => !open && setSimulated(null)}
          name={simulated.name}
          template={simulated.frame_url_template}
          count={simulated.frame_count}
          watermark={simulated.watermark_url}
        />
      )}
    </Page>
  );
}
