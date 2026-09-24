import {
  ArrowRight,
  CheckCircle2,
  CircleAlert,
  Film,
  GalleryHorizontalEnd,
  MonitorPlay,
  Play,
  Sparkles,
} from "lucide-react";
import { Link } from "react-router";
import { api, call } from "@/api/client";
import { useInstalledThemes, useJobMutation, useLibrary, useMeta } from "@/api/queries";
import { useConfirm } from "@/components/confirm";
import { FramePlayer } from "@/components/frame-player";
import { Page } from "@/components/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatRelative, formatSeconds } from "@/lib/utils";

function ActiveThemeHero() {
  const { data: themes, isLoading } = useInstalledThemes();
  const confirm = useConfirm();
  const preview = useJobMutation(() =>
    call(api.POST("/api/system/preview", { body: { seconds: 6 } })),
  );
  const active = themes?.find((t) => t.is_default);

  return (
    <Card className="relative overflow-hidden">
      <div className="grid md:grid-cols-[1.1fr_1fr]">
        <div className="stage-grid relative aspect-video md:aspect-auto md:min-h-72">
          {isLoading ? (
            <Skeleton className="absolute inset-6" />
          ) : active?.frame_url_template ? (
            <FramePlayer
              template={active.frame_url_template}
              count={active.frame_count}
              className="absolute inset-6"
            />
          ) : (
            <div className="absolute inset-0 grid place-items-center text-white/50">
              <div className="flex flex-col items-center gap-2 text-sm">
                <MonitorPlay className="size-8" />
                {active ? "Tema sin frames para previsualizar" : "Sin tema activo detectado"}
              </div>
            </div>
          )}
          <Badge className="absolute top-4 left-4 border-white/10 bg-black/50 text-white/80 backdrop-blur">
            <span className="size-1.5 rounded-full bg-success" /> En el arranque
          </Badge>
        </div>
        <div className="flex flex-col justify-between gap-6 p-7">
          <div>
            <div className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              Tema de arranque activo
            </div>
            {isLoading ? (
              <Skeleton className="mt-2 h-8 w-48" />
            ) : (
              <h2 className="mt-1.5 text-2xl font-semibold tracking-tight">
                {active?.name ?? "Ninguno"}
              </h2>
            )}
            <p className="mt-2 text-sm text-muted-foreground">
              {active?.is_plymotion
                ? `Animación de ${active.frame_count} frames, ${formatSeconds(active.frame_count / 50)} por loop.`
                : (active?.description ?? "Plymouth usará su tema por defecto.")}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={!active || preview.isPending}
              onClick={async () => {
                const ok = await confirm({
                  title: "Probar el tema activo",
                  description:
                    "La pantalla mostrará el splash de arranque durante 6 segundos y luego volverá sola. No reinicia el equipo.",
                  confirmLabel: "Probar ahora",
                  privileged: true,
                });
                if (ok) preview.mutate(undefined);
              }}
            >
              <Play /> Probar en vivo
            </Button>
            <Button variant="secondary" asChild>
              <Link to="/sistema">
                Cambiar tema <ArrowRight />
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}

function Checks() {
  const { data: meta } = useMeta();
  const checks = meta
    ? [
        {
          ok: meta.capabilities.ffmpeg,
          label: "ffmpeg",
          hint: meta.capabilities.ffmpeg ? "Extracción de frames" : "sudo apt install ffmpeg",
        },
        {
          ok: meta.capabilities.pkexec,
          label: "pkexec",
          hint: meta.capabilities.pkexec ? "Acciones de administrador" : "Instala policykit-1",
        },
        {
          ok: meta.capabilities.gdm,
          label: "GDM",
          hint: meta.capabilities.gdm ? "Logo del login" : "Solo para GNOME",
        },
        {
          ok: meta.capabilities.native_dialogs,
          label: "Diálogos nativos",
          hint: meta.capabilities.native_dialogs ? "Selector de archivos" : "Escribe rutas a mano",
        },
      ]
    : [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sistema</CardTitle>
        <CardDescription>
          {meta ? `${meta.system.distro} · kernel ${meta.system.kernel}` : "Cargando…"}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2.5">
        {!meta &&
          Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-5 w-full" />)}
        {checks.map((check) => (
          <div key={check.label} className="flex items-center justify-between gap-3 text-sm">
            <span className="flex items-center gap-2">
              {check.ok ? (
                <CheckCircle2 className="size-4 text-success" />
              ) : (
                <CircleAlert className="size-4 text-warning" />
              )}
              {check.label}
            </span>
            <span className="truncate text-xs text-muted-foreground">{check.hint}</span>
          </div>
        ))}
        {meta?.system.initramfs_tool && (
          <div className="flex items-center justify-between gap-3 border-t pt-2.5 text-sm">
            <span className="text-muted-foreground">Initramfs</span>
            <span className="font-mono text-xs">{meta.system.initramfs_tool}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function RecentThemes() {
  const { data: library, isLoading } = useLibrary();
  const recent = library?.slice(0, 4) ?? [];
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <div>
          <CardTitle>Recientes</CardTitle>
          <CardDescription>Últimos temas generados</CardDescription>
        </div>
        <Button variant="ghost" size="sm" asChild>
          <Link to="/galeria">
            Ver galería <ArrowRight />
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="aspect-video" />
            ))}
          </div>
        ) : recent.length === 0 ? (
          <div className="flex items-center justify-between gap-4 rounded-lg border border-dashed p-5">
            <p className="text-sm text-muted-foreground">Todavía no has creado ningún tema.</p>
            <Button size="sm" asChild>
              <Link to="/crear">
                <Sparkles /> Crear el primero
              </Link>
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {recent.map((theme) => (
              <Link
                key={theme.slug}
                to={`/galeria?tema=${theme.slug}`}
                className="group overflow-hidden rounded-lg border transition-colors hover:border-primary/50"
              >
                <div className="relative aspect-video bg-stage">
                  {theme.thumbnail_url && (
                    <img
                      src={theme.thumbnail_url}
                      alt=""
                      className="absolute inset-0 size-full object-contain p-2 transition-transform group-hover:scale-105"
                    />
                  )}
                </div>
                <div className="p-2.5">
                  <div className="truncate text-[13px] font-medium">{theme.name}</div>
                  <div className="text-[11px] text-muted-foreground">
                    {formatRelative(theme.created_at)}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function HomePage() {
  const { data: library } = useLibrary();
  const { data: installed } = useInstalledThemes();
  return (
    <Page>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Inicio</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Convierte cualquier video en la animación de arranque de tu equipo.
          </p>
        </div>
        <Button size="lg" asChild className="glow">
          <Link to="/crear">
            <Film /> Crear tema nuevo
          </Link>
        </Button>
      </div>

      <ActiveThemeHero />

      <div className="mt-5 grid items-start gap-5 lg:grid-cols-[1fr_320px]">
        <RecentThemes />
        <div className="space-y-5">
          <Checks />
          <div className="grid grid-cols-2 gap-3">
            <SmallStat
              to="/galeria"
              icon={GalleryHorizontalEnd}
              label="En galería"
              value={library?.length}
            />
            <SmallStat
              to="/sistema"
              icon={MonitorPlay}
              label="Instalados"
              value={installed?.length}
            />
          </div>
        </div>
      </div>
    </Page>
  );
}

function SmallStat({
  to,
  icon: Icon,
  label,
  value,
}: {
  to: string;
  icon: typeof Film;
  label: string;
  value: number | undefined;
}) {
  return (
    <Link
      to={to}
      className={cn(
        "rounded-xl border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-muted/40",
      )}
    >
      <Icon className="size-4 text-primary" />
      <div className="mt-3 text-2xl font-semibold tabular-nums">{value ?? "–"}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </Link>
  );
}
