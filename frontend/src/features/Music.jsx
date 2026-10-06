import { useCallback, useEffect, useState } from "react";
import { Plus, Search, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { SectionHeader } from "@/components/wv/bits";
import { useEvent } from "@/context/EventContext";
import { api, errorMessage } from "@/lib/api";
import { MOMENTS, MUSIC_LISTS } from "@/lib/constants";

function AddSong({ onAdd, placeholder = "Titel", testId }) {
  const [title, setTitle] = useState("");
  const [artist, setArtist] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    await onAdd({ title: title.trim(), artist: artist.trim() || null });
    setTitle("");
    setArtist("");
  };
  return (
    <form onSubmit={submit} className="flex flex-col gap-2 sm:flex-row" data-testid={testId}>
      <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={placeholder} className="wv-input h-11 flex-[1.3]" data-testid={`${testId}-title`} />
      <Input value={artist} onChange={(e) => setArtist(e.target.value)} placeholder="Artiest" className="wv-input h-11 flex-1" data-testid={`${testId}-artist`} />
      <button type="submit" className="wv-btn h-11" data-testid={`${testId}-submit`}><Plus className="h-4 w-4" />Toevoegen</button>
    </form>
  );
}

function MomentSlot({ moment, item, onPick, onRemove }) {
  return (
    <div className="wv-panel wv-hover flex min-h-[150px] flex-col justify-between p-5" data-testid={`moment-${moment.key}`}>
      <p className="text-[11px] uppercase tracking-[0.22em] text-zinc-500">{moment.label}</p>
      {item ? (
        <div className="group">
          <p className="font-display text-2xl leading-tight text-white">{item.title}</p>
          <p className="mt-1 flex items-center justify-between text-sm text-[#E5C158]">
            {item.artist}
            <button onClick={() => onRemove(item)} className="text-zinc-600 opacity-0 hover:text-red-400 group-hover:opacity-100" data-testid={`moment-remove-${moment.key}`}><Trash2 className="h-3.5 w-3.5" /></button>
          </p>
        </div>
      ) : (
        <button onClick={() => onPick(moment)} className="flex items-center gap-2 text-sm text-zinc-400 hover:text-[#D4AF37]" data-testid={`moment-add-${moment.key}`}>
          <Plus className="h-4 w-4" /> Kies een nummer
        </button>
      )}
    </div>
  );
}

function SongList({ list, items, onAdd, onRemove }) {
  return (
    <div className="space-y-6">
      <AddSong onAdd={(s) => onAdd({ ...s, category: list.key })} placeholder="Zoek of typ een nummer" testId={`add-${list.key}`} />
      <ol className="divide-y divide-white/[0.06] border-y border-white/[0.06]" data-testid={`list-${list.key}`}>
        {items.length === 0 && <li className="py-6 text-sm text-zinc-500">Nog niets toegevoegd.</li>}
        {items.map((s, i) => (
          <li key={s.id} className="group flex items-center gap-5 py-4" data-testid={`song-${s.id}`}>
            <span className="w-6 font-display text-xl tabular-nums text-zinc-600">{String(i + 1).padStart(2, "0")}</span>
            <div className="min-w-0 flex-1">
              <p className={`truncate text-[15px] ${list.key === "dont_play" ? "text-zinc-400 line-through decoration-red-400/60" : "text-white"}`}>{s.title}</p>
              {s.artist && <p className="truncate text-sm text-zinc-500">{s.artist}</p>}
            </div>
            <button onClick={() => onRemove(s)} className="p-2 text-zinc-600 opacity-100 hover:text-red-400 sm:opacity-0 sm:group-hover:opacity-100" data-testid={`delete-song-${s.id}`}><Trash2 className="h-4 w-4" /></button>
          </li>
        ))}
      </ol>
    </div>
  );
}

export default function Music() {
  const { event, reload } = useEvent();
  const [items, setItems] = useState([]);
  const [active, setActive] = useState("must_play");
  const [query, setQuery] = useState("");
  const [moment, setMoment] = useState(null);

  const load = useCallback(() => api.get(`/events/${event.id}/music`).then((r) => setItems(r.data)), [event.id]);
  useEffect(() => { load(); }, [load]);

  const add = async (payload) => {
    try {
      await api.post(`/events/${event.id}/music`, payload);
      await load();
      reload();
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };
  const remove = async (item) => {
    await api.delete(`/music/${item.id}`);
    await load();
    reload();
  };

  const q = query.toLowerCase();
  const matches = (s) => !q || `${s.title} ${s.artist || ""}`.toLowerCase().includes(q);
  const list = MUSIC_LISTS.find((l) => l.key === active);

  return (
    <div data-testid="music">
      <SectionHeader eyebrow="Muziekvoorkeuren" title="De soundtrack van jullie avond" text="Hoe meer we weten, hoe beter we de dansvloer kunnen lezen. Je DJ gebruikt dit als richting, niet als afspeellijst." />
      <section className="mb-16">
        <p className="font-display mb-5 text-2xl text-white">Speciale momenten</p>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
          {MOMENTS.map((m) => (
            <MomentSlot key={m.key} moment={m} item={items.find((s) => s.category === "special" && s.moment === m.key)} onPick={setMoment} onRemove={remove} />
          ))}
        </div>
      </section>
      <section>
        <div className="mb-8 flex flex-col gap-4 border-b border-white/[0.06] md:flex-row md:items-end md:justify-between">
          <div className="no-scrollbar flex gap-6 overflow-x-auto">
            {MUSIC_LISTS.map((l) => {
              const n = items.filter((s) => s.category === l.key).length;
              return (
                <button key={l.key} onClick={() => setActive(l.key)} data-testid={`music-tab-${l.key}`} className={`-mb-px whitespace-nowrap border-b-2 pb-4 text-left transition-colors duration-200 ${active === l.key ? "border-[#D4AF37] text-white" : "border-transparent text-zinc-500 hover:text-zinc-300"}`}>
                  <span className="font-display text-3xl">{l.label}</span>
                  <span className="ml-2 align-top text-xs tabular-nums text-zinc-500">{n}</span>
                </button>
              );
            })}
          </div>
          <div className="relative mb-4 md:w-64">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Zoek in lijst" className="wv-input h-10 pl-9" data-testid="music-search-input" />
          </div>
        </div>
        <p className="mb-5 text-sm text-zinc-400">{list.hint}</p>
        <SongList list={list} items={items.filter((s) => s.category === active && matches(s))} onAdd={add} onRemove={remove} />
      </section>
      <Dialog open={!!moment} onOpenChange={(o) => !o && setMoment(null)}>
        <DialogContent className="rounded-sm border-white/10 bg-[#111114] sm:max-w-lg" data-testid="moment-dialog">
          <DialogHeader><DialogTitle className="font-display text-3xl font-normal">{moment?.label}</DialogTitle></DialogHeader>
          <AddSong testId="moment-song" onAdd={async (s) => { await add({ ...s, category: "special", moment: moment.key }); setMoment(null); }} />
        </DialogContent>
      </Dialog>
    </div>
  );
}
