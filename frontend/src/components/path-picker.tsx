import { FolderOpen } from "lucide-react";
import { useState, type ReactNode } from "react";
import { pickFiles, useMeta } from "@/api/queries";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Kind = "video" | "image" | "images";

/**
 * Opens the native file dialog through the API. When the host has none
 * (browser dev mode without zenity), falls back to typing a path.
 */
export function PickButton({
  kind,
  onPick,
  children,
  variant = "default",
  size = "default",
}: {
  kind: Kind;
  onPick: (paths: string[]) => void;
  children: ReactNode;
  variant?: "default" | "secondary" | "outline";
  size?: "default" | "sm" | "lg";
}) {
  const { data: meta } = useMeta();
  const [manual, setManual] = useState("");
  const [busy, setBusy] = useState(false);

  if (meta && !meta.capabilities.native_dialogs) {
    return (
      <form
        className="flex w-full max-w-md gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const paths = manual.split("\n").map((p) => p.trim()).filter(Boolean);
          if (paths.length) onPick(paths);
        }}
      >
        <Input
          placeholder="/ruta/al/archivo"
          value={manual}
          onChange={(e) => setManual(e.target.value)}
        />
        <Button type="submit" variant={variant} size={size}>
          Usar ruta
        </Button>
      </form>
    );
  }

  return (
    <Button
      variant={variant}
      size={size}
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        const paths = await pickFiles(kind);
        setBusy(false);
        if (paths && paths.length) onPick(paths);
      }}
    >
      <FolderOpen />
      {children}
    </Button>
  );
}
