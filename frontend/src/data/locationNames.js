import locations from "./locations.json";

const byId = Object.fromEntries(locations.map((l) => [l.id, l]));

export function locationName(id) {
  return byId[id]?.name || id;
}

export function locationCoords(id) {
  const loc = byId[id];
  return loc ? [loc.lat, loc.lon] : null;
}

export { locations };
