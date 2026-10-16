import { useEffect, useState } from "react";
import { fetchReport } from "../api";
import { ChartResponse, ChartStyle, DashaPeriod, ReportParagraph, RuleMatch, SIGNS, SIGN_ABBR, WrittenReport } from "../types";
import ChartDiagram from "./ChartDiagram";

const TABS = ["Charts", "Planets", "Dasha", "Yogas & Doshas", "Strength", "Transits", "Report"] as const;
type Tab = (typeof TABS)[number];

const fmtDate = (iso: string) => new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });

export default function Results({ data, style, onStyle }: { data: ChartResponse; style: ChartStyle; onStyle: (s: ChartStyle) => void }) {
  const [tab, setTab] = useState<Tab>("Charts");
  // Kept here so the written report survives switching tabs; cleared when a new chart is cast.
  const [written, setWritten] = useState<ReportState>({ status: "idle" });
  useEffect(() => setWritten({ status: "idle" }), [data]);
  return (
    <section className="results">
      <div className="card summary">
        <div>
          <h2>{data.input.name || "Birth chart"}</h2>
          <p className="muted">
            {data.input.date} {data.input.time} · {data.place.display_name} · UTC{data.time.utc_offset_hours >= 0 ? "+" : ""}
            {data.time.utc_offset_hours} ({data.time.timezone}{data.time.dst ? ", DST" : ""})
          </p>
          <p className="muted">
            Lagna {data.lagna.sign} · Moon {data.planets.find((p) => p.name === "Moon")?.sign.name} ({data.planets.find((p) => p.name === "Moon")?.nakshatra.name})
            · Ayanamsa {data.settings.ayanamsa} {data.settings.ayanamsa_value.toFixed(4)}°
          </p>
          {data.time.notes.map((n) => <p key={n} className="warn">{n}</p>)}
        </div>
        <div className="segmented" role="group" aria-label="Chart style">
          {(["north", "south"] as ChartStyle[]).map((s) => (
            <button key={s} className={s === style ? "active" : ""} onClick={() => onStyle(s)}>
              {s === "north" ? "North Indian" : "South Indian"}
            </button>
          ))}
        </div>
      </div>

      <nav className="tabs">
        {TABS.map((t) => <button key={t} className={t === tab ? "active" : ""} onClick={() => setTab(t)}>{t}</button>)}
      </nav>

      {tab === "Charts" && <Charts data={data} style={style} />}
      {tab === "Planets" && <Planets data={data} />}
      {tab === "Dasha" && <Dasha data={data} />}
      {tab === "Yogas & Doshas" && <Yogas data={data} />}
      {tab === "Strength" && <Strength data={data} />}
      {tab === "Transits" && <Transits data={data} />}
      {tab === "Report" && <Report data={data} written={written} setWritten={setWritten} />}
    </section>
  );
}

function Charts({ data, style }: { data: ChartResponse; style: ChartStyle }) {
  const [div, setDiv] = useState("10");
  const retro = new Set(data.planets.filter((p) => p.retrograde).map((p) => p.name));
  const v = (d: string) => data.vargas[d];
  return (
    <div className="card">
      <div className="charts">
        <ChartDiagram style={style} title="Rashi (D1)" lagnaSign={v("1").lagna_sign} placements={v("1").placements} retrograde={retro} />
        <ChartDiagram style={style} title="Navamsa (D9)" lagnaSign={v("9").lagna_sign} placements={v("9").placements} retrograde={retro} />
        <div>
          <ChartDiagram style={style} title={`${v(div).name} (D${div})`} lagnaSign={v(div).lagna_sign} placements={v(div).placements} retrograde={retro} />
          <label className="inline">Divisional chart{" "}
            <select value={div} onChange={(e) => setDiv(e.target.value)}>
              {Object.values(data.vargas).map((x) => (
                <option key={x.division} value={String(x.division)}>D{x.division} {x.name} — {x.theme}</option>
              ))}
            </select>
          </label>
        </div>
      </div>
      {data.vargottama.length > 0 && <p className="muted">Vargottama (same sign in D1 and D9): {data.vargottama.join(", ")}</p>}
    </div>
  );
}

function Planets({ data }: { data: ChartResponse }) {
  return (
    <div className="card scroll">
      <table>
        <thead><tr><th>Planet</th><th>Sign</th><th>Degree</th><th>House</th><th>Nakshatra</th><th>Pada</th><th>Nak. lord</th><th>Navamsa</th><th>Dignity</th><th>Rules</th><th>Status</th></tr></thead>
        <tbody>
          {data.planets.map((p) => (
            <tr key={p.name}>
              <td>{p.name}</td><td>{p.sign.name}</td><td className="num">{p.degree}</td><td className="num">{p.house}</td>
              <td>{p.nakshatra.name}</td><td className="num">{p.nakshatra.pada}</td><td>{p.nakshatra.lord}</td>
              <td>{SIGNS[p.navamsa_sign]}</td><td>{p.dignity ?? "—"}</td><td>{p.rules.join(", ") || "—"}</td>
              <td>{[p.retrograde && p.name !== "Rahu" && p.name !== "Ketu" ? "Retrograde" : "", p.combust ? "Combust" : ""].filter(Boolean).join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3>Houses</h3>
      <table>
        <thead><tr><th>House</th><th>Sign</th><th>Lord</th><th>Lord in</th><th>Occupants</th><th>Aspected by</th></tr></thead>
        <tbody>
          {data.houses.map((h) => (
            <tr key={h.house}>
              <td className="num">{h.house}</td><td>{h.sign.name}</td><td>{h.lord}</td><td className="num">{h.lord_in_house}</td>
              <td>{h.occupants.join(", ") || "—"}</td><td>{h.aspected_by.join(", ") || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Dasha({ data }: { data: ChartResponse }) {
  const now = Date.now();
  const running = (p: DashaPeriod) => new Date(p.start).getTime() <= now && now < new Date(p.end).getTime();
  return (
    <div className="card">
      <p>Current period: <strong>{data.dasha.current.join(" › ")}</strong></p>
      <div className="dasha">
        {data.dasha.periods.map((md) => (
          <details key={md.start} open={running(md)} className={running(md) ? "running" : ""}>
            <summary><strong>{md.lord}</strong> Mahadasha <span className="muted">{fmtDate(md.start)} – {fmtDate(md.end)}</span></summary>
            {md.sub?.map((ad) => (
              <details key={ad.start} className={running(ad) ? "running sub" : "sub"} open={running(ad)}>
                <summary>{md.lord} / <strong>{ad.lord}</strong> <span className="muted">{fmtDate(ad.start)} – {fmtDate(ad.end)}</span></summary>
                <ul>
                  {ad.sub?.map((pd) => (
                    <li key={pd.start} className={running(pd) ? "running" : ""}>
                      {ad.lord} / {pd.lord} <span className="muted">{fmtDate(pd.start)} – {fmtDate(pd.end)}</span>
                    </li>
                  ))}
                </ul>
              </details>
            ))}
          </details>
        ))}
      </div>
    </div>
  );
}

function Yogas({ data }: { data: ChartResponse }) {
  return (
    <div className="card">
      <h3>Doshas</h3>
      <ul>
        {data.doshas.map((d) => (
          <li key={d.name}>
            <strong>{d.name}</strong>: {d.present ? "present" : "not present"}
            {d.name === "Mangal Dosha" && d.present ? ` (severity: ${d.severity}; from ${Object.keys(d.from as object).join(", ")})` : ""}
            {d.name === "Kaal Sarp Dosha" && d.present ? ` (${d.type})` : ""}
            {Array.isArray(d.mitigations) && d.mitigations.length > 0 && <span className="muted"> — mitigated: {(d.mitigations as string[]).join("; ")}</span>}
          </li>
        ))}
        <li><strong>Sade Sati</strong> (now): {data.transits.sade_sati.active ? data.transits.sade_sati.phase : "not active"}</li>
      </ul>
      <h3>Yogas ({data.yogas.length})</h3>
      <div className="yoga-list">
        {data.yogas.map((y, i) => (
          <div key={i} className={`yoga ${y.strength}`}>
            <div><strong>{y.name}</strong> <span className="tag">{y.category}</span>{y.strength !== "normal" && <span className="tag">{y.strength}</span>}</div>
            <p>{y.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function Strength({ data }: { data: ChartResponse }) {
  const sb = data.shadbala.planets;
  const max = Math.max(...Object.values(sb).map((r) => r.ratio), 1.5);
  const bavPlanets = Object.keys(data.ashtakavarga.bav);
  return (
    <div className="card scroll">
      <h3>Shadbala</h3>
      <table>
        <thead><tr><th>Planet</th><th>Sthana</th><th>Dig</th><th>Kala</th><th>Cheshta</th><th>Naisargika</th><th>Drik</th><th>Total (rupas)</th><th>Required</th><th>Strength</th></tr></thead>
        <tbody>
          {data.shadbala.ranking.map((p) => {
            const r = sb[p];
            return (
              <tr key={p}>
                <td>{p}</td>
                {[r.sthana, r.dig, r.kala, r.cheshta, r.naisargika, r.drik].map((v, i) => <td key={i} className="num">{v.toFixed(1)}</td>)}
                <td className="num">{r.total_rupas.toFixed(2)}</td><td className="num">{r.required_rupas}</td>
                <td><div className="bar"><div className={r.ratio >= 1 ? "fill ok" : "fill low"} style={{ width: `${(r.ratio / max) * 100}%` }} /></div>
                  <small>{(r.ratio * 100).toFixed(0)}%</small></td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <h3>Ashtakavarga</h3>
      <table>
        <thead><tr><th></th>{SIGN_ABBR.map((s) => <th key={s}>{s}</th>)}<th>Total</th></tr></thead>
        <tbody>
          {bavPlanets.map((p) => (
            <tr key={p}><td>{p}</td>{data.ashtakavarga.bav[p].map((v, i) => <td key={i} className="num">{v}</td>)}
              <td className="num">{data.ashtakavarga.bav[p].reduce((a, b) => a + b, 0)}</td></tr>
          ))}
          <tr className="total"><td>SAV</td>{data.ashtakavarga.sav.map((v, i) => <td key={i} className={`num ${v >= 28 ? "good" : "weak"}`}>{v}</td>)}
            <td className="num">{data.ashtakavarga.total}</td></tr>
        </tbody>
      </table>
      <p className="muted">Signs with 28 or more Sarvashtakavarga bindus are considered supportive.</p>
    </div>
  );
}

function Transits({ data }: { data: ChartResponse }) {
  const t = data.transits;
  return (
    <div className="card scroll">
      <p className="muted">As of {new Date(t.as_of).toLocaleString()}</p>
      <table>
        <thead><tr><th>Planet</th><th>Sign</th><th>House from Lagna</th><th>House from Moon</th><th></th></tr></thead>
        <tbody>
          {t.planets.map((p) => (
            <tr key={p.name}><td>{p.name}</td><td>{p.sign}</td><td className="num">{p.house_from_lagna}</td>
              <td className="num">{p.house_from_moon}</td><td>{p.retrograde && p.name !== "Rahu" && p.name !== "Ketu" ? "R" : ""}</td></tr>
          ))}
        </tbody>
      </table>
      <p>Sade Sati: {t.sade_sati.active ? t.sade_sati.phase : "not active"} · Shani Dhaiya: {t.shani_dhaiya.active ? t.shani_dhaiya.type : "not active"}</p>
      <TransitReadings data={data} />
    </div>
  );
}

// Slow planets first: their transits shape months or years, the fast ones only weeks.
const TRANSIT_ORDER = ["saturn", "rahu", "ketu", "jupiter", "mars", "sun", "venus", "mercury"];
const transitRank = (m: RuleMatch) => TRANSIT_ORDER.findIndex((p) => m.id.includes(`.26.${p}.`));

function TransitReadings({ data }: { data: ChartResponse }) {
  const readings = [...data.interpretation.transits].sort((a, b) => transitRank(a) - transitRank(b));
  if (readings.length === 0) return null;
  return (
    <div className="period">
      <h3>Transits now</h3>
      <p className="muted">
        Judged from the natal Moon, as of {new Date(data.transits.as_of).toLocaleDateString()}. Saturn stays in a sign about
        2½ years, Rahu and Ketu about 1½, Jupiter about a year; the Sun, Mercury and Venus about a month, Mars about six weeks.
      </p>
      <ul className="readings">{readings.map((m) => <Reading key={m.id} m={m} />)}</ul>
    </div>
  );
}

const BOOKS: Record<string, { name: string; volumes: boolean }> = {
  "bphs-sharma": { name: "BPHS", volumes: true },
  "phaladeepika-sastri": { name: "Phaladeepika", volumes: false },
};

function Reading({ m }: { m: RuleMatch }) {
  const src = m.source;
  return (
    <li className={`reading ${m.tone}`}>
      <p>{m.tone !== "neutral" && <span className={`tone ${m.tone}`}>{m.tone}</span>}{m.text}</p>
      {m.factors.length > 0 && <p className="why">Because: {m.factors.join("; ")}</p>}
      <p className="cite" title={src.chapter_title}>
        {BOOKS[src.book]?.name ?? src.book} ch. {src.chapter}, v. {src.verse} · {BOOKS[src.book]?.volumes ? `vol. ${src.volume} ` : ""}p. {src.page}
      </p>
    </li>
  );
}

function findPeriod(periods: DashaPeriod[], chain: string[]): DashaPeriod[] {
  const out: DashaPeriod[] = [];
  let level: DashaPeriod[] | undefined = periods;
  const now = Date.now();
  for (const lord of chain) {
    const hit: DashaPeriod | undefined = level?.find((p) => p.lord === lord && new Date(p.start).getTime() <= now && now < new Date(p.end).getTime());
    if (!hit) break;
    out.push(hit);
    level = hit.sub;
  }
  return out;
}

function CurrentPeriod({ data }: { data: ChartResponse }) {
  const [md, ad] = findPeriod(data.dasha.periods, data.dasha.current.slice(0, 2));
  if (!md) return null;
  const forMd = data.interpretation.current_period.filter((m) => !m.period?.ad);
  const forAd = data.interpretation.current_period.filter((m) => m.period?.ad);
  const span = (p: DashaPeriod) => `${fmtDate(p.start)} – ${fmtDate(p.end)}`;
  return (
    <div className="period">
      <h3>Current period</h3>
      <p className="muted">{md.lord} mahadasha ({span(md)}){ad && <> · {ad.lord} antardasha ({span(ad)})</>}</p>
      {forMd.length > 0 && <><h4>{md.lord} mahadasha</h4><ul className="readings">{forMd.map((m) => <Reading key={m.id} m={m} />)}</ul></>}
      {ad && <h4>{md.lord}–{ad.lord} antardasha</h4>}
      {ad && (forAd.length > 0
        ? <ul className="readings">{forAd.map((m) => <Reading key={m.id} m={m} />)}</ul>
        : <p className="muted">No rule from the texts applies to this sub-period for this chart.</p>)}
    </div>
  );
}

type ReportState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "done"; report: WrittenReport };

function Paragraphs({ items }: { items: ReportParagraph[] }) {
  return <>{items.map((p, i) => <p key={i} className="prose">{p.text}</p>)}</>;
}

function WrittenReportView({ data, written, setWritten }: ReportProps) {
  const write = () => {
    setWritten({ status: "loading" });
    fetchReport(data).then((report) => setWritten({ status: "done", report }))
      .catch((e: Error) => setWritten({ status: "error", message: e.message }));
  };
  if (written.status !== "done") {
    return (
      <div className="period">
        <h3>Written report</h3>
        <p className="muted">
          Claude writes a house-by-house report from the readings below. Only the chart factors and readings are sent —
          not your name, birth date or place. It takes about a minute.
        </p>
        {written.status === "error" && <p className="error">{written.message}</p>}
        <button onClick={write} disabled={written.status === "loading"}>
          {written.status === "loading" ? "Writing the report…" : written.status === "error" ? "Try again" : "Write the report"}
        </button>
      </div>
    );
  }
  const r = written.report.report;
  return (
    <div className="written">
      <h3>Your report</h3>
      <Paragraphs items={r.opening} />
      {r.houses.map((h) => (
        <section key={h.house}>
          <h4>{h.title}</h4>
          <p className="house-intro">{h.intro}</p>
          <Paragraphs items={h.paragraphs} />
        </section>
      ))}
      {r.current_period.length > 0 && <section><h4>The Period You Are In</h4><Paragraphs items={r.current_period} /></section>}
      {r.transits.length > 0 && <section><h4>Current Transits</h4><Paragraphs items={r.transits} /></section>}
      <p className="muted small">Written by {written.report.model} from the classical readings matched to this chart.</p>
    </div>
  );
}

interface ReportProps { data: ChartResponse; written: ReportState; setWritten: (s: ReportState) => void }

function Report({ data, written, setWritten }: ReportProps) {
  return (
    <div className="card">
      <WrittenReportView data={data} written={written} setWritten={setWritten} />
      <h3>Readings from the texts</h3>
      <p className="notice">
        Readings below are paraphrased from Brihat Parasara Hora Sastra and Phaladeepika and shown only where this chart meets the
        text's condition. Classical rules can contradict one another; the texts weigh them by planetary strength,
        so treat each as one factor, not a verdict.
      </p>
      <CurrentPeriod data={data} />
      <TransitReadings data={data} />
    </div>
  );
}
