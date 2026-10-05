import { useWorkspace } from "../state/Workspace";
import { OperationPage } from "./OperationPage";
import { TradingMoEPage } from "./TradingMoEPage";
import { MarketsPage } from "./MarketsPage";
import { ExpertsPage } from "./ExpertsPage";
import { LearningPage } from "./LearningPage";
import { PromotionPage } from "./PromotionPage";
import { AssemblyPage } from "./AssemblyPage";
import { ConnectionPage } from "./ConnectionPage";
import { SystemPage } from "./SystemPage";
export function PageRouter() {
  const state = useWorkspace();
  switch (state.page) {
    case 1:
      return <TradingMoEPage />;
    case 2:
      return <MarketsPage />;
    case 3:
      return <ExpertsPage />;
    case 4:
      return <LearningPage />;
    case 5:
      return <PromotionPage />;
    case 6:
      return <AssemblyPage />;
    case 7:
      return <ConnectionPage />;
    case 8:
      return <SystemPage />;
    default:
      return <OperationPage {...state} />;
  }
}
