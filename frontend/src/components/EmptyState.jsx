/**
 * Design review finding: empty matching result is a realistic outcome
 * (region's cargo asymmetry is the core premise), not an edge case — must
 * explain itself, not just show a blank list that looks like a bug.
 */
export default function EmptyState({ message, tripsInDatabase }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">🚚</div>
      <p>{message}</p>
      {typeof tripsInDatabase === "number" && (
        <p className="empty-state-detail">Всего в базе региона: {tripsInDatabase} рейсов</p>
      )}
    </div>
  );
}
