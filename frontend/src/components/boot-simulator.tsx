import { Monitor, Pause, Play } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { formatSeconds } from "@/lib/utils";
import { FramePlayer, PLYMOUTH_HZ } from "./frame-player";

const SCREENS = [
  { id: "1366x768", width: 1366, height: 768 },
  { id: "1920x1080", width: 1920, height: 1080 },
  { id: "1920x1200", width: 1920, height: 1200 },
  { id: "2560x1440", width: 2560, height: 1440 },
];

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  name: string;
  template: string;
  count: number;
  size?: { width: number; height: number };
};

/**
 * Plays a theme exactly as Plymouth will: every frame, 50 per second, centered
 * at its real pixel size on a black screen of the chosen resolution.
 */
export function BootSimulator({ open, onOpenChange, name, template, count, size }: Props) {
  const [screenId, setScreenId] = useState("1920x1080");
  const [playing, setPlaying] = useState(true);
  const screen = SCREENS.find((s) => s.id === screenId) ?? SCREENS[1]!;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl gap-0 overflow-hidden p-0" hideClose>
        <div className="flex items-center justify-between gap-4 border-b px-5 py-3">
          <div className="min-w-0">
            <DialogTitle className="truncate text-base">Simulador de arranque · {name}</DialogTitle>
            <DialogDescription className="text-xs">
              {count} frames a {PLYMOUTH_HZ} Hz = {formatSeconds(count / PLYMOUTH_HZ)} por loop
              {size ? ` · ${size.width}×${size.height} máx.` : ""}
            </DialogDescription>
          </div>
          <div className="flex items-center gap-2">
            <ToggleGroup
              type="single"
              value={screenId}
              onValueChange={(v) => v && setScreenId(v)}
              aria-label="Resolución de pantalla simulada"
            >
              {SCREENS.map((s) => (
                <ToggleGroupItem key={s.id} value={s.id}>
                  {s.id === "1920x1080" && <Monitor />}
                  {s.id.replace("x", "×")}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
            <Button
              variant="secondary"
              size="icon-sm"
              onClick={() => setPlaying((p) => !p)}
              aria-label={playing ? "Pausar" : "Reproducir"}
            >
              {playing ? <Pause /> : <Play />}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)}>
              Cerrar
            </Button>
          </div>
        </div>
        <div className="bg-black p-6">
          <div
            className="relative mx-auto w-full overflow-hidden rounded-md bg-black ring-1 ring-white/10"
            style={{ aspectRatio: `${screen.width} / ${screen.height}`, maxHeight: "70vh" }}
          >
            {open && (
              <FramePlayer
                template={template}
                count={count}
                playing={playing}
                mode="screen"
                screen={screen}
                className="size-full"
              />
            )}
          </div>
          <p className="mt-3 text-center text-[11px] text-white/40">
            Así se verá al arrancar: Plymouth centra la animación a su tamaño real sobre fondo
            negro.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
