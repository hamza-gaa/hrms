# Egypt Employee Master Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an Egypt regional module to HRMS that registers Egypt-specific
Employee custom fields (national ID, social insurance, military status,
etc.) and two new child-table doctypes (relatives-at-company,
emergency contacts), wired through the existing regional-override
mechanism so they activate automatically when a Company's country is set
to Egypt.

**Architecture:** New `hrms/regional/egypt/` Python module following the
exact structure of `hrms/regional/india/` — a `setup.py` exposing
`get_custom_fields()`, `setup()`, and `uninstall()`, discovered dynamically
by `hrms/overrides/company.py:run_regional_setup()` via
`frappe.get_attr(f"hrms.regional.{frappe.scrub(country)}.setup.setup")`.
Two new child doctypes (`Egypt Employee Relative`,
`Egypt Employee Emergency Contact`) live under `hrms/hr/doctype/` (the `HR`
module, per `hrms/modules.txt`) since regional folders hold Python
logic/fixtures only — no other HRMS regional module defines its own
doctypes. `Egypt Employee Relative` and `Egypt Employee Emergency Contact`
are attached to Employee as `Table` Custom Fields, exactly like the
existing `Employee Tax Exemption Declaration` pattern India uses for
non-core child data.

**Tech Stack:** Frappe Framework doctype JSON + Python controllers, Frappe
`create_custom_fields`/`delete_custom_fields` API, `bench run-tests`.

**Spec:** `docs/superpowers/specs/2026-08-13-egypt-payroll-localization-design.md`
(Section 4 — Area 1: Employee Master Data)

## Global Constraints

- Custom field `fieldname`s use **no `custom_` prefix** — confirmed by
  reading `hrms/regional/india/setup.py` (`ifsc_code`, `pan_number`, not
  `custom_ifsc_code`). This plan corrects the spec's `custom_` prefixes to
  match.
- All new doctypes belong to the `HR` module (`hrms/modules.txt` only
  declares `HR` and `Payroll`; there is no per-country module).
- Tab indentation, double quotes, line length 110 (ruff, `pyproject.toml`).
  Run `pre-commit run --all-files` before each commit.
- Tests live next to the code as `test_*.py` and extend
  `hrms.tests.utils.HRMSTestSuite`.
- Commit messages follow Conventional Commits (enforced by commitlint in
  CI) — e.g. `feat(egypt): ...`, `test(egypt): ...`.
- This plan assumes a bench environment (`frappe` + `erpnext` installed as
  sibling apps) for running tests; the sandbox used to write this plan did
  not have erpnext/frappe source available locally, so Task 1's first step
  is to verify a live anchor field on Employee before writing field
  definitions that reference it.

---

## Task 1: Verify Employee anchor fields and existing family/contact fields

Before writing any custom field definitions, confirm (against a real
bench/site, not assumption) what already exists on core `Employee`, so
Task 2 doesn't duplicate ERPNext core fields or reference a
non-existent `insert_after` anchor.

**Files:**
- None (read-only verification task; produces notes consumed by Task 2)

**Interfaces:**
- Produces: confirmed list of Employee fieldnames to use as
  `insert_after` anchors in Task 2, confirmation of whether
  `person_to_be_contacted` / `emergency_phone_number` / `relation` fields
  already exist on core Employee (if they do, Task 5's emergency-contact
  child table becomes unnecessary — use the core fields instead), and
  confirmation of whether a core family/dependent child table already
  exists (if so, Task 4's spouse/children child tables become
  unnecessary).

- [ ] **Step 1: Inspect Employee doctype fields on a live bench**

Run against a bench with `hrms` installed:

```bash
bench --site <site> console
```

```python
import frappe
meta = frappe.get_meta("Employee")
for f in meta.fields:
    print(f.fieldname, f.fieldtype, f.label)
```

Look specifically for:
- A field to anchor the new "Egypt Compliance" section after (a field in
  the "Personal" tab, e.g. `date_of_birth`, `gender`, or similar —
  confirm the exact fieldname present on this bench's Employee).
- Existing fields named `person_to_be_contacted`, `emergency_phone_number`,
  `relation`, or similar emergency-contact fields.
- Existing fields or child tables for family/dependents (search for
  `family`, `spouse`, `dependant` in fieldnames).

- [ ] **Step 2: Record findings**

Write the confirmed anchor fieldname and emergency-contact field status
into the top of `hrms/regional/egypt/setup.py` (created in Task 2) as a
one-line comment, e.g.:
`# anchor confirmed against Employee meta on <date>: date_of_birth`

No commit for this task — it's a verification step whose output feeds
directly into Task 2's field definitions. If emergency-contact fields
already exist on core Employee, skip Task 5 entirely and note why in the
Task 5 section when you reach it. If a core family/dependent child table
already exists, skip Task 4 entirely and note why in the Task 4 section
when you reach it.

---

## Task 2: Egypt regional module scaffold + Employee custom fields

**Files:**
- Create: `hrms/regional/egypt/__init__.py`
- Create: `hrms/regional/egypt/setup.py`
- Create: `hrms/regional/egypt/data/salary_components.json`
- Create: `hrms/regional/egypt/test_setup.py`
- Modify: `hrms/hooks.py` (no `regional_overrides` entry needed yet — Area
  1 has no Python function overrides; this task does NOT touch
  `regional_overrides`)

**Interfaces:**
- Produces: `hrms.regional.egypt.setup.get_custom_fields() -> dict[str, list[dict]]`,
  `hrms.regional.egypt.setup.setup() -> None`,
  `hrms.regional.egypt.setup.uninstall() -> None` — these three names and
  signatures are required by `hrms/overrides/company.py:run_regional_setup`
  and `hrms/setup.py:get_regional_custom_fields`, which discover them via
  `frappe.get_attr` using exactly this dotted path. Do not rename.

- [ ] **Step 1: Create the module skeleton**

`hrms/regional/egypt/__init__.py` (empty file):

```python
```

- [ ] **Step 2: Create an empty salary components fixture**

`hrms/regional/egypt/data/salary_components.json` — required to exist
because `hrms/overrides/company.py:make_salary_components()` reads
`hrms/regional/<country>/data/salary_components.json` unconditionally for
every country whenever a Company's country changes. Area 1 does not
define salary components (that's Area 3), so ship an empty list:

```json
[]
```

- [ ] **Step 3: Write the failing test for custom field registration**

`hrms/regional/egypt/test_setup.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from hrms.regional.egypt.setup import get_custom_fields, setup, uninstall


class TestEgyptSetup(IntegrationTestCase):
	def tearDown(self):
		uninstall()
		frappe.db.rollback()

	def test_get_custom_fields_returns_employee_fields(self):
		custom_fields = get_custom_fields()
		self.assertIn("Employee", custom_fields)
		fieldnames = [f["fieldname"] for f in custom_fields["Employee"]]
		self.assertIn("national_id", fieldnames)
		self.assertIn("social_insurance_number", fieldnames)
		self.assertIn("is_person_of_determination", fieldnames)

	def test_setup_creates_custom_fields_on_employee(self):
		setup()
		self.assertTrue(frappe.db.exists("Custom Field", "Employee-national_id"))
		self.assertTrue(
			frappe.db.exists("Custom Field", "Employee-social_insurance_number")
		)

	def test_uninstall_removes_custom_fields(self):
		setup()
		uninstall()
		self.assertFalse(frappe.db.exists("Custom Field", "Employee-national_id"))
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup`
Expected: FAIL with `ModuleNotFoundError: No module named 'hrms.regional.egypt.setup'`

- [ ] **Step 5: Write `hrms/regional/egypt/setup.py`**

Replace `<anchor_field>` below with the fieldname confirmed in Task 1
Step 1 (e.g. `date_of_birth`).

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.setup import delete_custom_fields

# anchor confirmed against Employee meta on 2026-08-13: <anchor_field>


def setup():
	make_custom_fields()


def uninstall():
	custom_fields = get_custom_fields()
	delete_custom_fields(custom_fields)


def make_custom_fields(update=True):
	custom_fields = get_custom_fields()
	create_custom_fields(custom_fields, update=update)


def get_custom_fields():
	return {
		"Employee": [
			{
				"fieldname": "egypt_compliance_section",
				"label": "Egypt Compliance",
				"fieldtype": "Section Break",
				"insert_after": "<anchor_field>",
				"collapsible": 1,
			},
			{
				"fieldname": "national_id",
				"label": "National ID",
				"fieldtype": "Data",
				"insert_after": "egypt_compliance_section",
				"translatable": 0,
			},
			{
				"fieldname": "national_id_issue_date",
				"label": "National ID Issue Date",
				"fieldtype": "Date",
				"insert_after": "national_id",
			},
			{
				"fieldname": "national_id_expiry_date",
				"label": "National ID Expiry Date",
				"fieldtype": "Date",
				"insert_after": "national_id_issue_date",
			},
			{
				"fieldname": "egypt_compliance_column_break_1",
				"fieldtype": "Column Break",
				"insert_after": "national_id_expiry_date",
			},
			{
				"fieldname": "social_insurance_number",
				"label": "Social Insurance Number",
				"fieldtype": "Data",
				"insert_after": "egypt_compliance_column_break_1",
				"translatable": 0,
				"description": "Presence of this field marks the employee as insured for leave eligibility and statutory fund headcount purposes.",
			},
			{
				"fieldname": "social_insurance_date",
				"label": "Social Insurance Date",
				"fieldtype": "Date",
				"insert_after": "social_insurance_number",
			},
			{
				"fieldname": "insurance_id",
				"label": "Insurance ID",
				"fieldtype": "Data",
				"insert_after": "social_insurance_date",
				"translatable": 0,
			},
			{
				"fieldname": "egypt_compliance_section_2",
				"label": "Identity & Travel Documents",
				"fieldtype": "Section Break",
				"insert_after": "insurance_id",
				"collapsible": 1,
			},
			{
				"fieldname": "passport_id",
				"label": "Passport ID",
				"fieldtype": "Data",
				"insert_after": "egypt_compliance_section_2",
				"translatable": 0,
			},
			{
				"fieldname": "passport_issue_date",
				"label": "Passport Issue Date",
				"fieldtype": "Date",
				"insert_after": "passport_id",
			},
			{
				"fieldname": "passport_expiry_date",
				"label": "Passport Expiry Date",
				"fieldtype": "Date",
				"insert_after": "passport_issue_date",
			},
			{
				"fieldname": "egypt_compliance_column_break_2",
				"fieldtype": "Column Break",
				"insert_after": "passport_expiry_date",
			},
			{
				"fieldname": "work_permit_start_date",
				"label": "Work Permit Start Date",
				"fieldtype": "Date",
				"insert_after": "egypt_compliance_column_break_2",
				"description": "For foreign employees only.",
			},
			{
				"fieldname": "work_permit_expiry_date",
				"label": "Work Permit Expiry Date",
				"fieldtype": "Date",
				"insert_after": "work_permit_start_date",
			},
			{
				"fieldname": "military_status",
				"label": "Military Status",
				"fieldtype": "Select",
				"options": "\nExempt\nCompleted\nPostponed\nServing",
				"insert_after": "work_permit_expiry_date",
			},
			{
				"fieldname": "egypt_compliance_section_3",
				"label": "Additional Personal Details",
				"fieldtype": "Section Break",
				"insert_after": "military_status",
				"collapsible": 1,
			},
			{
				"fieldname": "religion",
				"label": "Religion",
				"fieldtype": "Data",
				"insert_after": "egypt_compliance_section_3",
			},
			{
				"fieldname": "place_of_birth",
				"label": "Place of Birth",
				"fieldtype": "Data",
				"insert_after": "religion",
			},
			{
				"fieldname": "mothers_name",
				"label": "Mother's Name",
				"fieldtype": "Data",
				"insert_after": "place_of_birth",
			},
			{
				"fieldname": "egypt_compliance_column_break_3",
				"fieldtype": "Column Break",
				"insert_after": "mothers_name",
			},
			{
				"fieldname": "educational_specialization",
				"label": "Educational Specialization",
				"fieldtype": "Data",
				"insert_after": "egypt_compliance_column_break_3",
			},
			{
				"fieldname": "graduation_year",
				"label": "Graduation Year",
				"fieldtype": "Int",
				"insert_after": "educational_specialization",
			},
			{
				"fieldname": "is_person_of_determination",
				"label": "Is Person of Determination",
				"fieldtype": "Check",
				"insert_after": "graduation_year",
				"description": "Drives the extended leave tier, disability income tax slab selection, and higher personal tax exemption.",
			},
		],
	}
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup`
Expected: PASS (all 3 tests)

- [ ] **Step 7: Lint**

```bash
pre-commit run --files hrms/regional/egypt/__init__.py hrms/regional/egypt/setup.py hrms/regional/egypt/test_setup.py hrms/regional/egypt/data/salary_components.json
```

- [ ] **Step 8: Commit**

```bash
git add hrms/regional/egypt/
git commit -m "feat(egypt): add Egypt regional module with Employee compliance fields"
```

---

## Task 3: `Egypt Employee Relative` child doctype (conflict-of-interest tracking)

**Files:**
- Create: `hrms/hr/doctype/egypt_employee_relative/__init__.py`
- Create: `hrms/hr/doctype/egypt_employee_relative/egypt_employee_relative.json`
- Create: `hrms/hr/doctype/egypt_employee_relative/egypt_employee_relative.py`
- Modify: `hrms/regional/egypt/setup.py` (add `Employee` Table field
  `relatives_at_company` to `get_custom_fields()`)
- Modify: `hrms/regional/egypt/test_setup.py` (extend existing tests)

**Interfaces:**
- Consumes: `create_custom_fields`/`delete_custom_fields` from Task 2.
- Produces: doctype `Egypt Employee Relative` with fields
  `employee_name` (Data), `degree_of_kinship` (Data), `department`
  (Link → Department), `position` (Data) — consumed by the Employee
  `relatives_at_company` Table field added in this task.

- [ ] **Step 1: Write the failing test**

Add to `hrms/regional/egypt/test_setup.py`:

```python
	def test_get_custom_fields_includes_relatives_table(self):
		custom_fields = get_custom_fields()
		fieldnames = [f["fieldname"] for f in custom_fields["Employee"]]
		self.assertIn("relatives_at_company", fieldnames)
		relatives_field = next(
			f for f in custom_fields["Employee"] if f["fieldname"] == "relatives_at_company"
		)
		self.assertEqual(relatives_field["fieldtype"], "Table")
		self.assertEqual(relatives_field["options"], "Egypt Employee Relative")

	def test_setup_creates_relatives_child_table_field(self):
		setup()
		self.assertTrue(frappe.db.exists("Custom Field", "Employee-relatives_at_company"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup`
Expected: FAIL — `AssertionError` (fieldname not found) or, if the
doctype JSON doesn't exist yet, a `LinkValidationError`/`DoesNotExistError`
when `create_custom_fields` tries to validate `options: "Egypt Employee
Relative"` against a nonexistent doctype.

- [ ] **Step 3: Create the child doctype JSON**

`hrms/hr/doctype/egypt_employee_relative/egypt_employee_relative.json`:

```json
{
 "actions": [],
 "creation": "2026-08-13 00:00:00.000000",
 "doctype": "DocType",
 "editable_grid": 1,
 "engine": "InnoDB",
 "field_order": [
  "employee_name",
  "degree_of_kinship",
  "column_break_1",
  "department",
  "position"
 ],
 "fields": [
  {
   "fieldname": "employee_name",
   "fieldtype": "Data",
   "in_list_view": 1,
   "label": "Employee Name",
   "reqd": 1
  },
  {
   "fieldname": "degree_of_kinship",
   "fieldtype": "Data",
   "in_list_view": 1,
   "label": "Degree of Kinship",
   "reqd": 1
  },
  {
   "fieldname": "column_break_1",
   "fieldtype": "Column Break"
  },
  {
   "fieldname": "department",
   "fieldtype": "Link",
   "in_list_view": 1,
   "label": "Department",
   "options": "Department"
  },
  {
   "fieldname": "position",
   "fieldtype": "Data",
   "in_list_view": 1,
   "label": "Position"
  }
 ],
 "istable": 1,
 "links": [],
 "modified": "2026-08-13 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "HR",
 "name": "Egypt Employee Relative",
 "owner": "Administrator",
 "permissions": [],
 "row_format": "Dynamic",
 "sort_field": "creation",
 "sort_order": "DESC",
 "states": []
}
```

- [ ] **Step 4: Create the controller**

`hrms/hr/doctype/egypt_employee_relative/egypt_employee_relative.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from frappe.model.document import Document


class EgyptEmployeeRelative(Document):
	pass
```

`hrms/hr/doctype/egypt_employee_relative/__init__.py` (empty file).

- [ ] **Step 5: Add the Table field to Employee in `get_custom_fields()`**

In `hrms/regional/egypt/setup.py`, append to the `"Employee"` list (after
the last field added in Task 2, i.e. after `is_person_of_determination`):

```python
			{
				"fieldname": "relatives_section",
				"label": "Relatives Working at the Company",
				"fieldtype": "Section Break",
				"insert_after": "is_person_of_determination",
				"collapsible": 1,
			},
			{
				"fieldname": "relatives_at_company",
				"fieldtype": "Table",
				"options": "Egypt Employee Relative",
				"insert_after": "relatives_section",
			},
```

- [ ] **Step 6: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup`
Expected: PASS (all 5 tests)

- [ ] **Step 7: Lint**

```bash
pre-commit run --files hrms/hr/doctype/egypt_employee_relative/egypt_employee_relative.json hrms/hr/doctype/egypt_employee_relative/egypt_employee_relative.py hrms/hr/doctype/egypt_employee_relative/__init__.py hrms/regional/egypt/setup.py hrms/regional/egypt/test_setup.py
```

- [ ] **Step 8: Commit**

```bash
git add hrms/hr/doctype/egypt_employee_relative/ hrms/regional/egypt/setup.py hrms/regional/egypt/test_setup.py
git commit -m "feat(egypt): add Egypt Employee Relative child doctype for conflict-of-interest tracking"
```

---

## Task 4: Family data child tables (spouse, children)

This task only applies if Task 1 Step 1 confirmed that core `Employee`
does **not** already have family/dependent child tables. If core fields
exist, skip this task, note why in the plan file (e.g. "Skipped — core
Employee already has an Employee Dependant-style child table covering
spouse and children"), and move to Task 5.

The source document's "Family Data" section lists two distinct row
shapes — spouse (`Wife name|Wife Job|Wife Birth Date`) and children
(`Son/Daughter's Name|Son/Daughter's Job|Son/Daughter's Birth date`) —
each a repeatable row (an employee can have multiple children, and in
principle multiple spouse records over time), so this needs two child
doctypes, not one combined table with an empty "spouse job" column for
child rows.

**Files:**
- Create: `hrms/hr/doctype/egypt_employee_spouse/__init__.py`
- Create: `hrms/hr/doctype/egypt_employee_spouse/egypt_employee_spouse.json`
- Create: `hrms/hr/doctype/egypt_employee_spouse/egypt_employee_spouse.py`
- Create: `hrms/hr/doctype/egypt_employee_child/__init__.py`
- Create: `hrms/hr/doctype/egypt_employee_child/egypt_employee_child.json`
- Create: `hrms/hr/doctype/egypt_employee_child/egypt_employee_child.py`
- Modify: `hrms/regional/egypt/setup.py`
- Modify: `hrms/regional/egypt/test_setup.py`

**Interfaces:**
- Consumes: same `create_custom_fields` pattern as Task 3.
- Produces: doctype `Egypt Employee Spouse` with fields `spouse_name`
  (Data), `spouse_job` (Data), `spouse_birth_date` (Date) — consumed by
  Employee's `spouse_details` Table field. Doctype `Egypt Employee Child`
  with fields `child_name` (Data), `child_job` (Data), `child_birth_date`
  (Date) — consumed by Employee's `children_details` Table field.

- [ ] **Step 1: Write the failing tests**

Add to `hrms/regional/egypt/test_setup.py`:

```python
	def test_get_custom_fields_includes_spouse_table(self):
		custom_fields = get_custom_fields()
		fieldnames = [f["fieldname"] for f in custom_fields["Employee"]]
		self.assertIn("spouse_details", fieldnames)
		spouse_field = next(
			f for f in custom_fields["Employee"] if f["fieldname"] == "spouse_details"
		)
		self.assertEqual(spouse_field["fieldtype"], "Table")
		self.assertEqual(spouse_field["options"], "Egypt Employee Spouse")

	def test_get_custom_fields_includes_children_table(self):
		custom_fields = get_custom_fields()
		fieldnames = [f["fieldname"] for f in custom_fields["Employee"]]
		self.assertIn("children_details", fieldnames)
		children_field = next(
			f for f in custom_fields["Employee"] if f["fieldname"] == "children_details"
		)
		self.assertEqual(children_field["fieldtype"], "Table")
		self.assertEqual(children_field["options"], "Egypt Employee Child")

	def test_setup_creates_family_table_fields(self):
		setup()
		self.assertTrue(frappe.db.exists("Custom Field", "Employee-spouse_details"))
		self.assertTrue(frappe.db.exists("Custom Field", "Employee-children_details"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup`
Expected: FAIL — fieldnames not found / doctypes do not exist yet.

- [ ] **Step 3: Create the spouse child doctype JSON**

`hrms/hr/doctype/egypt_employee_spouse/egypt_employee_spouse.json`:

```json
{
 "actions": [],
 "creation": "2026-08-13 00:00:00.000000",
 "doctype": "DocType",
 "editable_grid": 1,
 "engine": "InnoDB",
 "field_order": [
  "spouse_name",
  "spouse_job",
  "spouse_birth_date"
 ],
 "fields": [
  {
   "fieldname": "spouse_name",
   "fieldtype": "Data",
   "in_list_view": 1,
   "label": "Name",
   "reqd": 1
  },
  {
   "fieldname": "spouse_job",
   "fieldtype": "Data",
   "in_list_view": 1,
   "label": "Job"
  },
  {
   "fieldname": "spouse_birth_date",
   "fieldtype": "Date",
   "in_list_view": 1,
   "label": "Birth Date"
  }
 ],
 "istable": 1,
 "links": [],
 "modified": "2026-08-13 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "HR",
 "name": "Egypt Employee Spouse",
 "owner": "Administrator",
 "permissions": [],
 "row_format": "Dynamic",
 "sort_field": "creation",
 "sort_order": "DESC",
 "states": []
}
```

`hrms/hr/doctype/egypt_employee_spouse/egypt_employee_spouse.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from frappe.model.document import Document


class EgyptEmployeeSpouse(Document):
	pass
```

`hrms/hr/doctype/egypt_employee_spouse/__init__.py` (empty file).

- [ ] **Step 4: Create the child (children) doctype JSON**

`hrms/hr/doctype/egypt_employee_child/egypt_employee_child.json`:

```json
{
 "actions": [],
 "creation": "2026-08-13 00:00:00.000000",
 "doctype": "DocType",
 "editable_grid": 1,
 "engine": "InnoDB",
 "field_order": [
  "child_name",
  "child_job",
  "child_birth_date"
 ],
 "fields": [
  {
   "fieldname": "child_name",
   "fieldtype": "Data",
   "in_list_view": 1,
   "label": "Name",
   "reqd": 1
  },
  {
   "fieldname": "child_job",
   "fieldtype": "Data",
   "in_list_view": 1,
   "label": "Job"
  },
  {
   "fieldname": "child_birth_date",
   "fieldtype": "Date",
   "in_list_view": 1,
   "label": "Birth Date"
  }
 ],
 "istable": 1,
 "links": [],
 "modified": "2026-08-13 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "HR",
 "name": "Egypt Employee Child",
 "owner": "Administrator",
 "permissions": [],
 "row_format": "Dynamic",
 "sort_field": "creation",
 "sort_order": "DESC",
 "states": []
}
```

`hrms/hr/doctype/egypt_employee_child/egypt_employee_child.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from frappe.model.document import Document


class EgyptEmployeeChild(Document):
	pass
```

`hrms/hr/doctype/egypt_employee_child/__init__.py` (empty file).

- [ ] **Step 5: Add the Table fields to Employee**

In `hrms/regional/egypt/setup.py`, append to the `"Employee"` list (after
`relatives_at_company` from Task 3 — this task runs immediately after
Task 3 and before Task 5's emergency contacts, so the anchor chain stays
valid regardless of whether Task 5 ends up skipped):

```python
			{
				"fieldname": "family_data_section",
				"label": "Family Data",
				"fieldtype": "Section Break",
				"insert_after": "relatives_at_company",
				"collapsible": 1,
			},
			{
				"fieldname": "spouse_details",
				"fieldtype": "Table",
				"options": "Egypt Employee Spouse",
				"insert_after": "family_data_section",
			},
			{
				"fieldname": "children_details",
				"fieldtype": "Table",
				"options": "Egypt Employee Child",
				"insert_after": "spouse_details",
			},
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup`
Expected: PASS (all tests so far)

- [ ] **Step 7: Lint**

```bash
pre-commit run --files hrms/hr/doctype/egypt_employee_spouse/egypt_employee_spouse.json hrms/hr/doctype/egypt_employee_spouse/egypt_employee_spouse.py hrms/hr/doctype/egypt_employee_spouse/__init__.py hrms/hr/doctype/egypt_employee_child/egypt_employee_child.json hrms/hr/doctype/egypt_employee_child/egypt_employee_child.py hrms/hr/doctype/egypt_employee_child/__init__.py hrms/regional/egypt/setup.py hrms/regional/egypt/test_setup.py
```

- [ ] **Step 8: Commit**

```bash
git add hrms/hr/doctype/egypt_employee_spouse/ hrms/hr/doctype/egypt_employee_child/ hrms/regional/egypt/setup.py hrms/regional/egypt/test_setup.py
git commit -m "feat(egypt): add spouse and children family data child doctypes"
```

---

## Task 5: Emergency contact child table (conditional on Task 1 findings)

This task only applies if Task 1 Step 1 confirmed that core `Employee`
does **not** already have emergency-contact fields
(`person_to_be_contacted`, `emergency_phone_number`, `relation`). If those
core fields exist, skip this task entirely, note in the plan file why
(e.g. "Skipped — core Employee already has person_to_be_contacted /
emergency_phone_number / relation"), and move to Task 6. The source
document requires only one emergency contact captured per employee in
its simplest reading ("Name/Job/Phone Number"), which a single set of
Data fields covers — a child table is only needed if multiple emergency
contacts must be recorded, which the source document's table layout
implies (repeatable row). Build the child table version below; if the
core fields exist, reusing them for a single contact is preferable to
introducing a duplicate mechanism, and this task is skipped as stated.

**Files:**
- Create: `hrms/hr/doctype/egypt_employee_emergency_contact/__init__.py`
- Create: `hrms/hr/doctype/egypt_employee_emergency_contact/egypt_employee_emergency_contact.json`
- Create: `hrms/hr/doctype/egypt_employee_emergency_contact/egypt_employee_emergency_contact.py`
- Modify: `hrms/regional/egypt/setup.py`
- Modify: `hrms/regional/egypt/test_setup.py`

**Interfaces:**
- Consumes: same `create_custom_fields` pattern as Task 3.
- Produces: doctype `Egypt Employee Emergency Contact` with fields
  `contact_name` (Data), `job` (Data), `phone_number` (Data) — consumed
  by the Employee `emergency_contacts` Table field added in this task.

- [ ] **Step 1: Write the failing test**

Add to `hrms/regional/egypt/test_setup.py`:

```python
	def test_get_custom_fields_includes_emergency_contacts_table(self):
		custom_fields = get_custom_fields()
		fieldnames = [f["fieldname"] for f in custom_fields["Employee"]]
		self.assertIn("emergency_contacts", fieldnames)
		contacts_field = next(
			f for f in custom_fields["Employee"] if f["fieldname"] == "emergency_contacts"
		)
		self.assertEqual(contacts_field["fieldtype"], "Table")
		self.assertEqual(contacts_field["options"], "Egypt Employee Emergency Contact")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup`
Expected: FAIL — fieldname not found / doctype does not exist yet.

- [ ] **Step 3: Create the child doctype JSON**

`hrms/hr/doctype/egypt_employee_emergency_contact/egypt_employee_emergency_contact.json`:

```json
{
 "actions": [],
 "creation": "2026-08-13 00:00:00.000000",
 "doctype": "DocType",
 "editable_grid": 1,
 "engine": "InnoDB",
 "field_order": [
  "contact_name",
  "job",
  "phone_number"
 ],
 "fields": [
  {
   "fieldname": "contact_name",
   "fieldtype": "Data",
   "in_list_view": 1,
   "label": "Name",
   "reqd": 1
  },
  {
   "fieldname": "job",
   "fieldtype": "Data",
   "in_list_view": 1,
   "label": "Job"
  },
  {
   "fieldname": "phone_number",
   "fieldtype": "Data",
   "in_list_view": 1,
   "label": "Phone Number",
   "reqd": 1
  }
 ],
 "istable": 1,
 "links": [],
 "modified": "2026-08-13 00:00:00.000000",
 "modified_by": "Administrator",
 "module": "HR",
 "name": "Egypt Employee Emergency Contact",
 "owner": "Administrator",
 "permissions": [],
 "row_format": "Dynamic",
 "sort_field": "creation",
 "sort_order": "DESC",
 "states": []
}
```

- [ ] **Step 4: Create the controller**

`hrms/hr/doctype/egypt_employee_emergency_contact/egypt_employee_emergency_contact.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from frappe.model.document import Document


class EgyptEmployeeEmergencyContact(Document):
	pass
```

`hrms/hr/doctype/egypt_employee_emergency_contact/__init__.py` (empty file).

- [ ] **Step 5: Add the Table field to Employee**

In `hrms/regional/egypt/setup.py`, append to the `"Employee"` list (after
`children_details` from Task 4 — this task runs immediately after Task 4,
so the family-data fields stay between relatives and emergency contacts).
If Task 4 was skipped (core family/dependent fields already existed on
Employee), change `insert_after` on `emergency_contacts_section` below to
`relatives_at_company` (Task 3's last field) instead:

```python
			{
				"fieldname": "emergency_contacts_section",
				"label": "Emergency Contacts",
				"fieldtype": "Section Break",
				"insert_after": "children_details",
				"collapsible": 1,
			},
			{
				"fieldname": "emergency_contacts",
				"fieldtype": "Table",
				"options": "Egypt Employee Emergency Contact",
				"insert_after": "emergency_contacts_section",
			},
```

- [ ] **Step 6: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup`
Expected: PASS (all tests in the module so far — 9 if Task 4 was not
skipped, 6 if it was)

- [ ] **Step 7: Lint**

```bash
pre-commit run --files hrms/hr/doctype/egypt_employee_emergency_contact/egypt_employee_emergency_contact.json hrms/hr/doctype/egypt_employee_emergency_contact/egypt_employee_emergency_contact.py hrms/hr/doctype/egypt_employee_emergency_contact/__init__.py hrms/regional/egypt/setup.py hrms/regional/egypt/test_setup.py
```

- [ ] **Step 8: Commit**

```bash
git add hrms/hr/doctype/egypt_employee_emergency_contact/ hrms/regional/egypt/setup.py hrms/regional/egypt/test_setup.py
git commit -m "feat(egypt): add Egypt Employee Emergency Contact child doctype"
```

---

## Task 6: Wire Egypt into `Company` country-change flow (integration test)

**Files:**
- Create: `hrms/regional/egypt/test_integration.py`
- Modify: none in `hrms/hooks.py` or `hrms/overrides/company.py` — the
  dispatch is already generic (`run_regional_setup` and
  `get_regional_custom_fields` use `frappe.scrub(country)` to find
  `hrms.regional.egypt.setup` automatically). This task only verifies the
  wiring works end-to-end; it does not add new wiring code.

**Interfaces:**
- Consumes: `hrms.regional.egypt.setup.setup`/`uninstall` (Task 2),
  `Egypt Employee Relative` (Task 3), `Egypt Employee Spouse` /
  `Egypt Employee Child` (Task 4, if built), `Egypt Employee Emergency
  Contact` (Task 5, if built).
- Produces: none — this is the final verification task for Area 1.

- [ ] **Step 1: Write the integration test**

`hrms/regional/egypt/test_integration.py`:

```python
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from hrms.regional.egypt.setup import uninstall


class TestEgyptCompanyIntegration(IntegrationTestCase):
	def tearDown(self):
		uninstall()
		frappe.db.rollback()

	def test_setting_company_country_to_egypt_creates_custom_fields(self):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "Test Egypt Co",
				"abbr": "TEC",
				"default_currency": "EGP",
				"country": "United Arab Emirates",
			}
		).insert(ignore_if_duplicate=True)

		company.country = "Egypt"
		frappe.flags.country_change = True
		company.save()
		frappe.flags.country_change = False

		self.assertTrue(frappe.db.exists("Custom Field", "Employee-national_id"))
		self.assertTrue(
			frappe.db.exists("Custom Field", "Employee-social_insurance_number")
		)

		company.delete()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_integration`

If Tasks 2-5 are already committed, this should actually PASS immediately
since the dispatch mechanism is pre-existing and generic — this step
exists to confirm that, not to find a red bar. If it fails, the failure
must be diagnosed against `hrms/overrides/company.py:make_company_fixtures`
(confirm `frappe.flags.country_change` is being read/set correctly) rather
than assumed to need new wiring code.

- [ ] **Step 3: If it fails, diagnose before adding code**

Common causes if this fails: `frappe.scrub("Egypt")` not matching the
module path (`hrms/regional/egypt/`), or the `Company` doctype's
`country` field not accepting "Egypt" as a valid option (a core Frappe
list of countries — no HRMS-side fix needed for this, "Egypt" is already
a standard Frappe country value). Do not add new hook code without first
confirming the existing generic mechanism is genuinely insufficient.

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_integration`
Expected: PASS

- [ ] **Step 5: Run the full Egypt module test suite together**

```bash
bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_setup
bench --site test_site run-tests --app hrms --module hrms.regional.egypt.test_integration
```

Expected: all PASS.

- [ ] **Step 6: Lint**

```bash
pre-commit run --files hrms/regional/egypt/test_integration.py
```

- [ ] **Step 7: Commit**

```bash
git add hrms/regional/egypt/test_integration.py
git commit -m "test(egypt): verify Company country-change dispatch activates Egypt setup"
```

---

## Self-Review Notes

**Spec coverage (spec §4, Area 1):**
- National ID + issue/expiry, Social Insurance Number/Date, Passport
  ID/issue/expiry, Military Status, Religion, Educational Specialization,
  Graduation Year, Place of Birth, Mother's Name, Work Permit dates,
  Insurance ID, Is Person of Determination → Task 2.
- Relatives working at company → Task 3.
- Family data (wife/children) → Task 4, as two child doctypes
  (`Egypt Employee Spouse`, `Egypt Employee Child`) since the source
  document's "Wife name/job/birth date" and "Son/Daughter name/job/birth
  date" rows have different field sets and both are repeatable.
  Conditional on Task 1 confirming no equivalent core doctype exists.
- Emergency contacts → Task 5 (conditional on Task 1 findings).
- Required reports (Employment Contract, Form 1, hiring-by-date/
  department/job reports) → explicitly deferred by the spec to "Area 1
  implementation" as standard Frappe Report Builder/Query Reports; not
  included in this plan since they depend on the custom fields existing
  first and were scoped by the spec as "no new architecture." A follow-up
  plan should cover these once this plan's fields are live.
- Company-country dispatch wiring verified end-to-end → Task 6.

**Placeholder scan:** No TBD/TODO left as vague prose. Tasks 4 and 5 carry
a genuine conditional (skip if Task 1 finds equivalent core fields), but
each gives the concrete skip instruction and, if not skipped, a fully
written doctype JSON/controller/test — no deferred "figure it out later."

**Type/name consistency:** `get_custom_fields()`, `setup()`, `uninstall()`
signatures match across Tasks 2-6. Doctype name `Egypt Employee Relative`
used consistently in JSON `name`, Python class `EgyptEmployeeRelative`,
and the `options` value on the `relatives_at_company` Table field. Same
consistency holds for `Egypt Employee Spouse` / `EgyptEmployeeSpouse`,
`Egypt Employee Child` / `EgyptEmployeeChild`, and
`Egypt Employee Emergency Contact` / `EgyptEmployeeEmergencyContact`.
Field-anchor chain verified end-to-end: Task 2 ends on
`is_person_of_determination` → Task 3 ends on `relatives_at_company` →
Task 4 ends on `children_details` → Task 5 ends on `emergency_contacts`.
Each task anchors to the immediately preceding task's last field, and
each of Task 4 and Task 5 documents the repoint needed if the *other*
one is skipped (Task 4 skipped → Task 5 anchors to `relatives_at_company`;
Task 5 skipped → nothing downstream depends on it, since it's the last
field group).
