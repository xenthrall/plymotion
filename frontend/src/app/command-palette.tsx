import { Command } from "cmdk";
import { Laptop, Moon, Search, Sun } from "lucide-react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { useLibrary, useUpdatePrefs } from "@/api/queries";
import { Kbd } from "@/components/ui/kbd";
import { NAV_ITEMS } from "./nav";

export function useCommandPalette() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key.toLowerCase() === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return [open, setOpen] as const;
}

const itemClass =
  "flex cursor-default items-center gap-3 rounded-md px-3 py-2 text-sm outline-none data-[selected=true]:bg-muted [&_svg]:size-4 [&_svg]:text-muted-foreground";
const groupClass =
  "[&_[cmdk-group-heading]]:px-3 [&_[cmdk-group-heading]]:pt-3 [&_[cmdk-group-heading]]:pb-1 [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground";

export function CommandPalette({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const navigate = useNavigate();
  const { data: library } = useLibrary();
  const updatePrefs = useUpdatePrefs();

  const run = (fn: () => void) => {
    onOpenChange(false);
    fn();
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-[2px] data-[state=open]:animate-[fade-in_120ms]" />
        <DialogPrimitive.Content className="fixed top-[18%] left-1/2 z-50 w-[calc(100%-2rem)] max-w-xl -translate-x-1/2 overflow-hidden rounded-xl border bg-popover shadow-2xl outline-none">
          <DialogPrimitive.Title className="sr-only">Buscar acciones</DialogPrimitive.Title>
          <Command loop>
            <div className="flex items-center gap-3 border-b px-4">
              <Search className="size-4 text-muted-foreground" />
              <Command.Input
                autoFocus
                placeholder="Buscar páginas, temas o acciones…"
                className="h-12 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              />
              <Kbd>Esc</Kbd>
            </div>
            <Command.List className="max-h-80 overflow-y-auto p-2">
              <Command.Empty className="py-10 text-center text-sm text-muted-foreground">
                Sin resultados.
              </Command.Empty>
              <Command.Group heading="Ir a" className={groupClass}>
                {NAV_ITEMS.map((item) => (
                  <Command.Item
                    key={item.to}
                    value={`${item.label} ${item.description}`}
                    className={itemClass}
                    onSelect={() => run(() => navigate(item.to))}
                  >
                    <item.icon />
                    <span>{item.label}</span>
                    <span className="ml-auto text-xs text-muted-foreground">{item.description}</span>
                  </Command.Item>
                ))}
              </Command.Group>
              {library && library.length > 0 && (
                <Command.Group heading="Temas de la galería" className={groupClass}>
                  {library.slice(0, 8).map((theme) => (
                    <Command.Item
                      key={theme.slug}
                      value={`tema ${theme.name} ${theme.slug}`}
                      className={itemClass}
                      onSelect={() => run(() => navigate(`/galeria?tema=${theme.slug}`))}
                    >
                      <img
                        src={theme.thumbnail_url ?? undefined}
                        alt=""
                        className="size-5 rounded bg-black object-contain"
                      />
                      <span>{theme.name}</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              )}
              <Command.Group heading="Apariencia" className={groupClass}>
                <Command.Item
                  className={itemClass}
                  onSelect={() => run(() => updatePrefs.mutate({ theme: "dark" }))}
                >
                  <Moon /> Tema oscuro
                </Command.Item>
                <Command.Item
                  className={itemClass}
                  onSelect={() => run(() => updatePrefs.mutate({ theme: "light" }))}
                >
                  <Sun /> Tema claro
                </Command.Item>
                <Command.Item
                  className={itemClass}
                  onSelect={() => run(() => updatePrefs.mutate({ theme: "system" }))}
                >
                  <Laptop /> Seguir al sistema
                </Command.Item>
              </Command.Group>
            </Command.List>
          </Command>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
