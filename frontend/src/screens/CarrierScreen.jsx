import { useState } from "react";
import { api } from "../api/client";
import { usePolling } from "../hooks/usePolling";
import { locations, locationName } from "../data/locationNames";
import MatchCard from "../components/MatchCard";
import EmptyState from "../components/EmptyState";
import Spinner from "../components/Spinner";
import BeforeAfter from "../components/BeforeAfter";

const VEHICLE_TYPES = ["тент", "борт", "рефрижератор"];

export default function CarrierScreen({ user }) {
  const [vehicle, setVehicle] = useState(null);
  const [form, setForm] = useState({ origin: "aktau", destination: "shetpe", vehicle_type: "тент", capacity_tons: 8 });
  const [acceptedMatch, setAcceptedMatch] = useState(null);
  const [acceptedLoad, setAcceptedLoad] = useState(null);
  const [delivering, setDelivering] = useState(false);

  const { data: matchData, loading: matchesLoading } = usePolling(
    () => (vehicle ? api.vehicleMatches(vehicle.id) : Promise.resolve(null)),
    [vehicle?.id],
    { enabled: !!vehicle },
  );

  async function postVehicle() {
    const created = await api.createVehicle({
      vehicle_type: form.vehicle_type,
      capacity_tons: Number(form.capacity_tons),
      origin: form.origin,
      destination: form.destination,
      departure_time: new Date().toISOString(),
    });
    setVehicle(created);
    setAcceptedMatch(null);
    setAcceptedLoad(null);
  }

  async function handleAccepted(updatedMatch) {
    const original = matchData?.matches?.find((m) => m.id === updatedMatch.id);
    setAcceptedMatch({ ...updatedMatch, load: original?.load });
    setAcceptedLoad(original?.load);
  }

  async function markDelivered() {
    if (!acceptedMatch) return;
    setDelivering(true);
    try {
      await api.markDelivered(acceptedMatch.load_id);
      // One click, instant transition (Design review) — immediately post the
      // return leg so "система ищет обратный груз" has something to match.
      const returnVehicle = await api.createVehicle({
        vehicle_type: form.vehicle_type,
        capacity_tons: Number(form.capacity_tons),
        origin: form.destination, // now at the delivery point
        destination: form.origin, // heading home
        departure_time: new Date().toISOString(),
      });
      setVehicle(returnVehicle);
      setAcceptedMatch(null);
      setAcceptedLoad(null);
    } finally {
      setDelivering(false);
    }
  }

  if (!vehicle) {
    return (
      <div className="screen carrier-screen">
        <h2>Моя машина</h2>
        <label>
          Откуда
          <select value={form.origin} onChange={(e) => setForm({ ...form, origin: e.target.value })}>
            {locations.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Куда
          <select value={form.destination} onChange={(e) => setForm({ ...form, destination: e.target.value })}>
            {locations.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Тип кузова
          <select value={form.vehicle_type} onChange={(e) => setForm({ ...form, vehicle_type: e.target.value })}>
            {VEHICLE_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        <label>
          Грузоподъёмность, т
          <input
            type="number"
            value={form.capacity_tons}
            onChange={(e) => setForm({ ...form, capacity_tons: e.target.value })}
          />
        </label>
        <button className="primary-button" onClick={postVehicle}>
          Выехать
        </button>
      </div>
    );
  }

  if (acceptedMatch) {
    return (
      <div className="screen carrier-screen">
        <h2>
          Маршрут: {locationName(vehicle.origin)} → {locationName(vehicle.destination)}
        </h2>
        <div className="status-badge">✅ Груз подтверждён</div>
        <button className="primary-button" disabled={delivering} onClick={markDelivered}>
          {delivering ? "..." : "Доставлено"}
        </button>
        {acceptedLoad && <BeforeAfter match={acceptedMatch} vehicle={vehicle} load={acceptedLoad} />}
      </div>
    );
  }

  return (
    <div className="screen carrier-screen">
      <h2>
        Маршрут: {locationName(vehicle.origin)} → {locationName(vehicle.destination)}
      </h2>
      <button className="link-button" onClick={() => setVehicle(null)}>
        сменить маршрут
      </button>

      {matchesLoading && !matchData && <Spinner label="Ищем подходящие грузы..." />}

      {matchData?.empty_state && (
        <EmptyState
          message={matchData.empty_state.message}
          tripsInDatabase={matchData.empty_state.trips_in_database}
        />
      )}

      {matchData?.matches?.length > 0 && (
        <div className="match-list">
          {matchData.matches.map((m) => (
            <MatchCard key={m.id} match={m} load={m.load} onAccepted={handleAccepted} />
          ))}
        </div>
      )}
    </div>
  );
}
