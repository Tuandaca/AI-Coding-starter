# Upstream Update Workflow — Maintainer Guide

This document describes the manual, maintainer-only workflow for updating upstream provenance
in `catalog/upstream-sources.yaml`. It is **not** an auto-updater, not a network service, and
not a CI automation. Every change is reviewed by a human before anything is committed.

## 1. Purpose

The purpose of this workflow is to keep the project's pinned upstream provenance (commit SHA,
reviewed date, license) in `catalog/upstream-sources.yaml` accurate, while guaranteeing that:

- Only a project maintainer may initiate an upstream update.
- Every update receives explicit human review before landing.
- No upstream source is silently replaced.
- End-user project generation remains fully offline — no GitHub access, no upstream network,
  no API calls, and no LLM involvement at generation time.

## 2. Prerequisites

- A local clone of the `AI-Coding-starter` repository on the maintainer's machine.
- Network access is allowed **for the maintainer only**, and only for the purpose of
  checking upstream state (e.g. `git ls-remote` / `git fetch` against the upstream remote).
- End-user environments must not require network access. `catalog/upstream-sources.yaml` and
  all bundled resource provenance are local files; generation uses only local artifacts.

## 3. Step-by-step workflow

1. **Check current pinned SHA.** Open `catalog/upstream-sources.yaml` and note the currently
   pinned commit SHA (and reviewed date) for each upstream source.
2. **Fetch/check new upstream SHA.** From the maintainer's local clone, query the upstream
   remote for the latest commit SHA using a local git command such as `git ls-remote`
   or `git fetch --dry-run`. Record the candidate new SHA.
3. **Review diff between current and new SHA.** Compare the current pinned SHA against the
   candidate new SHA locally. Inspect the diff of upstream changes to understand what would
   be introduced into the project's provenance.
4. **License check.** Confirm the upstream project's license is unchanged (still compatible
   with this project's licensing). Record the license in the provenance entry. Do not proceed
   if the license changed without a separate maintainer decision.
5. **Resource transformation review (if applicable).** If any imported/bundled resources
   changed between the current and new SHA, review those changes explicitly. Confirm whether
   bundled resource provenance needs updating and that no disallowed content is introduced.
6. **Tests.** Run the local provenance validation tests and lock tests to confirm the
   candidate provenance is valid and consistent with the lock file format. All tests must
   pass locally before committing.
7. **Explicit provenance update.** Edit `catalog/upstream-sources.yaml` to commit the new SHA
   and the reviewed date. Commit the change with a clear message referencing the reviewed
   upstream SHA. No silent replacement: the commit must be intentional and reviewable.

## 4. Rules

- **NEVER auto-pull latest.** Upstream SHAs are pinned; a maintainer must manually select
  each new SHA to pin.
- **NEVER auto-replace resource.** Bundled resources are never replaced automatically; any
  resource change requires explicit maintainer review (workflow step 5).
- **NEVER silent upstream sync.** There is no scheduled or background sync with upstream.
  Every provenance change is a deliberate, committed, reviewed action.
- **End-user generation must remain offline.** Project generation uses only local files
  (`catalog/upstream-sources.yaml` and bundled resource provenance). No GitHub access, no
  upstream network, no API calls, and no LLM are used during generation.
- **`catalog/upstream-sources.yaml` is local.** It is a checked-in local file maintained by
  project maintainers; bundled resource provenance is also local and bundled with the project.

## 5. OpenMontage firewall

- OpenMontage is AGPLv3-licensed.
- This project may take **architectural inspiration only** from OpenMontage.
- **NO source code is copied** from OpenMontage into this project.
- OpenMontage is **never imported** as a dependency, submodule, or bundled resource.
- Upstream provenance updates must never introduce OpenMontage source or imports. If a
  candidate upstream SHA would import OpenMontage code, the update is rejected.

## 6. Rollback

If an upstream update causes test failures, licensing concerns, or any other problem:

1. Revert `catalog/upstream-sources.yaml` to the previous commit (restoring the previous
   pinned SHA and reviewed date).
2. Stop writing the lock file if a new lock was generated as part of the failed update.
3. Re-run local provenance validation and lock tests to confirm the repository is back to a
   known-good state.
4. Document the rollback reason in the commit message or PR so future maintainers can learn
   from it.
