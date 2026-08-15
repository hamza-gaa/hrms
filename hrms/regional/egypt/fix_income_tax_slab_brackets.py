# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""One-off correction script for the Egypt income tax slab brackets.

Before 2026-08-15, `hrms.regional.egypt.setup.make_income_tax_slabs()`
seeded `Egypt Income Tax Slab - Standard`/`- Disability` with an incorrect
top bracket boundary (25% capped at 600,000 EGP, 27% starting at 600,000)
that did not match any of the schedules in docs/Payroll System.rtf.doc's
income tax table. The correct boundary, matching the document's
highest-income schedule (its rightmost column), is 25% up to 1,200,000
EGP, 27% above that.

`make_income_tax_slabs()` is idempotent (skips creation if a slab of the
same name already exists), so simply re-running `setup()` on a site that
already has these slabs will NOT apply the fix — the existing, wrong
records are silently left alone. This script updates them in place.

Run manually on any Egypt-country site that had `hrms.regional.egypt.setup.setup()`
(or `make_income_tax_slabs()` directly) run before 2026-08-15:

	bench --site <site-name> execute hrms.regional.egypt.fix_income_tax_slab_brackets.execute

Safe to run multiple times — it is idempotent (checks the current bracket
values before writing, exits early if they already match the target).
"""

import frappe

CORRECT_SLABS = [
	{"from_amount": 0, "to_amount": 40000, "percent_deduction": 0},
	{"from_amount": 40000, "to_amount": 55000, "percent_deduction": 10},
	{"from_amount": 55000, "to_amount": 70000, "percent_deduction": 15},
	{"from_amount": 70000, "to_amount": 200000, "percent_deduction": 20},
	{"from_amount": 200000, "to_amount": 400000, "percent_deduction": 22.5},
	{"from_amount": 400000, "to_amount": 1200000, "percent_deduction": 25},
	{"from_amount": 1200000, "to_amount": 0, "percent_deduction": 27},
]


def execute():
	for name in ("Egypt Income Tax Slab - Standard", "Egypt Income Tax Slab - Disability"):
		if not frappe.db.exists("Income Tax Slab", name):
			print(f"{name} does not exist on this site — nothing to fix, skipping.")
			continue

		doc = frappe.get_doc("Income Tax Slab", name)
		current_slabs = [
			{
				"from_amount": row.from_amount,
				"to_amount": row.to_amount,
				"percent_deduction": row.percent_deduction,
			}
			for row in doc.slabs
		]

		if current_slabs == CORRECT_SLABS:
			print(f"{name} already has the corrected bracket boundaries — nothing to do.")
			continue

		was_submitted = doc.docstatus == 1
		if was_submitted:
			doc.cancel()

		doc.set("slabs", CORRECT_SLABS)
		doc.save(ignore_permissions=True)

		if was_submitted:
			doc.submit()

		print(f"Corrected {name}: 25% bracket now 400,000-1,200,000, 27% now starts at 1,200,000.")

	frappe.db.commit()  # nosemgrep


if __name__ == "__main__":
	execute()
