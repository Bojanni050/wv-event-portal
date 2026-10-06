import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, Search, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { EmptyState, SectionHeader } from "@/components/wv/bits";
import { useAuth } from "@/context/AuthContext";
import { useEvent } from "@/context/EventContext";
import { api, errorMessage } from "@/lib/api";
import { formatRelative } from "@/lib/format";

const LABELS = { yes: "Komt", maybe: "Misschien", no: "Komt niet" };
const TONE = { yes: "text-[#E5C158] border-[#D4AF37]/50", maybe: "text-sky-300 border-sky-400/40", no: "text-zinc-500 border-zinc-600" };
const FILTERS = [["all", "Alle"], ["yes", "Komen"], ["maybe", "Misschien"], ["no", "Komen niet"]];

function exportCsv(rows, title) {
  const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const lines = [["Naam", "Reactie", "Personen", "E-mail", "Dieetwensen", "Bericht"].join(";"),
    ...rows.map((r) => [r.name, LABELS[r.attending], r.guests, r.email, r.dietary, r.message].map(esc).join(";"))];
  const blob = new Blob(["\ufeff" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `gastenlijst-${title.replace(/\W+/g, "-").toLowerCase()}.csv`;
  a.click();
}

function Stats({ rows }) {
  const sum = (k) => rows.filter((r) => r.attending === k);
  const items = [
    ["guests", "Gasten komen", sum("yes").reduce((n, r) => n + r.guests, 0)],
    ["responses", "Reacties", rows.length],
    ["maybe", "Misschien", sum("maybe").length],
    ["declined", "Komen niet", sum("no").length],
  ];
  return (
    <div className="mb-10 grid grid-cols-2 border-y border-white/[0.06] md:grid-cols-4">
      {items.map(([k, l, v], i) => (
        <div key={k} className={`py-6 ${i % 2 ? "border-l border-white/[0.06] pl-6" : ""} ${i ? "md:border-l md:pl-6" : ""}`} data-testid={`rsvp-stat-${k}`}>
          <p className="font-display text-5xl tabular-nums text-white">{v}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.2em] text-zinc-500">{l}</p>
        </div>
      ))}
    </div>
  );
}

export default function GuestList() {
  const { event, reload } = useEvent();
  const { isStaff } = useAuth();
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("all");
  const [q, setQ] = useState("");

  const load = useCallback(() => api.get(`/events/${event.id}/rsvps`).then((r) => setRows(r.data)), [event.id]);
  useEffect(() => { load(); }, [load]);

  const remove = async (r) => {
    if (!window.confirm(`Reactie van ${r.name} verwijderen?`)) return;
    try { await api.delete(`/rsvps/${r.id}`); await load(); reload(); } catch (e) { toast.error(errorMessage(e)); }
  };

  const shown = rows.filter((r) => (filter === "all" || r.attending === filter) && r.name.toLowerCase().includes(q.toLowerCase()));
  const invPath = isStaff ? `/admin/events/${event.id}?tab=invitation` : `/event/${event.id}/uitnodiging`;

  return (
    <div data-testid="guest-list">
      <SectionHeader eyebrow="Gasten" title="Wie is erbij?" text="Gasten reageren via de gedeelde link van jullie uitnodiging."
        action={rows.length > 0 && <button onClick={() => exportCsv(rows, event.title)} className="wv-btn-ghost" data-testid="rsvp-export-button"><Download className="h-4 w-4" />Exporteer CSV</button>} />
      <Stats rows={rows} />
      {rows.length === 0 ? (
        <EmptyState title="Nog geen reacties" text={event.stats.invitation_shared ? "Zodra gasten reageren op de uitnodiging, verschijnen ze hier." : "Deel eerst jullie uitnodiging, dan kunnen gasten zich aanmelden."}
          action={<Link to={invPath} className="wv-btn mt-2" data-testid="rsvp-go-invitation">Naar uitnodiging</Link>} />
      ) : (
        <>
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative sm:w-64">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
              <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Zoek gast" className="wv-input h-10 pl-9" data-testid="rsvp-search-input" />
            </div>
            <div className="no-scrollbar flex gap-2 overflow-x-auto">
              {FILTERS.map(([k, l]) => (
                <button key={k} onClick={() => setFilter(k)} data-testid={`rsvp-filter-${k}`} className={`whitespace-nowrap rounded-full border px-4 py-1.5 text-sm ${filter === k ? "border-[#D4AF37] text-white" : "border-white/10 text-zinc-500 hover:text-white"}`}>{l}</button>
              ))}
            </div>
          </div>
          <ul className="divide-y divide-white/[0.06] border-y border-white/[0.06]">
            {shown.map((r) => (
              <li key={r.id} className="group flex items-start gap-4 py-5" data-testid={`rsvp-${r.id}`}>
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/10 font-display text-lg text-zinc-200">{r.name[0]}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-[15px] text-white">{r.name}</p>
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wider ${TONE[r.attending]}`}>{LABELS[r.attending]}</span>
                    {r.attending !== "no" && <span className="text-xs text-zinc-500">{r.guests} {r.guests === 1 ? "persoon" : "personen"}</span>}
                  </div>
                  {r.dietary && <p className="mt-1 text-xs text-zinc-400">Dieet: {r.dietary}</p>}
                  {r.message && <p className="font-display mt-2 text-lg italic text-zinc-300">“{r.message}”</p>}
                  <p className="mt-1 text-xs text-zinc-600">{r.email ? `${r.email} · ` : ""}{formatRelative(r.created_at)}</p>
                </div>
                <button onClick={() => remove(r)} className="p-2 text-zinc-600 hover:text-red-400 sm:opacity-0 sm:group-hover:opacity-100" data-testid={`rsvp-delete-${r.id}`}><Trash2 className="h-4 w-4" /></button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
