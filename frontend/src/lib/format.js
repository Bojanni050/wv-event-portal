import { EVENT_TYPES } from "./constants";

export function formatDate(iso, opts = {}) {
  if (!iso) return "Datum volgt";
  return new Intl.DateTimeFormat("nl-NL", { day: "numeric", month: "long", year: "numeric", ...opts }).format(
    new Date(`${iso}T12:00:00`)
  );
}

export function daysUntil(iso) {
  if (!iso) return null;
  const today = new Date(new Date().toDateString());
  return Math.round((new Date(`${iso}T00:00:00`) - today) / 86400000);
}

export const formatClock = (ts) =>
  new Date(ts).toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" });

export function formatDay(ts) {
  const d = new Date(ts);
  const today = new Date();
  const yesterday = new Date(Date.now() - 86400000);
  if (d.toDateString() === today.toDateString()) return "Vandaag";
  if (d.toDateString() === yesterday.toDateString()) return "Gisteren";
  return d.toLocaleDateString("nl-NL", { weekday: "long", day: "numeric", month: "long" });
}

export function formatRelative(ts) {
  if (!ts) return "";
  const mins = Math.round((Date.now() - new Date(ts)) / 60000);
  if (mins < 1) return "zojuist";
  if (mins < 60) return `${mins} min geleden`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} uur geleden`;
  const days = Math.round(hours / 24);
  return days === 1 ? "gisteren" : `${days} dagen geleden`;
}

export function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export const eventSubtitle = (ev) => `${EVENT_TYPES[ev.event_type] || "Event"} · ${formatDate(ev.date)}`;

export const timeRange = (ev) =>
  ev.start_time ? `${ev.start_time}${ev.end_time ? ` — ${ev.end_time}` : ""}` : "Tijden volgen";
