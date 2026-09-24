import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  Download,
  FolderOpen,
  GalleryHorizontalEnd,
  MonitorPlay,
  MoreHorizontal,
  Search,
  Sparkles,
  Trash2,
  UserRound,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { toast } from "sonner";
import { api, call, errorMessage, type LibraryTheme } from "@/api/client";
import { keys, useJobMutation, useLibrary } from "@/api/queries";
import { BootSimulator } from "@/components/boot-simulator";
import { useConfirm } from "@/components/confirm";
import { FramePlayer } from "@/components/frame-player";
import { EmptyState, Page, PageHeader } from "@/components/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { formatBytes, formatRelative, formatSeconds } from "@/lib/utils";

type Sort = "recent" | "name" | "size";

function ThemeCard({
  theme,
  onSimulate,
}: {
  theme: LibraryTheme;
  onSimulate: () => void;
}) {
  const [hover, setHover] = useState(false);
  const confirm = useConfirm();
  const qc = useQueryClient();

  const install = useJobMutation(() =>
    call(api.POST("/api/library/{slug}/install", { params: { path: { slug: theme.slug } } })),
  );
  const bootLogo = useMutation({
    mutationFn: (enabled: boolean) =>
      call(
        api.POST("/api/library/{slug}/boot-logo", {
          params: { path: { slug: theme.slug } },
          body: { enabled },
        }),
      ),
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: keys.library });
      const verb = updated.boot_logo ? "añadido a" : "quitado de";
      if (updated.installed) {
        toast.success(`Logo ${verb} «${theme.name}»`, {
          description: "Reinstala el tema para que cambie en el arranque.",
          action: { label: "Reinstalar", onClick: () => install.mutate(undefined) },
        });
      } else {
        toast.success(`Logo ${verb} «${theme.name}»`);
      }
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const remove = useMutation({
    mutationFn: () =>
      call(api.DELETE("/api/library/{slug}", { params: { path: { slug: theme.slug } } })),
    onSuccess: () => {
      toast.success(`«${theme.name}» eliminado de la galería`);
      qc.invalidateQueries({ queryKey: keys.library });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.96 }}
      className="group overflow-hidden rounded-xl border bg-card transition-[border-color,box-shadow] hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5"
    >
      <button
        className="relative block aspect-video w-full bg-stage"
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        onClick={onSimulate}
        aria-label={`Simular ${theme.name}`}
      >
        {hover ? (
          <FramePlayer
            template={theme.frame_url_template}
            count={theme.frame_count}
            maxFrames={40}
            className="absolute inset-3"
          />
        ) : (
          theme.thumbnail_url && (
            <img
              src={theme.thumbnail_url}
              alt=""
              loading="lazy"
              className="absolute inset-3 size-[calc(100%-1.5rem)] object-contain"
            />
          )
        )}
        <div className="absolute inset-0 grid place-items-center bg-black/0 opacity-0 transition-all group-hover:bg-black/20 group-hover:opacity-100">
          <span className="flex items-center gap-1.5 rounded-full bg-black/60 px-3 py-1.5 text-xs font-medium text-white backdrop-blur">
            <MonitorPlay className="size-3.5" /> Simular arranque
          </span>
        </div>
        {theme.installed && (
          <Badge variant="success" className="absolute top-2.5 left-2.5 bg-black/60 backdrop-blur">
            <Check /> Instalado
          </Badge>
        )}
      </button>
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <h3 className="truncate font-medium">{theme.name}</h3>
            <p className="text-xs text-muted-foreground">{formatRelative(theme.created_at)}</p>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon-sm" className="-mr-2" aria-label="Más acciones">
                <MoreHorizontal />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={onSimulate}>
                <MonitorPlay /> Simular arranque
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => bootLogo.mutate(!theme.boot_logo)}>
                <UserRound /> {theme.boot_logo ? "Quitar logo del arranque" : "Añadir logo del login al arranque"}
              </DropdownMenuItem>
              <DropdownMenuItem
                onSelect={() =>
                  call(
                    api.POST("/api/library/{slug}/reveal", {
                      params: { path: { slug: theme.slug } },
                    }),
                  ).catch((e) => toast.error(errorMessage(e)))
                }
              >
                <FolderOpen /> Abrir carpeta
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                destructive
                onSelect={async () => {
                  const ok = await confirm({
                    title: `Eliminar «${theme.name}»`,
                    description:
                      "Se borra de la galería local. Si ya está instalado en el sistema, sigue instalado.",
                    confirmLabel: "Eliminar",
                    destructive: true,
                  });
                  if (ok) remove.mutate();
                }}
              >
                <Trash2 /> Eliminar
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          <Badge variant="secondary">
            {theme.width}×{theme.height}
          </Badge>
          <Badge variant="secondary">{theme.frame_count} frames</Badge>
          <Badge variant="secondary">{formatSeconds(theme.loop_seconds)}</Badge>
          <Badge variant="secondary">{formatBytes(theme.total_bytes)}</Badge>
          {theme.boot_logo && (
            <Badge>
              <UserRound /> Logo
            </Badge>
          )}
        </div>
        <Button
          className="mt-4 w-full"
          variant={theme.installed ? "secondary" : "default"}
          size="sm"
          disabled={install.isPending}
          onClick={async () => {
            const ok = await confirm({
              title: `${theme.installed ? "Reinstalar" : "Instalar"} «${theme.name}»`,
              description:
                "Se copia al sistema, se activa como animación de arranque y se regenera el initramfs. Si ya existía un tema con este nombre, se guarda un backup.",
              confirmLabel: "Instalar y activar",
              privileged: true,
            });
            if (ok) install.mutate(undefined);
          }}
        >
          <Download /> {theme.installed ? "Reinstalar y activar" : "Instalar y activar"}
        </Button>
      </div>
    </motion.div>
  );
}

export function GalleryPage() {
  const { data: themes, isLoading } = useLibrary();
  const [params, setParams] = useSearchParams();
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<Sort>("recent");
  const simulated = themes?.find((t) => t.slug === params.get("tema")) ?? null;

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = (themes ?? []).filter((t) => !q || t.name.toLowerCase().includes(q));
    if (sort === "name") list.sort((a, b) => a.name.localeCompare(b.name));
    if (sort === "size") list.sort((a, b) => b.total_bytes - a.total_bytes);
    return list;
  }, [themes, query, sort]);

  return (
    <Page>
      <PageHeader
        title="Galería"
        description="Los temas que has generado. Pasa el cursor para verlos animados."
        actions={
          <Button asChild>
            <Link to="/crear">
              <Sparkles /> Nuevo tema
            </Link>
          </Button>
        }
      />

      {(themes?.length ?? 0) > 0 && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div className="relative w-full max-w-xs">
            <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-9"
              placeholder="Buscar por nombre"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <ToggleGroup type="single" value={sort} onValueChange={(v) => v && setSort(v as Sort)}>
            <ToggleGroupItem value="recent">Recientes</ToggleGroupItem>
            <ToggleGroupItem value="name">Nombre</ToggleGroupItem>
            <ToggleGroupItem value="size">Peso</ToggleGroupItem>
          </ToggleGroup>
        </div>
      )}

      {isLoading ? (
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-80 rounded-xl" />
          ))}
        </div>
      ) : themes?.length === 0 ? (
        <EmptyState
          icon={GalleryHorizontalEnd}
          title="Tu galería está vacía"
          description="Crea tu primer tema a partir de un video o GIF y aparecerá aquí."
          action={
            <Button asChild>
              <Link to="/crear">
                <Sparkles /> Crear tema
              </Link>
            </Button>
          }
        />
      ) : (
        <motion.div layout className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          <AnimatePresence>
            {visible.map((theme) => (
              <ThemeCard
                key={theme.slug}
                theme={theme}
                onSimulate={() => setParams({ tema: theme.slug })}
              />
            ))}
          </AnimatePresence>
          {visible.length === 0 && (
            <p className="col-span-full py-10 text-center text-sm text-muted-foreground">
              Ningún tema coincide con «{query}».
            </p>
          )}
        </motion.div>
      )}

      {simulated && (
        <BootSimulator
          open
          onOpenChange={(open) => !open && setParams({})}
          name={simulated.name}
          template={simulated.frame_url_template}
          count={simulated.frame_count}
          size={{ width: simulated.width, height: simulated.height }}
          watermark={simulated.watermark_url}
        />
      )}
    </Page>
  );
}
