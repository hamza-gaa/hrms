# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.regional.egypt.test_utils import _make_salary_structure_assignment_with_gross_salary
from hrms.tests.utils import HRMSTestSuite


class TestEgyptEmployeePenalty(HRMSTestSuite):
	def test_blocks_more_than_five_absence_days_in_one_month(self):
		employee = self.make_employee("egypt_penalty_days@example.com")
		_make_salary_structure_assignment_with_gross_salary(employee, gross_salary=10000)

		for i in range(5):
			frappe.get_doc(
				{
					"doctype": "Egypt Employee Penalty",
					"employee": employee,
					"penalty_date": f"2026-03-0{i + 1}",
					"reason_category": "Violation",
					"basis": "Insurance Wage",
					"amount": 10,
					"days_deducted": 1,
				}
			).insert()

		sixth = frappe.get_doc(
			{
				"doctype": "Egypt Employee Penalty",
				"employee": employee,
				"penalty_date": "2026-03-06",
				"reason_category": "Violation",
				"basis": "Insurance Wage",
				"amount": 10,
				"days_deducted": 1,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			sixth.insert()

	def test_blocks_violation_amount_above_ten_percent_cap(self):
		employee = self.make_employee("egypt_penalty_violation_cap@example.com")
		_make_salary_structure_assignment_with_gross_salary(employee, gross_salary=10000)

		doc = frappe.get_doc(
			{
				"doctype": "Egypt Employee Penalty",
				"employee": employee,
				"penalty_date": "2026-03-01",
				"reason_category": "Violation",
				"basis": "Insurance Wage",
				"amount": 1500,  # 15% of 10000, exceeds the 10% Violation cap
				"days_deducted": 0,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_allows_damage_amount_up_to_twenty_five_percent_cap(self):
		employee = self.make_employee("egypt_penalty_damage_cap@example.com")
		_make_salary_structure_assignment_with_gross_salary(employee, gross_salary=10000)

		doc = frappe.get_doc(
			{
				"doctype": "Egypt Employee Penalty",
				"employee": employee,
				"penalty_date": "2026-03-01",
				"reason_category": "Damage",
				"basis": "Fixed Value",
				"amount": 2000,  # 20% of 10000, within the 25% Damage cap
				"days_deducted": 0,
			}
		)
		doc.insert()  # should not raise

	def test_allows_alimony_amount_up_to_fifty_percent_cap(self):
		employee = self.make_employee("egypt_penalty_alimony_cap@example.com")
		_make_salary_structure_assignment_with_gross_salary(employee, gross_salary=10000)

		doc = frappe.get_doc(
			{
				"doctype": "Egypt Employee Penalty",
				"employee": employee,
				"penalty_date": "2026-03-01",
				"reason_category": "Alimony",
				"basis": "Fixed Value",
				"amount": 4500,  # 45% of 10000, within the 50% Alimony cap
				"days_deducted": 0,
			}
		)
		doc.insert()  # should not raise
