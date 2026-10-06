import { Cake, GlassWater, Heart, Mic, Moon, Music2, Sparkles, Utensils, Camera, PartyPopper } from "lucide-react";

export const EVENT_TYPES = {
  wedding: "Bruiloft",
  birthday: "Verjaardag",
  corporate: "Bedrijfsfeest",
  party: "Feest",
  anniversary: "Jubileum",
  other: "Anders",
};

export const STATUSES = {
  new: "Nieuw",
  preparing: "In voorbereiding",
  ready: "Klaar",
  completed: "Afgerond",
};

export const MOMENTS = [
  { key: "entrance", label: "Binnenkomst" },
  { key: "opening_dance", label: "Openingsdans" },
  { key: "first_dance", label: "Eerste dans" },
  { key: "cake_cutting", label: "Taart aansnijden" },
  { key: "final_song", label: "Slotnummer" },
];

export const MUSIC_LISTS = [
  { key: "must_play", label: "Must Play", hint: "Deze nummers moeten absoluut voorbijkomen." },
  { key: "favorite", label: "Favorieten", hint: "Nummers waar jullie extra blij van worden." },
  { key: "dont_play", label: "Niet draaien", hint: "Nummers of artiesten die jullie liever niet horen." },
];

export const TIMELINE_ICONS = {
  glass: { icon: GlassWater, label: "Drankje" },
  mic: { icon: Mic, label: "Speech" },
  utensils: { icon: Utensils, label: "Diner" },
  heart: { icon: Heart, label: "Moment" },
  music: { icon: Music2, label: "Muziek" },
  cake: { icon: Cake, label: "Taart" },
  camera: { icon: Camera, label: "Foto's" },
  party: { icon: PartyPopper, label: "Feest" },
  sparkles: { icon: Sparkles, label: "Speciaal" },
  moon: { icon: Moon, label: "Einde" },
};

export const FONTS = {
  playfair: { label: "Playfair", stack: "'Playfair Display', serif" },
  cormorant: { label: "Cormorant", stack: "'Cormorant Garamond', serif" },
  italiana: { label: "Italiana", stack: "'Italiana', serif" },
  syne: { label: "Syne", stack: "'Syne', sans-serif" },
  jakarta: { label: "Jakarta", stack: "'Plus Jakarta Sans', sans-serif" },
};

export const LAYOUTS = {
  classic: "Klassiek",
  split: "Gesplitst",
  poster: "Poster",
  minimal: "Minimaal",
};

export const PALETTES = [
  ["#09090B", "#F4F4F5", "#D4AF37"],
  ["#FAFAFA", "#09090B", "#52525B"],
  ["#2A1E1A", "#F3E8EE", "#E5C158"],
  ["#0F0B1E", "#FFFFFF", "#00F0FF"],
  ["#FDFBF7", "#1C1917", "#B45309"],
  ["#14231C", "#EDEAE0", "#C9A86A"],
];
