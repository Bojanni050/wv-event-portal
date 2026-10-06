import { useCallback, useEffect, useState } from "react";
import { KeyRound, Loader2, Mail, Pencil, Plus } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Field, PageLoader, SectionHeader } from "@/components/wv/bits";
import { api, errorMessage } from "@/lib/api";
import { formatRelative } from "@/lib/format";

const COPY = {
  customers: { eyebrow: "Klanten", title: "Klanten", single: "klant", noteKey: "notes", noteLabel: "Notities" },
  djs: { eyebrow: "Team", title: "DJ's", single: "DJ", noteKey: "bio", noteLabel: "Bio" },
};

function PersonDialog({ kind, person, onClose, onSaved }) {
  const c = COPY[kind];
  const [form, setForm] = useState({});
  useEffect(() => setForm(person ? { name: "", email: "", phone: "", notes: "", bio: "", password: "", send_welcome: kind === "customers" && !person.id, ...person } : {}), [person, kind]);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const submit = async () => {
    const welcome = kind === "customers" && !form.id && form.send_welcome;
    const payload = { name: form.name, email: form.email || null, phone: form.phone || null, notes: form.notes || null, bio: form.bio || null, password: welcome ? null : form.password || null, send_welcome: welcome };
    if (welcome && !form.email) return toast.error("Vul een e-mailadres in voor de welkomstmail");
    try {
      if (form.id) await api.patch(`/${kind}/${form.id}`, payload);
      else {
        const { data } = await api.post(`/${kind}`, payload);
        if (data.welcome_error) toast.error(`Klant aangemaakt, maar: ${data.welcome_error}`);
        else if (welcome) toast.success(`Welkomstmail verstuurd naar ${data.email}`);
      }
      if (!welcome) toast.success("Opgeslagen");
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
          {kind === "customers" && !form.id && (
            <label className="flex items-start gap-3 text-sm text-zinc-300">
              <Checkbox checked={!!form.send_welcome} onCheckedChange={(v) => setForm((f) => ({ ...f, send_welcome: !!v }))} className="mt-0.5" data-testid="person-send-welcome-checkbox" />
              <span>Stuur een welkomstmail<span className="block text-xs text-zinc-500">De klant ontvangt een link (7 dagen geldig) om zelf een wachtwoord in te stellen.</span></span>
            </label>
          )}
          {!form.has_login && !(kind === "customers" && !form.id && form.send_welcome) && (
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
  const [sending, setSending] = useState(null);
  const sendWelcome = async (p) => {
    setSending(p.id);
    try {
      await api.post(`/customers/${p.id}/welcome`);
      toast.success(`Welkomstmail verstuurd naar ${p.email}`);
      load();
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setSending(null);
    }
  };
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
            {kind === "customers" && p.email && (
              <div className="mt-4 flex items-center justify-between border-t border-white/[0.06] pt-4">
                <span className="text-xs text-zinc-600" data-testid={`welcome-status-${p.id}`}>{p.welcome_sent_at ? `Welkomstmail ${formatRelative(p.welcome_sent_at)}` : "Nog geen welkomstmail"}</span>
                <button onClick={() => sendWelcome(p)} disabled={sending === p.id} className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-[#E5C158]" data-testid={`send-welcome-${p.id}`}>
                  {sending === p.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Mail className="h-3.5 w-3.5" />}{p.welcome_sent_at ? "Opnieuw sturen" : "Welkomstmail sturen"}
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
      <PersonDialog kind={kind} person={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />
    </div>
  );
}
