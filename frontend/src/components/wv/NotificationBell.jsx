import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bell } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { api } from "@/lib/api";

export function NotificationBell({ linkFor }) {
  const [data, setData] = useState({ total: 0, events: [] });

  useEffect(() => {
    let alive = true;
    const load = () => api.get("/notifications").then((r) => alive && setData(r.data)).catch(() => {});
    load();
    const t = setInterval(load, 15000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button data-testid="notification-bell" className="relative rounded-full p-2 text-zinc-300 hover:text-white">
          <Bell className="h-5 w-5" strokeWidth={1.5} />
          {data.total > 0 && (
            <span data-testid="notification-count" className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-[#D4AF37] px-1 text-[10px] font-bold text-black">
              {data.total}
            </span>
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 rounded-sm border-white/10 bg-[#111114] p-0">
        <p className="border-b border-white/10 px-4 py-3 text-xs uppercase tracking-[0.2em] text-zinc-500">Meldingen</p>
        {data.events.length === 0 && <p className="px-4 py-5 text-sm text-zinc-400">Je bent helemaal bij.</p>}
        {data.events.map((e) => (
          <Link key={e.event_id} to={linkFor(e.event_id)} data-testid={`notification-item-${e.event_id}`} className="flex items-center justify-between px-4 py-3 text-sm hover:bg-white/5">
            <span className="text-zinc-200">{e.title}</span>
            <span className="text-xs text-[#E5C158]">{e.unread} nieuw</span>
          </Link>
        ))}
      </PopoverContent>
    </Popover>
  );
}
