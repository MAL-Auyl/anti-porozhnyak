import { useState } from "react";
import { locationName } from "../data/locationNames";
import { api } from "../api/client";

/**
 * Visual hierarchy per Design review: match score is the largest element,
 * cargo details are secondary, the "Почему этот груз?" breakdown expands
 * on demand rather than always taking screen space.
 */
export default function MatchCard({ match, load, onAccepted }) {
  const [explain, setExplain] = useState(null);
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function toggleExplain() {
    if (!expanded && !explain) {
      try {
        const data = await api.explainMatch(match.id);
        setExplain(data);
      } catch (e) {
        setError(e.message);
      }
    }
    setExpanded((v) => !v);
  }

  async function accept() {
    setBusy(true);
    setError(null);
    try {
      const updated = await api.acceptMatch(match.id);
      onAccepted?.(updated);
    } catch (e) {
      setError(e.status === 409 ? "Уже взято другим перевозчиком" : e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`match-card status-${match.status.toLowerCase()}`}>
      <div className="match-score">{Math.round(match.score)}%</div>
      <div className="match-body">
        <div className="match-route">
          {locationName(load?.origin)} → {locationName(load?.destination)}
        </div>
        <div className="match-details">
          {load?.cargo_type} · {load?.weight_tons} т · {load?.cargo_category}
        </div>
        <div className="match-econ">
          Экономия: {match.empty_km_saved} км · {match.fuel_saved_kzt.toLocaleString("ru")} ₸
          <span className="demo-assumption"> *demo assumption</span>
        </div>

        <button className="link-button" onClick={toggleExplain}>
          {expanded ? "Скрыть разбор" : "Почему этот груз?"}
        </button>

        {expanded && explain && (
          <ul className="explain-breakdown">
            <li>{explain.coverage_pct}% маршрута совпадает</li>
            <li>{explain.detour_km} км отклонение</li>
            <li>{explain.compatibility_ok ? "✅ подходит кузов" : "❌ кузов не подходит"}</li>
            <li>{explain.time_window_ok ? "✅ временное окно совпадает" : "⚠ окно не совпадает"}</li>
          </ul>
        )}

        {match.status === "PROPOSED" && (
          <button className="accept-button" disabled={busy} onClick={accept}>
            {busy ? "..." : "Взять груз"}
          </button>
        )}
        {match.status === "ACCEPTED" && <div className="status-badge">✅ Подтверждено</div>}

        {error && <div className="error-inline">{error}</div>}
      </div>
    </div>
  );
}
