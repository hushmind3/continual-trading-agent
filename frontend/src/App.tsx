import {FrameworkWorkspace} from "./pages/FrameworkWorkspace";
import {FinrlWorkspace} from "./pages/FinrlWorkspace";
import { useEffect, useState } from "react";
import { Shell } from "./shell/Shell";
import { OperationsBoard } from "./pages/OperationsBoard";
import { ModelWorkspace } from "./pages/ModelWorkspace";
import { MarketScanner } from "./pages/MarketScanner";
import { PortfolioWorkspace } from "./pages/PortfolioWorkspace";
import { ConnectionSettings } from "./pages/ConnectionSettings";
import { Diagnostics } from "./pages/Diagnostics";

export function route(hash: string) {
  const name = hash.replace(/^#/, "") || "finrl";
  return ["finrl","control","moe","markets","portfolio","learning","connection","system","frameworks"].includes(name) ? name : "finrl";
}
export default function App() {
  const [active, setActive] = useState(() => route(location.hash));
  useEffect(() => {
    const changed = () => setActive(route(location.hash));
    window.addEventListener("hashchange", changed);
    return () => window.removeEventListener("hashchange", changed);
  }, []);
  const page =
    active === "finrl" ? (<FinrlWorkspace key={active}/>) : active === "frameworks" ? (<FrameworkWorkspace />) : active === "moe" ? (
      <ModelWorkspace />
    ) : active === "markets" ? (
      <MarketScanner />
    ) : active === "portfolio" ? (
      <PortfolioWorkspace />
    ) : active === "learning" ? (
      <FinrlWorkspace key={active}/>
    ) : active === "connection" ? (
      <ConnectionSettings />
    ) : active === "system" ? (
      <Diagnostics />
    ) : (
      <OperationsBoard />
    );
  return <Shell active={active}>{page}</Shell>;
}
