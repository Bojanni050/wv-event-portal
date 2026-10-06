import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { EventProvider, useEvent } from "@/context/EventContext";
import { useAuth } from "@/context/AuthContext";
import { ProgressLine } from "@/components/wv/bits";
import { api, errorMessage } from "@/lib/api";
import { STATUSES } from "@/lib/constants";
import { eventSubtitle, timeRange } from "@/lib/format";
import EventDetails from "@/features/EventDetails";
import Chat from "@/features/Chat";
import Music from "@/features/Music";
import Timeline from "@/features/Timeline";
import InvitationBuilder from "@/features/InvitationBuilder";
import Files from "@/features/Files";
import GuestList from "@/features/GuestList";

const TABS = [["details", "Gegevens", EventDetails], ["chat", "Chat", Chat], ["music", "Muziek", Music], ["timeline", "Draaischema", Timeline], ["invitation", "Uitnodiging", InvitationBuilder], ["guests", "Gasten", GuestList], ["files", "Bestanden", Files]];

function Header() {
  const { event, reload } = useEvent();
  const { user } = useAuth();
  const navigate = useNavigate();
  const setStatus = async (status) => {
    try { await api.patch(`/events/${event.id}`, { status }); await reload(); toast.success("Status bijgewerkt"); } catch (e) { toast.error(errorMessage(e)); }
  };
  const remove = async () => {
    if (!window.confirm(`Event "${event.title}" definitief verwijderen?`)) return;
    await api.delete(`/events/${event.id}`);
    navigate("/admin/events");
  };
  return (
    <div className="mb-10 border-b border-white/[0.06] pb-10">
      <Link to="/admin/events" className="mb-6 inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-zinc-500 hover:text-white" data-testid="back-to-events"><ArrowLeft className="h-3.5 w-3.5" />Events</Link>
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="font-display text-5xl font-medium leading-none text-white sm:text-6xl" data-testid="admin-event-title">{event.title}</h1>
          <p className="font-display mt-2 text-xl italic text-[#E5C158]">{eventSubtitle(event)} · {timeRange(event)}</p>
          <p className="mt-2 text-sm text-zinc-500">{event.customer?.name || "Geen klant"} · {event.dj ? `DJ ${event.dj.name}` : "Geen DJ"} · {event.venue_name || "Locatie volgt"}</p>
        </div>
        <div className="flex items-end gap-6">
          <div className="w-40">
            <p className="mb-2 text-xs text-zinc-500">Voorbereiding <span className="float-right text-white" data-testid="admin-event-progress">{event.progress.overall}%</span></p>
            <ProgressLine value={event.progress.overall} />
          </div>
          <Select value={event.status} onValueChange={setStatus}>
            <SelectTrigger className="wv-input h-10 w-44" data-testid="admin-event-status-select"><SelectValue /></SelectTrigger>
            <SelectContent className="border-white/10 bg-[#111114]">{Object.entries(STATUSES).map(([k, l]) => <SelectItem key={k} value={k}>{l}</SelectItem>)}</SelectContent>
          </Select>
          {user.role === "admin" && <button onClick={remove} className="p-2 text-zinc-600 hover:text-red-400" title="Verwijderen" data-testid="admin-event-delete"><Trash2 className="h-4 w-4" /></button>}
        </div>
      </div>
      <div className="mt-8 flex flex-wrap gap-x-8 gap-y-2">
        {event.progress.sections.map((s) => (
          <p key={s.key} className="text-xs text-zinc-500">{s.label} <span className={s.percent === 100 ? "text-[#E5C158]" : "text-zinc-300"}>{s.percent === 100 ? "✓" : `${s.percent}%`}</span></p>
        ))}
      </div>
    </div>
  );
}

export default function AdminEventDetail() {
  const { eventId } = useParams();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "details";
  return (
    <EventProvider eventId={eventId}>
      <Header />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList className="no-scrollbar mb-10 h-auto w-full justify-start gap-1 overflow-x-auto rounded-none border-b border-white/[0.06] bg-transparent p-0">
          {TABS.map(([v, l]) => (
            <TabsTrigger key={v} value={v} data-testid={`admin-tab-${v}`} className="rounded-none border-b-2 border-transparent px-4 py-3 text-zinc-500 data-[state=active]:border-[#D4AF37] data-[state=active]:bg-transparent data-[state=active]:text-white data-[state=active]:shadow-none">{l}</TabsTrigger>
          ))}
        </TabsList>
        {TABS.map(([v, , Comp]) => <TabsContent key={v} value={v}><Comp /></TabsContent>)}
      </Tabs>
    </EventProvider>
  );
}
