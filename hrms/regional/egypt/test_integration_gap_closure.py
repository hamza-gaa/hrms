# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import getdate

from hrms.payroll.utils import egypt_annual_bonus_amount
from hrms.regional.egypt.utils import validate_egypt_loan_cap
from hrms.tests.utils import HRMSTestSuite


class TestEgyptGapClosureIntegration(HRMSTestSuite):
	def test_all_three_gap_closure_features_are_reachable(self):
		# Annual Bonus fixture + settings
		self.assertTrue(
			frappe.db.exists("Salary Component", "Annual Bonus"),
			"Annual Bonus salary component must be seeded",
		)

		# Loan cap validation function is callable and enforces the interest-free rule
		employee = self.make_employee("egypt_gap_closure_integration@example.com")
		bad_loan = frappe._dict(
			applicant_type="Employee",
			applicant=employee,
			repay_from_salary=1,
			rate_of_interest=5,
			monthly_repayment_amount=0,
		)
		with self.assertRaises(frappe.ValidationError):
			validate_egypt_loan_cap(bad_loan)

		# Annual bonus helper returns 0 for a brand-new employee (no tenure yet)
		amount = egypt_annual_bonus_amount(
			date_of_joining=getdate(), company=None, date=getdate(), insurance_wage=10000
		)
		self.assertEqual(amount, 0)

		# Egypt Employee Penalty doctype is registered and insertable
		penalty = frappe.get_doc(
			{
				"doctype": "Egypt Employee Penalty",
				"employee": employee,
				"penalty_date": getdate(),
				"reason_category": "Violation",
				"basis": "Insurance Wage",
				"amount": 1,
				"days_deducted": 0,
			}
		)
		penalty.insert()
		self.assertTrue(frappe.db.exists("Egypt Employee Penalty", penalty.name))
