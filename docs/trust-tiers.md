# Trust tiers

Every listed port shows one trust tier, plus its health badge and scan label alongside it.

## The tiers, highest first

1. **✔ Verified by trevorbilt:** the curator ran the port on Apple Vision Pro. The record names the exact commit tested (`verified_commit`, which must equal the commit the index links to when the record is added) and the repo (`repo_id`). Once newer commits pass the safety check, the badge reads "repo updated since". If the entry is edited to point at a different repo, the badge drops until the curator verifies the new one.
2. **Self-reported status**, in this order:
   - `developer-verified`: the port's developer ran the current build on Apple Vision Pro, end to end.
   - `working`: the contributor reports it runs and is playable.
   - `partially-working`: playable with notable bugs or missing features.
   - `not-working`: does not currently run; listed for preservation.

## Curator's own port

A port is tagged "Curator's own port" when the curator owns its repo (or is a public member of the org that owns it), or when the curator submitted it and credits himself as the developer. The `developer.github` field alone never earns the tag, because contributors write it themselves. Curator's own ports can be verified like any other.

## Health and scan labels

- **Health:** "OK", or "⚠ May have issues" when the daily check found a problem. The entry stays listed while its developer has time to fix it.
- **Scan:** "Scanned <date> · N commits since" (the automated safety check covered the linked commit), or "Reviewed by the curator <date>" (the curator looked at that commit instead). N counts the newer commits that haven't been reviewed.

Community voting is out of scope.
