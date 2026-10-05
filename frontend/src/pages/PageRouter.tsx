import { useWorkspace } from "../state/Workspace";
import { OperationPage } from "./OperationPage";
import { AutoTradingPage } from "./AutoTradingPage";
import { MarketsPage } from "./MarketsPage";
import { LearningPage } from "./LearningPage";
import { PromotionPage } from "./PromotionPage";
import { AssemblyPage } from "./AssemblyPage";
import { ConnectionPage } from "./ConnectionPage";
import { SystemPage } from "./SystemPage";
export function PageRouter() {
  const state = useWorkspace();
  switch (state.page) {
    case 1:
      return <AutoTradingPage />;
    case 2:
      return <MarketsPage />;
    case 3:
      return <LearningPage />;
    case 4:
      return <PromotionPage />;
    case 5:
      return <AssemblyPage />;
    case 6:
      return <ConnectionPage />;
    case 7:
      return <SystemPage />;
    default:
      return <OperationPage />;
  }
}
