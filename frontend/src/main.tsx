import { createRoot } from "react-dom/client";
import App from "./App";
import { OperationsProvider } from "./data/Operations";
import "./theme.css";

createRoot(document.getElementById("root")!).render(
  <OperationsProvider>
    <App />
  </OperationsProvider>,
);
