import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Clapperboard, FolderOpen, Images, Trash2, Wand2, X } from "lucide-react";
import { useCallback, useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";
import { api, call, errorMessage } from "@/api/client";
import { useJob } from "@/api/jobs";
import { keys, useJobMutation, useSequenceOutputs } from "@/api/queries";
import { useConfirm } from "@/components/confirm";
import { JobProgress } from "@/components/job-status";
import { EmptyState, Page, PageHeader } from "@/components/page";
import { PickButton } from "@/components/path-picker";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { hasExtension, IMAGE_EXTENSIONS, useFileDrop } from "@/lib/desktop";
import { basename, formatBytes, formatRelative } from "@/lib/utils";

const collator = new Intl.Collator("es", { numeric: true });
const mediaUrl = (path: string) => `/api/media?path=${encodeURIComponent(path)}`;

export function SequencesPage() {
  const [images, setImages] = useState<string[]>([]);
  const [name, setName] = useState("video-restaurado");
  const [format, setFormat] = useState<"mp4" | "gif">("mp4");
  const [fps, setFps] = useState(24);
  const [maxWidth, setMaxWidth] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const job = useJob(jobId);
  const { data: outputs } = useSequenceOutputs();
  const navigate = useNavigate();
  const confirm = useConfirm();
  const qc = useQueryClient();

  const add = useCallback((paths: string[]) => {
    const valid = paths.filter((p) => hasExtension(p, IMAGE_EXTENSIONS));
    if (valid.length < paths.length) toast.warning("Se ignoraron archivos que no son imágenes.");
    setImages((prev) => [...new Set([...prev, ...valid])].sort(collator.compare));
  }, []);
  useFileDrop(add);

  const build = useJobMutation(() =>
    call(
      api.POST("/api/sequences", {
        body: {
          images,
          name: name.trim() || "video-restaurado",
          format,
          fps,
          max_width: maxWidth ? Number(maxWidth) : null,
        },
      }),
    ),
  );

  const remove = useMutation({
    mutationFn: (filename: string) =>
      call(api.DELETE("/api/sequences/outputs/{filename}", { params: { path: { filename } } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.sequences }),
    onError: (e) => toast.error(errorMessage(e)),
  });

  return (
    <Page>
      <PageHeader
        title="Secuencias"
        description="Une una serie de imágenes en un video o GIF, por ejemplo para recuperar la animación de un tema o preparar un clip."
        actions={
          <Button
            variant="secondary"
            onClick={() =>
              call(api.POST("/api/sequences/outputs/reveal")).catch((e) =>
                toast.error(errorMessage(e)),
              )
            }
          >
            <FolderOpen /> Abrir carpeta
          </Button>
        }
      />

      <div className="grid items-start gap-5 lg:grid-cols-[1fr_320px]">
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle>Imágenes</CardTitle>
              <CardDescription>
                {images.length
                  ? `${images.length} en orden natural (frame2 antes que frame10)`
                  : "Elige o arrastra las imágenes"}
              </CardDescription>
            </div>
            <div className="flex gap-2">
              {images.length > 0 && (
                <Button variant="ghost" size="sm" onClick={() => setImages([])}>
                  Limpiar
                </Button>
              )}
              <PickButton kind="images" size="sm" variant="secondary" onPick={add}>
                Añadir
              </PickButton>
            </div>
          </CardHeader>
          <CardContent>
            {images.length === 0 ? (
              <EmptyState
                icon={Images}
                title="Sin imágenes"
                description="PNG, JPG, WebP o BMP. Se ordenan por nombre de forma natural."
                action={
                  <PickButton kind="images" onPick={add}>
                    Elegir imágenes
                  </PickButton>
                }
              />
            ) : (
              <div className="grid max-h-[460px] grid-cols-4 gap-2 overflow-y-auto pr-1 sm:grid-cols-6">
                {images.slice(0, 120).map((path, i) => (
                  <div key={path} className="group relative aspect-square overflow-hidden rounded-md bg-stage">
                    <img src={mediaUrl(path)} alt="" loading="lazy" className="size-full object-contain" />
                    <span className="absolute bottom-1 left-1 rounded bg-black/60 px-1 font-mono text-[9px] text-white/80">
                      {i + 1}
                    </span>
                    <button
                      className="absolute top-1 right-1 hidden rounded bg-black/60 p-0.5 text-white group-hover:block"
                      onClick={() => setImages((prev) => prev.filter((p) => p !== path))}
                      aria-label={`Quitar ${basename(path)}`}
                    >
                      <X className="size-3" />
                    </button>
                  </div>
                ))}
                {images.length > 120 && (
                  <div className="col-span-full py-2 text-center text-xs text-muted-foreground">
                    y {images.length - 120} más
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:sticky lg:top-6">
          <CardHeader>
            <CardTitle>Salida</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="seq-name">Nombre</Label>
              <Input id="seq-name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Formato</Label>
              <ToggleGroup
                type="single"
                value={format}
                onValueChange={(v) => v && setFormat(v as "mp4" | "gif")}
                className="grid w-full grid-cols-2"
              >
                <ToggleGroupItem value="mp4">MP4 (H.264)</ToggleGroupItem>
                <ToggleGroupItem value="gif">GIF</ToggleGroupItem>
              </ToggleGroup>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label>FPS</Label>
                <Select value={String(fps)} onValueChange={(v) => setFps(Number(v))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[12, 15, 24, 25, 30, 50, 60].map((f) => (
                      <SelectItem key={f} value={String(f)}>
                        {f} fps
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="seq-width">Ancho máx.</Label>
                <Input
                  id="seq-width"
                  inputMode="numeric"
                  placeholder={format === "gif" ? "480" : "Original"}
                  value={maxWidth}
                  onChange={(e) => setMaxWidth(e.target.value.replace(/\D/g, ""))}
                />
              </div>
            </div>
            {job?.state === "running" && <JobProgress job={job} />}
            <Button
              className="w-full"
              disabled={images.length === 0 || job?.state === "running"}
              onClick={async () => {
                const created = await build.mutateAsync(undefined).catch(() => null);
                if (created) setJobId(created.id);
              }}
            >
              <Wand2 /> Crear {format.toUpperCase()}
            </Button>
          </CardContent>
        </Card>
      </div>

      {outputs && outputs.length > 0 && (
        <div className="mt-10">
          <h2 className="mb-4 text-lg font-semibold tracking-tight">Generados</h2>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {outputs.map((output) => (
              <Card key={output.filename} className="overflow-hidden">
                <div className="aspect-video bg-stage">
                  {output.filename.endsWith(".gif") ? (
                    <img src={output.url} alt="" className="size-full object-contain" />
                  ) : (
                    <video src={output.url} className="size-full object-contain" controls muted loop />
                  )}
                </div>
                <div className="flex items-center justify-between gap-2 p-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium">{output.filename}</div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Badge variant="secondary">{formatBytes(output.size_bytes)}</Badge>
                      {formatRelative(output.created_at)}
                    </div>
                  </div>
                  <div className="flex shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate(`/crear?video=${encodeURIComponent(output.path)}`)}
                    >
                      <Clapperboard /> Crear tema
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label="Eliminar"
                      onClick={async () => {
                        const ok = await confirm({
                          title: `Eliminar ${output.filename}`,
                          description: "Se borra el archivo del disco.",
                          confirmLabel: "Eliminar",
                          destructive: true,
                        });
                        if (ok) remove.mutate(output.filename);
                      }}
                    >
                      <Trash2 />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </Page>
  );
}
