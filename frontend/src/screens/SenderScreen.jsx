import { useState } from "react";
import { api } from "../api/client";
import { usePolling } from "../hooks/usePolling";
import { locations, locationName } from "../data/locationNames";
import Spinner from "../components/Spinner";

const STATUS_LABELS = {
  OPEN: "Ищем перевозчика",
  ACCEPTED: "Перевозчик подтверждён",
  IN_TRANSIT: "В пути",
  DELIVERED: "Доставлено",
};

export default function SenderScreen({ user }) {
  const [text, setText] = useState("нужно завтра из Актау в Шетпе отвезти 5 тонн кирпича, машина с тентом");
  const [parsing, setParsing] = useState(false);
  const [draft, setDraft] = useState(null);
  const [parseErrors, setParseErrors] = useState([]);
  const [creating, setCreating] = useState(false);
  const [price, setPrice] = useState(45000);

  const { data: loads } = usePolling(() => api.listLoads(), [user.id]);
  const myLoads = (loads || []).filter((l) => l.sender_id === user.id);

  async function handleParse() {
    setParsing(true);
    setParseErrors([]);
    setDraft(null);
    try {
      const result = await api.parseLoad(text);
      if (result.ok) {
        setDraft(result.draft);
      } else {
        setParseErrors(result.errors);
        // Design review: on validation failure, show a correctable form
        // with whatever fields did come back, not a dead end.
        setDraft({ ...result.raw_fields, weight_tons: result.raw_fields.weight_tons || 1 });
      }
    } catch (e) {
      setParseErrors([e.message]);
    } finally {
      setParsing(false);
    }
  }

  async function confirmDraft() {
    setCreating(true);
    try {
      await api.createLoad({
        origin: draft.origin,
        destination: draft.destination,
        cargo_type: draft.cargo,
        cargo_category: draft.cargo_category,
        weight_tons: Number(draft.weight_tons),
        required_vehicle: draft.vehicle_type,
        pickup_time: new Date().toISOString(),
        price_kzt: Number(price),
      });
      setDraft(null);
      setParseErrors([]);
    } catch (e) {
      setParseErrors([e.message]);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="screen sender-screen">
      <h2>Новая заявка</h2>
      <textarea
        rows={3}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="нужно завтра из Актау в Шетпе 5 тонн кирпича, машина с тентом"
      />
      <button className="primary-button" disabled={parsing} onClick={handleParse}>
        Разобрать
      </button>

      {parsing && <Spinner label="LLM разбирает сообщение..." />}

      {parseErrors.length > 0 && (
        <div className="error-banner">
          {parseErrors.map((e, i) => (
            <div key={i}>{e}</div>
          ))}
        </div>
      )}

      {draft && (
        <div className="draft-form">
          <h3>Проверьте заявку</h3>
          <label>
            Откуда
            <select value={draft.origin || ""} onChange={(e) => setDraft({ ...draft, origin: e.target.value })}>
              <option value="" disabled>
                выберите...
              </option>
              {locations.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Куда
            <select value={draft.destination || ""} onChange={(e) => setDraft({ ...draft, destination: e.target.value })}>
              <option value="" disabled>
                выберите...
              </option>
              {locations.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Груз
            <input value={draft.cargo || ""} onChange={(e) => setDraft({ ...draft, cargo: e.target.value })} />
          </label>
          <label>
            Категория
            <input
              value={draft.cargo_category || ""}
              onChange={(e) => setDraft({ ...draft, cargo_category: e.target.value })}
            />
          </label>
          <label>
            Вес, т
            <input
              type="number"
              value={draft.weight_tons || ""}
              onChange={(e) => setDraft({ ...draft, weight_tons: e.target.value })}
            />
          </label>
          <label>
            Тип машины
            <input
              value={draft.vehicle_type || ""}
              onChange={(e) => setDraft({ ...draft, vehicle_type: e.target.value })}
            />
          </label>
          <label>
            Цена, ₸
            <input type="number" value={price} onChange={(e) => setPrice(e.target.value)} />
          </label>
          <button className="primary-button" disabled={creating} onClick={confirmDraft}>
            Подтвердить заявку
          </button>
        </div>
      )}

      <h2>Мои заявки</h2>
      <ul className="load-list">
        {myLoads.map((l) => (
          <li key={l.id} className={`load-row status-${l.status.toLowerCase()}`}>
            <span className="load-route">
              {locationName(l.origin)} → {locationName(l.destination)}
            </span>
            <span className="load-status-badge">{STATUS_LABELS[l.status] || l.status}</span>
          </li>
        ))}
        {myLoads.length === 0 && <li className="empty-hint">Заявок пока нет</li>}
      </ul>
    </div>
  );
}
