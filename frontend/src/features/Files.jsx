import { useCallback, useEffect, useRef, useState } from "react";
import { FileText, Loader2, Trash2, UploadCloud } from "lucide-react";
import { toast } from "sonner";
import { EmptyState, SectionHeader } from "@/components/wv/bits";
import { useAuth } from "@/context/AuthContext";
import { useEvent } from "@/context/EventContext";
import { api, errorMessage, fileUrl } from "@/lib/api";
import { formatRelative, formatSize } from "@/lib/format";

const FILTERS = [["all", "Alles"], ["image", "Afbeeldingen"], ["document", "Documenten"], ["chat", "Uit de chat"], ["invitation", "Uitnodiging"]];

function FileTile({ f, canDelete, onDelete }) {
  const isImage = f.content_type.startsWith("image/");
  return (
    <div className="wv-panel wv-hover group overflow-hidden" data-testid={`file-${f.id}`}>
      <a href={fileUrl(f.id)} target="_blank" rel="noreferrer" className="block aspect-[4/3] overflow-hidden bg-[#0c0c0f]">
        {isImage ? <img src={fileUrl(f.id)} alt={f.filename} loading="lazy" className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105" />
          : <div className="flex h-full items-center justify-center"><FileText className="h-10 w-10 text-[#D4AF37]" strokeWidth={1} /></div>}
      </a>
      <div className="flex items-start justify-between gap-2 p-4">
        <div className="min-w-0">
          <p className="truncate text-sm text-white">{f.filename}</p>
          <p className="text-xs text-zinc-500">{formatSize(f.size)} · {f.uploaded_by_name} · {formatRelative(f.created_at)}</p>
        </div>
        {canDelete && <button onClick={() => onDelete(f)} className="p-1 text-zinc-600 hover:text-red-400" data-testid={`delete-file-${f.id}`}><Trash2 className="h-4 w-4" /></button>}
      </div>
    </div>
  );
}

export default function Files() {
  const { event, reload } = useEvent();
  const { user, isStaff } = useAuth();
  const [files, setFiles] = useState([]);
  const [filter, setFilter] = useState("all");
  const [busy, setBusy] = useState(false);
  const input = useRef(null);

  const load = useCallback(() => api.get(`/events/${event.id}/files`).then((r) => setFiles(r.data)), [event.id]);
  useEffect(() => { load(); }, [load]);

  const upload = async (list) => {
    setBusy(true);
    for (const file of list) {
      const fd = new FormData();
      fd.append("file", file);
      try { await api.post(`/events/${event.id}/files`, fd); } catch (e) { toast.error(`${file.name}: ${errorMessage(e)}`); }
    }
    setBusy(false);
    input.current.value = "";
    await load();
    reload();
  };
  const remove = async (f) => {
    try { await api.delete(`/files/${f.id}`); await load(); reload(); } catch (e) { toast.error(errorMessage(e)); }
  };

  const shown = files.filter((f) => filter === "all" || f.category === filter);
  return (
    <div data-testid="files">
      <SectionHeader eyebrow="Bestanden" title="Alles voor jullie event" text="Foto's, contracten, sfeerbeelden en documenten. Gedeeld tussen jullie en White Vision." />
      <input ref={input} type="file" multiple accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt" className="hidden" onChange={(e) => upload([...e.target.files])} data-testid="files-input" />
      <button
        onClick={() => input.current.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); upload([...e.dataTransfer.files]); }}
        className="mb-10 flex w-full flex-col items-center gap-3 border border-dashed border-white/15 py-12 text-sm text-zinc-400 transition-colors duration-200 hover:border-[#D4AF37]/60 hover:text-white"
        data-testid="files-upload-button"
      >
        {busy ? <Loader2 className="h-7 w-7 animate-spin text-[#D4AF37]" /> : <UploadCloud className="h-7 w-7 text-[#D4AF37]" strokeWidth={1.5} />}
        Sleep bestanden hierheen of klik om te uploaden <span className="text-xs text-zinc-600">Afbeeldingen, PDF en documenten · max 15 MB</span>
      </button>
      <div className="no-scrollbar mb-6 flex gap-2 overflow-x-auto">
        {FILTERS.map(([k, l]) => (
          <button key={k} onClick={() => setFilter(k)} data-testid={`files-filter-${k}`} className={`whitespace-nowrap rounded-full border px-4 py-1.5 text-sm ${filter === k ? "border-[#D4AF37] text-white" : "border-white/10 text-zinc-500 hover:text-white"}`}>{l}</button>
        ))}
      </div>
      {shown.length === 0 ? <EmptyState title="Nog geen bestanden" text="Upload bijvoorbeeld een sfeerbord of de plattegrond van de locatie." /> : (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
          {shown.map((f) => <FileTile key={f.id} f={f} canDelete={isStaff || f.uploaded_by === user.id} onDelete={remove} />)}
        </div>
      )}
    </div>
  );
}
