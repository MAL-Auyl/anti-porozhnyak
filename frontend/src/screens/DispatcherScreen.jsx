import { api } from "../api/client";
import { usePolling } from "../hooks/usePolling";
import EmptyState from "../components/EmptyState";

const STATUS_LABELS = {
  PROPOSED: "Предложено",
  ACCEPTED: "Взято перевозчиком",
  REJECTED: "Отклонено",
};

/**
 * Design review finding closing requirement 05 ("диспетчер отслеживает"):
 * a third, read-only window — same 2s polling as sender/carrier, no
 * interactivity. Third window in the demo script, not two.
 */
export default function DispatcherScreen() {
  const { data: matches, loading } = usePolling(() => api.allMatches(), []);

  return (
    <div className="screen dispatcher-screen">
      <h2>Диспетчер — все совпадения</h2>
      {loading && !matches && <p>Загрузка...</p>}
      {matches && matches.length === 0 && (
        <EmptyState message="Совпадений пока нет — активность появится, как только перевозчики и отправители начнут работать." />
      )}
      <table className="dispatcher-table">
        <thead>
          <tr>
            <th>Score</th>
            <th>Детур, км</th>
            <th>Экономия, км</th>
            <th>Статус</th>
          </tr>
        </thead>
        <tbody>
          {(matches || []).map((m) => (
            <tr key={m.id} className={`status-${m.status.toLowerCase()}`}>
              <td>{Math.round(m.score)}%</td>
              <td>{m.detour_km}</td>
              <td>{m.empty_km_saved}</td>
              <td>{STATUS_LABELS[m.status] || m.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
