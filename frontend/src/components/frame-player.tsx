import { useEffect, useMemo, useRef, useState } from "react";
import { cn, frameUrl } from "@/lib/utils";

/** Plymouth's script module refreshes at a fixed 50 Hz and advances one frame per refresh. */
export const PLYMOUTH_HZ = 50;
/** Where generated scripts (and bgrt, and GDM's login logo) place the watermark. */
const WATERMARK_ALIGN = { x: 0.5, y: 0.96 };

type Props = {
  template: string;
  count: number;
  /** Playback rate; defaults to Plymouth's real rate, so what you see is what boots. */
  fps?: number;
  playing?: boolean;
  /** Load at most this many frames, evenly sampled (for lightweight thumbnails). */
  maxFrames?: number;
  /**
   * "fit": scale the frame to fill the box (thumbnails).
   * "screen": draw at true size relative to a simulated screen of `screen` pixels.
   */
  mode?: "fit" | "screen";
  screen?: { width: number; height: number };
  /** Logo drawn where Plymouth draws the theme's watermark (only in "screen" mode). */
  watermark?: string | null;
  className?: string;
  onFrame?: (index: number) => void;
};

function sampleIndexes(count: number, maxFrames?: number): number[] {
  const all = Array.from({ length: count }, (_, i) => i + 1);
  if (!maxFrames || count <= maxFrames) return all;
  const step = count / maxFrames;
  return Array.from({ length: maxFrames }, (_, i) => all[Math.floor(i * step)]!);
}

export function FramePlayer({
  template,
  count,
  fps = PLYMOUTH_HZ,
  playing = true,
  maxFrames,
  mode = "fit",
  screen,
  watermark,
  className,
  onFrame,
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const indexes = useMemo(() => sampleIndexes(count, maxFrames), [count, maxFrames]);
  const images = useMemo(
    () =>
      indexes.map((n) => {
        const img = new Image();
        img.decoding = "async";
        img.src = frameUrl(template, n);
        return img;
      }),
    [template, indexes],
  );
  // Load progress, tied to the image set it counts so a new set starts from 0.
  const [progress, setProgress] = useState<{ images: HTMLImageElement[]; loaded: number }>({
    images: [],
    loaded: 0,
  });
  const loaded = progress.images === images ? progress.loaded : 0;
  // When sampling, keep the loop's duration: skip ahead proportionally.
  const effectiveFps = maxFrames && count > maxFrames ? (fps * indexes.length) / count : fps;

  useEffect(() => {
    let cancelled = false;
    const bump = () =>
      !cancelled &&
      setProgress((prev) =>
        prev.images === images ? { images, loaded: prev.loaded + 1 } : { images, loaded: 1 },
      );
    for (const img of images) {
      if (img.complete && img.naturalWidth > 0) bump();
      else img.addEventListener("load", bump, { once: true });
    }
    return () => {
      cancelled = true;
    };
  }, [images]);

  const watermarkImage = useMemo(() => {
    if (!watermark) return null;
    const img = new Image();
    img.src = watermark;
    return img;
  }, [watermark]);

  const ready = images.length > 0 && loaded >= Math.min(images.length, 1);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !ready) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let frame = 0;
    let raf = 0;
    let last = performance.now();
    let acc = 0;
    const interval = 1000 / effectiveFps;

    const draw = () => {
      const img = images[frame];
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      const w = Math.max(1, Math.round(rect.width * dpr));
      const h = Math.max(1, Math.round(rect.height * dpr));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }
      ctx.clearRect(0, 0, w, h);
      if (!img || !img.complete || img.naturalWidth === 0) return;
      let scale: number;
      if (mode === "screen" && screen) {
        scale = Math.min(w / screen.width, h / screen.height);
      } else {
        scale = Math.min(w / img.naturalWidth, h / img.naturalHeight);
      }
      const dw = img.naturalWidth * scale;
      const dh = img.naturalHeight * scale;
      ctx.imageSmoothingQuality = "high";
      ctx.drawImage(img, (w - dw) / 2, (h - dh) / 2, dw, dh);
      const wm = watermarkImage;
      if (mode === "screen" && screen && wm?.complete && wm.naturalWidth > 0) {
        const ww = wm.naturalWidth * scale;
        const wh = wm.naturalHeight * scale;
        const sx = (w - screen.width * scale) / 2;
        const sy = (h - screen.height * scale) / 2;
        const x = sx + (screen.width - wm.naturalWidth) * WATERMARK_ALIGN.x * scale;
        const y = sy + (screen.height - wm.naturalHeight) * WATERMARK_ALIGN.y * scale;
        ctx.drawImage(wm, x, y, ww, wh);
      }
      onFrame?.(indexes[frame] ?? 1);
    };

    const tick = (now: number) => {
      acc += now - last;
      last = now;
      if (acc >= interval) {
        const steps = Math.floor(acc / interval);
        acc -= steps * interval;
        frame = (frame + steps) % images.length;
        draw();
      }
      raf = requestAnimationFrame(tick);
    };

    draw();
    if (playing && images.length > 1) raf = requestAnimationFrame(tick);
    const observer = new ResizeObserver(draw);
    observer.observe(canvas);
    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
    };
  }, [ready, images, playing, effectiveFps, mode, screen, indexes, onFrame, watermarkImage]);

  return (
    <div className={cn("relative", className)}>
      <canvas ref={canvasRef} className="absolute inset-0 size-full" />
      {images.length > 0 && loaded < images.length && (
        <div className="absolute right-2 bottom-2 rounded-full bg-black/60 px-2 py-0.5 font-mono text-[10px] text-white/70">
          {Math.round((loaded / images.length) * 100)}%
        </div>
      )}
    </div>
  );
}
