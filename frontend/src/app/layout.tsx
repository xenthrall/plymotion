import { Laptop, Moon, PanelLeftClose, PanelLeftOpen, Search, Sun, Upload } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { NavLink, Outlet } from "react-router";
import { useMeta, usePrefs, useUpdatePrefs } from "@/api/queries";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Kbd } from "@/components/ui/kbd";
import { Tooltip } from "@/components/ui/tooltip";
import { useDragActive } from "@/lib/desktop";
import { cn } from "@/lib/utils";
import { ActivityButton } from "./activity";
import { CommandPalette, useCommandPalette } from "./command-palette";
import { NAV_GROUPS } from "./nav";

function Logo({ collapsed }: { collapsed: boolean }) {
  return (
    <div className="flex h-14 items-center gap-2.5 px-4">
      <div className="grid size-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-violet-400 to-violet-700 shadow-md shadow-violet-900/30">
        <svg viewBox="0 0 24 24" className="size-4 fill-white">
          <path d="M8 5.5v13l10.5-6.5z" />
        </svg>
      </div>
      {!collapsed && (
        <div className="leading-tight">
          <div className="text-[15px] font-semibold tracking-tight">Plymotion</div>
          <div className="text-[11px] text-muted-foreground">Arranque animado</div>
        </div>
      )}
    </div>
  );
}

function Sidebar() {
  const { data: prefs } = usePrefs();
  const updatePrefs = useUpdatePrefs();
  const { data: meta } = useMeta();
  const collapsed = prefs?.sidebar_collapsed ?? false;

  return (
    <aside
      className={cn(
        "flex shrink-0 flex-col border-r border-sidebar-border bg-sidebar transition-[width] duration-200",
        collapsed ? "w-[68px]" : "w-60",
      )}
    >
      <Logo collapsed={collapsed} />
      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-3">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            {!collapsed && (
              <div className="mb-1.5 px-2 text-[11px] font-medium tracking-wide text-muted-foreground/80 uppercase">
                {group.label}
              </div>
            )}
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const link = (
                  <NavLink
                    to={item.to}
                    end={item.to === "/"}
                    className={({ isActive }) =>
                      cn(
                        "group relative flex h-9 items-center gap-3 rounded-lg px-2.5 text-sm font-medium transition-colors",
                        isActive
                          ? "bg-primary-soft text-foreground"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground",
                        collapsed && "justify-center px-0",
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && (
                          <motion.span
                            layoutId="nav-indicator"
                            className="absolute top-2 bottom-2 -left-3 w-[3px] rounded-r-full bg-primary"
                          />
                        )}
                        <item.icon
                          className={cn("size-[18px] shrink-0", isActive && "text-primary")}
                        />
                        {!collapsed && <span className="truncate">{item.label}</span>}
                      </>
                    )}
                  </NavLink>
                );
                return collapsed ? (
                  <Tooltip key={item.to} content={item.label} side="right">
                    {link}
                  </Tooltip>
                ) : (
                  <div key={item.to}>{link}</div>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
      <div className="border-t border-sidebar-border p-3">
        {!collapsed && meta && (
          <div className="mb-2 rounded-lg px-2.5 py-2">
            <div className="text-[11px] text-muted-foreground">Tema activo</div>
            <div className="truncate text-sm font-medium">
              {meta.system.default_theme ?? "Desconocido"}
            </div>
          </div>
        )}
        <Button
          variant="ghost"
          size="sm"
          className={cn("w-full justify-start", collapsed && "justify-center")}
          onClick={() => updatePrefs.mutate({ sidebar_collapsed: !collapsed })}
        >
          {collapsed ? <PanelLeftOpen /> : <PanelLeftClose />}
          {!collapsed && "Contraer"}
        </Button>
      </div>
    </aside>
  );
}

function ThemeMenu() {
  const { data: prefs } = usePrefs();
  const updatePrefs = useUpdatePrefs();
  const mode = prefs?.theme ?? "system";
  const Icon = mode === "dark" ? Moon : mode === "light" ? Sun : Laptop;
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label="Apariencia">
          <Icon />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>Apariencia</DropdownMenuLabel>
        <DropdownMenuItem onSelect={() => updatePrefs.mutate({ theme: "dark" })}>
          <Moon /> Oscuro
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => updatePrefs.mutate({ theme: "light" })}>
          <Sun /> Claro
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => updatePrefs.mutate({ theme: "system" })}>
          <Laptop /> Sistema
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function DropOverlay() {
  const active = useDragActive();
  return (
    <AnimatePresence>
      {active && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="pointer-events-none fixed inset-3 z-[60] grid place-items-center rounded-2xl border-2 border-dashed border-primary bg-primary-soft backdrop-blur-sm"
        >
          <div className="flex flex-col items-center gap-3 text-primary">
            <Upload className="size-10" />
            <div className="text-lg font-semibold">Suelta el archivo</div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function Layout() {
  const [paletteOpen, setPaletteOpen] = useCommandPalette();
  return (
    <div className="flex h-full overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b px-6">
          <button
            onClick={() => setPaletteOpen(true)}
            className="flex h-8 w-full max-w-sm items-center gap-2 rounded-lg border bg-muted/40 px-3 text-sm text-muted-foreground transition-colors hover:bg-muted"
          >
            <Search className="size-4" />
            <span className="flex-1 text-left">Buscar…</span>
            <Kbd>Ctrl</Kbd>
            <Kbd>K</Kbd>
          </button>
          <div className="flex items-center gap-1">
            <ActivityButton />
            <ThemeMenu />
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
      <DropOverlay />
    </div>
  );
}
