import { useCallback, useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field, PageLoader, SectionHeader } from "@/components/wv/bits";
import { api, errorMessage } from "@/lib/api";
import { FONTS, LAYOUTS } from "@/lib/constants";
import { InvitationCard } from "@/features/InvitationCard";

const SAMPLE = { title: "Jeroen & Mark", date_text: "14 juni 2027", time_text: "20:00 — 01:00", location: "Landgoed De Wilmersberg" };
const BLANK = { name: "", description: "", layout: "classic", background_color: "#09090B", text_color: "#F4F4F5", accent_color: "#D4AF37", font: "playfair", subtitle: "Let's celebrate!", photo_url: "/images/login.jpg", active: true };
const KEYS = Object.keys(BLANK);

function TemplateDialog({ tpl, onClose, onSaved }) {
  const [form, setForm] = useState(BLANK);
  useEffect(() => tpl && setForm({ ...BLANK, ...tpl }), [tpl]);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v?.target ? v.target.value : v }));
  const submit = async () => {
    const body = Object.fromEntries(KEYS.map((k) => [k, form[k] === "" ? null : form[k]]));
    try {
      if (form.id) await api.put(`/invitation-templates/${form.id}`, body);
      else await api.post("/invitation-templates", body);
      toast.success("Sjabloon opgeslagen");
      onSaved();
    } catch (e) { toast.error(errorMessage(e)); }
  };
  const chips = (key, entries) => (
    <div className="flex flex-wrap gap-2">{entries.map(([k, l]) => <button key={k} type="button" onClick={() => set(key)(k)} data-testid={`tpl-${key}-${k}`} className={`rounded-full border px-3 py-1 text-xs ${form[key] === k ? "border-[#D4AF37] text-white" : "border-white/10 text-zinc-500"}`}>{l}</button>)}</div>
  );
  return (
    <Dialog open={!!tpl} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[92vh] overflow-y-auto rounded-sm border-white/10 bg-[#111114] sm:max-w-3xl" data-testid="template-dialog">
        <DialogHeader><DialogTitle className="font-display text-3xl font-normal">{form.id ? "Sjabloon bewerken" : "Nieuw sjabloon"}</DialogTitle></DialogHeader>
        <div className="grid gap-6 md:grid-cols-[1fr_260px]">
          <div className="space-y-4">
            <Field label="Naam"><Input value={form.name} onChange={set("name")} className="wv-input h-10" data-testid="tpl-name-input" /></Field>
            <Field label="Omschrijving"><Input value={form.description || ""} onChange={set("description")} className="wv-input h-10" data-testid="tpl-description-input" /></Field>
            <Field label="Ondertitel"><Input value={form.subtitle || ""} onChange={set("subtitle")} className="wv-input h-10" data-testid="tpl-subtitle-input" /></Field>
            <Field label="Foto-URL" hint="Bijv. /images/party.jpg"><Input value={form.photo_url || ""} onChange={set("photo_url")} className="wv-input h-10" data-testid="tpl-photo-input" /></Field>
            <Field label="Layout">{chips("layout", Object.entries(LAYOUTS))}</Field>
            <Field label="Lettertype">{chips("font", Object.entries(FONTS).map(([k, f]) => [k, f.label]))}</Field>
            <div className="grid grid-cols-3 gap-3">
              {[["background_color", "Achtergrond"], ["text_color", "Tekst"], ["accent_color", "Accent"]].map(([k, l]) => (
                <Field key={k} label={l}><input type="color" value={form[k]} onChange={set(k)} className="h-10 w-full cursor-pointer bg-transparent" data-testid={`tpl-${k}`} /></Field>
              ))}
            </div>
            <label className="flex items-center gap-3 text-sm text-zinc-300"><Switch checked={form.active} onCheckedChange={set("active")} data-testid="tpl-active-switch" />Zichtbaar voor klanten</label>
          </div>
          <div>
            <InvitationCard inv={{ ...form, ...SAMPLE }} photo={form.photo_url} testId="tpl-preview" />
            <button onClick={submit} disabled={!form.name.trim()} className="wv-btn mt-6 w-full" data-testid="tpl-save-button">Opslaan</button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function AdminTemplates() {
  const [items, setItems] = useState(null);
  const [editing, setEditing] = useState(null);
  const load = useCallback(() => api.get("/invitation-templates").then((r) => setItems(r.data)), []);
  useEffect(() => { load(); }, [load]);
  if (!items) return <PageLoader />;
  const remove = async (t) => {
    if (!window.confirm(`Sjabloon "${t.name}" verwijderen?`)) return;
    await api.delete(`/invitation-templates/${t.id}`);
    load();
  };
  return (
    <div data-testid="admin-templates">
      <SectionHeader eyebrow="Uitnodigingen" title="Sjablonen" text="Deze ontwerpen kunnen klanten kiezen als basis voor hun uitnodiging."
        action={<button onClick={() => setEditing({ ...BLANK })} className="wv-btn" data-testid="create-template-button"><Plus className="h-4 w-4" />Nieuw sjabloon</button>} />
      <div className="grid grid-cols-2 gap-6 md:grid-cols-3 lg:grid-cols-5">
        {items.map((t) => (
          <div key={t.id} className={`group ${t.active ? "" : "opacity-50"}`} data-testid={`template-${t.id}`}>
            <button onClick={() => setEditing(t)} className="block w-full transition-transform duration-300 hover:-translate-y-1" data-testid={`edit-template-${t.id}`}>
              <InvitationCard inv={{ ...t, ...SAMPLE }} photo={t.photo_url} testId={`template-preview-${t.id}`} />
            </button>
            <div className="mt-3 flex items-start justify-between">
              <div><p className="text-sm text-white">{t.name}</p><p className="text-xs text-zinc-500">{t.active ? LAYOUTS[t.layout] : "Verborgen"}</p></div>
              <button onClick={() => remove(t)} className="p-1 text-zinc-700 hover:text-red-400" data-testid={`delete-template-${t.id}`}><Trash2 className="h-3.5 w-3.5" /></button>
            </div>
          </div>
        ))}
      </div>
      <TemplateDialog tpl={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />
    </div>
  );
}
