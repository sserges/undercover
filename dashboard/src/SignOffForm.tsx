import { useState, type SubmitEvent } from "react";
import { fetchHandlers, signOff } from "./api";
import { usePolling } from "./usePolling";

export function SignOffForm({ claimId }: Readonly<{ claimId: string }>) {
  const { data: handlers } = usePolling(fetchHandlers);
  const [handlerId, setHandlerId] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const submit = (event: SubmitEvent) => {
    event.preventDefault();
    setSending(true);
    signOff(claimId, handlerId).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : String(reason));
      setSending(false);
    });
  };

  return (
    <form className="sign-off" onSubmit={submit}>
      <p>
        Payouts over $1,000 need a handler's sign-off. The payment is held until
        then.
      </p>
      <label>
        Handler{" "}
        <select
          value={handlerId}
          onChange={(event) => {
            setHandlerId(event.target.value);
          }}
        >
          <option value="">Choose a handler</option>
          {handlers?.map((handler) => (
            <option key={handler.handler_id} value={handler.handler_id}>
              {handler.name}
            </option>
          ))}
        </select>
      </label>{" "}
      <button type="submit" disabled={!handlerId || sending}>
        Sign off and pay
      </button>
      {error && (
        <p className="panel error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
