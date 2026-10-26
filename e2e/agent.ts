import { expect, type APIRequestContext } from "@playwright/test";

/** Plays the agent's part through the API, as the UnderCover Agent would. */
export function actAsAgent(request: APIRequestContext, claimId: string) {
  const post = async (path: string, data?: object) => {
    const response = await request.post(`/api/claims/${claimId}${path}`, {
      data,
    });
    return response;
  };
  return {
    start: async () => {
      expect((await post("/start")).ok()).toBe(true);
    },
    step: async (kind: string, text: string) => {
      expect(
        (await post("/steps", { thread_id: "e2e", kind, text })).ok(),
      ).toBe(true);
    },
    decide: async (
      decision: string,
      payout: number,
      reasons: string,
      section: string,
    ) => {
      const response = await post("/decision", {
        decision,
        payout,
        reasons,
        policy_section: section,
      });
      expect(response.ok()).toBe(true);
    },
    pay: (amount: number) => post("/payment", { amount }),
  };
}
