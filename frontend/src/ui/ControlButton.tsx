import { useState } from "react";
import { Play, Square } from "lucide-react";
import { useOperations } from "../data/Operations";
import type { Control } from "../data/types";
import { Button, ErrorMessage } from "./Primitives";

export function ControlButton({
  name,
  label,
  compact = false,
}: {
  name: Control;
  label: string;
  compact?: boolean;
}) {
  const { state, error: serverError, pending, command } = useOperations();
  const [error, setError] = useState("");
  const requested = state?.controls[name] ?? false;
  const click = async () => {
    setError("");
    try {
      await command(name, !requested);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "요청 실패");
    }
  };
  return (
    <div className="space-y-2">
      <Button
        tone={requested ? "neutral" : "primary"}
        busy={pending.has(name)}
        disabled={!state || Boolean(serverError)}
        onClick={() => void click()}
        className={compact ? "px-3 py-2" : ""}
      >
        {requested ? <Square size={13} /> : <Play size={13} />} {label}{" "}
        {requested ? "정지" : "시작"}
      </Button>
      {error && <ErrorMessage message={error} />}
    </div>
  );
}
