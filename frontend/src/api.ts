import { AskAnswer, BirthInput, ChartResponse, Place, Topic, WrittenReport } from "./types";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch { /* keep statusText */ }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function searchPlaces(city: string, state?: string, country?: string): Promise<Place[]> {
  const q = new URLSearchParams({ city });
  if (state) q.set("state", state);
  if (country) q.set("country", country);
  return handle<Place[]>(await fetch(`/api/places?${q}`));
}

export async function fetchChart(input: BirthInput): Promise<ChartResponse> {
  return handle<ChartResponse>(await fetch("/api/chart", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...input, time: input.time.length === 5 ? `${input.time}:00` : input.time }),
  }));
}

/** Asks a question about one house of the chart; answered from the matched readings only. */
export async function askQuestion(chart: ChartResponse, house: number, question: string,
                                  accessCode?: string): Promise<AskAnswer> {
  const birth = { ...chart.input, latitude: chart.place.latitude, longitude: chart.place.longitude,
                  timezone: chart.place.timezone };
  return handle<AskAnswer>(await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(accessCode ? { "X-Access-Code": accessCode } : {}) },
    body: JSON.stringify({ birth, house, question }),
  }));
}

/** Asks the backend to write the report with Claude. Uses the place already resolved for the chart. */
export async function fetchReport(chart: ChartResponse, accessCode?: string): Promise<WrittenReport> {
  const input = { ...chart.input, latitude: chart.place.latitude, longitude: chart.place.longitude,
                  timezone: chart.place.timezone };
  return handle<WrittenReport>(await fetch("/api/report", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(accessCode ? { "X-Access-Code": accessCode } : {}) },
    body: JSON.stringify(input),
  }));
}

/** Whether writing a report needs the shared access code (set on the server when the site is shared). */
export async function fetchConfig(): Promise<{ report_requires_code: boolean; topics: Topic[] }> {
  return handle(await fetch("/api/config"));
}
