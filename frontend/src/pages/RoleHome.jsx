import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { CalendarHeart } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { daysUntil } from "@/lib/format";
import { EmptyState, PageLoader } from "@/components/wv/bits";
import { Logo } from "@/components/wv/Logo";

export default function RoleHome() {
  const { user, isStaff, logout } = useAuth();
  const [events, setEvents] = useState(null);

  useEffect(() => {
    if (!isStaff) api.get("/events").then((r) => setEvents(r.data)).catch(() => setEvents([]));
  }, [isStaff]);

  if (isStaff) return <Navigate to="/admin" replace />;
  if (events === null) return <PageLoader />;
  if (events.length) {
    const next = events.find((e) => (daysUntil(e.date) ?? 0) >= 0) || events[0];
    return <Navigate to={`/event/${next.id}`} replace />;
  }
  return (
    <div className="mx-auto max-w-xl px-6 py-20">
      <Logo className="mb-12" />
      <EmptyState
        icon={CalendarHeart}
        title={`Welkom, ${user.name}`}
        text="Je event wordt op dit moment klaargezet door White Vision. Zodra het klaarstaat, vind je het hier."
        action={<button className="wv-btn-ghost mt-2" onClick={logout} data-testid="empty-logout-button">Uitloggen</button>}
      />
    </div>
  );
}
