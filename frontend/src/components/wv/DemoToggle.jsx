import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Switch } from "@/components/ui/switch";
import { api, errorMessage } from "@/lib/api";

// Admin-only: zet de demo-inhoud (voorbeeldklanten, -DJ's en -events) aan of uit.
export default function DemoToggle({ onChange }) {
  const [state, setState] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.get("/admin/demo").then((r) => setState(r.data)).catch(() => setState(null)); }, []);
  if (!state) return null;

  const toggle = async (enabled) => {
    if (!enabled && !window.confirm("Alle demo-klanten, demo-DJ's en hun events (met chat, muziek, draaischema en bestanden) worden verwijderd. Doorgaan?")) return;
    setBusy(true);
    try {
      const { data } = await api.post("/admin/demo", { enabled });
      setState(data);
      toast.success(enabled ? "Demo-inhoud toegevoegd" : "Demo-inhoud verwijderd");
      onChange?.();
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section data-testid="admin-demo-toggle" className="flex items-start justify-between gap-6 border-y border-white/[0.06] py-6">
      <div>
        <p className="font-display text-2xl text-white">Demo-inhoud</p>
        <p className="mt-1 max-w-xl text-sm text-zinc-500">
          Voorbeeldklanten, twee demo-DJ's en {state.enabled ? `${state.events} events` : "drie events"} om de portal te laten zien.
          Uitzetten verwijdert alleen deze demo-gegevens; echte klanten en events blijven staan.
        </p>
      </div>
      <Switch checked={state.enabled} disabled={busy} onCheckedChange={toggle} data-testid="admin-demo-switch" />
    </section>
  );
}
