import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Check, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { API, api, errorMessage } from "@/lib/api";
import { InvitationCard } from "@/features/InvitationCard";
import { Logo } from "@/components/wv/Logo";
import { Field, PageLoader } from "@/components/wv/bits";

const CHOICES = [["yes", "Ik kom graag"], ["maybe", "Misschien"], ["no", "Helaas niet"]];
const EMPTY = { name: "", email: "", attending: "", guests: 1, dietary: "", message: "" };

function RsvpForm({ token, deadline }) {
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(null);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e?.target ? e.target.value : e }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.attending) return setError("Laat even weten of je komt.");
    setBusy(true);
    setError("");
    try {
      const payload = { ...form, guests: Number(form.guests) || 1, email: form.email || null, dietary: form.dietary || null, message: form.message || null };
      const { data } = await api.post(`/public/invitations/${token}/rsvp`, payload);
      setDone(data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <div className="wv-panel wv-rise p-8" data-testid="rsvp-success">
        <span className="mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-[#D4AF37] text-black"><Check className="h-5 w-5" /></span>
        <p className="font-display text-3xl text-white">Dank je wel, {done.name}!</p>
        <p className="mt-2 text-sm text-zinc-400">{done.attending === "no" ? "Jammer dat je er niet bij kunt zijn. Je reactie is doorgegeven." : "Je reactie is doorgegeven. Tot dan!"}</p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="wv-panel space-y-5 p-6 sm:p-8" data-testid="rsvp-form">
      <div>
        <p className="wv-eyebrow mb-2">Laat het ons weten</p>
        <p className="font-display text-3xl text-white">Ben je erbij?</p>
        {deadline && <p className="mt-1 text-sm text-zinc-400">Graag reageren voor {deadline}</p>}
      </div>
      <div className="grid grid-cols-3 gap-2">
        {CHOICES.map(([k, l]) => (
          <button type="button" key={k} onClick={() => set("attending")(k)} data-testid={`rsvp-attending-${k}`} className={`rounded-full border px-3 py-2.5 text-sm transition-colors duration-200 ${form.attending === k ? "border-[#D4AF37] bg-[#D4AF37] font-semibold text-black" : "border-white/15 text-zinc-300 hover:border-white/40"}`}>{l}</button>
        ))}
      </div>
      <Field label="Naam"><Input required value={form.name} onChange={set("name")} className="wv-input h-11" data-testid="rsvp-name-input" /></Field>
      <div className="grid grid-cols-[1fr_110px] gap-3">
        <Field label="E-mail (optioneel)"><Input type="email" value={form.email} onChange={set("email")} className="wv-input h-11" data-testid="rsvp-email-input" /></Field>
        {form.attending !== "no" && <Field label="Personen"><Input type="number" min={1} max={20} value={form.guests} onChange={set("guests")} className="wv-input h-11" data-testid="rsvp-guests-input" /></Field>}
      </div>
      {form.attending !== "no" && <Field label="Dieetwensen (optioneel)"><Input value={form.dietary} onChange={set("dietary")} className="wv-input h-11" data-testid="rsvp-dietary-input" /></Field>}
      <Field label="Bericht voor het feestvarken (optioneel)"><Textarea rows={3} value={form.message} onChange={set("message")} className="wv-input" data-testid="rsvp-message-input" /></Field>
      {error && <p className="text-sm text-red-400" data-testid="rsvp-error">{error}</p>}
      <button type="submit" disabled={busy} className="wv-btn h-12 w-full" data-testid="rsvp-submit-button">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Versturen"}</button>
    </form>
  );
}

export default function PublicInvitation() {
  const { token } = useParams();
  const [inv, setInv] = useState(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    api.get(`/public/invitations/${token}`).then((r) => setInv(r.data)).catch(() => setMissing(true));
  }, [token]);

  if (missing) return <div className="flex min-h-screen items-center justify-center text-zinc-400" data-testid="public-invitation-missing">Deze uitnodiging bestaat niet (meer).</div>;
  if (!inv) return <PageLoader />;
  const photo = inv.photo_file_id ? `${API}/public/invitations/${token}/photo` : inv.photo_url;

  return (
    <div className="flex min-h-screen flex-col items-center bg-[#09090B] px-4 py-12" data-testid="public-invitation">
      <div className="wv-rise w-full max-w-md shadow-[0_40px_120px_-20px_rgba(0,0,0,0.9)]">
        <InvitationCard inv={inv} photo={photo} />
      </div>
      {inv.rsvp_enabled !== false && <div className="wv-rise wv-d2 mt-10 w-full max-w-md"><RsvpForm token={token} deadline={inv.rsvp_deadline} /></div>}
      <div className="mt-10 opacity-60"><Logo /></div>
    </div>
  );
}
