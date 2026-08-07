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

_(none yet)_
