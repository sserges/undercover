import { useCallback } from "react";
import { fetchSteps, type Step } from "./api";
import { usePolling } from "./usePolling";

export function Steps({ claimId }: Readonly<{ claimId: string }>) {
  const load = useCallback(() => fetchSteps(claimId), [claimId]);
  const { data: steps } = usePolling(load, 1000);

  return (
    <section className="panel" aria-label="The agent's steps">
      <h2>The agent's steps</h2>
      {steps?.length === 0 && <p className="muted">No steps yet.</p>}
      <ol className="steps">
        {steps?.map((step) => (
          <li key={step.step_id} className={`step step-${step.kind}`}>
            <StepText step={step} />
          </li>
        ))}
      </ol>
    </section>
  );
}

function StepText({ step }: Readonly<{ step: Step }>) {
  if (step.kind === "tool_call") {
    return <code className="mono">{step.text}</code>;
  }
  if (step.kind === "tool_result") {
    const refused = step.text.startsWith("Refused");
    return (
      <details>
        <summary className={refused ? "refused" : undefined}>
          {refused ? step.text : "Result"}
        </summary>
        <pre className="mono">{step.text}</pre>
      </details>
    );
  }
  return <p>{step.text}</p>;
}
