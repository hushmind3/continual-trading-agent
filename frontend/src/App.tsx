import { useEffect, useState } from "react";
import { Shell } from "./shell/Shell";
import { OperationsBoard } from "./pages/OperationsBoard";
import { ModelWorkspace } from "./pages/ModelWorkspace";
import { MarketScanner } from "./pages/MarketScanner";
import { PortfolioWorkspace } from "./pages/PortfolioWorkspace";
import { TrainingWorkspace } from "./pages/TrainingWorkspace";
import { ConnectionSettings } from "./pages/ConnectionSettings";
import { Diagnostics } from "./pages/Diagnostics";

export function route(hash: string) {
  const aliases: Record<string, string> = {
    assembly: "moe",
    experts: "moe",
    "trading-moe": "portfolio",
    autoTrading: "portfolio",
    promotionTrial: "learning",
  };
  const name = hash.replace(/^#/, "") || "control";
  return aliases[name] ?? name;
}
export default function App() {
  const [active, setActive] = useState(() => route(location.hash));
  useEffect(() => {
    const changed = () => setActive(route(location.hash));
    window.addEventListener("hashchange", changed);
    return () => window.removeEventListener("hashchange", changed);
  }, []);
  const page =
    active === "moe" ? (
      <ModelWorkspace />
    ) : active === "markets" ? (
      <MarketScanner />
    ) : active === "portfolio" ? (
      <PortfolioWorkspace />
    ) : active === "learning" ? (
      <TrainingWorkspace />
    ) : active === "connection" ? (
      <ConnectionSettings />
    ) : active === "system" ? (
      <Diagnostics />
    ) : (
      <OperationsBoard />
    );
  return <Shell active={active}>{page}</Shell>;
}
