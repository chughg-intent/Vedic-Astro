import { useState } from "react";
import { fetchChart } from "./api";
import BirthForm from "./components/BirthForm";
import Results from "./components/Results";
import { BirthInput, ChartResponse, ChartStyle } from "./types";

export default function App() {
  const [data, setData] = useState<ChartResponse | null>(null);
  const [style, setStyle] = useState<ChartStyle>("north");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate(input: BirthInput) {
    setLoading(true);
    setError(null);
    try {
      setData(await fetchChart(input));
      setStyle(input.chart_style);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <header className="hero">
        <h1>Vedic Destiny</h1>
        <p className="subtitle">Your birth chart, dashas, yogas and a written reading from the classical texts.</p>
      </header>
      <BirthForm loading={loading} onSubmit={generate} />
      {error && <p className="error card">{error}</p>}
      {data && <Results data={data} style={style} onStyle={setStyle} />}
    </main>
  );
}
