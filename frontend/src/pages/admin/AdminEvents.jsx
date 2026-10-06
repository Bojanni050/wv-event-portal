import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Search } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Field, PageLoader, SectionHeader } from "@/components/wv/bits";
import { useAuth } from "@/context/AuthContext";
import { api, errorMessage } from "@/lib/api";
import { EVENT_TYPES, STATUSES } from "@/lib/constants";
import { EventRow } from "./AdminDashboard";

const Pick = ({ value, onChange, options, testId }) => (
  <Select value={value} onValueChange={onChange}>
    <SelectTrigger className="wv-input h-11" data-testid={testId}><SelectValue /></SelectTrigger>
    <SelectContent className="border-white/10 bg-[#111114]">{options.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
  </Select>
);

function CreateEvent({ open, onClose }) {
  const navigate = useNavigate();
  const [form, setForm] = useState({ title: "", event_type: "wedding", date: "", start_time: "", end_time: "", venue_name: "", venue_city: "", customer_id: "none", dj_id: "none" });
  const [customers, setCustomers] = useState([]);
  const [djs, setDjs] = useState([]);
  useEffect(() => {
    if (!open) return;
    api.get("/customers").then((r) => setCustomers(r.data));
    api.get("/djs").then((r) => setDjs(r.data));
  }, [open]);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v?.target ? v.target.value : v }));
  const submit = async () => {
    const payload = Object.fromEntries(Object.entries(form).map(([k, v]) => [k, v === "" || v === "none" ? null : v]));
    try {
      const { data } = await api.post("/events", { ...payload, status: "new", cover_image: "/images/stage.jpg" });
      toast.success("Event aangemaakt");
      navigate(`/admin/events/${data.id}`);
    } catch (e) { toast.error(errorMessage(e)); }
  };
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="rounded-sm border-white/10 bg-[#111114] sm:max-w-xl" data-testid="create-event-dialog">
        <DialogHeader><DialogTitle className="font-display text-3xl font-normal">Nieuw event</DialogTitle></DialogHeader>
        <div className="space-y-4">
          <Field label="Naam"><Input value={form.title} onChange={set("title")} className="wv-input h-11" placeholder="Jeroen & Mark" data-testid="new-event-title" /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Type"><Pick value={form.event_type} onChange={set("event_type")} options={Object.entries(EVENT_TYPES)} testId="new-event-type" /></Field>
            <Field label="Datum"><Input type="date" value={form.date} onChange={set("date")} className="wv-input h-11" data-testid="new-event-date" /></Field>
            <Field label="Start"><Input type="time" value={form.start_time} onChange={set("start_time")} className="wv-input h-11" data-testid="new-event-start" /></Field>
            <Field label="Einde"><Input type="time" value={form.end_time} onChange={set("end_time")} className="wv-input h-11" data-testid="new-event-end" /></Field>
            <Field label="Locatie"><Input value={form.venue_name} onChange={set("venue_name")} className="wv-input h-11" data-testid="new-event-venue" /></Field>
            <Field label="Plaats"><Input value={form.venue_city} onChange={set("venue_city")} className="wv-input h-11" data-testid="new-event-city" /></Field>
            <Field label="Klant"><Pick value={form.customer_id} onChange={set("customer_id")} options={[["none", "Kies klant"], ...customers.map((c) => [c.id, c.name])]} testId="new-event-customer" /></Field>
            <Field label="DJ"><Pick value={form.dj_id} onChange={set("dj_id")} options={[["none", "Later toewijzen"], ...djs.map((d) => [d.id, d.name])]} testId="new-event-dj" /></Field>
          </div>
          <button onClick={submit} disabled={!form.title.trim()} className="wv-btn w-full" data-testid="new-event-submit">Event aanmaken</button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function AdminEvents() {
  const { user } = useAuth();
  const [events, setEvents] = useState(null);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");
  const [creating, setCreating] = useState(false);
  useEffect(() => { api.get("/events").then((r) => setEvents(r.data)); }, []);
  if (!events) return <PageLoader />;

  const shown = events.filter((e) => (status === "all" || e.status === status) && `${e.title} ${e.customer?.name || ""} ${e.venue_city || ""}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <div data-testid="admin-events">
      <SectionHeader eyebrow="Events" title="Alle events" text={`${events.length} events in totaal`}
        action={user.role === "admin" && <button onClick={() => setCreating(true)} className="wv-btn" data-testid="create-event-button"><Plus className="h-4 w-4" />Nieuw event</button>} />
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative sm:w-72">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Zoek op naam, klant of plaats" className="wv-input h-10 pl-9" data-testid="admin-events-search" />
        </div>
        <div className="no-scrollbar flex gap-2 overflow-x-auto">
          {[["all", "Alle"], ...Object.entries(STATUSES)].map(([k, l]) => (
            <button key={k} onClick={() => setStatus(k)} data-testid={`admin-events-filter-${k}`} className={`whitespace-nowrap rounded-full border px-4 py-1.5 text-sm ${status === k ? "border-[#D4AF37] text-white" : "border-white/10 text-zinc-500 hover:text-white"}`}>{l}</button>
          ))}
        </div>
      </div>
      <div className="border-t border-white/[0.06]">
        {shown.map((e) => <EventRow key={e.id} e={e} extra={e.customer && <p className="mt-0.5 text-xs text-zinc-600">Klant: {e.customer.name}</p>} />)}
        {!shown.length && <p className="py-8 text-sm text-zinc-500">Geen events gevonden.</p>}
      </div>
      <CreateEvent open={creating} onClose={() => setCreating(false)} />
    </div>
  );
}
