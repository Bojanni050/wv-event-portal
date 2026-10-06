import { useEffect, useRef, useState } from "react";
import { Download, ImagePlus, Link2, Loader2, Save, X } from "lucide-react";
import { toPng } from "html-to-image";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Field, PageLoader, SectionHeader } from "@/components/wv/bits";
import { useEvent } from "@/context/EventContext";
import { api, errorMessage, fileUrl } from "@/lib/api";
import { FONTS, LAYOUTS, PALETTES } from "@/lib/constants";
import { formatDate } from "@/lib/format";
import { InvitationCard } from "./InvitationCard";

const STYLE_KEYS = ["layout", "background_color", "text_color", "accent_color", "font", "subtitle"];
export const photoSrc = (inv) => (inv.photo_file_id ? fileUrl(inv.photo_file_id) : inv.photo_url);

function defaults(event, tpl) {
  return {
    template_id: tpl?.id || null, title: event.title, subtitle: tpl?.subtitle || "Let's celebrate!",
    date_text: event.date ? formatDate(event.date) : "", time_text: event.start_time ? `${event.start_time}${event.end_time ? ` — ${event.end_time}` : ""}` : "",
    location: event.venue_name || "", description: "", photo_url: tpl?.photo_url || null, photo_file_id: null,
    background_color: tpl?.background_color || "#09090B", text_color: tpl?.text_color || "#F4F4F5",
    accent_color: tpl?.accent_color || "#D4AF37", font: tpl?.font || "playfair", layout: tpl?.layout || "classic",
  };
}

const Chip = ({ active, onClick, children, testId, style }) => (
  <button type="button" onClick={onClick} style={style} data-testid={testId} className={`rounded-full border px-4 py-2 text-sm transition-colors duration-200 ${active ? "border-[#D4AF37] text-white" : "border-white/10 text-zinc-400 hover:text-white"}`}>{children}</button>
);

function ColorInput({ label, value, onChange, testId }) {
  return (
    <Field label={label}>
      <div className="flex items-center gap-2 rounded-sm border border-white/10 bg-[#0c0c0f] px-2">
        <input type="color" value={value} onChange={(e) => onChange(e.target.value)} className="h-9 w-9 cursor-pointer bg-transparent" data-testid={testId} />
        <span className="font-mono text-xs uppercase text-zinc-400">{value}</span>
      </div>
    </Field>
  );
}

export default function InvitationBuilder() {
  const { event, reload } = useEvent();
  const [inv, setInv] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [token, setToken] = useState(null);
  const [busy, setBusy] = useState("");
  const preview = useRef(null);
  const photoInput = useRef(null);

  useEffect(() => {
    Promise.all([api.get(`/events/${event.id}/invitation`), api.get("/invitation-templates")]).then(([a, b]) => {
      setTemplates(b.data);
      setInv(a.data || defaults(event, b.data[0]));
      setToken(a.data?.share_token || null);
    });
  }, [event]);

  if (!inv) return <PageLoader />;
  const set = (k) => (v) => setInv((x) => ({ ...x, [k]: v?.target ? v.target.value : v }));
  const applyTemplate = (t) =>
    setInv((x) => ({ ...x, template_id: t.id, ...Object.fromEntries(STYLE_KEYS.map((k) => [k, t[k]])), photo_url: x.photo_file_id ? x.photo_url : t.photo_url }));

  const act = async (name, fn) => {
    setBusy(name);
    try { await fn(); } catch (e) { toast.error(errorMessage(e)); } finally { setBusy(""); }
  };
  const persist = async () => {
    const { id, event_id, share_token, updated_at, ...body } = inv;
    const { data } = await api.put(`/events/${event.id}/invitation`, body);
    setInv(data);
    reload();
  };
  const save = () => act("save", async () => { await persist(); toast.success("Uitnodiging opgeslagen"); });
  const share = () => act("share", async () => {
    await persist();
    const { data } = await api.post(`/events/${event.id}/invitation/share`);
    setToken(data.share_token);
    const url = `${window.location.origin}/u/${data.share_token}`;
    await navigator.clipboard?.writeText(url).catch(() => {});
    toast.success("Deellink gekopieerd", { description: url });
  });
  const download = () => act("png", async () => {
    const dataUrl = await toPng(preview.current, { pixelRatio: 2, cacheBust: true });
    const a = document.createElement("a");
    a.href = dataUrl;
    a.download = `uitnodiging-${event.title.replace(/\W+/g, "-").toLowerCase()}.png`;
    a.click();
  });
  const upload = (file) => file && act("photo", async () => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("category", "invitation");
    const { data } = await api.post(`/events/${event.id}/files`, fd);
    setInv((x) => ({ ...x, photo_file_id: data.id, photo_url: null }));
  });

  const txt = (k, label, area) => (
    <Field label={label}>
      {area ? <Textarea rows={3} value={inv[k] || ""} onChange={set(k)} className="wv-input" data-testid={`inv-${k}-input`} />
        : <Input value={inv[k] || ""} onChange={set(k)} className="wv-input h-11" data-testid={`inv-${k}-input`} />}
    </Field>
  );

  return (
    <div data-testid="invitation-builder">
      <SectionHeader
        eyebrow="Uitnodiging"
        title="Ontwerp jullie uitnodiging"
        text="Kies een sjabloon, pas tekst en stijl aan en deel hem direct met je gasten."
        action={
          <div className="flex flex-wrap gap-2">
            <button onClick={download} disabled={!!busy} className="wv-btn-ghost" data-testid="inv-download-button">{busy === "png" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}PNG</button>
            <button onClick={share} disabled={!!busy} className="wv-btn-ghost" data-testid="inv-share-button"><Link2 className="h-4 w-4" />Delen</button>
            <button onClick={save} disabled={!!busy} className="wv-btn" data-testid="inv-save-button"><Save className="h-4 w-4" />Opslaan</button>
          </div>
        }
      />
      <div className="grid gap-10 lg:grid-cols-[1fr_minmax(0,460px)]">
        <Tabs defaultValue="templates" className="order-2 lg:order-1">
          <TabsList className="mb-6 h-auto w-full justify-start gap-1 rounded-none border-b border-white/[0.06] bg-transparent p-0">
            {[["templates", "Sjabloon"], ["text", "Tekst"], ["style", "Stijl"], ["photo", "Foto"]].map(([v, l]) => (
              <TabsTrigger key={v} value={v} data-testid={`inv-tab-${v}`} className="rounded-none border-b-2 border-transparent px-4 py-3 text-zinc-500 data-[state=active]:border-[#D4AF37] data-[state=active]:bg-transparent data-[state=active]:text-white data-[state=active]:shadow-none">{l}</TabsTrigger>
            ))}
          </TabsList>
          <TabsContent value="templates">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              {templates.map((t) => (
                <button key={t.id} onClick={() => applyTemplate(t)} data-testid={`inv-template-${t.id}`} className={`group text-left ${inv.template_id === t.id ? "" : "opacity-80 hover:opacity-100"}`}>
                  <div className={`border p-1 transition-colors duration-200 ${inv.template_id === t.id ? "border-[#D4AF37]" : "border-transparent"}`}>
                    <InvitationCard inv={{ ...inv, ...t, title: inv.title || t.name }} photo={t.photo_url} testId={`inv-template-preview-${t.id}`} />
                  </div>
                  <p className="mt-2 text-sm text-white">{t.name}</p>
                  <p className="text-xs text-zinc-500">{t.description}</p>
                </button>
              ))}
            </div>
          </TabsContent>
          <TabsContent value="text" className="space-y-4">
            {txt("title", "Titel")}
            {txt("subtitle", "Ondertitel")}
            <div className="grid grid-cols-2 gap-4">{txt("date_text", "Datum")}{txt("time_text", "Tijd")}</div>
            {txt("location", "Locatie")}
            {txt("description", "Persoonlijke tekst", true)}
          </TabsContent>
          <TabsContent value="style" className="space-y-8">
            <Field label="Layout"><div className="flex flex-wrap gap-2">{Object.entries(LAYOUTS).map(([k, l]) => <Chip key={k} active={inv.layout === k} onClick={() => set("layout")(k)} testId={`inv-layout-${k}`}>{l}</Chip>)}</div></Field>
            <Field label="Typografie"><div className="flex flex-wrap gap-2">{Object.entries(FONTS).map(([k, f]) => <Chip key={k} active={inv.font === k} onClick={() => set("font")(k)} testId={`inv-font-${k}`} style={{ fontFamily: f.stack }}>Aa {f.label}</Chip>)}</div></Field>
            <Field label="Kleurenschema">
              <div className="flex flex-wrap gap-3">
                {PALETTES.map((p, i) => (
                  <button key={i} onClick={() => setInv((x) => ({ ...x, background_color: p[0], text_color: p[1], accent_color: p[2] }))} data-testid={`inv-palette-${i}`} className="flex overflow-hidden rounded-full border border-white/15 transition-transform duration-200 hover:scale-105">
                    {p.map((c) => <span key={c} className="h-8 w-6" style={{ background: c }} />)}
                  </button>
                ))}
              </div>
            </Field>
            <div className="grid grid-cols-3 gap-3">
              <ColorInput label="Achtergrond" value={inv.background_color} onChange={set("background_color")} testId="inv-bg-color" />
              <ColorInput label="Tekst" value={inv.text_color} onChange={set("text_color")} testId="inv-text-color" />
              <ColorInput label="Accent" value={inv.accent_color} onChange={set("accent_color")} testId="inv-accent-color" />
            </div>
          </TabsContent>
          <TabsContent value="photo" className="space-y-4">
            <input ref={photoInput} type="file" accept="image/*" className="hidden" onChange={(e) => upload(e.target.files[0])} data-testid="inv-photo-input" />
            <button onClick={() => photoInput.current.click()} className="wv-panel wv-hover flex w-full flex-col items-center gap-3 py-12 text-sm text-zinc-400" data-testid="inv-photo-upload-button">
              {busy === "photo" ? <Loader2 className="h-6 w-6 animate-spin text-[#D4AF37]" /> : <ImagePlus className="h-6 w-6 text-[#D4AF37]" strokeWidth={1.5} />}
              Upload een eigen foto
            </button>
            {photoSrc(inv) && <button onClick={() => setInv((x) => ({ ...x, photo_file_id: null, photo_url: null }))} className="flex items-center gap-2 text-sm text-zinc-500 hover:text-white" data-testid="inv-photo-remove-button"><X className="h-4 w-4" />Foto verwijderen</button>}
          </TabsContent>
        </Tabs>
        <div className="order-1 lg:order-2 lg:sticky lg:top-36 lg:self-start">
          <div className="shadow-[0_40px_80px_-20px_rgba(0,0,0,0.8)]">
            <InvitationCard inv={inv} photo={photoSrc(inv)} innerRef={preview} />
          </div>
          {token && <a href={`/u/${token}`} target="_blank" rel="noreferrer" className="mt-4 block text-center text-xs text-zinc-500 hover:text-[#E5C158]" data-testid="inv-public-link">Bekijk gedeelde versie →</a>}
        </div>
      </div>
    </div>
  );
}
