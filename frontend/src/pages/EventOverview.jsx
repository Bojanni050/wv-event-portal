import { Link } from "react-router-dom";
import { ArrowUpRight, Check, Clock, MapPin, Users } from "lucide-react";
import { useEvent } from "@/context/EventContext";
import { ProgressLine, StatusBadge } from "@/components/wv/bits";
import { daysUntil, eventSubtitle, formatRelative, timeRange } from "@/lib/format";

function Hero({ event }) {
  const days = daysUntil(event.date);
  return (
    <section className="relative -mx-4 overflow-hidden sm:mx-0" data-testid="event-hero">
      <img src={event.cover_image || "/images/stage.jpg"} alt="" className="wv-kenburns absolute inset-0 h-full w-full object-cover" />
      <div className="absolute inset-0 bg-black/50" />
      <div className="absolute inset-0 bg-gradient-to-t from-[#09090B] via-[#09090B]/40 to-transparent" />
      <div className="relative flex min-h-[420px] flex-col justify-end p-6 sm:min-h-[480px] sm:p-12">
        <div className="wv-rise mb-5 flex flex-wrap items-center gap-3">
          <StatusBadge status={event.status} testId="event-status" />
          {days !== null && days >= 0 && (
            <span className="text-xs uppercase tracking-[0.25em] text-zinc-300" data-testid="event-countdown">
              Nog {days} {days === 1 ? "dag" : "dagen"}
            </span>
          )}
        </div>
        <h1 data-testid="event-title" className="font-display wv-rise wv-d1 text-6xl font-medium leading-[0.92] text-white sm:text-7xl lg:text-8xl">
          {event.title}
        </h1>
        <p data-testid="event-subtitle" className="font-display wv-rise wv-d2 mt-3 text-2xl italic text-[#E5C158] sm:text-3xl">{eventSubtitle(event)}</p>
        <div className="wv-rise wv-d3 mt-6 flex flex-wrap gap-x-6 gap-y-2 text-sm text-zinc-300">
          <span className="flex items-center gap-2"><Clock className="h-4 w-4 text-zinc-500" />{timeRange(event)}</span>
          {event.venue_name && <span className="flex items-center gap-2"><MapPin className="h-4 w-4 text-zinc-500" />{event.venue_name}{event.venue_city ? `, ${event.venue_city}` : ""}</span>}
          {event.guest_count && <span className="flex items-center gap-2"><Users className="h-4 w-4 text-zinc-500" />{event.guest_count} gasten</span>}
        </div>
      </div>
    </section>
  );
}

function Readiness({ event }) {
  const { overall, sections } = event.progress;
  return (
    <section className="wv-rise wv-d3 grid gap-10 border-b border-white/[0.06] py-12 lg:grid-cols-[1fr_1.4fr]" data-testid="event-progress">
      <div>
        <p className="wv-eyebrow mb-4">Voorbereiding</p>
        <p className="font-display text-4xl leading-tight text-white sm:text-5xl">
          Jullie event is <span data-testid="progress-overall" className="text-[#E5C158]">{overall}%</span> klaar
        </p>
        <ProgressLine value={overall} className="mt-6 max-w-sm" />
      </div>
      <ul className="grid gap-x-10 gap-y-4 sm:grid-cols-2">
        {sections.map((s) => (
          <li key={s.key} data-testid={`progress-section-${s.key}`} className="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <span className="flex items-center gap-3 text-sm text-zinc-300">
              <span className={`flex h-5 w-5 items-center justify-center rounded-full border ${s.percent === 100 ? "border-[#D4AF37] bg-[#D4AF37] text-black" : "border-white/20"}`}>
                {s.percent === 100 && <Check className="h-3 w-3" strokeWidth={3} />}
              </span>
              {s.label}
            </span>
            <span className={`text-sm tabular-nums ${s.percent === 100 ? "text-[#E5C158]" : "text-zinc-500"}`}>
              {s.percent === 100 ? "Klaar" : s.percent === 0 ? "Nog open" : `${s.percent}%`}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

const Card = ({ to, eyebrow, title, children, testId, className = "", delay = "" }) => (
  <Link to={to} data-testid={testId} className={`wv-panel wv-hover wv-rise ${delay} group flex flex-col justify-between p-6 sm:p-8 ${className}`}>
    <div className="flex items-start justify-between">
      <p className="wv-eyebrow">{eyebrow}</p>
      <ArrowUpRight className="h-4 w-4 text-zinc-600 transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-[#D4AF37]" />
    </div>
    <div className="mt-8">
      <p className="font-display text-3xl text-white">{title}</p>
      <div className="mt-3 text-sm text-zinc-400">{children}</div>
    </div>
  </Link>
);

export default function EventOverview() {
  const { event } = useEvent();
  const s = event.stats;
  const base = `/event/${event.id}`;
  const last = s.last_message;
  return (
    <div>
      <Hero event={event} />
      <Readiness event={event} />
      <section className="grid gap-4 py-12 md:grid-cols-6" data-testid="event-cards">
        <Card to={`${base}/chat`} eyebrow="Praat met je DJ" title={event.dj ? `${event.dj.name} — White Vision` : "White Vision"} testId="card-chat" className="md:col-span-4" delay="wv-d1">
          {last ? (
            <p className="line-clamp-2">
              <span className="text-zinc-500">{last.sender_role === "customer" ? "Jij" : last.sender_name}: </span>“{last.text}”
              <span className="ml-2 text-xs text-zinc-600">{formatRelative(last.created_at)}</span>
            </p>
          ) : "Stuur je DJ een eerste bericht."}
          {event.unread > 0 && <span data-testid="card-chat-unread" className="mt-3 inline-block rounded-full bg-[#D4AF37] px-2.5 py-0.5 text-xs font-semibold text-black">{event.unread} nieuw</span>}
        </Card>
        <Card to={`${base}/details`} eyebrow="Mijn event" title="Gegevens" testId="card-details" className="md:col-span-2" delay="wv-d2">
          {s.missing_info.length ? `Nog aan te vullen: ${s.missing_info.slice(0, 2).join(", ")}` : "Alle eventinformatie is compleet."}
        </Card>
        <Card to={`${base}/muziek`} eyebrow="Muziek" title={`${s.music.must_play} must plays`} testId="card-music" className="md:col-span-2" delay="wv-d2">
          {s.music.favorite} favorieten · {s.music.special} speciale momenten · {s.music.dont_play} liever niet
        </Card>
        <Card to={`${base}/draaischema`} eyebrow="Draaischema" title={`${s.timeline_count} momenten`} testId="card-timeline" className="md:col-span-2" delay="wv-d3">
          {s.timeline_confirmed} bevestigd door White Vision
        </Card>
        <Card to={`${base}/uitnodiging`} eyebrow="Uitnodiging" title={s.invitation_saved ? "Klaar om te delen" : "Ontwerp je uitnodiging"} testId="card-invitation" className="md:col-span-2" delay="wv-d3">
          {s.invitation_shared ? "Je uitnodiging is gedeeld." : "Kies een sjabloon en maak hem helemaal van jullie."}
        </Card>
        <Card to={`${base}/bestanden`} eyebrow="Bestanden" title={`${s.files_count} bestanden`} testId="card-files" className="md:col-span-6" delay="wv-d4">
          Foto's, contracten en documenten voor dit event.
        </Card>
      </section>
    </div>
  );
}
