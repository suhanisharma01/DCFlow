import { useState, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000";

const DEFAULT_ASSUMPTIONS = {
  ticker: "AMZN",
  base_revenue: 469822,
  revenue_growth_rates: [0.10, 0.09, 0.08, 0.07, 0.06],
  ebit_margins: [0.08, 0.09, 0.10, 0.11, 0.12],
  tax_rates: [0.15, 0.15, 0.15, 0.15, 0.15],
  da_pct_sales: [0.07, 0.07, 0.07, 0.07, 0.07],
  capex_pct_sales: [0.10, 0.09, 0.09, 0.08, 0.08],
  nwc_change_pct_sales: [-0.005, -0.005, -0.005, -0.005, -0.005],
  wacc: 0.09,
  terminal_growth_rate: 0.03,
  cash: 66385,
  debt: 47556,
  shares_outstanding: 10456,
  current_share_price: 122.42,
  year_labels: ["2022", "2023", "2024", "2025", "2026"],
};

function Slider({ label, value, min, max, step, onChange, format }) {
  return (
    <div className="mb-3">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-300">{label}</span>
        <span className="text-white font-mono">{format(value)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-emerald-500"
      />
    </div>
  );
}

function YearSliderGroup({ label, values, onChange, min, max, step }) {
  const updateYear = (i, v) => {
    const next = [...values];
    next[i] = v;
    onChange(next);
  };
  return (
    <div className="mb-4">
      <div className="text-sm text-gray-400 mb-2">{label}</div>
      {values.map((v, i) => (
        <Slider
          key={i}
          label={`Year ${i + 1}`}
          value={v}
          min={min}
          max={max}
          step={step}
          onChange={(val) => updateYear(i, val)}
          format={(x) => `${(x * 100).toFixed(1)}%`}
        />
      ))}
    </div>
  );
}

export default function DCFDashboard() {
  const [assumptions, setAssumptions] = useState(DEFAULT_ASSUMPTIONS);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [recommendation, setRecommendation] = useState(null);
  const [recLoading, setRecLoading] = useState(false);

  const recalculate = useCallback(async (a) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/dcf/calculate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(a),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Calculation failed");
      }
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => recalculate(assumptions), 150); // debounce
    return () => clearTimeout(timer);
  }, [assumptions, recalculate]);

  const update = (field, value) => setAssumptions((prev) => ({ ...prev, [field]: value }));

  const getRecommendation = async () => {
    setRecLoading(true);
    try {
      const res = await fetch(`${API_BASE}/dcf/recommendation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(assumptions),
      });
      const data = await res.json();
      setRecommendation(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setRecLoading(false);
    }
  };

const exportExcel = async () => {
  const res = await fetch(`${API_BASE}/dcf/export-excel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(assumptions),
  });
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${assumptions.ticker}_dcf.xlsx`;
  a.click();
};

  const upside = result?.upside_downside;

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <h1 className="text-2xl font-bold mb-1">{assumptions.ticker} DCF Dashboard</h1>
      <p className="text-gray-400 text-sm mb-6">Adjust assumptions to see fair value update in real time</p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sliders panel */}
        <div className="bg-gray-900 rounded-xl p-5">
          <h2 className="font-semibold mb-4">Assumptions</h2>

          <YearSliderGroup
            label="Revenue Growth"
            values={assumptions.revenue_growth_rates}
            onChange={(v) => update("revenue_growth_rates", v)}
            min={-0.1} max={0.5} step={0.005}
          />
          <YearSliderGroup
            label="EBIT Margin"
            values={assumptions.ebit_margins}
            onChange={(v) => update("ebit_margins", v)}
            min={0} max={0.4} step={0.005}
          />

          <Slider
            label="WACC"
            value={assumptions.wacc}
            min={0.04} max={0.16} step={0.001}
            onChange={(v) => update("wacc", v)}
            format={(x) => `${(x * 100).toFixed(1)}%`}
          />
          <Slider
            label="Terminal Growth Rate"
            value={assumptions.terminal_growth_rate}
            min={0.005} max={Math.max(0.005, assumptions.wacc - 0.005)} step={0.001}
            onChange={(v) => update("terminal_growth_rate", v)}
            format={(x) => `${(x * 100).toFixed(1)}%`}
          />
        </div>

        {/* Results panel */}
        <div className="bg-gray-900 rounded-xl p-5 lg:col-span-2">
          <h2 className="font-semibold mb-4">Valuation Output {loading && <span className="text-xs text-gray-500">(updating...)</span>}</h2>

          {error && <div className="text-red-400 text-sm mb-3">{error}</div>}

          {result && (
            <>
              <div className="grid grid-cols-3 gap-4 mb-6">
                <Stat label="Fair Value / Share" value={`$${result.fair_value_per_share.toFixed(2)}`} />
                <Stat label="Current Price" value={`$${assumptions.current_share_price.toFixed(2)}`} />
                <Stat
                  label="Upside / (Downside)"
                  value={`${(upside * 100).toFixed(1)}%`}
                  positive={upside > 0}
                />
              </div>

              <table className="w-full text-sm mb-6">
                <thead>
                  <tr className="text-gray-400 border-b border-gray-800">
                    <th className="text-left py-1">Year</th>
                    <th className="text-right">Revenue</th>
                    <th className="text-right">EBIT</th>
                    <th className="text-right">Unlevered FCF</th>
                    <th className="text-right">PV of FCF</th>
                  </tr>
                </thead>
                <tbody>
                  {result.lines.map((l) => (
                    <tr key={l.year_label} className="border-b border-gray-900">
                      <td className="py-1">{l.year_label}</td>
                      <td className="text-right font-mono">{Math.round(l.revenue).toLocaleString()}</td>
                      <td className="text-right font-mono">{Math.round(l.ebit).toLocaleString()}</td>
                      <td className="text-right font-mono">{Math.round(l.unlevered_fcf).toLocaleString()}</td>
                      <td className="text-right font-mono">{Math.round(l.pv_fcf).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="flex gap-3">
                <button
                  onClick={getRecommendation}
                  disabled={recLoading}
                  className="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded-lg text-sm font-medium"
                >
                  {recLoading ? "Thinking..." : "Get AI Read"}
                </button>
                <button
                  onClick={exportExcel}
                  className="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded-lg text-sm font-medium"
                >
                  Export to Excel
                </button>
              </div>

              {recommendation && (
                <div className="mt-4 bg-gray-800 rounded-lg p-4">
                  <div className="font-semibold mb-1">
                    {recommendation.stance} ({(recommendation.upside_pct * 100).toFixed(1)}%)
                  </div>
                  <p className="text-sm text-gray-300">{recommendation.explanation}</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, positive }) {
  return (
    <div className="bg-gray-800 rounded-lg p-3">
      <div className="text-xs text-gray-400 mb-1">{label}</div>
      <div className={`text-xl font-bold ${positive === true ? "text-emerald-400" : positive === false ? "text-red-400" : "text-white"}`}>
        {value}
      </div>
    </div>
  );
}