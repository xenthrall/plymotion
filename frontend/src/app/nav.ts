import {
  Film,
  GalleryHorizontalEnd,
  Images,
  LayoutDashboard,
  type LucideIcon,
  MonitorCog,
  UserRound,
} from "lucide-react";

export type NavItem = { to: string; label: string; icon: LucideIcon; description: string };

export const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: "General",
    items: [
      { to: "/", label: "Inicio", icon: LayoutDashboard, description: "Estado del sistema" },
      { to: "/crear", label: "Crear tema", icon: Film, description: "Video o GIF a animación" },
    ],
  },
  {
    label: "Temas",
    items: [
      {
        to: "/galeria",
        label: "Galería",
        icon: GalleryHorizontalEnd,
        description: "Temas generados",
      },
      { to: "/sistema", label: "Sistema", icon: MonitorCog, description: "Temas instalados" },
    ],
  },
  {
    label: "Extras",
    items: [
      { to: "/login", label: "Logo del login", icon: UserRound, description: "Pantalla de GDM" },
      { to: "/secuencias", label: "Secuencias", icon: Images, description: "Imágenes a video" },
    ],
  },
];

export const NAV_ITEMS = NAV_GROUPS.flatMap((g) => g.items);
