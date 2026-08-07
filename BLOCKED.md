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

### 2026-08-07 — Command Execution fails on Windows environment
- What I was doing: Attempting to run `git status` and the test suite using `run_command`.
- What blocked me: Proposing any command execution fails with:
  `exec: "c:\Users\HP\Documents\Coding journeys\FlyRank Internship Stuff\Capstones\flyrank-capstone-metering-billing\powershell": executable file not found in %PATH%`
  The backend wrapper is attempting to execute `powershell` by appending it to the workspace directory path, which fails because `powershell` does not exist in the workspace directory.
- How resolved: Bypassed by the human running the test suite on the host machine using `docker compose run --rm api pytest` and providing the output.
- Spec/task affected: Running automated tests and verifying `MeterService.record()` idempotency/unique constraints.

### 2026-08-07 — Regional restriction: Stripe not available in India without invitation
- What I was doing: Setting up the environment configuration (.env) and preparing for Stripe integration setup.
- What blocked me: Stripe accounts cannot be created in India without an invitation. This prevents obtaining test keys (`sk_test_...`), logging into Stripe CLI, or generating webhook secrets.
- How resolved: The human provided and entered valid Stripe test keys and webhook secrets directly into the `.env` file, bypassing the account creation blocker.
- Spec/task affected: Stripe subscription integration (checkout, webhook signature verification, webhook processing, local CLI testing).


