# Clean-room implementation boundary

## What this repository is

TrustQuery is an independent implementation created from an empty directory and a new Git repository. Its requirements are expressed in this repository's own architecture, tests, datasets, and acceptance reports.

## What is excluded

- No Yuxi or SQLBot source file, prompt, README paragraph, screenshot, logo, asset, Docker file, or Git object is copied into this repository.
- The repository does not claim authorship of FastAPI, PostgreSQL, SQLGlot, Vue, or other dependencies. They are used through public APIs and declared in dependency manifests.
- Evaluation figures are published only after the committed runner produces a machine-readable report from a fixed dataset.

## Review checklist

Before publishing:

1. Verify this Git repository has its own root commit and no alternate object database or upstream remote.
2. Compare filenames and representative code structure against prior projects to catch accidental copying.
3. Run license and secret scans on the full tracked tree.
4. Keep this declaration and the MIT license in the public repository.

