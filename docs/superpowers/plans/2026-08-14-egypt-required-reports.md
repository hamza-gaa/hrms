# Egypt Required Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the four "Required reports" listed under Area 1 of the
source document: three hiring-analysis Query Reports (by date, by
department, by job) reusing standard Frappe Report Builder patterns
already established in `hrms/hr/report/`, plus scaffolding for an
"Employment Contract" print flow modeled on HRMS's existing `Appointment
Letter` doctype. "Form 1" (an Egyptian government labor-registration
form) and the Employment Contract's actual legal wording are explicitly
**not** fabricated by this plan — see Task 4.

**Architecture:** The three hiring reports are standard Script Reports
(`execute(filters) -> (columns, data)`) against `Employee`, copying the
exact 3-file structure (`.json` config + `.py` execute function) already
used throughout `hrms/hr/report/`. Employment Contract reuses the
existing `Appointment Letter` + `Appointment Letter Template` + `Standard
Appointment Letter` print-format infrastructure rather than building a
parallel doctype from scratch — Egypt's contract becomes a second print
format (`Egypt Employment Contract`) against the same `Appointment
Letter` doctype, with Egypt-specific placeholder sections the user/legal
team fills in before use.

**Tech Stack:** Frappe Framework Script Report (JSON config + Python
`execute()`), Jinja print format JSON, `bench run-tests`.

**Spec:** `docs/superpowers/specs/2026-08-13-egypt-payroll-localization-design.md`
(Section 4 — Area 1, "Required reports" bullet), cross-checked against
`docs/Payroll System.rtf.doc`'s "Required reports" line under "First
Employees Personal Data": *"Employment Contract, Form 1, Report for the
hiring by date, Report for the hiring by Department and Report for the
hiring by Job"*.

## Global Constraints

- New reports belong to the `HR` module (`hrms/hr/report/`), matching
  every other Employee-facing report in the repo.
- Tab indentation, double quotes, line length 110 (ruff,
  `pyproject.toml`). No bench/pre-commit/ruff binary was available in the
  session that wrote this plan — trace changes by hand if unavailable at
  implementation time; do not fabricate PASS output.
- Tests live next to the code as `test_*.py`, extending
  `hrms.tests.utils.HRMSTestSuite`.
- Commit messages follow Conventional Commits.
- **No fabricated legal/government-form content.** This is a planning-time
  scope decision, not yet confirmed with the user/repo owner — flag it for
  their sign-off before or during implementation. Task 4 (Employment
  Contract) builds only the doctype/print-format scaffolding, with
  placeholder section markers the user or a legal reviewer must fill in —
  it does not invent legal clauses. "Form 1" is not built at all in this
  plan (see Task 4's notes) since neither the source document nor this
  session has the actual government form layout.
- **Confirmed against current code** (read during planning, 2026-08-14):
  - `hrms/hr/report/daily_work_summary_replies/` is the smallest existing
    Script Report (61-line `.py`), used as the structural template:
    `.json` has `doctype: "Report"`, `report_type: "Script Report"`,
    `ref_doctype`, `roles` (list of `{"role": "..."}"`), `is_standard:
    "Yes"`; `.py` exports `execute(filters=None) -> (columns, data)`
    where `columns` is a list of `{"label", "fieldname", "fieldtype",
    "width"}` dicts and `data` is a list of row lists.
  - `Appointment Letter` doctype
    (`hrms/hr/doctype/appointment_letter/appointment_letter.json`) has
    fields `applicant_name`, `appointment_date`,
    `appointment_letter_template` (Link → `Appointment Letter Template`),
    `introduction`, `body_section`, `job_applicant`, `company`,
    `closing_notes`, `terms` — confirmed present and already generic
    enough to reuse (not Egypt-specific, no changes needed to the
    doctype itself).
  - `Standard Appointment Letter` print format
    (`hrms/hr/print_format/standard_appointment_letter/standard_appointment_letter.json`)
    has `doc_type: "Appointment Letter"`, `print_format_type: "Jinja"` —
    confirmed this is the exact print-format shape Task 4 copies for
    `Egypt Employment Contract`.
  - No `Egypt Employment Contract` or Egyptian "Form 1" doctype/print
    format exists anywhere in the repo (confirmed via filesystem search).
  - `Employee` doctype has `date_of_joining`, `department`, `designation`
    fields (standard ERPNext/core fields, not Egypt-specific) — sufficient
    for all three hiring reports without any new custom fields.

---

## Task 1: Report — Hiring by Date

**Files:**
- Create: `hrms/hr/report/employee_hiring_by_date/__init__.py`
- Create: `hrms/hr/report/employee_hiring_by_date/employee_hiring_by_date.json`
- Create: `hrms/hr/report/employee_hiring_by_date/employee_hiring_by_date.py`
- Create: `hrms/hr/report/employee_hiring_by_date/test_employee_hiring_by_date.py`

**Interfaces:**
- Produces: `hrms.hr.report.employee_hiring_by_date.employee_hiring_by_date.execute(filters=None)
  -> tuple[list[dict], list[list]]` — Script Report showing Employee
  records grouped/sortable by `date_of_joining`, with columns Employee,
  Employee Name, Date of Joining, Department, Designation, Company.
  Filters: `company` (optional), `from_date`/`to_date` (optional, filter
  on `date_of_joining`).

- [ ] **Step 1: Write the failing test**

`hrms/hr/report/employee_hiring_by_date/test_employee_hiring_by_date.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.hr.report.employee_hiring_by_date.employee_hiring_by_date import execute
from hrms.tests.utils import HRMSTestSuite


class TestEmployeeHiringByDate(HRMSTestSuite):
	def test_execute_returns_columns_and_employee_row(self):
		employee = self.make_employee("egypt_report_hiring_date@example.com")
		frappe.db.set_value("Employee", employee, "date_of_joining", "2026-03-01")

		columns, data = execute(frappe._dict(from_date="2026-01-01", to_date="2026-12-31"))

		fieldnames = [c["fieldname"] for c in columns]
		self.assertIn("employee", fieldnames)
		self.assertIn("date_of_joining", fieldnames)

		employee_rows = [row for row in data if row[0] == employee]
		self.assertEqual(len(employee_rows), 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.report.employee_hiring_by_date.test_employee_hiring_by_date`
Expected: FAIL — `ModuleNotFoundError` (report doesn't exist yet). If no
bench, report NOT EXECUTED with rationale.

- [ ] **Step 3: Create the report files**

`hrms/hr/report/employee_hiring_by_date/employee_hiring_by_date.json`:

```json
{
 "add_total_row": 0,
 "columns": [],
 "creation": "2026-08-14 00:00:00.000000",
 "disabled": 0,
 "docstatus": 0,
 "doctype": "Report",
 "filters": [],
 "is_standard": "Yes",
 "letter_head": null,
 "modified": "2026-08-14 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "HR",
 "name": "Employee Hiring By Date",
 "owner": "Administrator",
 "prepared_report": 0,
 "ref_doctype": "Employee",
 "report_name": "Employee Hiring By Date",
 "report_type": "Script Report",
 "roles": [
  {
   "role": "HR User"
  },
  {
   "role": "HR Manager"
  }
 ],
 "timeout": 0
}
```

`hrms/hr/report/employee_hiring_by_date/employee_hiring_by_date.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or frappe._dict()
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
		{"label": _("Date of Joining"), "fieldname": "date_of_joining", "fieldtype": "Date", "width": 120},
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 150},
		{"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 150},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
	]


def get_data(filters):
	conditions = [["date_of_joining", "is", "set"]]
	if filters.get("company"):
		conditions.append(["company", "=", filters.company])
	if filters.get("from_date"):
		conditions.append(["date_of_joining", ">=", filters.from_date])
	if filters.get("to_date"):
		conditions.append(["date_of_joining", "<=", filters.to_date])

	employees = frappe.get_all(
		"Employee",
		filters=conditions,
		fields=["name", "employee_name", "date_of_joining", "department", "designation", "company"],
		order_by="date_of_joining asc",
	)
	return [
		[e.name, e.employee_name, e.date_of_joining, e.department, e.designation, e.company]
		for e in employees
	]
```

`hrms/hr/report/employee_hiring_by_date/__init__.py` (empty file).

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.report.employee_hiring_by_date.test_employee_hiring_by_date`
Expected: PASS. If no bench, report NOT EXECUTED with static-read
rationale.

- [ ] **Step 5: Lint**

```bash
pre-commit run --files hrms/hr/report/employee_hiring_by_date/
```

- [ ] **Step 6: Commit**

```bash
git add hrms/hr/report/employee_hiring_by_date/
git commit -m "feat(hr): add Employee Hiring By Date report"
```

---

## Task 2: Report — Hiring by Department

**Files:**
- Create: `hrms/hr/report/employee_hiring_by_department/__init__.py`
- Create: `hrms/hr/report/employee_hiring_by_department/employee_hiring_by_department.json`
- Create: `hrms/hr/report/employee_hiring_by_department/employee_hiring_by_department.py`
- Create: `hrms/hr/report/employee_hiring_by_department/test_employee_hiring_by_department.py`

**Interfaces:**
- Produces: `hrms.hr.report.employee_hiring_by_department.employee_hiring_by_department.execute(filters=None)
  -> tuple[list[dict], list[list]]` — same shape as Task 1, grouped by
  `department` with a per-department employee count column added.
  Filters: `company` (optional).

- [ ] **Step 1: Write the failing test**

`hrms/hr/report/employee_hiring_by_department/test_employee_hiring_by_department.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.hr.report.employee_hiring_by_department.employee_hiring_by_department import execute
from hrms.tests.utils import HRMSTestSuite


class TestEmployeeHiringByDepartment(HRMSTestSuite):
	def test_execute_groups_by_department(self):
		employee = self.make_employee("egypt_report_hiring_dept@example.com")
		department = frappe.db.get_value("Employee", employee, "department")

		columns, data = execute(frappe._dict())

		fieldnames = [c["fieldname"] for c in columns]
		self.assertIn("department", fieldnames)
		self.assertIn("employee_count", fieldnames)

		if department:
			department_rows = [row for row in data if row[0] == department]
			self.assertEqual(len(department_rows), 1)
			self.assertGreaterEqual(department_rows[0][1], 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.report.employee_hiring_by_department.test_employee_hiring_by_department`
Expected: FAIL — `ModuleNotFoundError`. If no bench, report NOT EXECUTED
with rationale.

- [ ] **Step 3: Create the report files**

`hrms/hr/report/employee_hiring_by_department/employee_hiring_by_department.json`:

```json
{
 "add_total_row": 1,
 "columns": [],
 "creation": "2026-08-14 00:00:00.000000",
 "disabled": 0,
 "docstatus": 0,
 "doctype": "Report",
 "filters": [],
 "is_standard": "Yes",
 "letter_head": null,
 "modified": "2026-08-14 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "HR",
 "name": "Employee Hiring By Department",
 "owner": "Administrator",
 "prepared_report": 0,
 "ref_doctype": "Employee",
 "report_name": "Employee Hiring By Department",
 "report_type": "Script Report",
 "roles": [
  {
   "role": "HR User"
  },
  {
   "role": "HR Manager"
  }
 ],
 "timeout": 0
}
```

`hrms/hr/report/employee_hiring_by_department/employee_hiring_by_department.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or frappe._dict()
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 220},
		{"label": _("Employee Count"), "fieldname": "employee_count", "fieldtype": "Int", "width": 130},
	]


def get_data(filters):
	conditions = {"status": "Active"}
	if filters.get("company"):
		conditions["company"] = filters.company

	employees = frappe.get_all("Employee", filters=conditions, fields=["department"])

	counts = {}
	for e in employees:
		department = e.department or _("No Department")
		counts[department] = counts.get(department, 0) + 1

	return [[department, count] for department, count in sorted(counts.items())]
```

`hrms/hr/report/employee_hiring_by_department/__init__.py` (empty file).

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.report.employee_hiring_by_department.test_employee_hiring_by_department`
Expected: PASS. If no bench, report NOT EXECUTED with static-read
rationale.

- [ ] **Step 5: Lint**

```bash
pre-commit run --files hrms/hr/report/employee_hiring_by_department/
```

- [ ] **Step 6: Commit**

```bash
git add hrms/hr/report/employee_hiring_by_department/
git commit -m "feat(hr): add Employee Hiring By Department report"
```

---

## Task 3: Report — Hiring by Job

**Files:**
- Create: `hrms/hr/report/employee_hiring_by_job/__init__.py`
- Create: `hrms/hr/report/employee_hiring_by_job/employee_hiring_by_job.json`
- Create: `hrms/hr/report/employee_hiring_by_job/employee_hiring_by_job.py`
- Create: `hrms/hr/report/employee_hiring_by_job/test_employee_hiring_by_job.py`

**Interfaces:**
- Produces: `hrms.hr.report.employee_hiring_by_job.employee_hiring_by_job.execute(filters=None)
  -> tuple[list[dict], list[list]]` — identical shape/structure to Task
  2, grouped by `designation` ("Job" in the source document maps to
  ERPNext's `Designation` field on Employee, confirmed the field exists
  and no separate "Job Title" custom field is needed — `job_title` isn't
  a distinct Employee field in this codebase, `designation` is the
  existing equivalent).

- [ ] **Step 1: Write the failing test**

`hrms/hr/report/employee_hiring_by_job/test_employee_hiring_by_job.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.hr.report.employee_hiring_by_job.employee_hiring_by_job import execute
from hrms.tests.utils import HRMSTestSuite


class TestEmployeeHiringByJob(HRMSTestSuite):
	def test_execute_groups_by_designation(self):
		employee = self.make_employee("egypt_report_hiring_job@example.com")
		designation = frappe.db.get_value("Employee", employee, "designation")

		columns, data = execute(frappe._dict())

		fieldnames = [c["fieldname"] for c in columns]
		self.assertIn("designation", fieldnames)
		self.assertIn("employee_count", fieldnames)

		if designation:
			designation_rows = [row for row in data if row[0] == designation]
			self.assertEqual(len(designation_rows), 1)
			self.assertGreaterEqual(designation_rows[0][1], 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.report.employee_hiring_by_job.test_employee_hiring_by_job`
Expected: FAIL — `ModuleNotFoundError`. If no bench, report NOT EXECUTED
with rationale.

- [ ] **Step 3: Create the report files**

`hrms/hr/report/employee_hiring_by_job/employee_hiring_by_job.json`:

```json
{
 "add_total_row": 1,
 "columns": [],
 "creation": "2026-08-14 00:00:00.000000",
 "disabled": 0,
 "docstatus": 0,
 "doctype": "Report",
 "filters": [],
 "is_standard": "Yes",
 "letter_head": null,
 "modified": "2026-08-14 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "HR",
 "name": "Employee Hiring By Job",
 "owner": "Administrator",
 "prepared_report": 0,
 "ref_doctype": "Employee",
 "report_name": "Employee Hiring By Job",
 "report_type": "Script Report",
 "roles": [
  {
   "role": "HR User"
  },
  {
   "role": "HR Manager"
  }
 ],
 "timeout": 0
}
```

`hrms/hr/report/employee_hiring_by_job/employee_hiring_by_job.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or frappe._dict()
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 220},
		{"label": _("Employee Count"), "fieldname": "employee_count", "fieldtype": "Int", "width": 130},
	]


def get_data(filters):
	conditions = {"status": "Active"}
	if filters.get("company"):
		conditions["company"] = filters.company

	employees = frappe.get_all("Employee", filters=conditions, fields=["designation"])

	counts = {}
	for e in employees:
		designation = e.designation or _("No Designation")
		counts[designation] = counts.get(designation, 0) + 1

	return [[designation, count] for designation, count in sorted(counts.items())]
```

`hrms/hr/report/employee_hiring_by_job/__init__.py` (empty file).

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.report.employee_hiring_by_job.test_employee_hiring_by_job`
Expected: PASS. If no bench, report NOT EXECUTED with static-read
rationale.

- [ ] **Step 5: Lint**

```bash
pre-commit run --files hrms/hr/report/employee_hiring_by_job/
```

- [ ] **Step 6: Commit**

```bash
git add hrms/hr/report/employee_hiring_by_job/
git commit -m "feat(hr): add Employee Hiring By Job report"
```

---

## Task 4: Employment Contract print format scaffold (Form 1 explicitly out of scope)

**Files:**
- Create: `hrms/hr/print_format/egypt_employment_contract/egypt_employment_contract.json`
- Create: `hrms/hr/print_format/egypt_employment_contract/test_egypt_employment_contract.py`

**Interfaces:**
- Consumes: existing `Appointment Letter` doctype (no changes).
- Produces: a new `Egypt Employment Contract` print format
  (`doc_type: "Appointment Letter"`, `print_format_type: "Jinja"`) with
  section placeholders for the clauses an Egyptian employment contract
  needs, marked with explicit `[FILL IN: ...]` Jinja comments rather than
  invented legal text.

**Scope decision (planning-time judgment call, NOT yet confirmed with the
user — surface this explicitly before implementing):** neither this
session nor the source document has the
actual legal wording of a compliant Egyptian employment contract, nor
any layout/field specification for "Form 1" (an Egyptian government
labor-registration form — a specific numbered government document, not
something safely reconstructable from a one-line spec mention). Rather
than fabricate legal or government-form content:
- This task builds the **print format scaffold only** — reuses the
  existing `Appointment Letter` doctype (already has `terms` as a Text
  Editor field for exactly this kind of body content), with a
  Jinja-templated layout whose legal clauses are explicit placeholders.
- **"Form 1" is not attempted at all in this plan.** No doctype, no
  print format, nothing — building a fake version of a real numbered
  government form would be actively harmful (a user could mistake it for
  the genuine form and submit it to Egyptian authorities). If Form 1
  support is wanted, the next step is for the user or a local legal/HR
  consultant to supply the actual form layout, at which point a follow-up
  plan can be written against real content the same way Areas 1-4 were
  built against the real `docs/Payroll System.rtf.doc`.

- [ ] **Step 1: Write the failing test**

`hrms/hr/print_format/egypt_employment_contract/test_egypt_employment_contract.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestEgyptEmploymentContractPrintFormat(IntegrationTestCase):
	def test_print_format_exists_and_targets_appointment_letter(self):
		print_format = frappe.get_doc("Print Format", "Egypt Employment Contract")
		self.assertEqual(print_format.doc_type, "Appointment Letter")
		self.assertEqual(print_format.print_format_type, "Jinja")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.print_format.egypt_employment_contract.test_egypt_employment_contract`
Expected: FAIL — `frappe.DoesNotExistError` (print format record doesn't
exist / fixture not loaded yet). If no bench, report NOT EXECUTED with
rationale — no `hrms/hr/print_format/egypt_employment_contract/` directory
exists yet, confirmed during planning.

- [ ] **Step 3: Create the print format fixture**

`hrms/hr/print_format/egypt_employment_contract/egypt_employment_contract.json`
(modeled directly on the structure of
`hrms/hr/print_format/standard_appointment_letter/standard_appointment_letter.json`,
read in full during planning):

```json
{
 "align_labels_right": 0,
 "css": "",
 "disabled": 0,
 "doc_type": "Appointment Letter",
 "docstatus": 0,
 "doctype": "Print Format",
 "font": "Default",
 "html": "<div class=\"contract-header\">\n  <h2>{{ _(\"Employment Contract\") }}</h2>\n  <!-- [FILL IN: company letterhead / logo block] -->\n</div>\n\n<div class=\"contract-parties\">\n  <!-- [FILL IN: legally required party identification clause -- company\n       registration number, employee national ID, per Egyptian Labor Law\n       No. 12 of 2003 contract requirements. Not fabricated here -- confirm\n       exact required wording with a local legal reviewer before use.] -->\n  <p>{{ _(\"Employer\") }}: {{ doc.company }}</p>\n  <p>{{ _(\"Employee\") }}: {{ doc.applicant_name }}</p>\n  <p>{{ _(\"Start Date\") }}: {{ frappe.utils.formatdate(doc.appointment_date) }}</p>\n</div>\n\n<div class=\"contract-terms\">\n  <!-- [FILL IN: contract-type clause (definite/indefinite term per Labor\n       Law), probation period clause, working hours, place of work,\n       job title/duties, wage and payment terms, notice period,\n       termination conditions -- all must match this employer's actual\n       Salary Structure Assignment and the Labor Law's mandatory\n       minimums. Not fabricated here.] -->\n  {{ doc.terms or \"\" }}\n</div>\n\n<div class=\"contract-signatures\">\n  <!-- [FILL IN: signature blocks, Labor Office approval stamp area,\n       per standard Egyptian contract format] -->\n</div>\n",
 "line_breaks": 0,
 "module": "HR",
 "name": "Egypt Employment Contract",
 "owner": "Administrator",
 "print_format_builder": 0,
 "print_format_type": "Jinja",
 "raw_printing": 0,
 "show_section_headings": 0,
 "standard": "Yes"
}
```

Note: every `[FILL IN: ...]` block above is an HTML comment (`<!-- -->`),
so the print format renders without visible placeholder text — it is
inert scaffolding, not something that would accidentally get printed and
handed to an employee as if it were a real contract. The `{{ doc.terms
or "" }}` line is the one live, functional piece: it reuses
`Appointment Letter.terms` (existing Text Editor field) so a company can
paste in their own reviewed contract text per appointment without any
further code change, exactly like `Standard Appointment Letter` already
does for its own body content.

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.hr.print_format.egypt_employment_contract.test_egypt_employment_contract`
Expected: PASS. If no bench, report NOT EXECUTED with static-read
rationale — trace the JSON's `doc_type`/`print_format_type` fields
against the test's assertions by hand.

- [ ] **Step 5: Lint**

```bash
pre-commit run --files hrms/hr/print_format/egypt_employment_contract/
```

- [ ] **Step 6: Commit**

```bash
git add hrms/hr/print_format/egypt_employment_contract/
git commit -m "feat(hr): scaffold Egypt Employment Contract print format (legal content pending review)"
```

---

## Self-Review Notes

**Spec coverage (spec §4's "Required reports" bullet), cross-checked
against the source document directly:**
- "Report for the hiring by date" → Task 1.
- "Report for the hiring by Department" → Task 2.
- "Report for the hiring by Job" → Task 3 (mapped to `designation`,
  confirmed the closest existing Employee field to the document's "Job"
  column in its personal-data table).
- "Employment Contract" → Task 4, scaffold only, non-fabrication decision
  recorded — this is a planning-time judgment call still pending user
  sign-off, not yet confirmed.
- "Form 1" → **deliberately not implemented**, per the same
  non-fabrication decision — flagged prominently in Task 4, not silently
  dropped from the report's read-through of the spec.

**Explicitly deferred / flagged, not silently dropped:**
- Form 1 (Task 4) — needs real government-form content from the user or
  a local legal/HR consultant before any implementation is possible;
  fabricating one would risk being mistaken for the genuine document.
- Employment Contract's actual legal clauses (Task 4) — same reasoning,
  scoped down to inert HTML-comment placeholders plus reuse of the
  existing `Appointment Letter.terms` field for real content the company
  supplies themselves.

**Placeholder scan:** The `[FILL IN: ...]` markers in Task 4 are the one
apparent exception to the "No Placeholders" rule, but they are
**deliberately, explicitly flagged non-code content** (legal text a
qualified reviewer must supply, not an implementation detail the
engineer forgot to write) — a planning-time judgment call pending user
sign-off, not silently left vague. Tasks 1-3 have zero placeholders;
every report is fully implemented, runnable code.

**Type/name consistency:** All three reports follow the identical
`execute(filters=None) -> (columns, data)` signature confirmed from
`hrms/hr/report/daily_work_summary_replies/daily_work_summary_replies.py`
during planning. Column/fieldname choices (`employee`, `department`,
`designation`, `employee_count`) are consistent across all three test
files and their corresponding `get_columns()`/`get_data()` functions.
