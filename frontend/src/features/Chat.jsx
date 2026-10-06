import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { Check, CheckCheck, FileText, Loader2, Paperclip, Pin, PinOff, Send, X } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { useEvent } from "@/context/EventContext";
import { api, errorMessage, fileUrl } from "@/lib/api";
import { formatClock, formatDay } from "@/lib/format";

const isStaffRole = (r) => r === "admin" || r === "dj";

function Attachment({ a }) {
  if (a.content_type.startsWith("image/")) {
    return (
      <a href={fileUrl(a.file_id)} target="_blank" rel="noreferrer" className="mb-1 block overflow-hidden">
        <img src={fileUrl(a.file_id)} alt={a.filename} className="max-h-64 w-full object-cover" />
      </a>
    );
  }
  return (
    <a href={fileUrl(a.file_id)} target="_blank" rel="noreferrer" className="mb-1 flex items-center gap-2 bg-black/20 px-3 py-2 text-sm underline-offset-2 hover:underline">
      <FileText className="h-4 w-4" /> {a.filename}
    </a>
  );
}

function Bubble({ m, mine, onPin }) {
  const fromStaff = isStaffRole(m.sender_role);
  const read = fromStaff ? m.read_by_customer : m.read_by_staff;
  const tone = fromStaff ? "bg-[#D4AF37] text-black" : "bg-[#232327] text-zinc-100";
  return (
    <div className={`group flex ${mine ? "justify-end" : "justify-start"}`} data-testid={`message-${m.id}`}>
      <div className={`flex max-w-[82%] items-end gap-2 sm:max-w-[65%] ${mine ? "flex-row-reverse" : ""}`}>
        <div className={`px-4 py-2.5 ${tone} ${mine ? "rounded-2xl rounded-br-sm" : "rounded-2xl rounded-bl-sm"}`}>
          {!mine && <p className={`mb-0.5 text-[11px] font-semibold ${fromStaff ? "text-black/60" : "text-[#E5C158]"}`}>{fromStaff ? `${m.sender_name} — White Vision` : m.sender_name}</p>}
          {m.attachment && <Attachment a={m.attachment} />}
          {m.text && <p className="whitespace-pre-wrap text-[15px] leading-snug">{m.text}</p>}
          <p className={`mt-1 flex items-center justify-end gap-1 text-[10px] ${fromStaff ? "text-black/55" : "text-zinc-500"}`}>
            {m.pinned && <Pin className="h-2.5 w-2.5" />}
            {formatClock(m.created_at)}
            {mine && (read ? <CheckCheck className="h-3 w-3" data-testid="message-read" /> : <Check className="h-3 w-3" data-testid="message-sent" />)}
          </p>
        </div>
        <button onClick={() => onPin(m)} data-testid={`pin-message-${m.id}`} title={m.pinned ? "Losmaken" : "Vastzetten als afspraak"} className="mb-1 p-1 text-zinc-600 opacity-0 transition-opacity duration-200 hover:text-[#D4AF37] group-hover:opacity-100">
          {m.pinned ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
        </button>
      </div>
    </div>
  );
}

function Agreements({ items, onPin }) {
  return (
    <aside className="wv-panel h-fit p-6" data-testid="agreements-panel">
      <p className="wv-eyebrow mb-1">Belangrijke afspraken</p>
      <p className="mb-5 text-xs text-zinc-500">Zet een bericht vast met het speldje om het hier te bewaren.</p>
      {items.length === 0 && <p className="text-sm text-zinc-500">Nog geen afspraken vastgezet.</p>}
      <ul className="space-y-4">
        {items.map((m) => (
          <li key={m.id} className="group border-l border-[#D4AF37]/60 pl-4" data-testid={`agreement-${m.id}`}>
            <p className="font-display text-lg leading-snug text-white">“{m.text || m.attachment?.filename}”</p>
            <p className="mt-1 flex items-center justify-between text-xs text-zinc-500">
              {m.sender_name} · {formatDay(m.created_at)}
              <button onClick={() => onPin(m)} className="opacity-0 hover:text-white group-hover:opacity-100"><X className="h-3 w-3" /></button>
            </p>
          </li>
        ))}
      </ul>
    </aside>
  );
}

export default function Chat() {
  const { event } = useEvent();
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const scroller = useRef(null);
  const fileInput = useRef(null);
  const count = useRef(0);

  const load = useCallback(async () => {
    const { data } = await api.get(`/events/${event.id}/messages`);
    setMessages(data);
  }, [event.id]);

  useEffect(() => {
    load().catch(() => {});
    const t = setInterval(() => load().catch(() => {}), 4000);
    return () => clearInterval(t);
  }, [load]);

  useEffect(() => {
    if (messages.length !== count.current && scroller.current) {
      scroller.current.scrollTop = scroller.current.scrollHeight;
      count.current = messages.length;
    }
  }, [messages]);

  const send = async (payload) => {
    setBusy(true);
    try {
      const { data } = await api.post(`/events/${event.id}/messages`, payload);
      setMessages((m) => [...m, data]);
      setText("");
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const attach = async (file) => {
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("category", "chat");
    setBusy(true);
    try {
      const { data } = await api.post(`/events/${event.id}/files`, fd);
      await send({ text: text.trim(), attachment_file_id: data.id });
    } catch (e) {
      toast.error(errorMessage(e));
      setBusy(false);
    }
    fileInput.current.value = "";
  };

  const togglePin = async (m) => {
    const { data } = await api.patch(`/messages/${m.id}`, { pinned: !m.pinned });
    setMessages((list) => list.map((x) => (x.id === data.id ? data : x)));
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (text.trim()) send({ text });
    }
  };

  const partner = event.dj ? `${event.dj.name} — White Vision` : "White Vision";
  const header = isStaffRole(user.role) ? event.customer?.name || event.title : partner;

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]" data-testid="chat">
      <section className="wv-panel flex h-[70vh] min-h-[480px] flex-col">
        <div className="flex items-center gap-3 border-b border-white/[0.06] px-5 py-4">
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#D4AF37] font-display text-lg font-semibold text-black">{header[0]}</span>
          <div>
            <p className="text-sm font-semibold text-white" data-testid="chat-partner-name">{header}</p>
            <p className="text-xs text-zinc-500">{event.title}</p>
          </div>
        </div>
        <div ref={scroller} className="wv-scroll flex-1 space-y-2 overflow-y-auto px-4 py-6 sm:px-6" data-testid="chat-messages">
          {messages.length === 0 && <p className="mt-10 text-center text-sm text-zinc-500">Nog geen berichten. Zeg hallo!</p>}
          {messages.map((m, i) => {
            const day = formatDay(m.created_at);
            const showDay = i === 0 || formatDay(messages[i - 1].created_at) !== day;
            return (
              <Fragment key={m.id}>
                {showDay && <p className="py-3 text-center text-[11px] uppercase tracking-[0.2em] text-zinc-600">{day}</p>}
                <Bubble m={m} mine={m.sender_id === user.id} onPin={togglePin} />
              </Fragment>
            );
          })}
        </div>
        <div className="flex items-end gap-2 border-t border-white/[0.06] p-3 sm:p-4">
          <input ref={fileInput} type="file" className="hidden" accept="image/*,.pdf,.doc,.docx" onChange={(e) => attach(e.target.files[0])} data-testid="chat-file-input" />
          <button onClick={() => fileInput.current.click()} disabled={busy} className="rounded-full p-3 text-zinc-400 hover:bg-white/5 hover:text-white" data-testid="chat-attach-button"><Paperclip className="h-5 w-5" /></button>
          <textarea value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKey} rows={1} placeholder="Typ een bericht..." className="max-h-32 flex-1 resize-none rounded-3xl border border-white/10 bg-[#0c0c0f] px-4 py-3 text-sm text-white outline-none focus:border-[#D4AF37]/50" data-testid="chat-input" />
          <button onClick={() => send({ text })} disabled={busy || !text.trim()} className="flex h-11 w-11 items-center justify-center rounded-full bg-[#D4AF37] text-black transition-transform duration-200 active:scale-95 disabled:opacity-40" data-testid="chat-send-button">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </div>
      </section>
      <Agreements items={messages.filter((m) => m.pinned)} onPin={togglePin} />
    </div>
  );
}
