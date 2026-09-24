import { ShieldCheck } from "lucide-react";
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type ConfirmOptions = {
  title: string;
  description: ReactNode;
  confirmLabel?: string;
  destructive?: boolean;
  /** Shows a notice that the system will ask for the admin password (pkexec). */
  privileged?: boolean;
};

const ConfirmContext = createContext<(options: ConfirmOptions) => Promise<boolean>>(
  async () => false,
);

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const resolver = useRef<((value: boolean) => void) | null>(null);

  const confirm = useCallback((next: ConfirmOptions) => {
    setOptions(next);
    return new Promise<boolean>((resolve) => {
      resolver.current = resolve;
    });
  }, []);

  const close = (value: boolean) => {
    resolver.current?.(value);
    resolver.current = null;
    setOptions(null);
  };

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      <Dialog open={options !== null} onOpenChange={(open) => !open && close(false)}>
        {options && (
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{options.title}</DialogTitle>
              <DialogDescription asChild>
                <div>{options.description}</div>
              </DialogDescription>
            </DialogHeader>
            {options.privileged && (
              <div className="flex items-start gap-3 rounded-lg border bg-muted/50 p-3 text-[13px] text-muted-foreground">
                <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" />
                <span>
                  El sistema te pedirá la contraseña de administrador una sola vez para esta
                  acción.
                </span>
              </div>
            )}
            <DialogFooter>
              <Button variant="ghost" onClick={() => close(false)}>
                Cancelar
              </Button>
              <Button
                variant={options.destructive ? "destructive" : "default"}
                onClick={() => close(true)}
                autoFocus
              >
                {options.confirmLabel ?? "Continuar"}
              </Button>
            </DialogFooter>
          </DialogContent>
        )}
      </Dialog>
    </ConfirmContext.Provider>
  );
}

export function useConfirm() {
  return useContext(ConfirmContext);
}
