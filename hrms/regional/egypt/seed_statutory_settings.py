# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""One-off data seed for the first Egypt Statutory Settings record.

Run manually after installing/migrating with `hrms` on an Egypt-country site:

	bench --site <site-name> execute hrms.regional.egypt.seed_statutory_settings.execute

Values are the 2026 figures from docs/Payroll System.rtf.doc:
- Basic wage: 440-2740 EGP (updates +7%/year)
- Insurance wage: 4900-16700 EGP (updates +15%/year)
- Social insurance: 11% employee / 18.75% employer
- Overtime: 1.35x day / 1.70x night / 2.0x rest-day & public holiday
- Emergency Relief Fund rate: 1%
- Social, Health and Cultural Services Fund: 8-16 EGP per insured employee
- Training and Rehabilitation Fund rate: 0.25%, bounded 10-30 EGP per insured employee

Pass company="Your Company" to scope the record to one company instead of
leaving it as the company-less default used by every Egypt company on site.
"""

import frappe


def execute(company=None, effective_from="2026-01-01"):
	if frappe.db.exists(
		"Egypt Statutory Settings", {"effective_from": effective_from, "company": company or ""}
	):
		print(f"Egypt Statutory Settings for {effective_from} ({company or 'default'}) already exists.")
		return

	doc = frappe.get_doc(
		{
			"doctype": "Egypt Statutory Settings",
			"effective_from": effective_from,
			"company": company,
			"min_basic_wage": 440,
			"max_basic_wage": 2740,
			"min_insurance_wage": 4900,
			"max_insurance_wage": 16700,
			"social_insurance_employee_rate": 11,
			"social_insurance_employer_rate": 18.75,
			"overtime_day_multiplier": 1.35,
			"overtime_night_multiplier": 1.70,
			"overtime_rest_day_multiplier": 2.0,
			"emergency_relief_fund_rate": 1,
			"cultural_services_fund_min": 8,
			"cultural_services_fund_max": 16,
			"training_fund_rate": 0.25,
			"training_fund_min": 10,
			"training_fund_max": 30,
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()  # nosemgrep
	print(f"Created Egypt Statutory Settings: {doc.name}")


if __name__ == "__main__":
	execute()
