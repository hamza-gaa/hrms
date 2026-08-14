# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from hrms.regional.egypt.utils import calculate_leave_encashment_amount, validate_overtime_detail
from hrms.tests.utils import HRMSTestSuite


class TestEgyptOvertimeValidation(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_rejects_overtime_below_30_minutes(self):
		slip = frappe._dict(employee=None)
		detail = frappe._dict(overtime_duration=0.4, date=getdate("2026-06-01"))

		with self.assertRaises(frappe.ValidationError):
			validate_overtime_detail(slip, detail)

	def test_allows_overtime_at_or_above_30_minutes(self):
		slip = frappe._dict(employee=None)
		detail = frappe._dict(overtime_duration=0.5, date=getdate("2026-06-01"))

		# should not raise
		validate_overtime_detail(slip, detail)


class TestEgyptOvertimeValidationWithEmployees(HRMSTestSuite):
	def test_rejects_overtime_for_manager_grade_employee(self):
		manager = self.make_employee("egypt_manager@example.com")
		self.make_employee("egypt_report@example.com")
		frappe.db.set_value("Employee", "egypt_report@example.com", "reports_to", manager)

		slip = frappe._dict(employee=manager)
		detail = frappe._dict(overtime_duration=1.0, date=getdate("2026-06-01"))

		with self.assertRaises(frappe.ValidationError):
			validate_overtime_detail(slip, detail)

	def test_allows_manager_overtime_on_rest_day(self):
		manager = self.make_employee("egypt_manager_2@example.com")
		self.make_employee("egypt_report_2@example.com")
		frappe.db.set_value("Employee", "egypt_report_2@example.com", "reports_to", manager)

		holiday_list = frappe.db.get_value("Employee", manager, "holiday_list")
		weekly_off_date = _get_a_weekly_off_date(holiday_list)
		if not weekly_off_date:
			self.skipTest("No weekly off configured on the test company's holiday list")

		slip = frappe._dict(employee=manager)
		detail = frappe._dict(overtime_duration=1.0, date=weekly_off_date)

		# should not raise — rest day is exempt from all three checks
		validate_overtime_detail(slip, detail)


class TestEgyptLeaveEncashmentAmount(HRMSTestSuite):
	def test_returns_default_amount_when_service_under_3_years(self):
		employee = self.make_employee("egypt_short_tenure@example.com")
		frappe.db.set_value("Employee", employee, "date_of_joining", "2025-01-01")
		doc = frappe._dict(employee=employee, encashment_days=10, encashment_date="2026-06-01")

		amount = calculate_leave_encashment_amount(doc, default_amount=500)
		self.assertEqual(amount, 500)

	def test_applies_egypt_formula_after_3_years_of_service(self):
		employee = self.make_employee("egypt_long_tenure@example.com")
		frappe.db.set_value("Employee", employee, "date_of_joining", "2020-01-01")
		_make_salary_structure_assignment_with_gross_salary(employee, gross_salary=30000)
		doc = frappe._dict(employee=employee, encashment_days=15, encashment_date="2026-06-01")

		amount = calculate_leave_encashment_amount(doc, default_amount=0)
		# 30000 * 0.75 * 15 / 30 = 11250
		self.assertEqual(amount, 11250)


def _get_a_weekly_off_date(holiday_list):
	if not holiday_list:
		return None

	from hrms.utils.holiday_list import get_holiday_dates_between

	start = getdate("2026-06-01")
	end = add_days(start, 13)
	holidays = get_holiday_dates_between(holiday_list, start, end, select_weekly_off=True, as_dict=True)
	weekly_offs = [h.holiday_date for h in holidays if h.weekly_off]
	return weekly_offs[0] if weekly_offs else None


def _make_salary_structure_assignment_with_gross_salary(employee, gross_salary):
	company = frappe.db.get_value("Employee", employee, "company")

	if not frappe.db.exists("Salary Component", "Gross Salary"):
		frappe.get_doc(
			{
				"doctype": "Salary Component",
				"salary_component": "Gross Salary",
				"type": "Earning",
			}
		).insert(ignore_permissions=True)

	structure_name = f"Egypt Test Structure - {employee}"
	structure = frappe.get_doc(
		{
			"doctype": "Salary Structure",
			"name": structure_name,
			"company": company,
			"currency": "EGP",
			"is_active": "Yes",
			"payroll_frequency": "Monthly",
			"earnings": [
				{
					"salary_component": "Gross Salary",
					"amount": gross_salary,
				}
			],
			"deductions": [],
		}
	)
	structure.insert(ignore_permissions=True, ignore_mandatory=True)
	structure.submit()

	assignment = frappe.get_doc(
		{
			"doctype": "Salary Structure Assignment",
			"employee": employee,
			"salary_structure": structure_name,
			"company": company,
			"currency": "EGP",
			"from_date": "2020-01-01",
		}
	)
	assignment.insert(ignore_permissions=True, ignore_mandatory=True)
	assignment.submit()
