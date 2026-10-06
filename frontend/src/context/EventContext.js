import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { EmptyState, PageLoader } from "@/components/wv/bits";

const EventCtx = createContext(null);

export function EventProvider({ eventId, children }) {
  const [event, setEvent] = useState(null);
  const [error, setError] = useState(null);

  const reload = useCallback(async () => {
    try {
      const { data } = await api.get(`/events/${eventId}`);
      setEvent(data);
      setError(null);
    } catch (e) {
      setError(errorMessage(e));
    }
  }, [eventId]);

  useEffect(() => {
    setEvent(null);
    reload();
  }, [reload]);

  if (error) return <EmptyState title="Event niet gevonden" text={error} />;
  if (!event) return <PageLoader />;
  return <EventCtx.Provider value={{ event, reload }}>{children}</EventCtx.Provider>;
}

export const useEvent = () => useContext(EventCtx);
