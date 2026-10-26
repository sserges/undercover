import { useCallback } from "react";
import { Link, useParams } from "react-router";
import { fetchClaim, fetchCustomer, fetchPolicy, type Claim } from "./api";
import { DecisionChip, StatusChip } from "./chips";
import { date, dateTime, label, money } from "./format";
import { SignOffForm } from "./SignOffForm";
import { Steps } from "./Steps";
import { usePolling } from "./usePolling";

export function ClaimPage() {
  const { claimId = "" } = useParams();
  const load = useCallback(() => fetchClaim(claimId), [claimId]);
  const { data: claim, failed } = usePolling(load, 1000);

  if (!claim) {
    return failed ? (
      <p className="panel error">Claim {claimId} wasn't found.</p>
    ) : null;
  }
  return (
    <>
      <div className="page-header">
        <Link to="/">Back to the queue</Link>
        <div className="claim-title">
          <h1 className="mono">{claim.claim_id}</h1>
          <StatusChip status={claim.status} />
        </div>
        <p className="lead">{claim.summary}</p>
        <p className="muted">
          {label(claim.claim_type)} claim submitted {date(claim.submitted_on)},
          claiming <span className="mono">{money(claim.amount_claimed)}</span>.
        </p>
      </div>
      <div className="claim-layout">
        <div className="claim-main">
          <DecisionPanel claim={claim} />
          <ClaimDetails claim={claim} />
          <PolicyPanel policyId={claim.policy_id} />
          <CustomerPanel customerId={claim.customer_id} />
        </div>
        <Steps claimId={claim.claim_id} />
      </div>
    </>
  );
}

function DecisionPanel({ claim }: Readonly<{ claim: Claim }>) {
  const { decision, payment, sign_off: signedOff } = claim;
  return (
    <section className="panel" aria-label="Decision">
      <h2>Decision</h2>
      {decision ? (
        <>
          <p className="decision-line">
            <DecisionChip decision={decision.decision} />
            {decision.decision === "approve" && (
              <span className="mono payout">{money(decision.payout)}</span>
            )}
            <span className="muted">Section {decision.policy_section}</span>
          </p>
          <p className="reasons">{decision.reasons}</p>
        </>
      ) : (
        <p className="muted">The agent hasn't decided this claim yet.</p>
      )}
      {payment && (
        <p>
          Paid <span className="mono">{money(payment.amount)}</span> on{" "}
          {dateTime(payment.paid_at)}.
        </p>
      )}
      {signedOff && (
        <p>
          Signed off by {signedOff.handler_name} on{" "}
          {dateTime(signedOff.signed_off_at)}.
        </p>
      )}
      {claim.status === "waiting_for_sign_off" && (
        <SignOffForm claimId={claim.claim_id} />
      )}
    </section>
  );
}

function ClaimDetails({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <section className="panel" aria-label="The claim">
      <h2>The claim</h2>
      <p className="muted">
        Incident on {date(claim.incident_date)} in {claim.incident_location}.
      </p>
      <blockquote className="story">{claim.story}</blockquote>
      <h3>Items claimed</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Item</th>
              <th>Category</th>
              <th className="number">Amount</th>
            </tr>
          </thead>
          <tbody>
            {claim.items.map((item) => (
              <tr key={item.description}>
                <td>{item.description}</td>
                <td>{label(item.category)}</td>
                <td className="number mono nowrap">{money(item.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3>Documents</h3>
      <ul className="documents">
        {claim.documents.map((document) => (
          <li key={document.name}>
            <strong>{document.name}</strong>{" "}
            <span className="muted">({label(document.type)})</span>
            <p>{document.content}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function PolicyPanel({ policyId }: Readonly<{ policyId: string }>) {
  const load = useCallback(() => fetchPolicy(policyId), [policyId]);
  const { data: policy } = usePolling(load);
  if (!policy) return null;
  const { trip } = policy;
  return (
    <section className="panel" aria-label="Policy">
      <h2>
        Policy <span className="mono">{policy.policy_id}</span>
      </h2>
      <dl className="facts">
        <dt>Plan</dt>
        <dd>{policy.plan_details.name}</dd>
        <dt>Add-ons</dt>
        <dd>{policy.add_ons.map(label).join(", ") || "None"}</dd>
        <dt>Bought</dt>
        <dd>{date(policy.purchased_on)}</dd>
        <dt>Trip</dt>
        <dd>
          {trip.destination}, {date(trip.departs_on)} to {date(trip.returns_on)}
        </dd>
        <dt>Trip cost</dt>
        <dd className="mono">{money(trip.trip_cost)}</dd>
        <dt>Travelers</dt>
        <dd>{policy.travelers.join(", ")}</dd>
      </dl>
    </section>
  );
}

function CustomerPanel({ customerId }: Readonly<{ customerId: string }>) {
  const load = useCallback(() => fetchCustomer(customerId), [customerId]);
  const { data: customer } = usePolling(load);
  if (!customer) return null;
  return (
    <section className="panel" aria-label="Customer">
      <h2>{customer.name}</h2>
      <p className="muted">Customer since {date(customer.customer_since)}.</p>
      <h3>Earlier claims</h3>
      {customer.previous_claims.length === 0 && (
        <p className="muted">No earlier claims.</p>
      )}
      <ul className="history">
        {customer.previous_claims.map((previous) => (
          <li key={previous.claim_id}>
            <span className="mono">{previous.claim_id}</span>,{" "}
            {date(previous.filed_on)}: {previous.summary}.{" "}
            {label(previous.outcome)}, paid{" "}
            <span className="mono">{money(previous.amount_paid)}</span>.
          </li>
        ))}
      </ul>
    </section>
  );
}
