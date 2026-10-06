import { useEffect, useState } from "react";
import { Lock, Save } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Field, SectionHeader } from "@/components/wv/bits";
import { useAuth } from "@/context/AuthContext";
import { useEvent } from "@/context/EventContext";
import { api, errorMessage } from "@/lib/api";
import { EVENT_TYPES, STATUSES } from "@/lib/constants";

const CUSTOMER_FIELDS = ["title", "guest_count", "notes", "contact_name", "contact_phone", "setup_notes", "venue_notes"];
const KEYS = ["title", "event_type", "date", "start_time", "end_time", "venue_name", "venue_city", "venue_address", "venue_notes", "guest_count", "notes", "contact_name", "contact_phone", "setup_notes", "dj_id", "customer_id", "status"];

const pick = (ev) => Object.fromEntries(KEYS.map((k) => [k, ev[k] ?? ""]));

function SelectField({ label, value, onChange, options, disabled, testId }) {
  return (
    <Field label={label}>
      <Select value={value || "none"} onValueChange={(v) => onChange(v === "none" ? "" : v)} disabled={disabled}>
        <SelectTrigger className="wv-input h-11" data-testid={testId}><SelectValue /></SelectTrigger>
        <SelectContent className="border-white/10 bg-[#111114]">
          {options.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}
        </SelectContent>
      </Select>
    </Field>
  );
}

export default function EventDetails() {
  const { event, reload } = useEvent();
  const { user, isStaff } = useAuth();
  const [form, setForm] = useState(pick(event));
  const [djs, setDjs] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isStaff) return;
    api.get("/djs").then((r) => setDjs(r.data)).catch(() => {});
    api.get("/customers").then((r) => setCustomers(r.data)).catch(() => {});
  }, [isStaff]);

  const can = (k) => isStaff || CUSTOMER_FIELDS.includes(k);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e?.target ? e.target.value : e }));

  const save = async () => {
    setSaving(true);
    const allowed = KEYS.filter((k) => can(k) && !(user.role === "dj" && ["dj_id", "customer_id"].includes(k)));
    const payload = Object.fromEntries(allowed.map((k) => [k, form[k] === "" ? null : form[k]]));
    if (payload.guest_count != null) payload.guest_count = Number(payload.guest_count);
    try {
      await api.patch(`/events/${event.id}`, payload);
      await reload();
      toast.success("Gegevens opgeslagen");
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  const text = (k, label, type = "text") => (
    <Field label={<span className="flex items-center gap-1.5">{label}{!can(k) && <Lock className="h-3 w-3" />}</span>}>
      <Input type={type} value={form[k]} onChange={set(k)} disabled={!can(k)} className="wv-input h-11" data-testid={`field-${k}`} />
    </Field>
  );

  return (
    <div data-testid="event-details">
      <SectionHeader
        eyebrow="Mijn event"
        title="Alles over de avond"
        text={isStaff ? "Als White Vision kun je alle gegevens aanpassen." : "Velden met een slotje beheert White Vision. Klopt er iets niet? Stuur je DJ een bericht."}
        action={<button onClick={save} disabled={saving} className="wv-btn" data-testid="save-event-button"><Save className="h-4 w-4" />Opslaan</button>}
      />
      <div className="grid gap-12 lg:grid-cols-2">
        <section className="space-y-5">
          <p className="font-display text-2xl text-white">Het event</p>
          {text("title", "Naam van het event")}
          <div className="grid grid-cols-2 gap-4">
            <SelectField label="Type" value={form.event_type} onChange={set("event_type")} disabled={!can("event_type")} options={Object.entries(EVENT_TYPES)} testId="field-event_type" />
            {text("guest_count", "Aantal gasten", "number")}
          </div>
          <div className="grid grid-cols-3 gap-4">
            {text("date", "Datum", "date")}
            {text("start_time", "Start", "time")}
            {text("end_time", "Einde", "time")}
          </div>
          {isStaff && (
            <div className="grid grid-cols-2 gap-4">
              <SelectField label="Status" value={form.status} onChange={set("status")} options={Object.entries(STATUSES)} testId="field-status" />
              <SelectField label="DJ" value={form.dj_id} onChange={set("dj_id")} disabled={user.role !== "admin"} options={[["none", "Nog niet toegewezen"], ...djs.map((d) => [d.id, d.name])]} testId="field-dj_id" />
            </div>
          )}
          {user.role === "admin" && (
            <SelectField label="Klant" value={form.customer_id} onChange={set("customer_id")} options={[["none", "Geen klant"], ...customers.map((c) => [c.id, c.name])]} testId="field-customer_id" />
          )}
          {!isStaff && event.dj && (
            <Field label={<span className="flex items-center gap-1.5">Jullie DJ<Lock className="h-3 w-3" /></span>}>
              <p className="py-2 text-white" data-testid="assigned-dj">{event.dj.name} — White Vision</p>
            </Field>
          )}
          <Field label="Notities voor de DJ">
            <Textarea rows={4} value={form.notes} onChange={set("notes")} className="wv-input" data-testid="field-notes" />
          </Field>
        </section>
        <section className="space-y-5">
          <p className="font-display text-2xl text-white">Locatie</p>
          <div className="grid grid-cols-2 gap-4">
            {text("venue_name", "Locatie")}
            {text("venue_city", "Plaats")}
          </div>
          {text("venue_address", "Adres")}
          <Field label="Over de locatie">
            <Textarea rows={3} value={form.venue_notes} onChange={set("venue_notes")} className="wv-input" placeholder="Zaal, verdieping, bijzonderheden..." data-testid="field-venue_notes" />
          </Field>
          <p className="font-display pt-4 text-2xl text-white">Laatste details</p>
          <div className="grid grid-cols-2 gap-4">
            {text("contact_name", "Contactpersoon op de dag")}
            {text("contact_phone", "Telefoon")}
          </div>
          <Field label="Opbouw & logistiek">
            <Textarea rows={3} value={form.setup_notes} onChange={set("setup_notes")} className="wv-input" placeholder="Parkeren, laad- en losplek, opbouwtijd..." data-testid="field-setup_notes" />
          </Field>
        </section>
      </div>
    </div>
  );
}
