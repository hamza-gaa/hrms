# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.payroll.doctype.egypt_statutory_fund.egypt_statutory_fund import FUND_HEADCOUNT_THRESHOLDS
from hrms.tests.utils import HRMSTestSuite


class TestEgyptArea4Integration(HRMSTestSuite):
	def test_all_four_fund_types_are_computable(self):
		frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"effective_from": "2026-01-01",
				"emergency_relief_fund_rate": 1,
				"cultural_services_fund_min": 8,
				"cultural_services_fund_max": 16,
				"training_fund_rate": 0.25,
				"training_fund_min": 10,
				"training_fund_max": 30,
			}
		).insert(ignore_if_duplicate=True)

		employee = self.make_employee("egypt_area4_integration@example.com")
		company = frappe.db.get_value("Employee", employee, "company")

		for fund_type in FUND_HEADCOUNT_THRESHOLDS:
			fund = frappe.get_doc(
				{
					"doctype": "Egypt Statutory Fund",
					"fund_type": fund_type,
					"company": company,
					"period_start": "2026-01-01",
					"period_end": "2026-01-31",
				}
			).insert()
			fund.compute()
			self.assertIn(fund.status, ("Draft", "Computed"))
