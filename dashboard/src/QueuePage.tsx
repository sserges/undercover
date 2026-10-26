import { Link } from "react-router";
import { fetchClaims, type ClaimSummary } from "./api";
import { DecisionChip, StatusChip } from "./chips";
import { STATUS_LABELS, STATUSES, date, label, money } from "./format";
import { usePolling } from "./usePolling";

export function QueuePage() {
  const { data: claims, failed } = usePolling(fetchClaims, 2000);

  return (
    <>
      <h1>Claims queue</h1>
      {failed && <p className="panel error">The backend isn't responding.</p>}
      {claims && <StatusTiles claims={claims} />}
      {claims && <ClaimsTable claims={claims} />}
    </>
  );
}

function StatusTiles({ claims }: Readonly<{ claims: ClaimSummary[] }>) {
  return (
    <ul className="tiles" aria-label="Claims by status">
      {STATUSES.map((status) => (
        <li key={status} className={`tile status-${status}`}>
          <span className="tile-count">
            {claims.filter((claim) => claim.status === status).length}
          </span>{" "}
          <span className="tile-label">{STATUS_LABELS[status]}</span>
        </li>
      ))}
    </ul>
  );
}

function ClaimsTable({ claims }: Readonly<{ claims: ClaimSummary[] }>) {
  return (
    <section className="panel table-wrap">
      <table>
        <thead>
          <tr>
            <th>Claim</th>
            <th>Customer</th>
            <th>Type</th>
            <th>Summary</th>
            <th className="number">Claimed</th>
            <th>Submitted</th>
            <th>Status</th>
            <th>Decision</th>
          </tr>
        </thead>
        <tbody>
          {claims.map((claim) => (
            <tr key={claim.claim_id}>
              <td className="mono nowrap">
                <Link to={`/claims/${claim.claim_id}`}>{claim.claim_id}</Link>
              </td>
              <td>{claim.customer_name}</td>
              <td>{label(claim.claim_type)}</td>
              <td>{claim.summary}</td>
              <td className="number mono nowrap">
                {money(claim.amount_claimed)}
              </td>
              <td className="nowrap">{date(claim.submitted_on)}</td>
              <td>
                <StatusChip status={claim.status} />
              </td>
              <td className="nowrap">
                <Decision claim={claim} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function Decision({ claim }: Readonly<{ claim: ClaimSummary }>) {
  if (!claim.decision) return null;
  return (
    <>
      <DecisionChip decision={claim.decision} />
      {claim.decision === "approve" && claim.payout !== null && (
        <span className="mono"> {money(claim.payout)}</span>
      )}
    </>
  );
}
