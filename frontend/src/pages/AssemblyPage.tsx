import { useMemo, useState } from "react";
import type { Expert } from "../api/types";
import { QueryState } from "../components/controls";
import { useWorkspace } from "../state/Workspace";
import { AssemblyControls } from "./assembly/AssemblyControls";
import { AssemblyOverview } from "./assembly/AssemblyOverview";
import { AssemblyQueue } from "./assembly/AssemblyQueue";
import { ExpertCatalog } from "./assembly/ExpertCatalog";
import { AssemblyComposition } from "./assembly/AssemblyComposition";

export function AssemblyPage() {
  const { assembly, registry, command, pending } = useWorkspace();
  const data = assembly.data;
  const candidate = data?.candidate;
  const [inspectedExpert, setInspectedExpert] = useState<string | null>(null);
  const experts = useMemo(() => {
    const assemblyExperts = new Map(
      (data?.experts ?? []).map((expert) => [expert.id, expert]),
    );
    const merged = new Map<string, Expert>(
      (registry.data?.experts ?? []).map((expert) => {
        const assemblyExpert = assemblyExperts.get(expert.id);
        return [
          expert.id,
          {
            ...expert,
            ...assemblyExpert,
            description: assemblyExpert?.description ?? expert.role,
            role:
              assemblyExpert?.role ??
              candidate?.expert_roles?.[expert.id] ??
              expert.role,
          },
        ];
      }),
    );
    for (const expert of assemblyExperts.values()) {
      if (!merged.has(expert.id))
        merged.set(expert.id, {
          ...expert,
          description: expert.description ?? expert.role,
        });
    }
    return [...merged.values()];
  }, [data?.experts, registry.data?.experts, candidate?.expert_roles]);

  return (
    <>
      <QueryState {...assembly} />
      <QueryState {...registry} />
      {data && (
        <AssemblyControls
          data={data}
          candidate={candidate}
          command={command}
          disabled={!!assembly.error || !!pending.assembly}
          enabled={!!data.enabled}
          trialActive={!!data.worker?.alive}
          onInspectExperts={() => setInspectedExpert("")}
        />
      )}
      <div className="grid items-start gap-6 md:grid-cols-[minmax(0,1fr)_320px] xl:grid-cols-[minmax(0,1fr)_340px]">
        <section className="min-w-0">
          <AssemblyComposition
            experts={experts}
            candidate={candidate}
            newExperts={data?.new_experts ?? []}
            onInspect={setInspectedExpert}
          />
        </section>
        <aside className="min-w-0 space-y-5 md:sticky md:top-24">
          {data && <AssemblyOverview data={data} experts={experts} />}
          {data && (
            <AssemblyQueue recipes={data.queue ?? []} experts={experts} />
          )}
        </aside>
      </div>
      {inspectedExpert !== null && (
        <ExpertCatalog
          experts={experts}
          candidate={candidate}
          newExperts={data?.new_experts ?? []}
          selectedId={inspectedExpert}
          onSelect={setInspectedExpert}
          onClose={() => setInspectedExpert(null)}
        />
      )}
    </>
  );
}
