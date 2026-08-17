"use client";

import { useState, useEffect, useCallback } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

const API_BASE = "https://dcflow.onrender.com";

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
        <span className="text-gray-600">{label}</span>
        <span className="text-gray-900 font-mono">{format(value)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-emerald-600"
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
      <div className="text-sm text-gray-500 mb-2">{label}</div>
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

function ProjectionChart({ lines }) {
  const data = lines.map((l) => ({
    year: l.year_label,
    Revenue: Math.round(l.revenue),
    "Unlevered FCF": Math.round(l.unlevered_fcf),
  }));

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
      <h3 className="font-semibold mb-4 text-sm text-gray-900">Revenue & FCF Projection</h3>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="year" stroke="#6b7280" fontSize={12} />
          <YAxis
            stroke="#6b7280"
            fontSize={12}
            tickFormatter={(v) => `${(v / 1000).toFixed(0)}K`}
          />
          <Tooltip
            contentStyle={{
              background: "#ffffff",
              border: "1px solid #e5e7eb",
              borderRadius: "8px",
              color: "#111827",
            }}
            formatter={(value) => value.toLocaleString()}
          />
          <Legend />
          <Line type="monotone" dataKey="Revenue" stroke="#059669" strokeWidth={2} dot={{ r: 3 }} />
          <Line type="monotone" dataKey="Unlevered FCF" stroke="#2563eb" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function ScenarioComparison({ scenarios, currentPrice }) {
  const colors = { Bear: "text-red-600", Base: "text-gray-700", Bull: "text-emerald-600" };
  const bgColors = {
    Bear: "bg-red-50 border-red-200",
    Base: "bg-gray-100 border-gray-200",
    Bull: "bg-emerald-50 border-emerald-200",
  };
  const deltas = {
    Bear: "Growth −3pts, Margin −2pts, WACC +1.5pts",
    Base: "Your current assumptions",
    Bull: "Growth +3pts, Margin +2pts, WACC −1pt",
  };

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
      <h3 className="font-semibold mb-4 text-sm text-gray-900">Bull / Base / Bear Scenarios</h3>
      <div className="grid grid-cols-3 gap-3">
        {scenarios.map(({ label, result }) => {
          const upside = currentPrice ? (result.fair_value_per_share / currentPrice - 1) * 100 : null;
          return (
            <div key={label} className={`rounded-lg p-4 border ${bgColors[label]}`}>
              <div className={`text-xs font-semibold mb-1 ${colors[label]}`}>{label}</div>
              <div className="text-lg font-bold text-gray-900">${result.fair_value_per_share.toFixed(2)}</div>
              {upside !== null && (
                <div className={`text-xs mt-1 ${upside >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                  {upside >= 0 ? "+" : ""}
                  {upside.toFixed(1)}%
                </div>
              )}
              <div className="text-[11px] text-gray-500 mt-2 leading-snug">{deltas[label]}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Stat({ label, value, positive }) {
  return (
    <div className="bg-gray-100 border border-gray-200 rounded-lg p-3">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div
        className={`text-xl font-bold ${
          positive === true ? "text-emerald-600" : positive === false ? "text-red-600" : "text-gray-900"
        }`}
      >
        {value}
      </div>
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
  const [tickerOptions, setTickerOptions] = useState([]);
  const [selectedTicker, setSelectedTicker] = useState("AMZN");
  const [tickerLoading, setTickerLoading] = useState(false);
  const [rationale, setRationale] = useState(null);
  const [scenarios, setScenarios] = useState(null);
  const [scenariosLoading, setScenariosLoading] = useState(false);

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

  const buildScenario = (base, growthDelta, marginDelta, waccDelta) => ({
    ...base,
    revenue_growth_rates: base.revenue_growth_rates.map((g) => Math.max(-0.5, g + growthDelta)),
    ebit_margins: base.ebit_margins.map((m) => Math.max(0.01, m + marginDelta)),
    wacc: Math.max(0.02, base.wacc + waccDelta),
  });

  const runScenarios = useCallback(async (a) => {
    setScenariosLoading(true);
    try {
      const scenarioDefs = [
        { label: "Bear", assumptions: buildScenario(a, -0.03, -0.02, 0.015) },
        { label: "Base", assumptions: a },
        { label: "Bull", assumptions: buildScenario(a, 0.03, 0.02, -0.01) },
      ];

      const results = await Promise.all(
        scenarioDefs.map(async (s) => {
          const res = await fetch(`${API_BASE}/dcf/calculate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(s.assumptions),
          });
          if (!res.ok) throw new Error(`Failed to calculate ${s.label} case`);
          const data = await res.json();
          return { label: s.label, result: data };
        })
      );

      setScenarios(results);
    } catch (e) {
      setError(e.message);
    } finally {
      setScenariosLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      recalculate(assumptions);
      runScenarios(assumptions);
    }, 150); // debounce
    return () => clearTimeout(timer);
  }, [assumptions, recalculate, runScenarios]);

  useEffect(() => {
    fetch(`${API_BASE}/dcf/supported-tickers`)
      .then((res) => res.json())
      .then((data) => setTickerOptions(data.tickers))
      .catch(() => setTickerOptions(["AMZN"])); // fallback if backend not reachable yet
  }, []);

  const update = (field, value) => setAssumptions((prev) => ({ ...prev, [field]: value }));

  const loadTicker = async () => {
    setTickerLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/dcf/load-ticker?ticker=${selectedTicker}`);
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to load ticker");
      }
      const data = await res.json();
      setAssumptions(data.assumptions);
      setRationale(data.rationale);
      setRecommendation(null); // clear stale AI read from the previous ticker
    } catch (e) {
      setError(e.message);
    } finally {
      setTickerLoading(false);
    }
  };

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
    <div className="min-h-screen bg-white text-gray-900 p-6">
      <div className="flex items-center justify-between mb-1">
        <h1 className="text-2xl font-bold text-gray-900">{assumptions.ticker} DCF Dashboard</h1>
      </div>
      <p className="text-gray-500 text-sm mb-4">Adjust assumptions to see fair value update in real time</p>

      <div className="flex items-center gap-3 mb-6">
        <select
          value={selectedTicker}
          onChange={(e) => setSelectedTicker(e.target.value)}
          className="bg-white border border-gray-300 text-gray-900 px-3 py-2 rounded-lg text-sm"
        >
          {tickerOptions.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <button
          onClick={loadTicker}
          disabled={tickerLoading}
          className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          {tickerLoading ? "Loading..." : "Load Ticker"}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Sliders — narrower column */}
        <div className="lg:col-span-2 bg-gray-50 border border-gray-200 rounded-xl p-5 max-h-[calc(100vh-220px)] overflow-y-auto">
          <h2 className="font-semibold mb-4 text-gray-900">Assumptions</h2>

          <YearSliderGroup
            label="Revenue Growth"
            values={assumptions.revenue_growth_rates}
            onChange={(v) => update("revenue_growth_rates", v)}
            min={-0.1}
            max={0.5}
            step={0.005}
          />
          <YearSliderGroup
            label="EBIT Margin"
            values={assumptions.ebit_margins}
            onChange={(v) => update("ebit_margins", v)}
            min={0}
            max={0.4}
            step={0.005}
          />

          <Slider
            label="WACC"
            value={assumptions.wacc}
            min={0.04}
            max={0.16}
            step={0.001}
            onChange={(v) => update("wacc", v)}
            format={(x) => `${(x * 100).toFixed(1)}%`}
          />
          <Slider
            label="Terminal Growth Rate"
            value={assumptions.terminal_growth_rate}
            min={0.005}
            max={Math.max(0.005, assumptions.wacc - 0.005)}
            step={0.001}
            onChange={(v) => update("terminal_growth_rate", v)}
            format={(x) => `${(x * 100).toFixed(1)}%`}
          />
        </div>

        {/* Results — wider column */}
        <div className="lg:col-span-3 space-y-6">
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-5">
            <h2 className="font-semibold mb-4 text-gray-900">
              Valuation Output {loading && <span className="text-xs text-gray-400">(updating...)</span>}
            </h2>

            {error && <div className="text-red-600 text-sm mb-3">{error}</div>}

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

                <table className="w-full text-sm mb-2">
                  <thead>
                    <tr className="text-gray-500 border-b border-gray-200">
                      <th className="text-left py-1">Year</th>
                      <th className="text-right">Revenue</th>
                      <th className="text-right">EBIT</th>
                      <th className="text-right">Unlevered FCF</th>
                      <th className="text-right">PV of FCF</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.lines.map((l) => (
                      <tr key={l.year_label} className="border-b border-gray-100 text-gray-800">
                        <td className="py-1">{l.year_label}</td>
                        <td className="text-right font-mono">{Math.round(l.revenue).toLocaleString()}</td>
                        <td className="text-right font-mono">{Math.round(l.ebit).toLocaleString()}</td>
                        <td className="text-right font-mono">{Math.round(l.unlevered_fcf).toLocaleString()}</td>
                        <td className="text-right font-mono">{Math.round(l.pv_fcf).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <div className="flex gap-3 mt-4">
                  <button
                    onClick={getRecommendation}
                    disabled={recLoading}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg text-sm font-medium"
                  >
                    {recLoading ? "Thinking..." : "Get AI Read"}
                  </button>
                  <button
                    onClick={exportExcel}
                    className="bg-gray-200 hover:bg-gray-300 text-gray-900 px-4 py-2 rounded-lg text-sm font-medium"
                  >
                    Export to Excel
                  </button>
                </div>

                {recommendation && (
                  <div className="mt-4 bg-gray-100 border border-gray-200 rounded-lg p-4">
                    <div className="font-semibold mb-1 text-gray-900">
                      {recommendation.stance} ({(recommendation.upside_pct * 100).toFixed(1)}%)
                    </div>
                    <p className="text-sm text-gray-600">{recommendation.explanation}</p>
                  </div>
                )}
              </>
            )}
          </div>

          {result && <ProjectionChart lines={result.lines} />}

          {scenarios && <ScenarioComparison scenarios={scenarios} currentPrice={assumptions.current_share_price} />}

          {/* Rationale — compact and collapsible */}
          {rationale && (
            <details className="bg-gray-50 border border-gray-200 rounded-xl p-5">
              <summary className="font-semibold cursor-pointer text-sm text-gray-900">
                Why these starting assumptions?
              </summary>
              <div className="mt-3 text-xs text-gray-500 space-y-2">
                <p>
                  <span className="text-gray-700 font-medium">Growth:</span> {rationale.revenue_growth}
                </p>
                <p>
                  <span className="text-gray-700 font-medium">Margins:</span> {rationale.ebit_margin}
                </p>
                <p>
                  <span className="text-gray-700 font-medium">WACC:</span> {rationale.wacc}
                </p>
              </div>
            </details>
          )}
        </div>
      </div>

      <footer className="mt-10 pt-6 border-t border-gray-200 text-xs text-gray-400 text-center">
        ⚠️ This tool is for educational purposes only. Valuations are generated by AI-assisted models and should not
        be used as financial advice or a basis for investment decisions. Always consult a licensed financial advisor.
      </footer>
    </div>
  );
}