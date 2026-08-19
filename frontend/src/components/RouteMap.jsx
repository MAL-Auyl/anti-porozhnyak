import { MapContainer, TileLayer, Marker, Popup, Polyline } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { locations, locationCoords } from "../data/locationNames";
import { api } from "../api/client";
import { usePolling } from "../hooks/usePolling";

// Default Leaflet marker icons reference bundled image paths that break
// under Vite's asset pipeline — reset to CDN URLs, a well-known workaround.
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const STATUS_COLOR = {
  OPEN: "#9aa0a6",
  ACCEPTED: "#1a73e8",
  IN_TRANSIT: "#1a73e8",
  DELIVERED: "#188038",
};

const CENTER = [43.9, 51.8]; // Mangystau region

/**
 * Map is last, per plan.md: "Карта — только визуализация результата, не
 * источник вычислений." Straight lines between node coordinates, no real
 * road routing (explicitly cut from scope).
 */
export default function RouteMap() {
  const { data: loads } = usePolling(() => api.listLoads(), []);

  return (
    <div className="route-map">
      <MapContainer center={CENTER} zoom={7.5} style={{ height: "320px", width: "100%" }}>
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {locations.map((loc) => (
          <Marker key={loc.id} position={[loc.lat, loc.lon]}>
            <Popup>{loc.name}</Popup>
          </Marker>
        ))}
        {(loads || []).map((load) => {
          const from = locationCoords(load.origin);
          const to = locationCoords(load.destination);
          if (!from || !to) return null;
          return (
            <Polyline
              key={load.id}
              positions={[from, to]}
              pathOptions={{ color: STATUS_COLOR[load.status] || "#9aa0a6", weight: load.status === "OPEN" ? 1 : 3 }}
            />
          );
        })}
      </MapContainer>
    </div>
  );
}
