import { NavLink, Outlet } from "react-router-dom";
import { CalendarDays, LayoutGrid, LogOut, Palette, Disc3, Users } from "lucide-react";
import { Logo } from "./Logo";
import { NotificationBell } from "./NotificationBell";
import { useAuth } from "@/context/AuthContext";

const NAV = [
  { to: "/admin", label: "Overzicht", icon: LayoutGrid, end: true, id: "overview" },
  { to: "/admin/events", label: "Events", icon: CalendarDays, id: "events" },
  { to: "/admin/klanten", label: "Klanten", icon: Users, id: "customers", admin: true },
  { to: "/admin/djs", label: "DJ's", icon: Disc3, id: "djs", admin: true },
  { to: "/admin/sjablonen", label: "Sjablonen", icon: Palette, id: "templates", admin: true },
];

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const items = NAV.filter((n) => !n.admin || user.role === "admin");
  const linkCls = ({ isActive }) =>
    `flex items-center gap-3 whitespace-nowrap px-3 py-2.5 text-sm transition-colors duration-200 ${isActive ? "bg-white/[0.05] text-white" : "text-zinc-500 hover:text-zinc-200"}`;

  return (
    <div className="min-h-screen bg-[#09090B] lg:flex">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-white/[0.06] bg-[#0b0b0d] p-6 lg:flex lg:sticky lg:top-0 lg:h-screen">
        <Logo subtitle="Studio" />
        <nav className="mt-12 flex flex-col gap-1">
          {items.map(({ to, label, icon: Icon, end, id }) => (
            <NavLink key={to} to={to} end={end} className={linkCls} data-testid={`admin-nav-${id}`}>
              <Icon className="h-4 w-4" strokeWidth={1.5} /> {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto border-t border-white/[0.06] pt-5">
          <p className="text-sm text-white">{user.name}</p>
          <p className="text-xs text-zinc-500">{user.role === "admin" ? "Beheerder" : "DJ"}</p>
          <button onClick={logout} data-testid="admin-logout-button" className="mt-4 flex items-center gap-2 text-xs text-zinc-500 hover:text-white">
            <LogOut className="h-3.5 w-3.5" /> Uitloggen
          </button>
        </div>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-[#09090B]/80 backdrop-blur-xl">
          <div className="flex h-16 items-center justify-between px-4 sm:px-8">
            <div className="lg:hidden"><Logo /></div>
            <p className="hidden text-xs uppercase tracking-[0.3em] text-zinc-600 lg:block">White Vision · Beheer</p>
            <div className="flex items-center gap-2">
              <NotificationBell linkFor={(id) => `/admin/events/${id}?tab=chat`} />
              <button onClick={logout} className="p-2 text-zinc-400 hover:text-white lg:hidden" data-testid="admin-logout-mobile">
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
          <nav className="no-scrollbar flex gap-1 overflow-x-auto px-2 pb-2 lg:hidden">
            {items.map(({ to, label, end, id }) => (
              <NavLink key={to} to={to} end={end} className={linkCls} data-testid={`admin-mnav-${id}`}>{label}</NavLink>
            ))}
          </nav>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-8 sm:py-12">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
