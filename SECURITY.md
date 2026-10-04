# Security and takedowns

## Reporting a malicious or broken entry

Open a [Report an entry](../../issues/new?template=report-entry.yml) issue, or email admin@trevorbilt.com for sensitive details. Credible security reports are pulled from the index immediately and investigated after. If a pull turns out to be wrong, the entry is restored.

## What the automated review covers, and what it doesn't

Most entries are not human-reviewed. Automated checks confirm the linked repo is public, has an install guide, has links that resolve, and contains no known game-data files; archives and prebuilt downloads go to the curator. An AI agent (Google's Jules) reviews the specific commit the index links to for signs of malicious code, paying closest attention to build scripts, which run on your Mac with your permissions. The review covers source code, not prebuilt apps a developer publishes.

Automation can't confirm a port runs on Apple Vision Pro, doesn't vet third-party code downloaded during a build, may not read every file, and can miss malicious code. Build the exact commit the index links to, check its "commits since scan" count, and consider building from a separate macOS user account.

## Takedown

The index hosts no game files, binaries or emulators. It only links to third-party source repositories.

To request removal, open a [Takedown request](../../issues/new?template=takedown-request.yml) issue (fastest), or email **admin@trevorbilt.com** (the formal channel). Include the entry id or URL, the work concerned, and your contact details.

- Valid requests are actioned promptly. The entry is removed from every surface and blocked from resubmission.
- Notices received by email are not published. Takedown request issues are public, so please use email for anything you'd rather keep private.
- Contributors can remove their own entries at any time.
- Rights holders may also contact GitHub about the linked repositories themselves.
