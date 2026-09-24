import { useQuery } from "@tanstack/react-query";
import { CircleAlert, ImageUp, RotateCcw, UserRound, Wand2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { api, call, errorMessage } from "@/api/client";
import { useRunningJobs } from "@/api/jobs";
import { useJobMutation, useLoginLogo } from "@/api/queries";
import { useConfirm } from "@/components/confirm";
import { Page, PageHeader } from "@/components/page";
import { PickButton } from "@/components/path-picker";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { hasExtension, IMAGE_EXTENSIONS, useFileDrop } from "@/lib/desktop";
import { basename } from "@/lib/utils";

/** The screen GDM is drawn on, used to scale the mock: logos render at real pixel size. */
const MOCK_SCREEN_WIDTH = 1920;

function GdmMock({ logo, logoSize }: { logo: string | null; logoSize: { w: number; h: number } | null }) {
  const [clock, setClock] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setClock(new Date()), 30_000);
    return () => clearInterval(id);
  }, []);

  return (
    <div
      className="@container relative aspect-video w-full overflow-hidden rounded-xl bg-[radial-gradient(ellipse_at_top,#2b2d3a,#16171d_70%)] ring-1 ring-black/20"
      style={{ containerType: "inline-size" }}
    >
      <div className="absolute inset-x-0 top-0 flex h-[3.2cqw] items-center justify-center bg-black/80 text-[1.3cqw] font-semibold text-white/90">
        {clock.toLocaleDateString("es", { weekday: "short", day: "numeric", month: "short" })}{" "}
        {clock.toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" })}
      </div>
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-[1.2cqw]">
        <div className="grid size-[6.5cqw] place-items-center rounded-full bg-white/10">
          <UserRound className="size-[3.5cqw] text-white/70" />
        </div>
        <div className="text-[1.6cqw] font-semibold text-white/90">Usuario</div>
        <div className="h-[2.6cqw] w-[20cqw] rounded-[0.6cqw] bg-white/10" />
      </div>
      {logo && logoSize && (
        <img
          src={logo}
          alt="Logo"
          className="absolute left-1/2 -translate-x-1/2"
          style={{
            bottom: `${(40 / MOCK_SCREEN_WIDTH) * 100}cqw`,
            width: `${(logoSize.w / MOCK_SCREEN_WIDTH) * 100}cqw`,
            height: `${(logoSize.h / MOCK_SCREEN_WIDTH) * 100}cqw`,
          }}
        />
      )}
    </div>
  );
}

function useImageSize(url: string | null) {
  const [state, setState] = useState<{ url: string; w: number; h: number } | null>(null);
  useEffect(() => {
    if (!url) return;
    const img = new Image();
    img.onload = () => setState({ url, w: img.naturalWidth, h: img.naturalHeight });
    img.src = url;
  }, [url]);
  return state && state.url === url ? { w: state.w, h: state.h } : null;
}

export function LoginLogoPage() {
  const { data: state } = useLoginLogo();
  const [source, setSource] = useState<string | null>(null);
  const [height, setHeight] = useState(72);
  const [view, setView] = useState<"new" | "current">("new");
  const confirm = useConfirm();
  const busy = useRunningJobs().some((j) => j.kind.startsWith("login-logo"));

  const { data: preview, error } = useQuery({
    queryKey: ["logo-preview", source, height],
    queryFn: () =>
      call(api.POST("/api/login-logo/preview", { body: { path: source!, max_height: height } })),
    enabled: !!source,
    placeholderData: (prev) => prev,
  });
  useEffect(() => {
    if (error) toast.error(errorMessage(error));
  }, [error]);

  const currentUrl = state?.current_url ? `${state.current_url}?v=${state.custom_installed}` : null;
  const currentSize = useImageSize(currentUrl);

  const apply = useJobMutation(() =>
    call(api.POST("/api/login-logo/apply", { body: { path: source!, max_height: height } })),
  );
  const restore = useJobMutation(() => call(api.POST("/api/login-logo/restore")));

  const pick = useCallback((path: string) => {
    setSource(path);
    setView("new");
  }, []);
  useFileDrop(
    useCallback(
      (paths: string[]) => {
        const image = paths.find((p) => hasExtension(p, IMAGE_EXTENSIONS));
        if (image) pick(image);
        else toast.error("Usa una imagen PNG, JPG, WebP o BMP.");
      },
      [pick],
    ),
  );

  const effectiveView = preview ? view : "current";
  const showingNew = effectiveView === "new" && preview;
  const mockLogo = showingNew ? preview.url : currentUrl;
  const mockSize = showingNew ? { w: preview.width, h: preview.height } : currentSize;

  if (state && !state.gdm_available) {
    return (
      <Page>
        <PageHeader title="Logo del login" />
        <Card>
          <CardContent className="flex items-start gap-3 pt-5 text-sm">
            <CircleAlert className="mt-0.5 size-5 text-warning" />
            <div>
              <div className="font-medium">GDM no está disponible</div>
              <p className="mt-1 text-muted-foreground">
                Esta función cambia el logo de la pantalla de login de GNOME (GDM) y no encontró su
                configuración en /usr/share/gdm/dconf.
              </p>
            </div>
          </CardContent>
        </Card>
      </Page>
    );
  }

  return (
    <Page>
      <PageHeader
        title="Logo del login"
        description="Cambia el logo que GDM muestra abajo en la pantalla de inicio de sesión. No modifica archivos de la distro."
      />
      <div className="grid items-start gap-5 lg:grid-cols-[1fr_320px]">
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b px-5 py-3">
            <div className="text-sm font-medium">Vista previa a tamaño real</div>
            <ToggleGroup
              type="single"
              value={effectiveView}
              onValueChange={(v) => v && setView(v as "new" | "current")}
            >
              <ToggleGroupItem value="current">Actual</ToggleGroupItem>
              <ToggleGroupItem value="new" disabled={!preview}>
                Nuevo
              </ToggleGroupItem>
            </ToggleGroup>
          </div>
          <div className="bg-muted/30 p-5">
            <GdmMock logo={mockLogo} logoSize={mockSize} />
            <p className="mt-3 text-center text-xs text-muted-foreground">
              Simulación en una pantalla de 1920 px de ancho. GDM no escala el logo.
            </p>
          </div>
        </Card>

        <div className="space-y-5 lg:sticky lg:top-6">
          <Card>
            <CardHeader>
              <CardTitle>Imagen</CardTitle>
              <CardDescription>
                Ideal: PNG con fondo transparente y colores claros (el login es oscuro).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              {source ? (
                <div className="flex items-center gap-3 rounded-lg border p-2.5">
                  <div className="grid size-12 shrink-0 place-items-center rounded-md bg-stage">
                    {preview && (
                      <img src={preview.url} alt="" className="max-h-10 max-w-10 object-contain" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">{basename(source)}</div>
                    <div className="text-xs text-muted-foreground">
                      {preview ? `${preview.width}×${preview.height} px` : "Procesando…"}
                    </div>
                  </div>
                </div>
              ) : null}
              <PickButton
                kind="image"
                variant={source ? "secondary" : "default"}
                onPick={(paths) => paths[0] && pick(paths[0])}
              >
                {source ? "Cambiar imagen" : "Elegir imagen"}
              </PickButton>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Alto máximo</Label>
                  <span className="font-mono text-xs text-muted-foreground tabular-nums">
                    {height} px
                  </span>
                </div>
                <Slider
                  min={24}
                  max={200}
                  step={2}
                  value={[height]}
                  onValueChange={(v) => setHeight(v[0] ?? 72)}
                />
                <p className="text-xs text-muted-foreground">
                  72 px es el alto del logo de Ubuntu. Ancho máximo {state?.max_width ?? 480} px.
                </p>
              </div>

              <Button
                className="w-full"
                disabled={!source || !preview || busy}
                onClick={async () => {
                  const ok = await confirm({
                    title: "Aplicar logo del login",
                    description:
                      "Se copia a /usr/share/plymotion y se añade una configuración de GDM. Lo verás la próxima vez que aparezca el login.",
                    confirmLabel: "Aplicar",
                    privileged: true,
                  });
                  if (ok) apply.mutate(undefined);
                }}
              >
                <Wand2 /> Aplicar logo
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="flex items-center justify-between gap-3 pt-5">
              <div className="text-sm">
                <div className="flex items-center gap-2 font-medium whitespace-nowrap">
                  Logo actual
                  {state?.custom_installed ? (
                    <Badge>Personalizado</Badge>
                  ) : (
                    <Badge variant="secondary">De la distro</Badge>
                  )}
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                disabled={!state?.custom_installed || busy}
                onClick={async () => {
                  const ok = await confirm({
                    title: "Restaurar el logo de la distro",
                    description: "Se borran el logo y la configuración que añadió Plymotion.",
                    confirmLabel: "Restaurar",
                    privileged: true,
                  });
                  if (ok) restore.mutate(undefined);
                }}
              >
                <RotateCcw /> Restaurar
              </Button>
            </CardContent>
          </Card>
          {!source && (
            <p className="flex items-center gap-2 px-1 text-xs text-muted-foreground">
              <ImageUp className="size-3.5" /> También puedes arrastrar una imagen a la ventana.
            </p>
          )}
        </div>
      </div>
    </Page>
  );
}
