# BLOCKED.md — The Handbrake

If the agent hits an external blocker (Stripe outage, ambiguous spec,
missing credential, a probe that can't be satisfied as written), it
STOPS and logs it here instead of guessing. A human resolves the entry,
then either fixes the environment (rule/spec/credential) or explicitly
clears the block, before work resumes.

Never invent a workaround to clear your own blocker. Never delete an
entry — move resolved ones to the "Resolved" section with the fix applied.

## Open

_(none yet)_

Template for a new entry:
```
### [DATE] — <short title>
- What I was doing:
- What blocked me:
- What I need from a human:
- Spec/task affected:
```

## Resolved

### 2026-08-07 — Regional restriction: Stripe not available in India without invitation
- What I was doing: Setting up the environment configuration (.env) and preparing for Stripe integration setup.
- What blocked me: Stripe accounts cannot be created in India without an invitation. This prevents obtaining test keys (`sk_test_...`), logging into Stripe CLI, or generating webhook secrets.
- How resolved: The human provided and entered valid Stripe test keys and webhook secrets directly into the `.env` file, bypassing the account creation blocker.
- Spec/task affected: Stripe subscription integration (checkout, webhook signature verification, webhook processing, local CLI testing).

