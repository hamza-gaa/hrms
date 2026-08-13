# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Frappe HR (HRMS) — an open-source HR & Payroll app built on the **Frappe Framework**, requiring **ERPNext** as a dependency (`required_apps = ["frappe/erpnext"]` in `hrms/hooks.py`). It is not a standalone app: it is installed as a third bench app alongside `frappe` and `erpnext` and extends/overrides their doctypes rather than duplicating them (e.g. `Employee`, `Company`, `Payment Entry`, `Project`, `Timesheet` are all ERPNext/Frappe doctypes that this app hooks into).

The repo has three deployable pieces:
- **`hrms/`** — the Python/Frappe backend app (doctypes, business logic, reports, patches).
- **`frontend/`** — a Vue 3 + Ionic PWA ("Frappe HR" mobile-style app) served at `/hrms`.
- **`roster/`** — a separate Vue 3 + TypeScript app (shift/roster UI) served at `/hr`, routed via `website_route_rules` in `hooks.py`.

Both frontends use **frappe-ui** (Frappe's Vue component/data library) rather than hand-rolled API clients.

## Prerequisites for working on this repo

This app cannot run standalone — it needs a Frappe **bench** with `frappe` and `erpnext` apps installed on a site. All backend commands below assume you are inside a bench (commands run from the bench root, e.g. `~/frappe-bench`), not from this repo's root.

## Common commands

### Backend setup (from bench root)
```sh
bench new-site hrms.localhost
bench get-app erpnext
bench get-app hrms   # or use this local checkout
bench --site hrms.localhost install-app hrms
bench --site hrms.localhost add-to-hosts
bench start
```

### Running Python tests
```sh
# Run all hrms tests
bench --site test_site run-tests --app hrms

# Run a single test module
bench --site test_site run-tests --app hrms --module hrms.hr.doctype.employee_advance.test_employee_advance

# Run a single test case / method
bench --site test_site run-tests --app hrms --module hrms.hr.doctype.employee_advance.test_employee_advance --test TestEmployeeAdvance.test_paid_amount_and_status

# Parallel test run (matches CI, see .github/workflows/ci.yml)
bench --site test_site run-parallel-tests --app hrms --total-builds 1 --build-number 1
```
Tests live next to the code they test as `test_*.py` inside each doctype folder (e.g. `hrms/hr/doctype/employee_advance/test_employee_advance.py`). Most test suites extend `hrms.tests.utils.HRMSTestSuite`, which itself builds on ERPNext's `ERPNextTestSuite` and seeds common master data (company, holiday lists, leave types/allocations, salary components) via `BootStrapTestData`. Reuse existing `make_*` helpers from sibling `test_*.py` files (e.g. `make_employee`, `make_employee_advance`, `make_payroll_entry`) instead of constructing documents by hand.

### Python linting/formatting
Managed via `ruff` (config in `pyproject.toml`, tab indentation, double quotes, line length 110) and pre-commit:
```sh
pre-commit run --all-files   # ruff lint+fix, ruff-format, prettier (non-frontend JS/Vue/CSS), yaml/whitespace checks
```
Note: a pre-commit hook (`no-commit-to-branch`) blocks direct commits to `develop` — work on a feature branch.

### Frontend (PWA) — from `frontend/`
```sh
yarn install --check-files
yarn dev            # vite dev server
yarn build           # production build; also copies built index.html into hrms/www/hrms.html
```

### Roster app — from `roster/`
```sh
yarn install --check-files
yarn dev
yarn build           # copies built index.html into hrms/www/roster.html
```

### Building both frontends from repo root
```sh
yarn install          # postinstall installs deps for both frontend/ and roster/
yarn build             # builds pwa (frontend) then roster
```

## Architecture

### Doctypes are organized by Frappe module
`hrms/modules.txt` declares two modules: **HR** (`hrms/hr/`) and **Payroll** (`hrms/payroll/`), each with their own `doctype/`, `report/`, `dashboard_chart/`, `workspace/`, `notification/`, `print_format/` subfolders. Each doctype folder follows the standard Frappe layout: `<name>.json` (schema), `<name>.py` (controller), `<name>.js` (desk form script), `test_<name>.py` (tests), sometimes `<name>_dashboard.py`.

### `hooks.py` is the integration map — read it first
`hrms/hooks.py` is the single most important file for understanding how this app plugs into Frappe/ERPNext. Key sections to know:
- `override_doctype_class` — HRMS replaces the controller class for core doctypes like `Employee`, `Timesheet`, `Payment Entry`, `Project` with subclasses in `hrms/overrides/` (e.g. `EmployeeMaster`, `EmployeeTimesheet`). This is how HR behavior (leave, attendance, payroll linkage) attaches to ERPNext's core objects without forking them.
- `doc_events` — hooks into lifecycle events of both HRMS and non-HRMS doctypes (`User`, `Company`, `Journal Entry`, `Payment Entry`, `Loan`, `Project`, `Task`, etc). When tracing "why does X happen when I save Y", check here first.
- `scheduler_events` — background/cron jobs (attendance auto-processing, leave allocation, reminder emails), grouped by frequency (`hourly`, `daily`, `daily_long`, `weekly`, `monthly`).
- `regional_overrides` — country-specific logic (currently India) swaps in alternate implementations of functions like tax/HRA calculations at runtime; see `hrms/regional/india/` and `hrms/regional/united_arab_emirates/`.
- `override_doctype_dashboards` — customizes the "Connections" dashboard shown on core doctypes.

### Key backend directories
- `hrms/overrides/` — subclasses/monkeypatches for ERPNext core doctypes (see above).
- `hrms/mixins/` — mixin classes shared across doctype controllers (e.g. `appraisal.py`, `pwa_notifications.py`).
- `hrms/controllers/` — cross-cutting business logic not tied to a single doctype (employee boarding/onboarding status propagation, birthday/anniversary reminder emails).
- `hrms/api/` — whitelisted REST-style endpoints consumed by the frontend/roster apps and OAuth/system settings.
- `hrms/regional/` — country-specific overrides selected via `regional_overrides` in hooks.
- `hrms/patches/` + `hrms/patches.txt` — data migration scripts run on `bench migrate`, ordered by `patches.txt`.
- `hrms/tests/utils.py` — shared test scaffolding (`HRMSTestSuite`, `BootStrapTestData`) used across most `test_*.py` files.
- `hrms/telemetry.py` — opt-in usage analytics hooks (milestone/activation and recurring feature usage events), wired into `doc_events` and `scheduler_events`.

### Payroll domain
Payroll (`hrms/payroll/`) is the most complex module: Salary Structure → Salary Structure Assignment → Salary Slip → Payroll Entry is the core document chain. Salary calculation involves formula evaluation on Salary Components, tax slabs (`Income Tax Slab`), and regional exemption rules (HRA, marginal relief) resolved through `regional_overrides`. When touching payroll code, check `hrms/payroll/doctype/salary_slip/`, `salary_structure/`, and `payroll_entry/` together — they're tightly coupled.

### Frontend apps talk to the backend via frappe-ui
Both `frontend/` and `roster/` are Vite + Vue 3 SPAs using `frappe-ui` for resource fetching/auth against the Frappe REST/RPC API — there is no separate custom backend API layer beyond whitelisted methods in `hrms/api/` and doctype controller methods. `frontend/` additionally uses `@ionic/vue` (mobile-style navigation) and Firebase (push notifications), and is a PWA (`vite-plugin-pwa`, service worker). Built assets from both apps are copied into `hrms/public/{frontend,roster}` and `hrms/www/{hrms,roster}.html` — routing between them happens via `website_route_rules` in `hooks.py` (`/hrms/*` → frontend PWA, `/hr/*` → roster).

## CI notes relevant to local dev
- `.github/workflows/ci.yml` runs Python tests in 3 parallel containers against MariaDB via `bench run-parallel-tests`.
- `.github/workflows/linters.yml` runs commitlint (conventional commits, see `commitlint.config.js`), pre-commit (ruff + prettier), and Semgrep (`frappe/semgrep-rules` plus this repo's own rules in `semgrep/`).
- Commit messages must follow Conventional Commits (enforced by commitlint in CI).
