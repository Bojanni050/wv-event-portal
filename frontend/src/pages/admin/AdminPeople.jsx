import { useCallback, useEffect, useState } from "react";
import { KeyRound, Pencil, Plus } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field, PageLoader, SectionHeader } from "@/components/wv/bits";
import { api, errorMessage } from "@/lib/api";

const COPY = {
  customers: { eyebrow: "Klanten", title: "Klanten", single: "klant", noteKey: "notes", noteLabel: "Notities" },
  djs: { eyebrow: "Team", title: "DJ's", single: "DJ", noteKey: "bio", noteLabel: "Bio" },
};

function PersonDialog({ kind, person, onClose, onSaved }) {
  const c = COPY[kind];
  const [form, setForm] = useState({});
  useEffect(() => setForm(person ? { name: "", email: "", phone: "", notes: "", bio: "", password: "", ...person } : {}), [person]);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const submit = async () => {
    const payload = { name: form.name, email: form.email || null, phone: form.phone || null, notes: form.notes || null, bio: form.bio || null, password: form.password || null };
    try {
      if (form.id) await api.patch(`/${kind}/${form.id}`, payload);
      else await api.post(`/${kind}`, payload);
      toast.success("Opgeslagen");
      onSaved();
    } catch (e) { toast.error(errorMessage(e)); }
  };
  return (
    <Dialog open={!!person} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="rounded-sm border-white/10 bg-[#111114] sm:max-w-lg" data-testid="person-dialog">
        <DialogHeader><DialogTitle className="font-display text-3xl font-normal">{form.id ? form.name : `Nieuwe ${c.single}`}</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <Field label="Naam"><Input value={form.name || ""} onChange={set("name")} className="wv-input h-11" data-testid="person-name-input" /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="E-mail"><Input type="email" value={form.email || ""} onChange={set("email")} className="wv-input h-11" data-testid="person-email-input" /></Field>
            <Field label="Telefoon"><Input value={form.phone || ""} onChange={set("phone")} className="wv-input h-11" data-testid="person-phone-input" /></Field>
          </div>
          <Field label={c.noteLabel}><Textarea rows={3} value={form[c.noteKey] || ""} onChange={set(c.noteKey)} className="wv-input" data-testid="person-note-input" /></Field>
          {!form.has_login && (
            <Field label="Wachtwoord voor login" hint="Optioneel. Vul in om direct een account aan te maken (min. 8 tekens). Deel het wachtwoord zelf veilig met de persoon.">
              <Input type="text" value={form.password || ""} onChange={set("password")} className="wv-input h-11" data-testid="person-password-input" />
            </Field>
          )}
          <button onClick={submit} disabled={!form.name?.trim()} className="wv-btn w-full" data-testid="person-save-button">Opslaan</button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function AdminPeople({ kind }) {
  const c = COPY[kind];
  const [people, setPeople] = useState(null);
  const [editing, setEditing] = useState(null);
  const load = useCallback(() => api.get(`/${kind}`).then((r) => setPeople(r.data)), [kind]);
  useEffect(() => { setPeople(null); load(); }, [load]);
  if (!people) return <PageLoader />;

  return (
    <div data-testid={`admin-${kind}`}>
      <SectionHeader eyebrow={c.eyebrow} title={c.title} text={`${people.length} in totaal`}
        action={<button onClick={() => setEditing({})} className="wv-btn" data-testid={`create-${kind}-button`}><Plus className="h-4 w-4" />Nieuwe {c.single}</button>} />
      <div className="grid gap-px overflow-hidden border border-white/[0.06] bg-white/[0.06] sm:grid-cols-2 lg:grid-cols-3">
        {people.map((p) => (
          <div key={p.id} className="group bg-[#09090B] p-6 transition-colors duration-200 hover:bg-[#111114]" data-testid={`person-${p.id}`}>
            <div className="flex items-start justify-between">
              <span className="flex h-11 w-11 items-center justify-center rounded-full border border-[#D4AF37]/40 font-display text-xl text-[#E5C158]">{p.name[0]}</span>
              <button onClick={() => setEditing(p)} className="p-1 text-zinc-600 hover:text-white" data-testid={`edit-person-${p.id}`}><Pencil className="h-4 w-4" /></button>
            </div>
            <p className="font-display mt-5 text-2xl text-white">{p.name}</p>
            <p className="mt-1 truncate text-sm text-zinc-500">{p.email || "Geen e-mail"}{p.phone ? ` · ${p.phone}` : ""}</p>
            <div className="mt-4 flex items-center gap-4 text-xs text-zinc-500">
              <span>{p.event_count} event{p.event_count === 1 ? "" : "s"}</span>
              {p.has_login && <span className="flex items-center gap-1 text-[#E5C158]"><KeyRound className="h-3 w-3" />Heeft login</span>}
            </div>
          </div>
        ))}
      </div>
      <PersonDialog kind={kind} person={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />
    </div>
  );
}
