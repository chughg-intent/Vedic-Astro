import { FormEvent, useState } from "react";
import { searchPlaces } from "../api";
import { BirthInput, ChartStyle, Place } from "../types";

interface Props {
  loading: boolean;
  onSubmit: (input: BirthInput) => void;
}

export default function BirthForm({ loading, onSubmit }: Props) {
  const [form, setForm] = useState<BirthInput>({
    name: "", date: "", time: "", city: "", state: "", country: "",
    chart_style: "north", ayanamsa: "lahiri",
  });
  const [places, setPlaces] = useState<Place[] | null>(null);
  const [place, setPlace] = useState<Place | null>(null);
  const [placeError, setPlaceError] = useState<string | null>(null);

  const set = <K extends keyof BirthInput>(k: K, v: BirthInput[K]) => {
    setForm((f) => ({ ...f, [k]: v }));
    if (k === "city" || k === "state" || k === "country") setPlace(null);
  };

  async function findPlace() {
    setPlaceError(null);
    try {
      const res = await searchPlaces(form.city, form.state, form.country);
      setPlaces(res);
      if (res.length === 1) setPlace(res[0]);
      if (!res.length) setPlaceError("No matching place found. Try a nearby larger city.");
    } catch (e) {
      setPlaceError((e as Error).message);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    onSubmit({
      ...form,
      gender: form.gender || undefined,
      ...(place ? { latitude: place.latitude, longitude: place.longitude, timezone: place.timezone } : {}),
    });
  }

  return (
    <form className="card form" onSubmit={submit}>
      <h2>Birth details</h2>
      <div className="form-grid">
        <label><span className="label-text">Name <span className="optional">optional</span></span>
          <input value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Your name" />
        </label>
        <label><span className="label-text">Gender <span className="optional">optional</span></span>
          <select value={form.gender ?? ""} onChange={(e) => set("gender", (e.target.value || undefined) as BirthInput["gender"])}>
            <option value="">Prefer not to say</option><option value="male">Male</option>
            <option value="female">Female</option><option value="other">Other</option>
          </select>
        </label>
        <label><span className="label-text">Date of birth</span>
          <input type="date" required value={form.date} onChange={(e) => set("date", e.target.value)} />
        </label>
        <label><span className="label-text">Time of birth <span className="optional">local time</span></span>
          <input type="time" step={1} required value={form.time} onChange={(e) => set("time", e.target.value)} />
        </label>
        <label><span className="label-text">City</span>
          <input required value={form.city} onChange={(e) => set("city", e.target.value)} placeholder="e.g. Jaipur" />
        </label>
        <label><span className="label-text">State / Province <span className="optional">optional</span></span>
          <input value={form.state} onChange={(e) => set("state", e.target.value)} />
        </label>
        <label><span className="label-text">Country</span>
          <input required value={form.country} onChange={(e) => set("country", e.target.value)} placeholder="e.g. India" />
        </label>
        <div className="place-lookup">
          <button type="button" className="secondary" disabled={!form.city || !form.country} onClick={findPlace}>
            Verify place
          </button>
        </div>
      </div>

      {placeError && <p className="error">{placeError}</p>}
      {places && places.length > 1 && (
        <div className="place-options">
          <p>Several places match. Pick the right one:</p>
          {places.map((p, i) => (
            <label key={i} className="radio">
              <input type="radio" name="place" checked={place === p} onChange={() => setPlace(p)} />
              {p.display_name} <small>({p.latitude.toFixed(2)}, {p.longitude.toFixed(2)} · {p.timezone})</small>
            </label>
          ))}
        </div>
      )}
      {place && (
        <p className="muted">
          Using {place.display_name} — {place.latitude.toFixed(4)}, {place.longitude.toFixed(4)}, {place.timezone}
        </p>
      )}

      <div className="field-row">
        <span className="field-label">Chart style</span>
        <div className="segmented" role="group" aria-label="Chart style">
          {(["north", "south"] as ChartStyle[]).map((st) => (
            <button key={st} type="button" className={form.chart_style === st ? "active" : ""}
                    aria-pressed={form.chart_style === st} onClick={() => set("chart_style", st)}>
              {st === "north" ? "North Indian" : "South Indian"}
            </button>
          ))}
        </div>
      </div>

      <details className="advanced">
        <summary>Advanced</summary>
        <label className="half"><span className="label-text">Ayanamsa</span>
          <select value={form.ayanamsa} onChange={(e) => set("ayanamsa", e.target.value as BirthInput["ayanamsa"])}>
            <option value="lahiri">Lahiri (Chitrapaksha)</option>
            <option value="raman">B.V. Raman</option>
            <option value="krishnamurti">Krishnamurti (KP)</option>
            <option value="true_chitra">True Chitra</option>
          </select>
        </label>
      </details>

      <button type="submit" className="primary" disabled={loading}>{loading ? "Calculating…" : "Generate chart"}</button>
      <p className="muted privacy">
        Your birth details are used only to calculate the chart and are not stored. The place you type is looked up
        with OpenStreetMap to find its coordinates and time zone.
      </p>
    </form>
  );
}
