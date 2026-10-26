import type { DecisionKind, Status } from "./api";

const dollars = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

const day = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeZone: "UTC",
});

export const STATUSES: Status[] = [
  "waiting",
  "in_progress",
  "waiting_for_sign_off",
  "decided",
];

export const STATUS_LABELS: Record<Status, string> = {
  waiting: "Waiting",
  in_progress: "In progress",
  waiting_for_sign_off: "Waiting for sign-off",
  decided: "Decided",
};

export const DECISION_LABELS: Record<DecisionKind, string> = {
  approve: "Approve",
  decline: "Decline",
  refer: "Refer",
};

export function money(amount: number): string {
  return dollars.format(amount);
}

const moment = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function date(isoDate: string): string {
  return day.format(new Date(isoDate));
}

export function dateTime(isoDateTime: string): string {
  return moment.format(new Date(isoDateTime));
}

/** Turn an id such as "trip_delay" into a label such as "Trip delay". */
export function label(id: string): string {
  const words = id.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}
