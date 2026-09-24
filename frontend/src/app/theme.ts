import { useEffect } from "react";
import { usePrefs } from "@/api/queries";

/** Apply the persisted light/dark/system preference to <html>. */
export function useApplyTheme() {
  const { data: prefs } = usePrefs();
  const mode = prefs?.theme ?? "system";

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = () => {
      const dark = mode === "dark" || (mode === "system" && media.matches);
      document.documentElement.classList.toggle("dark", dark);
    };
    apply();
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [mode]);
}
