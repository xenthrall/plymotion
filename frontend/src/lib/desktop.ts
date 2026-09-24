import { useEffect, useState } from "react";

/**
 * Files dropped onto the desktop window. WebKit never exposes a dropped
 * file's real path to page JS, so the pywebview shell (plymotion/desktop.py)
 * catches the drop natively and re-dispatches it as `plymotion:drop` with
 * absolute paths.
 */
export function useFileDrop(onDrop: (paths: string[]) => void) {
  useEffect(() => {
    const handler = (event: Event) => {
      const paths = (event as CustomEvent<string[]>).detail;
      if (Array.isArray(paths) && paths.length) onDrop(paths);
    };
    window.addEventListener("plymotion:drop", handler);
    return () => window.removeEventListener("plymotion:drop", handler);
  }, [onDrop]);
}

/** Whether files are being dragged over the window (for the drop overlay). */
export function useDragActive(): boolean {
  const [active, setActive] = useState(false);
  useEffect(() => {
    let depth = 0;
    const hasFiles = (e: DragEvent) => Array.from(e.dataTransfer?.types ?? []).includes("Files");
    const enter = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      depth += 1;
      setActive(true);
    };
    const leave = () => {
      depth = Math.max(0, depth - 1);
      if (depth === 0) setActive(false);
    };
    const over = (e: DragEvent) => {
      if (hasFiles(e)) e.preventDefault();
    };
    const drop = (e: DragEvent) => {
      e.preventDefault();
      depth = 0;
      setActive(false);
    };
    window.addEventListener("dragenter", enter);
    window.addEventListener("dragleave", leave);
    window.addEventListener("dragover", over);
    window.addEventListener("drop", drop);
    return () => {
      window.removeEventListener("dragenter", enter);
      window.removeEventListener("dragleave", leave);
      window.removeEventListener("dragover", over);
      window.removeEventListener("drop", drop);
    };
  }, []);
  return active;
}

export const VIDEO_EXTENSIONS = ["mp4", "mkv", "webm", "avi", "mov", "m4v", "gif"];
export const IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "webp", "bmp"];

export function hasExtension(path: string, extensions: string[]): boolean {
  const ext = path.split(".").pop()?.toLowerCase() ?? "";
  return extensions.includes(ext);
}
