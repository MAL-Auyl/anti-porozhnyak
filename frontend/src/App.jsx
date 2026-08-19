import { useState } from "react";
import "./App.css";
import Login from "./screens/Login";
import SenderScreen from "./screens/SenderScreen";
import CarrierScreen from "./screens/CarrierScreen";
import DispatcherScreen from "./screens/DispatcherScreen";
import RouteMap from "./components/RouteMap";

const SCREENS = {
  sender: SenderScreen,
  carrier: CarrierScreen,
  dispatcher: DispatcherScreen,
};

function App() {
  const [user, setUser] = useState(null);

  if (!user) {
    return <Login onLogin={setUser} />;
  }

  const Screen = SCREENS[user.role];

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="app-title">Anti-Порожняк</span>
        <span className="app-user">
          {user.name} · {user.role}
        </span>
        <button className="link-button" onClick={() => setUser(null)}>
          выйти
        </button>
      </header>
      <main className="app-main">
        <Screen user={user} />
      </main>
      <RouteMap />
    </div>
  );
}

export default App;
