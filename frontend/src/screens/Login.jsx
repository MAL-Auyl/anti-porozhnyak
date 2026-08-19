import { useState } from "react";
import { api } from "../api/client";

const ROLES = [
  { id: "sender", label: "Отправитель", hint: "создаю заявку на груз" },
  { id: "carrier", label: "Перевозчик", hint: "везу машину, ищу обратную загрузку" },
  { id: "dispatcher", label: "Диспетчер", hint: "слежу за статусами" },
];

export default function Login({ onLogin }) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function loginAs(role) {
    if (!name.trim()) {
      setError("Введите имя");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const user = await api.login(name.trim(), role);
      onLogin(user);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-screen">
      <h1>Anti-Порожняк</h1>
      <p className="subtitle">Мы не ищем перевозчика. Мы устраняем пустой обратный рейс.</p>

      <input
        className="name-input"
        placeholder="Ваше имя"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />

      <div className="role-buttons">
        {ROLES.map((r) => (
          <button key={r.id} disabled={busy} onClick={() => loginAs(r.id)} className="role-button">
            <strong>Войти как {r.label}</strong>
            <span>{r.hint}</span>
          </button>
        ))}
      </div>

      {error && <div className="error-banner">{error}</div>}
    </div>
  );
}
