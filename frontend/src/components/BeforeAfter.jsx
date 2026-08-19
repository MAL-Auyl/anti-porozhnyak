import { locationName } from "../data/locationNames";

const FUEL_CONSUMPTION_L_PER_100KM = 30;
const DIESEL_PRICE_KZT = 300;

/**
 * "Главный экран защиты" (plan.md). The Calculation block is mandatory —
 * every number is labeled a demo assumption where applicable, per the
 * team's rule: nothing on screen without a source or explicit assumption.
 */
export default function BeforeAfter({ match, vehicle, load, returnLoad }) {
  if (!match) return null;

  return (
    <div className="before-after">
      <h2>Empty KM Saved</h2>

      <div className="ba-columns">
        <div className="ba-col">
          <h3>ДО</h3>
          <div className="ba-route">
            {locationName(vehicle.origin)} → {locationName(vehicle.destination)}
          </div>
          <div className="ba-arrow">↓</div>
          <div className="ba-empty-tag">ПУСТО</div>
        </div>
        <div className="ba-col">
          <h3>ПОСЛЕ</h3>
          <div className="ba-route">
            {locationName(vehicle.origin)} → {locationName(vehicle.destination)}
          </div>
          <div className="ba-arrow">↓</div>
          <div className="ba-cargo-tag">
            ГРУЗ: {returnLoad?.cargo_type || load.cargo_type} → {locationName(returnLoad?.destination || load.destination)}
          </div>
        </div>
      </div>

      <div className="ba-headline">{match.empty_km_saved} KM SAVED</div>

      <table className="calculation-block">
        <tbody>
          <tr>
            <td>Empty distance before:</td>
            <td>{match.empty_km_before} km</td>
          </tr>
          <tr>
            <td>Empty distance after:</td>
            <td>{match.empty_km_after} km</td>
          </tr>
          <tr className="ba-highlight">
            <td>EMPTY KM SAVED:</td>
            <td>{match.empty_km_saved} km</td>
          </tr>
          <tr>
            <td>Vehicle consumption:</td>
            <td>{FUEL_CONSUMPTION_L_PER_100KM} L/100 km</td>
          </tr>
          <tr>
            <td>Fuel saved:</td>
            <td>{match.fuel_saved_l} L</td>
          </tr>
          <tr>
            <td>Fuel price:</td>
            <td>{DIESEL_PRICE_KZT} ₸/L*</td>
          </tr>
          <tr className="ba-highlight">
            <td>Fuel saving:</td>
            <td>{match.fuel_saved_kzt.toLocaleString("ru")} ₸*</td>
          </tr>
        </tbody>
      </table>
      <p className="demo-assumption-footnote">* demo assumptions — цена топлива, тариф обратного рейса не подтверждены опросом</p>
    </div>
  );
}
