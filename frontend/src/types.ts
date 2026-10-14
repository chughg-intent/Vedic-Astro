export type ChartStyle = "north" | "south";

export interface BirthInput {
  name?: string;
  gender?: "male" | "female" | "other";
  date: string;
  time: string;
  city: string;
  state?: string;
  country: string;
  latitude?: number;
  longitude?: number;
  timezone?: string;
  chart_style: ChartStyle;
  ayanamsa: "lahiri" | "raman" | "krishnamurti" | "true_chitra";
}

export interface Place {
  name: string;
  display_name: string;
  latitude: number;
  longitude: number;
  timezone: string;
  country_code: string | null;
  source: string;
}

export interface SignLabel { index: number; name: string; sanskrit: string; lord: string }

export interface PlanetRow {
  name: string;
  abbr: string;
  longitude: number;
  sign: SignLabel;
  degree: string;
  house: number;
  nakshatra: { index: number; name: string; pada: number; lord: string };
  retrograde: boolean;
  combust: boolean;
  dignity: string | null;
  rules: number[];
  navamsa_sign: number;
}

export interface HouseRow {
  house: number;
  sign: SignLabel;
  lord: string;
  lord_in_house: number;
  occupants: string[];
  aspected_by: string[];
}

export interface Varga {
  division: number;
  name: string;
  theme: string;
  lagna_sign: number;
  placements: Record<string, number>;
  houses: Record<string, number>;
}

export interface DashaPeriod { lord: string; start: string; end: string; sub?: DashaPeriod[] }

export interface Yoga {
  name: string;
  category: string;
  planets: string[];
  description: string;
  conditions: string[];
  strength: string;
}

export interface ShadbalaRow {
  sthana: number; dig: number; kala: number; cheshta: number; naisargika: number; drik: number;
  total_rupas: number; required_rupas: number; ratio: number;
}

export interface ChartResponse {
  input: BirthInput;
  place: Place;
  time: { utc: string; timezone: string; utc_offset_hours: number; dst: boolean; notes: string[] };
  settings: { ayanamsa: string; ayanamsa_value: number; node: string; house_system: string };
  lagna: { longitude: number; sign: string };
  planets: PlanetRow[];
  houses: HouseRow[];
  vargas: Record<string, Varga>;
  vargottama: string[];
  dasha: { system: string; periods: DashaPeriod[]; current: string[] };
  yogas: Yoga[];
  doshas: Array<Record<string, unknown> & { name: string; present: boolean }>;
  ashtakavarga: { bav: Record<string, number[]>; sav: number[]; sav_by_house: number[]; total: number };
  shadbala: { planets: Record<string, ShadbalaRow>; ranking: string[] };
  transits: {
    as_of: string;
    planets: Array<{ name: string; sign: string; retrograde: boolean; house_from_lagna: number; house_from_moon: number }>;
    sade_sati: { active: boolean; phase: string | null };
    shani_dhaiya: { active: boolean; type: string | null };
  };
  life_areas: Record<string, LifeArea>;
}

export interface LifeArea {
  title: string;
  houses: Array<{ house: number; signifies: string; sign: string; occupants: string[]; aspected_by: string[];
    lord: PlanetFact }>;
  karakas: PlanetFact[];
  yogas: Yoga[];
  dasha_periods: Array<{ lord: string; start: string; end: string }>;
}

export interface PlanetFact {
  planet: string; house: number; sign: string; dignity: string; retrograde: boolean; combust: boolean;
  conjunctions: string[]; aspected_by: string[];
}

export const SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
  "Sagittarius", "Capricorn", "Aquarius", "Pisces"];
export const SIGN_ABBR = ["Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"];
export const ABBR: Record<string, string> = {
  Sun: "Su", Moon: "Mo", Mars: "Ma", Mercury: "Me", Jupiter: "Ju", Venus: "Ve", Saturn: "Sa",
  Rahu: "Ra", Ketu: "Ke", Ascendant: "As",
};
