import { createRoot } from "react-dom/client";
import App from "./App";
import { WorkspaceProvider } from "./state/Workspace";
import "./theme.css";
createRoot(document.getElementById("root")!).render(<WorkspaceProvider><App /></WorkspaceProvider>);
