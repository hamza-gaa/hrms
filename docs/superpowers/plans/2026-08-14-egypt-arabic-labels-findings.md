# Egypt Arabic Labels (Area 5) — Findings, Not a Plan

**Date:** 2026-08-14
**Spec:** `docs/superpowers/specs/2026-08-13-egypt-payroll-localization-design.md`
(Section 8 — Area 5: Arabic Labels & RTL)

## Why there is no implementation plan for this area

Spec §8 assumes Arabic labels get added "via Frappe's standard Translation
tool (`ar` locale), same mechanism as the existing `hrms/locale/ar.po`" —
i.e. that a contributor edits `hrms/locale/ar.po` directly, the same way
Areas 1-4 edit Python/JSON source files.

**This assumption does not hold in this repository.** Confirmed by reading
`hrms/locale/ar.po`'s header and `crowdin.yml`:

- `hrms/locale/ar.po`'s header identifies it as Crowdin-managed:
  `X-Crowdin-Project`, `X-Crowdin-File: /[frappe.hrms] develop/hrms/locale/main.pot`,
  `Generated-By: Babel 2.16.0`.
- `crowdin.yml` (repo root) declares `hrms/locale/main.pot` as the single
  source file, with every `hrms/locale/<lang>.po` (including `ar.po`) as a
  generated `translation:` target, auto-synced back via a bot PR
  (`pull_request_title: 'fix: sync translations from crowdin'`,
  `commit_message: 'fix: %language% translations'`).
- `.github/workflows/ci.yml` and `patch.yml` both trigger specifically on
  `**.po` and `crowdin.yml` changes — treating `.po` files as a distinct,
  externally-managed category from regular source changes.
- `hrms/locale/ar.po` currently has **zero** Egypt-related entries
  (`grep -c "national_id\|social_insurance\|Egypt"` → 0), confirming no
  prior session attempted to hand-edit it either.

**Conclusion:** hand-editing `hrms/locale/ar.po` in this repo would either
be silently overwritten by the next Crowdin sync, or create a merge
conflict with the bot's own PRs. There is no in-repo action available for
"add Arabic translations" — translation happens on the Crowdin platform by
Arabic-speaking translators, against `main.pot`, outside this repository
entirely.

## What actually IS in scope, and its current status

The only thing this repository controls is whether the **English source
strings** (`label` fields in doctype/custom-field JSON, and any `_("...")`
wrapped Python strings) exist correctly — Frappe's own message-extraction
tooling (which produces `main.pot`, run by Frappe/Crowdin infrastructure,
not by this repo's CI) picks those strings up automatically once they're
in the codebase, no manual `.po` edit required for a string to become
*available* for translation.

**Status: already done.** Every Egypt-related label already exists as a
plain, correctly-capitalized English string, confirmed by reading:

- `hrms/regional/egypt/setup.py` — all Area 1 custom field `label`s
  (`"National ID"`, `"Social Insurance Number"`, `"Military Status"`,
  `"Is Person of Determination"`, etc. — 22 labeled fields total across
  4 collapsible sections).
- `hrms/payroll/doctype/egypt_statutory_settings/egypt_statutory_settings.json` —
  all field labels (`"Min Basic Wage"`, `"Social Insurance Employer Rate"`,
  etc.) plus fund-rate labels added in the Area 4 plan.
- `hrms/hr/doctype/egypt_employee_relative/`,
  `egypt_employee_spouse/`, `egypt_employee_child/` — child doctype and
  field labels.
- `hrms/regional/egypt/data/salary_components.json` — salary component
  names (`"Basic Salary"`, `"Meal Allowance"`, `"Insurance Wage"`, etc.).
- New Leave Type / Egypt Statutory Fund labels added by the Area 2 and
  Area 4 plans, once implemented.

No code change is needed here. Frappe Desk already renders RTL
automatically for users with Arabic selected as their language (spec
§8's second bullet), which requires no work either — this was confirmed
structurally by spec §8 itself and not re-verified in this session since
it's a Frappe-core behavior, not an hrms-specific one.

## If Arabic translations are genuinely wanted sooner than the next Crowdin sync

Two options, neither of which this plan implements:

1. **Wait for Crowdin.** Once this branch merges to `develop` and a
   `main.pot` regeneration + Crowdin sync cycle runs (existing repo
   process, outside this repo's direct control), Egyptian/Arabic
   translators can pick up the new strings on the Crowdin platform.
2. **Manually seed `ar.po` as a one-off, accepting sync-conflict risk.**
   Only if the user explicitly wants Arabic strings available
   immediately, independent of the Crowdin cycle — this would need
   explicit sign-off since it deviates from the repo's established
   translation workflow and creates the overwrite/conflict risk described
   above. Not recommended without that explicit ask.

`frontend/`/`roster/` RTL CSS support remains explicitly out of scope per
spec §9, unchanged from the original spec.
