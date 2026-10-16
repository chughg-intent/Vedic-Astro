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
      <div className="grid">
        <label>Name (optional)
          <input value={form.name} onChange={(e) => set("name", e.target.value)} />
        </label>
        <label>Gender (optional)
          <select value={form.gender ?? ""} onChange={(e) => set("gender", (e.target.value || undefined) as BirthInput["gender"])}>
            <option value="">—</option><option value="male">Male</option>
            <option value="female">Female</option><option value="other">Other</option>
          </select>
        </label>
        <label>Date of birth
          <input type="date" required value={form.date} onChange={(e) => set("date", e.target.value)} />
        </label>
        <label>Time of birth (local)
          <input type="time" step={1} required value={form.time} onChange={(e) => set("time", e.target.value)} />
        </label>
        <label>City
          <input required value={form.city} onChange={(e) => set("city", e.target.value)} />
        </label>
        <label>State / Province
          <input value={form.state} onChange={(e) => set("state", e.target.value)} />
        </label>
        <label>Country
          <input required value={form.country} onChange={(e) => set("country", e.target.value)} />
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

      <fieldset className="style-picker">
        <legend>Chart style</legend>
        {(["north", "south"] as ChartStyle[]).map((s) => (
          <label key={s} className="radio">
            <input type="radio" name="style" checked={form.chart_style === s} onChange={() => set("chart_style", s)} />
            {s === "north" ? "North Indian" : "South Indian"}
          </label>
        ))}
      </fieldset>

      <details>
        <summary>Advanced</summary>
        <label>Ayanamsa
          <select value={form.ayanamsa} onChange={(e) => set("ayanamsa", e.target.value as BirthInput["ayanamsa"])}>
            <option value="lahiri">Lahiri (Chitrapaksha)</option>
            <option value="raman">B.V. Raman</option>
            <option value="krishnamurti">Krishnamurti (KP)</option>
            <option value="true_chitra">True Chitra</option>
          </select>
        </label>
      </details>

      <button type="submit" disabled={loading}>{loading ? "Calculating…" : "Generate chart"}</button>
      <p className="muted privacy">
        Your birth details are used only to calculate the chart and are not stored. The place you type is looked up
        with OpenStreetMap to find its coordinates and time zone.
      </p>
    </form>
  );
}
