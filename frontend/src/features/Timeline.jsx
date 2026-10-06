import { useCallback, useEffect, useState } from "react";
import { Check, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field, SectionHeader, EmptyState } from "@/components/wv/bits";
import { useAuth } from "@/context/AuthContext";
import { useEvent } from "@/context/EventContext";
import { api, errorMessage } from "@/lib/api";
import { TIMELINE_ICONS } from "@/lib/constants";

const EMPTY = { time: "", title: "", description: "", icon: "sparkles" };

function ItemDialog({ item, onClose, onSave }) {
  const [form, setForm] = useState(item || EMPTY);
  useEffect(() => setForm(item || EMPTY), [item]);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  return (
    <Dialog open={!!item} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="rounded-sm border-white/10 bg-[#111114] sm:max-w-lg" data-testid="timeline-dialog">
        <DialogHeader><DialogTitle className="font-display text-3xl font-normal">{form.id ? "Moment aanpassen" : "Nieuw moment"}</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-[120px_1fr] gap-3">
            <Field label="Tijd"><Input type="time" value={form.time} onChange={set("time")} className="wv-input h-11" data-testid="timeline-time-input" /></Field>
            <Field label="Wat gebeurt er"><Input value={form.title} onChange={set("title")} className="wv-input h-11" placeholder="Openingsdans" data-testid="timeline-title-input" /></Field>
          </div>
          <Field label="Toelichting"><Textarea rows={2} value={form.description || ""} onChange={set("description")} className="wv-input" data-testid="timeline-description-input" /></Field>
          <Field label="Icoon">
            <div className="flex flex-wrap gap-2">
              {Object.entries(TIMELINE_ICONS).map(([k, { icon: Icon, label }]) => (
                <button key={k} type="button" title={label} onClick={() => setForm((f) => ({ ...f, icon: k }))} data-testid={`timeline-icon-${k}`} className={`flex h-10 w-10 items-center justify-center rounded-full border ${form.icon === k ? "border-[#D4AF37] text-[#D4AF37]" : "border-white/10 text-zinc-500 hover:text-white"}`}>
                  <Icon className="h-4 w-4" />
                </button>
              ))}
            </div>
          </Field>
          <button onClick={() => onSave(form)} className="wv-btn w-full" data-testid="timeline-save-button">Opslaan</button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Row({ item, canEdit, isStaff, onEdit, onDelete, onConfirm, index }) {
  const Icon = (TIMELINE_ICONS[item.icon] || TIMELINE_ICONS.sparkles).icon;
  const suggested = item.status === "suggested";
  return (
    <li className="wv-rise group grid grid-cols-[72px_32px_1fr] gap-4 sm:grid-cols-[120px_40px_1fr] sm:gap-6" style={{ animationDelay: `${index * 60}ms` }} data-testid={`timeline-item-${item.id}`}>
      <p className="font-display pt-1 text-right text-3xl tabular-nums text-white sm:text-5xl">{item.time}</p>
      <div className="relative flex justify-center">
        <span className="absolute bottom-[-2rem] top-0 w-px bg-white/10 group-last:hidden" />
        <span className={`relative mt-2 flex h-8 w-8 items-center justify-center rounded-full sm:h-10 sm:w-10 ${suggested ? "border border-dashed border-[#D4AF37]/60 bg-[#09090B] text-[#D4AF37]" : "bg-[#D4AF37] text-black"}`}>
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <div className="pb-10">
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-lg font-medium text-white sm:text-xl">{item.title}</p>
          {suggested && <span className="rounded-full border border-dashed border-[#D4AF37]/50 px-2 py-0.5 text-[10px] uppercase tracking-wider text-[#E5C158]" data-testid={`timeline-suggested-${item.id}`}>Voorstel</span>}
        </div>
        {item.description && <p className="mt-1 text-sm text-zinc-400">{item.description}</p>}
        <div className="mt-3 flex gap-3 text-xs text-zinc-500 sm:opacity-0 sm:transition-opacity sm:duration-200 sm:group-hover:opacity-100">
          {isStaff && suggested && <button onClick={() => onConfirm(item)} className="flex items-center gap-1 hover:text-[#D4AF37]" data-testid={`timeline-confirm-${item.id}`}><Check className="h-3.5 w-3.5" />Bevestigen</button>}
          {canEdit && <button onClick={() => onEdit(item)} className="flex items-center gap-1 hover:text-white" data-testid={`timeline-edit-${item.id}`}><Pencil className="h-3.5 w-3.5" />Aanpassen</button>}
          {canEdit && <button onClick={() => onDelete(item)} className="flex items-center gap-1 hover:text-red-400" data-testid={`timeline-delete-${item.id}`}><Trash2 className="h-3.5 w-3.5" />Verwijderen</button>}
        </div>
      </div>
    </li>
  );
}

export default function Timeline() {
  const { event, reload } = useEvent();
  const { isStaff } = useAuth();
  const [items, setItems] = useState([]);
  const [editing, setEditing] = useState(null);

  const load = useCallback(() => api.get(`/events/${event.id}/timeline`).then((r) => setItems(r.data)), [event.id]);
  useEffect(() => { load(); }, [load]);

  const refresh = async () => { await load(); reload(); };
  const run = async (fn, msg) => {
    try { await fn(); await refresh(); if (msg) toast.success(msg); } catch (e) { toast.error(errorMessage(e)); }
  };
  const save = (form) => run(async () => {
    const payload = { time: form.time, title: form.title, description: form.description || null, icon: form.icon };
    if (form.id) await api.patch(`/timeline/${form.id}`, payload);
    else await api.post(`/events/${event.id}/timeline`, payload);
    setEditing(null);
  }, isStaff || form.id ? "Opgeslagen" : "Voorstel verstuurd naar White Vision");

  return (
    <div data-testid="timeline">
      <SectionHeader
        eyebrow="Draaischema"
        title="De avond, minuut voor minuut"
        text={isStaff ? "Bevestig voorstellen van de klant om ze definitief te maken." : "Gouden momenten zijn bevestigd door White Vision. Je eigen voorstellen hebben een stippellijn."}
        action={<button onClick={() => setEditing({ ...EMPTY })} className="wv-btn" data-testid="timeline-add-button"><Plus className="h-4 w-4" />{isStaff ? "Moment toevoegen" : "Moment voorstellen"}</button>}
      />
      {items.length === 0 ? (
        <EmptyState title="Nog geen draaischema" text="Voeg het eerste moment toe, bijvoorbeeld de ontvangst van de gasten." />
      ) : (
        <ol className="mt-4 max-w-3xl">
          {items.map((it, i) => (
            <Row key={it.id} index={i} item={it} isStaff={isStaff} canEdit={isStaff || it.status === "suggested"} onEdit={setEditing}
              onDelete={(x) => run(() => api.delete(`/timeline/${x.id}`))}
              onConfirm={(x) => run(() => api.patch(`/timeline/${x.id}`, { status: "confirmed" }), "Bevestigd")} />
          ))}
        </ol>
      )}
      <ItemDialog item={editing} onClose={() => setEditing(null)} onSave={save} />
    </div>
  );
}
