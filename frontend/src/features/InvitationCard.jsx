import { FONTS } from "@/lib/constants";

const fs = (n) => ({ fontSize: `${n}cqw` });

function Details({ inv, align = "center" }) {
  return (
    <div style={{ textAlign: align }}>
      {inv.date_text && <p style={{ ...fs(4.6), lineHeight: 1.2 }}>{inv.date_text}</p>}
      {inv.time_text && <p style={{ ...fs(3.4), opacity: 0.85, marginTop: "1cqw" }}>{inv.time_text}</p>}
      {inv.location && <p style={{ ...fs(2.8), color: inv.accent_color, letterSpacing: "0.25em", textTransform: "uppercase", marginTop: "2.5cqw" }}>{inv.location}</p>}
    </div>
  );
}

const Desc = ({ inv, align }) =>
  inv.description ? <p style={{ ...fs(3), opacity: 0.78, marginTop: "4cqw", lineHeight: 1.5, textAlign: align }}>{inv.description}</p> : null;

const Sub = ({ inv }) =>
  inv.subtitle ? <p style={{ ...fs(3.4), color: inv.accent_color, fontStyle: "italic" }}>{inv.subtitle}</p> : null;

function Classic({ inv, photo }) {
  return (
    <div className="absolute flex flex-col items-center justify-center" style={{ inset: "4%", border: `1px solid ${inv.accent_color}66`, padding: "7%" }}>
      {photo && (
        <div style={{ width: "34%", aspectRatio: "3/4", borderRadius: "999px 999px 0 0", overflow: "hidden", marginBottom: "5cqw" }}>
          <img src={photo} alt="" crossOrigin="anonymous" className="h-full w-full object-cover" />
        </div>
      )}
      <Sub inv={inv} />
      <h1 style={{ ...fs(11), lineHeight: 1, margin: "3cqw 0", textAlign: "center" }}>{inv.title}</h1>
      <div style={{ width: "12%", height: 1, background: inv.accent_color, marginBottom: "4cqw" }} />
      <Details inv={inv} />
      <Desc inv={inv} align="center" />
    </div>
  );
}

function Poster({ inv, photo }) {
  return (
    <>
      {photo && <img src={photo} alt="" crossOrigin="anonymous" className="absolute inset-0 h-full w-full object-cover" />}
      <div className="absolute inset-0" style={{ background: `linear-gradient(to top, ${inv.background_color} 22%, ${inv.background_color}99 55%, transparent)` }} />
      <div className="absolute inset-x-0 bottom-0" style={{ padding: "8%" }}>
        <Sub inv={inv} />
        <h1 style={{ ...fs(15), lineHeight: 0.9, margin: "2cqw 0 5cqw", textTransform: "uppercase", fontWeight: 800 }}>{inv.title}</h1>
        <div style={{ borderTop: `2px solid ${inv.accent_color}`, paddingTop: "4cqw" }}><Details inv={inv} align="left" /></div>
        <Desc inv={inv} align="left" />
      </div>
    </>
  );
}

function Split({ inv, photo }) {
  return (
    <div className="absolute inset-0 grid grid-cols-2">
      <div className="h-full overflow-hidden" style={{ background: inv.accent_color + "33" }}>
        {photo && <img src={photo} alt="" crossOrigin="anonymous" className="h-full w-full object-cover" />}
      </div>
      <div className="flex flex-col justify-center" style={{ padding: "8%" }}>
        <Sub inv={inv} />
        <h1 style={{ ...fs(8.5), lineHeight: 1, margin: "3cqw 0 5cqw" }}>{inv.title}</h1>
        <Details inv={inv} align="left" />
        <Desc inv={inv} align="left" />
      </div>
    </div>
  );
}

function Minimal({ inv }) {
  return (
    <div className="absolute inset-0 flex flex-col justify-between" style={{ padding: "9%" }}>
      <div>
        <p style={{ ...fs(2.6), letterSpacing: "0.35em", textTransform: "uppercase", color: inv.accent_color }}>{inv.subtitle}</p>
        <h1 style={{ ...fs(14), lineHeight: 0.95, marginTop: "5cqw", fontWeight: 700, letterSpacing: "-0.03em" }}>{inv.title}</h1>
      </div>
      <div>
        <div style={{ height: 2, background: inv.text_color, marginBottom: "5cqw" }} />
        <Details inv={inv} align="left" />
        <Desc inv={inv} align="left" />
      </div>
    </div>
  );
}

const LAYOUT_COMPONENTS = { classic: Classic, poster: Poster, split: Split, minimal: Minimal };

export function InvitationCard({ inv, photo, innerRef, className = "", testId = "invitation-preview" }) {
  const Layout = LAYOUT_COMPONENTS[inv.layout] || Classic;
  return (
    <div
      ref={innerRef}
      data-testid={testId}
      className={`relative aspect-[4/5] w-full overflow-hidden ${className}`}
      style={{ background: inv.background_color, color: inv.text_color, fontFamily: (FONTS[inv.font] || FONTS.playfair).stack, containerType: "inline-size" }}
    >
      <Layout inv={inv} photo={photo} />
    </div>
  );
}
