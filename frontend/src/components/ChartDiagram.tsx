import { ABBR, ChartStyle, SIGN_ABBR } from "../types";

interface Props {
  style: ChartStyle;
  title: string;
  lagnaSign: number;
  /** planet name -> sign index (0 = Aries) */
  placements: Record<string, number>;
  retrograde?: Set<string>;
}

const SIZE = 360;

/** Planets grouped by sign, excluding the ascendant entry. */
function bySign(placements: Record<string, number>, retro?: Set<string>): string[][] {
  const out: string[][] = Array.from({ length: 12 }, () => []);
  for (const [p, s] of Object.entries(placements)) {
    if (p === "Ascendant") continue;
    const label = (ABBR[p] ?? p.slice(0, 2)) + (retro?.has(p) && p !== "Rahu" && p !== "Ketu" ? "ᴿ" : "");
    out[s].push(label);
  }
  return out;
}

function PlanetLabels({ x, y, items, perLine = 3 }: { x: number; y: number; items: string[]; perLine?: number }) {
  const lineH = 15;
  const lines: string[] = [];
  for (let i = 0; i < items.length; i += perLine) lines.push(items.slice(i, i + perLine).join(" "));
  const y0 = y - ((lines.length - 1) * lineH) / 2;
  return (
    <>
      {lines.map((l, i) => (
        <text key={i} x={x} y={y0 + i * lineH} className="chart-planet" textAnchor="middle" dominantBaseline="middle">
          {l}
        </text>
      ))}
    </>
  );
}

// ---------------------------------------------------------------- North Indian (houses fixed)
const S = SIZE;
const H = S / 2;
const Q = S / 4;
const NORTH_HOUSES: Array<{ poly: [number, number][]; c: [number, number]; n: [number, number] }> = [
  { poly: [[H, 0], [3 * Q, Q], [H, H], [Q, Q]], c: [H, Q * 0.95], n: [H, H - 18] },
  { poly: [[0, 0], [H, 0], [Q, Q]], c: [Q, Q * 0.42], n: [Q, Q - 14] },
  { poly: [[0, 0], [Q, Q], [0, H]], c: [Q * 0.4, Q], n: [Q - 14, Q] },
  { poly: [[0, H], [Q, Q], [H, H], [Q, 3 * Q]], c: [Q * 0.95, H], n: [H - 18, H] },
  { poly: [[0, H], [Q, 3 * Q], [0, S]], c: [Q * 0.4, 3 * Q], n: [Q - 14, 3 * Q] },
  { poly: [[0, S], [Q, 3 * Q], [H, S]], c: [Q, S - Q * 0.42], n: [Q, 3 * Q + 14] },
  { poly: [[H, S], [Q, 3 * Q], [H, H], [3 * Q, 3 * Q]], c: [H, 3 * Q * 1.02], n: [H, H + 18] },
  { poly: [[H, S], [3 * Q, 3 * Q], [S, S]], c: [3 * Q, S - Q * 0.42], n: [3 * Q, 3 * Q + 14] },
  { poly: [[S, S], [3 * Q, 3 * Q], [S, H]], c: [S - Q * 0.4, 3 * Q], n: [3 * Q + 14, 3 * Q] },
  { poly: [[S, H], [3 * Q, 3 * Q], [H, H], [3 * Q, Q]], c: [3 * Q * 1.02, H], n: [H + 18, H] },
  { poly: [[S, H], [3 * Q, Q], [S, 0]], c: [S - Q * 0.4, Q], n: [3 * Q + 14, Q] },
  { poly: [[S, 0], [3 * Q, Q], [H, 0]], c: [3 * Q, Q * 0.42], n: [3 * Q, Q - 14] },
];

function NorthChart({ lagnaSign, groups }: { lagnaSign: number; groups: string[][] }) {
  return (
    <>
      {NORTH_HOUSES.map((h, i) => {
        const sign = (lagnaSign + i) % 12;
        return (
          <g key={i}>
            <polygon points={h.poly.map((p) => p.join(",")).join(" ")}
              className={i === 0 ? "chart-cell chart-lagna" : "chart-cell"} />
            <text x={h.n[0]} y={h.n[1]} className="chart-signnum" textAnchor="middle" dominantBaseline="middle">
              {sign + 1}
            </text>
            <PlanetLabels x={h.c[0]} y={h.c[1]} items={groups[sign]} perLine={h.poly.length === 3 ? 2 : 3} />
          </g>
        );
      })}
    </>
  );
}

// ---------------------------------------------------------------- South Indian (signs fixed)
const SOUTH_CELLS: Array<[number, number]> = [
  [1, 0], [2, 0], [3, 0], [3, 1], [3, 2], [3, 3], [2, 3], [1, 3], [0, 3], [0, 2], [0, 1], [0, 0],
]; // index = sign (Aries..Pisces) -> [col,row]

function SouthChart({ lagnaSign, groups, title }: { lagnaSign: number; groups: string[][]; title: string }) {
  const c = S / 4;
  return (
    <>
      {SOUTH_CELLS.map(([col, row], sign) => {
        const x = col * c;
        const y = row * c;
        const isLagna = sign === lagnaSign;
        return (
          <g key={sign}>
            <rect x={x} y={y} width={c} height={c} className={isLagna ? "chart-cell chart-lagna" : "chart-cell"} />
            {isLagna && <line x1={x} y1={y + 18} x2={x + 18} y2={y} className="chart-lagna-mark" />}
            <text x={x + c - 5} y={y + 12} className="chart-signnum" textAnchor="end">{SIGN_ABBR[sign]}</text>
            <PlanetLabels x={x + c / 2} y={y + c / 2 + 4}
              items={isLagna ? ["As", ...groups[sign]] : groups[sign]} />
          </g>
        );
      })}
      <rect x={c} y={c} width={2 * c} height={2 * c} className="chart-center" />
      <text x={H} y={H} className="chart-title" textAnchor="middle" dominantBaseline="middle">{title}</text>
    </>
  );
}

export default function ChartDiagram({ style, title, lagnaSign, placements, retrograde }: Props) {
  const groups = bySign(placements, retrograde);
  return (
    <figure className="chart">
      <svg viewBox={`-2 -2 ${SIZE + 4} ${SIZE + 4}`} role="img" aria-label={`${title} (${style} Indian style)`}>
        {style === "north"
          ? <><rect x={0} y={0} width={S} height={S} className="chart-frame" /><NorthChart lagnaSign={lagnaSign} groups={groups} /></>
          : <SouthChart lagnaSign={lagnaSign} groups={groups} title={title} />}
      </svg>
      <figcaption>{title}</figcaption>
    </figure>
  );
}
