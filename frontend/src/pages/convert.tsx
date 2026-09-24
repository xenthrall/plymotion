import { useQuery } from "@tanstack/react-query";
import {
  Clapperboard,
  Download,
  Film,
  GalleryHorizontalEnd,
  Info,
  MonitorPlay,
  Pause,
  Play,
  Repeat,
  Scissors,
  Sparkles,
  TriangleAlert,
  X,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { toast } from "sonner";
import { api, call, errorMessage, type LibraryTheme, type VideoInfo } from "@/api/client";
import { jobsStore, useJob, useJobsState } from "@/api/jobs";
import { useJobMutation, useLoginLogo, usePrefs, useUpdatePrefs } from "@/api/queries";
import { BootSimulator } from "@/components/boot-simulator";
import { useConfirm } from "@/components/confirm";
import { FramePlayer, PLYMOUTH_HZ } from "@/components/frame-player";
import { JobLog, JobProgress } from "@/components/job-status";
import { Page, PageHeader, Stat } from "@/components/page";
import { PickButton } from "@/components/path-picker";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Tooltip } from "@/components/ui/tooltip";
import { hasExtension, useFileDrop, VIDEO_EXTENSIONS } from "@/lib/desktop";
import { cn, formatBytes, formatClock, formatSeconds } from "@/lib/utils";

// Boot splash sprites don't need the screen's resolution: Plymouth centers
// them on a black console, and smaller frames load much faster at boot.
const SIZES = [
  { id: "160x120", label: "160 × 120", hint: "Mínimo" },
  { id: "240x180", label: "240 × 180", hint: "" },
  { id: "320x240", label: "320 × 240", hint: "Recomendado" },
  { id: "480x360", label: "480 × 360", hint: "" },
  { id: "640x480", label: "640 × 480", hint: "" },
  { id: "1280x720", label: "1280 × 720", hint: "HD" },
  { id: "1920x1080", label: "1920 × 1080", hint: "Pantalla completa" },
];
const FPS = [10, 15, 24, 25, 30, 50, 60];
const COLORS = [16, 32, 64, 128, 256];

type Settings = { name: string; size: string; fps: number; colors: number; bootLogo: boolean };
const DEFAULTS: Settings = { name: "", size: "320x240", fps: 30, colors: 64, bootLogo: true };

function nameFromPath(path: string) {
  const base = path.split("/").pop() ?? "tema";
  const stem = base.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ").trim();
  return stem.charAt(0).toUpperCase() + stem.slice(1, 60);
}

/* ---------------------------------------------------------------- source --- */

function SourceEmpty({ onPick }: { onPick: (path: string) => void }) {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center justify-center px-8 py-20 text-center">
        <div className="relative mb-6">
          <div className="absolute inset-0 rounded-2xl bg-primary/30 blur-2xl" />
          <div className="relative grid size-16 place-items-center rounded-2xl bg-gradient-to-br from-violet-400 to-violet-700 text-white shadow-lg">
            <Clapperboard className="size-7" />
          </div>
        </div>
        <h2 className="text-lg font-semibold">Elige un video o GIF</h2>
        <p className="mt-1.5 max-w-sm text-sm text-muted-foreground">
          Arrástralo a la ventana o búscalo en tu equipo. MP4, WebM, MKV, MOV, AVI o GIF animado.
        </p>
        <div className="mt-6">
          <PickButton kind="video" size="lg" onPick={(paths) => paths[0] && onPick(paths[0])}>
            Examinar archivos
          </PickButton>
        </div>
      </CardContent>
    </Card>
  );
}

function TrimEditor({
  info,
  range,
  onRange,
  onClear,
}: {
  info: VideoInfo;
  range: [number, number];
  onRange: (range: [number, number]) => void;
  onClear: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [loopTrim, setLoopTrim] = useState(true);
  const [time, setTime] = useState(0);
  const duration = info.duration || 0;
  const [start, end] = range;

  // Keep playback inside the trimmed range while "loop selection" is on.
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const onTime = () => {
      setTime(video.currentTime);
      if (loopTrim && video.currentTime >= end) video.currentTime = start;
    };
    video.addEventListener("timeupdate", onTime);
    return () => video.removeEventListener("timeupdate", onTime);
  }, [start, end, loopTrim]);

  const seek = (t: number) => {
    if (videoRef.current) videoRef.current.currentTime = t;
  };

  const togglePlay = () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      if (video.currentTime < start || video.currentTime >= end) video.currentTime = start;
      void video.play();
    } else video.pause();
  };

  const isGif = info.codec === "gif";

  return (
    <Card className="overflow-hidden">
      <div className="relative bg-stage">
        {isGif ? (
          <img src={info.media_url} alt="" className="mx-auto max-h-[420px] object-contain" />
        ) : (
          <video
            ref={videoRef}
            src={info.media_url}
            className="mx-auto max-h-[420px] w-full object-contain"
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onLoadedMetadata={() => seek(start)}
            muted
            playsInline
          />
        )}
        <Button
          variant="secondary"
          size="icon-sm"
          className="absolute top-3 right-3 bg-black/50 text-white backdrop-blur hover:bg-black/70"
          onClick={onClear}
          aria-label="Quitar video"
        >
          <X />
        </Button>
      </div>
      <CardContent className="space-y-4 pt-4">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <div className="min-w-0 flex-1">
            <div className="truncate font-medium" title={info.path}>
              {info.name}
            </div>
            <div className="truncate text-xs text-muted-foreground">{info.path}</div>
          </div>
          <Stat label="Original" value={`${info.width}×${info.height}`} />
          <Stat label="Duración" value={formatSeconds(duration)} />
          <Stat label="FPS" value={info.fps ? info.fps.toFixed(info.fps % 1 ? 2 : 0) : "—"} />
          <Stat label="Tamaño" value={formatBytes(info.size_bytes)} />
        </div>

        <div className="rounded-lg border bg-muted/30 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Scissors className="size-4 text-primary" /> Recorte
              <span className="font-mono text-xs font-normal text-muted-foreground">
                {formatClock(start)} – {formatClock(end)} · {formatSeconds(end - start)}
              </span>
            </div>
            {!isGif && (
              <div className="flex items-center gap-1">
                <Tooltip content={loopTrim ? "Repetir solo el recorte" : "Reproducir todo"}>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className={cn(loopTrim && "text-primary")}
                    onClick={() => setLoopTrim((v) => !v)}
                  >
                    <Repeat />
                  </Button>
                </Tooltip>
                <Button variant="secondary" size="sm" onClick={togglePlay}>
                  {playing ? <Pause /> : <Play />}
                  {playing ? "Pausar" : "Reproducir recorte"}
                </Button>
              </div>
            )}
          </div>
          <div className="relative">
            <Slider
              min={0}
              max={Math.max(duration, 0.1)}
              step={0.05}
              minStepsBetweenThumbs={1}
              value={[start, end]}
              onValueChange={(v) => {
                const next: [number, number] = [v[0] ?? 0, v[1] ?? duration];
                if (next[0] !== start) seek(next[0]);
                else if (next[1] !== end) seek(Math.max(next[1] - 0.05, 0));
                onRange(next);
              }}
            />
            {!isGif && duration > 0 && (
              <div
                className="pointer-events-none absolute -top-1 h-3.5 w-0.5 rounded-full bg-foreground/70"
                style={{ left: `${(time / duration) * 100}%` }}
              />
            )}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            El arranque real dura pocos segundos: un clip corto y en loop se ve mejor que un video
            largo.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

/* --------------------------------------------------------------- settings --- */

function EstimatePanel({ info, range, fps }: { info: VideoInfo; range: [number, number]; fps: number }) {
  const [start, end] = range;
  const trimDuration = end - start;
  const { data } = useQuery({
    queryKey: ["estimate", info.duration, fps, start, trimDuration],
    queryFn: () =>
      call(
        api.POST("/api/convert/estimate", {
          body: { duration: info.duration, fps, trim_start: start, trim_duration: trimDuration },
        }),
      ),
    placeholderData: (prev) => prev,
  });
  if (!data) return null;
  const speed = PLYMOUTH_HZ / fps;
  const heavy = data.frame_count > 400;

  return (
    <div className="space-y-3 rounded-lg border bg-muted/30 p-4">
      <div className="grid grid-cols-3 gap-3">
        <Stat label="Frames" value={data.frame_count} />
        <Stat label="Loop" value={formatSeconds(data.loop_seconds)} />
        <Stat
          label="Velocidad"
          value={`${speed.toFixed(speed % 1 ? 2 : 0)}×`}
          hint="Plymouth reproduce a 50 Hz fijos"
        />
      </div>
      <p className="flex gap-2 text-xs text-muted-foreground">
        <Info className="mt-px size-3.5 shrink-0" />
        {Math.abs(speed - 1) < 0.01
          ? "A 50 fps el loop dura lo mismo que el clip original."
          : `Plymouth muestra 50 frames por segundo: extraer a ${fps} fps hace que la animación se vea ${speed > 1 ? "más rápida" : "más lenta"}. Usa 50 fps para la velocidad real.`}
      </p>
      {heavy && (
        <p className="flex gap-2 text-xs text-warning">
          <TriangleAlert className="mt-px size-3.5 shrink-0" />
          Muchos frames alargan la carga del arranque. Acorta el recorte o baja los FPS.
        </p>
      )}
    </div>
  );
}

function SettingsCard({
  info,
  range,
  settings,
  setSettings,
  running,
  onConvert,
}: {
  info: VideoInfo | null;
  range: [number, number];
  settings: Settings;
  setSettings: (patch: Partial<Settings>) => void;
  running: boolean;
  onConvert: () => void;
}) {
  const disabled = !info || running;
  return (
    <Card className={cn("transition-opacity", !info && "opacity-60")}>
      <CardHeader>
        <CardTitle>Ajustes</CardTitle>
        <CardDescription>Tamaño y colores más bajos = arranque más rápido.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-2">
          <Label htmlFor="theme-name">Nombre del tema</Label>
          <Input
            id="theme-name"
            value={settings.name}
            disabled={disabled}
            placeholder="Mi animación"
            maxLength={80}
            onChange={(e) => setSettings({ name: e.target.value })}
          />
        </div>

        <div className="space-y-2">
          <Label>Tamaño máximo</Label>
          <Select
            value={settings.size}
            disabled={disabled}
            onValueChange={(size) => setSettings({ size })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SIZES.map((s) => (
                <SelectItem key={s.id} value={s.id}>
                  {s.label}
                  {s.hint && <span className="ml-2 text-muted-foreground">· {s.hint}</span>}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            Se conserva la proporción; la animación se centra en pantalla.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label>FPS de extracción</Label>
            <Select
              value={String(settings.fps)}
              disabled={disabled}
              onValueChange={(v) => setSettings({ fps: Number(v) })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {FPS.map((f) => (
                  <SelectItem key={f} value={String(f)}>
                    {f} fps{f === 50 ? " · real" : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label>Colores</Label>
            <Select
              value={String(settings.colors)}
              disabled={disabled}
              onValueChange={(v) => setSettings({ colors: Number(v) })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {COLORS.map((c) => (
                  <SelectItem key={c} value={String(c)}>
                    {c} colores
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <BootLogoSwitch
          checked={settings.bootLogo}
          disabled={disabled}
          onChange={(bootLogo) => setSettings({ bootLogo })}
        />

        {info && <EstimatePanel info={info} range={range} fps={settings.fps} />}

        <Button
          size="lg"
          className="w-full"
          disabled={disabled || !settings.name.trim()}
          onClick={onConvert}
        >
          <Sparkles /> Generar tema
        </Button>
      </CardContent>
    </Card>
  );
}

function BootLogoSwitch({
  checked,
  disabled,
  onChange,
}: {
  checked: boolean;
  disabled: boolean;
  onChange: (checked: boolean) => void;
}) {
  const { data: logo } = useLoginLogo();
  const available = !!logo?.current_url;
  return (
    <div className="flex items-center gap-3 rounded-lg border p-3">
      <div className="grid h-9 w-14 shrink-0 place-items-center rounded-md bg-stage">
        {available && (
          <img src={logo.current_url!} alt="" className="max-h-7 max-w-12 object-contain" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <Label htmlFor="boot-logo" className="text-[13px]">
          Logo del login en el arranque
        </Label>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {available ? (
            "Abajo, donde luego aparece en el login."
          ) : (
            <>
              Sin logo de login. <Link to="/login" className="text-primary hover:underline">Configurar</Link>
            </>
          )}
        </p>
      </div>
      <Switch
        id="boot-logo"
        checked={checked && available}
        disabled={disabled || !available}
        onCheckedChange={onChange}
      />
    </div>
  );
}

/* ----------------------------------------------------------------- result --- */

function ResultCard({ theme, onReset }: { theme: LibraryTheme; onReset: () => void }) {
  const [simOpen, setSimOpen] = useState(false);
  const confirm = useConfirm();
  const install = useJobMutation(() =>
    call(
      api.POST("/api/library/{slug}/install", { params: { path: { slug: theme.slug } } }),
    ),
  );

  return (
    <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }}>
      <Card className="glow overflow-hidden">
        <div className="grid md:grid-cols-[1.2fr_1fr]">
          <div className="stage-grid relative aspect-video">
            <FramePlayer
              template={theme.frame_url_template}
              count={theme.frame_count}
              className="absolute inset-6"
            />
          </div>
          <div className="flex flex-col justify-between gap-5 p-6">
            <div>
              <Badge variant="success">
                <Sparkles /> Tema listo
              </Badge>
              <h2 className="mt-3 text-xl font-semibold tracking-tight">{theme.name}</h2>
              <div className="mt-4 grid grid-cols-3 gap-3">
                <Stat label="Frames" value={theme.frame_count} />
                <Stat label="Loop" value={formatSeconds(theme.loop_seconds)} />
                <Stat label="Peso" value={formatBytes(theme.total_bytes)} />
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <Button
                disabled={install.isPending}
                onClick={async () => {
                  const ok = await confirm({
                    title: `Instalar «${theme.name}»`,
                    description:
                      "Se copiará al sistema, se activará como animación de arranque y se regenerará el initramfs. Si ya había un tema con este nombre, se guarda un backup.",
                    confirmLabel: "Instalar y activar",
                    privileged: true,
                  });
                  if (ok) install.mutate(undefined);
                }}
              >
                <Download /> Instalar como arranque
              </Button>
              <div className="grid grid-cols-2 gap-2">
                <Button variant="secondary" onClick={() => setSimOpen(true)}>
                  <MonitorPlay /> Simular
                </Button>
                <Button variant="secondary" asChild>
                  <Link to={`/galeria?tema=${theme.slug}`}>
                    <GalleryHorizontalEnd /> Galería
                  </Link>
                </Button>
              </div>
              <Button variant="ghost" onClick={onReset}>
                <Film /> Crear otro
              </Button>
            </div>
          </div>
        </div>
      </Card>
      <BootSimulator
        open={simOpen}
        onOpenChange={setSimOpen}
        name={theme.name}
        template={theme.frame_url_template}
        count={theme.frame_count}
        size={{ width: theme.width, height: theme.height }}
        watermark={theme.watermark_url}
      />
    </motion.div>
  );
}

/* ------------------------------------------------------------------- page --- */

export function ConvertPage() {
  const [params, setParams] = useSearchParams();
  const { data: prefs } = usePrefs();
  const updatePrefs = useUpdatePrefs();
  const [info, setInfo] = useState<VideoInfo | null>(null);
  const [loadingPath, setLoadingPath] = useState<string | null>(null);
  const [range, setRange] = useState<[number, number]>([0, 0]);
  const [settings, setSettingsState] = useState<Settings>(DEFAULTS);
  const [jobId, setJobId] = useState<string | null>(null);
  const [result, setResult] = useState<LibraryTheme | null>(null);

  // Restore the last-used settings once prefs load.
  const restored = useRef(false);
  useEffect(() => {
    if (restored.current || !prefs) return;
    restored.current = true;
    const saved = prefs.convert_defaults as Partial<Settings>;
    setSettingsState((s) => ({ ...s, ...saved, name: s.name }));
  }, [prefs]);

  const setSettings = (patch: Partial<Settings>) => setSettingsState((s) => ({ ...s, ...patch }));

  // Pick up a conversion that's still running if the user navigated away and back.
  const { jobs } = useJobsState();
  const runningConvert = jobs.find((j) => j.kind === "convert" && j.state === "running");
  const activeId = jobId ?? runningConvert?.id ?? null;
  const job = useJob(activeId);

  useEffect(
    () =>
      jobsStore.onFinish((finished) => {
        if (finished.kind !== "convert") return;
        if (finished.state === "succeeded" && finished.result) {
          setResult(finished.result as LibraryTheme);
        }
        setJobId(null);
      }),
    [],
  );

  const load = useCallback(async (path: string) => {
    setLoadingPath(path);
    try {
      const video = await call(api.POST("/api/videos/inspect", { body: { path } }));
      setInfo(video);
      setResult(null);
      const clip = Math.min(video.duration, 6);
      setRange([0, clip || video.duration]);
      setSettingsState((s) => ({ ...s, name: nameFromPath(path) }));
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setLoadingPath(null);
    }
  }, []);

  // /crear?video=/path (from the Secuencias page).
  useEffect(() => {
    const video = params.get("video");
    if (video) {
      // Loading is driven by the URL (an external input), not by React state.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void load(video);
      setParams({}, { replace: true });
    }
  }, [params, setParams, load]);

  useFileDrop(
    useCallback(
      (paths: string[]) => {
        const video = paths.find((p) => hasExtension(p, VIDEO_EXTENSIONS));
        if (video) void load(video);
        else toast.error("Ese archivo no es un video ni un GIF.");
      },
      [load],
    ),
  );

  const confirm = useConfirm();
  const convert = useJobMutation((vars: { path: string }) => {
    const [w, h] = settings.size.split("x").map(Number);
    const [start, end] = range;
    const full = info && start <= 0.01 && end >= info.duration - 0.01;
    return call(
      api.POST("/api/convert", {
        body: {
          path: vars.path,
          name: settings.name.trim(),
          max_width: w ?? 320,
          max_height: h ?? 240,
          fps: settings.fps,
          colors: settings.colors,
          trim_start: start,
          trim_duration: full ? null : end - start,
          boot_logo: settings.bootLogo,
        },
      }),
    );
  });

  const start = async () => {
    if (!info) return;
    const [s, e] = range;
    if ((e - s) * settings.fps > 900) {
      const ok = await confirm({
        title: "Animación muy larga",
        description: `Se generarán unos ${Math.round((e - s) * settings.fps)} frames. Eso puede tardar y hacer más lento el arranque. ¿Continuar igualmente?`,
        confirmLabel: "Generar igualmente",
      });
      if (!ok) return;
    }
    updatePrefs.mutate({
      convert_defaults: {
        size: settings.size,
        fps: settings.fps,
        colors: settings.colors,
        bootLogo: settings.bootLogo,
      },
    });
    const created = await convert.mutateAsync({ path: info.path }).catch(() => null);
    if (created) {
      setJobId(created.id);
      setResult(null);
    }
  };

  const running = job?.state === "running";
  // Stable identity, so React calls it once when the progress card mounts.
  const scrollIntoView = useCallback((el: HTMLDivElement | null) => {
    el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, []);
  const cancel = () =>
    activeId &&
    call(api.DELETE("/api/jobs/{job_id}", { params: { path: { job_id: activeId } } })).catch(
      (e) => toast.error(errorMessage(e)),
    );

  const reset = () => {
    setInfo(null);
    setResult(null);
    setSettings({ name: "" });
  };

  return (
    <Page>
      <PageHeader
        title="Crear tema"
        description="Convierte un video o GIF en una animación de arranque de Plymouth."
      />

      <AnimatePresence mode="wait">
        {result ? (
          <ResultCard key="result" theme={result} onReset={reset} />
        ) : (
          <motion.div
            key="editor"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="grid items-start gap-5 lg:grid-cols-[1fr_340px]"
          >
            <div className="space-y-5">
              {loadingPath ? (
                <Card className="grid h-80 place-items-center">
                  <div className="flex flex-col items-center gap-3 text-sm text-muted-foreground">
                    <div className="size-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                    Leyendo el video…
                  </div>
                </Card>
              ) : info ? (
                <TrimEditor info={info} range={range} onRange={setRange} onClear={reset} />
              ) : (
                <SourceEmpty onPick={load} />
              )}

              {job && job.state === "running" && (
                <Card ref={scrollIntoView}>
                  <CardHeader className="flex-row items-center justify-between">
                    <div>
                      <CardTitle>Generando «{settings.name || job.title}»</CardTitle>
                      <CardDescription>Puedes seguir navegando; la tarea sigue en segundo plano.</CardDescription>
                    </div>
                    {job.cancellable && (
                      <Button variant="destructive-ghost" size="sm" onClick={cancel}>
                        Cancelar
                      </Button>
                    )}
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <JobProgress job={job} />
                    <JobLog jobId={job.id} />
                  </CardContent>
                </Card>
              )}
            </div>
            <div className="lg:sticky lg:top-6">
              <SettingsCard
                info={info}
                range={range}
                settings={settings}
                setSettings={setSettings}
                running={running}
                onConvert={start}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Page>
  );
}
