import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate, useParams } from "react-router-dom";
import { ChevronDown, LogOut } from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Logo } from "./Logo";
import { NotificationBell } from "./NotificationBell";
import { useAuth } from "@/context/AuthContext";
import { EventProvider } from "@/context/EventContext";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";

const NAV = [
  ["", "Overzicht"], ["details", "Mijn event"], ["chat", "Chat met DJ"], ["muziek", "Muziek"],
  ["draaischema", "Draaischema"], ["uitnodiging", "Uitnodiging"], ["bestanden", "Bestanden"],
];

export default function CustomerLayout() {
  const { eventId } = useParams();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);

  useEffect(() => {
    api.get("/events").then((r) => setEvents(r.data)).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-[#09090B]">
      <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-[#09090B]/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-8">
          <Logo />
          <div className="flex items-center gap-2">
            <NotificationBell linkFor={(id) => `/event/${id}/chat`} />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button data-testid="user-menu-trigger" className="flex items-center gap-2 rounded-full border border-white/10 py-1 pl-1 pr-3 text-sm text-zinc-200 hover:border-white/25">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#D4AF37] text-xs font-bold text-black">{user.name?.[0]}</span>
                  <span className="hidden sm:inline">{user.name}</span>
                  <ChevronDown className="h-3.5 w-3.5" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64 rounded-sm border-white/10 bg-[#111114]">
                {events.length > 1 && (
                  <>
                    <DropdownMenuLabel className="text-xs uppercase tracking-[0.2em] text-zinc-500">Mijn events</DropdownMenuLabel>
                    {events.map((e) => (
                      <DropdownMenuItem key={e.id} data-testid={`switch-event-${e.id}`} onClick={() => navigate(`/event/${e.id}`)}>
                        <div>
                          <p className="text-sm">{e.title}</p>
                          <p className="text-xs text-zinc-500">{formatDate(e.date)}</p>
                        </div>
                      </DropdownMenuItem>
                    ))}
                    <DropdownMenuSeparator />
                  </>
                )}
                <DropdownMenuItem data-testid="logout-button" onClick={logout}>
                  <LogOut className="mr-2 h-4 w-4" /> Uitloggen
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
        <nav className="no-scrollbar mx-auto flex max-w-7xl gap-1 overflow-x-auto px-4 sm:px-8" data-testid="event-nav">
          {NAV.map(([path, label]) => (
            <NavLink
              key={path}
              end={path === ""}
              to={`/event/${eventId}/${path}`}
              data-testid={`nav-${path || "overview"}`}
              className={({ isActive }) =>
                `whitespace-nowrap border-b-2 px-3 py-3 text-sm transition-colors duration-200 ${isActive ? "border-[#D4AF37] text-white" : "border-transparent text-zinc-500 hover:text-zinc-200"}`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-8 sm:py-12">
        <EventProvider eventId={eventId}>
          <Outlet />
        </EventProvider>
      </main>
    </div>
  );
}
