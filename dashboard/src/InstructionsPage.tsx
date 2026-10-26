import { fetchInstructions } from "./api";
import { usePolling } from "./usePolling";

export function InstructionsPage() {
  const { data: instructions } = usePolling(fetchInstructions);

  return (
    <>
      <div className="page-header">
        <h1>The agent's instructions</h1>
        <p className="muted">
          The UnderCover Agent works every claim from these instructions. They
          are read only.
        </p>
      </div>
      {instructions && (
        <section className="panel">
          <pre className="instructions">{instructions.text}</pre>
        </section>
      )}
    </>
  );
}
