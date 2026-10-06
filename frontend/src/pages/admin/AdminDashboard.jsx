import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { EVENT_TYPES } from "@/lib/constants";
import { daysUntil, formatRelative } from "@/lib/format";
import { PageLoader, ProgressLine, StatusBadge } from "@/components/wv/bits";

export const DateBlock = ({ iso }) => {
  const d = iso ? new Date(`${iso}T12:00:00`) : null;
  return (
    <div className="w-14 shrink-0 text-center">
      <p className="font-display text-3xl leading-none text-white">{d ? d.getDate() : "–"}</p>
      <p className="mt-1 text-[10px] uppercase tracking-[0.2em] text-zinc-500">{d ? d.toLocaleDateString("nl-NL", { month: "short", year: "2-digit" }) : "n.n.b."}</p>
    </div>
  );
};

export const EventRow = ({ e, extra }) => (
  <Link to={`/admin/events/${e.id}`} data-testid={`admin-event-row-${e.id}`} className="group flex items-center gap-5 border-b border-white/[0.06] py-4 transition-colors duration-200 hover:bg-white/[0.02]">
    <DateBlock iso={e.date} />
    <div className="min-w-0 flex-1">
      <div className="flex flex-wrap items-center gap-2">
        <p className="truncate text-[15px] font-medium text-white">{e.title}</p>
        <StatusBadge status={e.status} testId={`admin-event-status-${e.id}`} />
        {e.unread > 0 && <span className="rounded-full bg-[#D4AF37] px-2 text-[10px] font-bold text-black">{e.unread}</span>}
      </div>
      <p className="mt-0.5 truncate text-xs text-zinc-500">{EVENT_TYPES[e.event_type]} · {e.dj ? `DJ ${e.dj.name}` : "Geen DJ"}{e.venue_city ? ` · ${e.venue_city}` : ""}</p>
      {extra}
    </div>
    <div className="hidden w-28 sm:block">
      <p className="mb-1.5 text-right text-xs tabular-nums text-zinc-400">{e.progress.overall}%</p>
      <ProgressLine value={e.progress.overall} />
    </div>
    <ArrowUpRight className="h-4 w-4 text-zinc-700 group-hover:text-[#D4AF37]" />
  </Link>
);

const Block = ({ title, children, testId, empty }) => (
  <section data-testid={testId}>
    <p className="font-display mb-2 text-2xl text-white">{title}</p>
    {empty ? <p className="border-t border-white/[0.06] py-6 text-sm text-zinc-500">{empty}</p> : <div className="border-t border-white/[0.06]">{children}</div>}
  </section>
);

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Goedemorgen" : h < 18 ? "Goedemiddag" : "Goedenavond";
}

export default function AdminDashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/admin/overview").then((r) => setData(r.data)); }, []);
  if (!data) return <PageLoader />;
  const c = data.counts;
  const next = data.upcoming[0];

  return (
    <div className="space-y-16" data-testid="admin-dashboard">
      <div className="wv-rise">
        <p className="wv-eyebrow mb-4">{greeting()}, {user.name}</p>
        <h1 className="font-display text-5xl font-medium leading-[1] text-white sm:text-6xl">
          {next ? <>Volgende: <em className="text-[#E5C158]">{next.title}</em>{daysUntil(next.date) !== null && <span className="text-zinc-500"> over {daysUntil(next.date)} dagen</span>}</> : "Geen events gepland"}
        </h1>
      </div>
      <div className="wv-rise wv-d1 grid grid-cols-2 border-y border-white/[0.06] md:grid-cols-4">
        {[["upcoming", "Aankomend"], ["attention", "Vraagt aandacht"], ["unread", "Ongelezen berichten"], ["incomplete", "Onvolledige info"]].map(([k, l], i) => (
          <div key={k} className={`py-6 ${i ? "md:border-l" : ""} border-white/[0.06] md:px-6 ${i % 2 ? "border-l pl-6 md:pl-6" : ""}`} data-testid={`admin-count-${k}`}>
            <p className="font-display text-5xl tabular-nums text-white">{c[k]}</p>
            <p className="mt-1 text-xs uppercase tracking-[0.2em] text-zinc-500">{l}</p>
          </div>
        ))}
      </div>
      <div className="grid gap-14 lg:grid-cols-2">
        <Block title="Aankomende events" testId="admin-upcoming" empty={!data.upcoming.length && "Geen aankomende events."}>
          {data.upcoming.map((e) => <EventRow key={e.id} e={e} />)}
        </Block>
        <Block title="Vraagt aandacht" testId="admin-attention" empty={!data.attention.length && "Alles loopt op schema."}>
          {data.attention.map((e) => <EventRow key={e.id} e={e} extra={<p className="mt-1 text-xs text-[#E5C158]">{e.reasons.join(" · ")}</p>} />)}
        </Block>
        <Block title="Ongelezen berichten" testId="admin-unread" empty={!data.unread_messages.length && "Geen ongelezen berichten."}>
          {data.unread_messages.map((m) => (
            <Link key={m.id} to={`/admin/events/${m.event_id}?tab=chat`} className="block border-b border-white/[0.06] py-4 hover:bg-white/[0.02]" data-testid={`admin-unread-${m.id}`}>
              <p className="text-xs text-zinc-500">{m.sender_name} · {m.event_title} · {formatRelative(m.created_at)}</p>
              <p className="mt-1 line-clamp-2 text-sm text-zinc-200">“{m.text || m.attachment?.filename}”</p>
            </Link>
          ))}
        </Block>
        <Block title="Onvolledige informatie" testId="admin-incomplete" empty={!data.incomplete.length && "Alle events zijn compleet."}>
          {data.incomplete.map((e) => <EventRow key={e.id} e={e} extra={<p className="mt-1 text-xs text-zinc-500">Mist: {e.stats.missing_info.join(", ")}</p>} />)}
        </Block>
        <Block title="Recent bijgewerkt" testId="admin-recent">
          {data.recent.map((e) => <EventRow key={e.id} e={e} extra={<p className="mt-1 text-xs text-zinc-600">{formatRelative(e.updated_at)}</p>} />)}
        </Block>
      </div>
    </div>
  );
}
