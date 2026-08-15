# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import add_days, getdate

from hrms.tests.utils import HRMSTestSuite


class TestLeaveApplicationMinYearsOfService(HRMSTestSuite):
	def test_blocks_application_before_min_years_of_service(self):
		leave_type = frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": "Test Hajj-Style Leave",
				"min_years_of_service": 5,
				"allow_negative": 1,
			}
		).insert()

		employee = self.make_employee("egypt_hajj_short_tenure@example.com")
		frappe.db.set_value("Employee", employee, "date_of_joining", add_days(getdate(), -365))

		application = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"leave_type": leave_type.name,
				"from_date": getdate(),
				"to_date": add_days(getdate(), 2),
				"company": frappe.db.get_value("Employee", employee, "company"),
			}
		)
		with self.assertRaises(frappe.ValidationError):
			application.insert()

	def test_allows_application_after_min_years_of_service(self):
		leave_type = frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": "Test Hajj-Style Leave 2",
				"min_years_of_service": 5,
				"allow_negative": 1,
			}
		).insert()

		employee = self.make_employee("egypt_hajj_long_tenure@example.com")
		frappe.db.set_value("Employee", employee, "date_of_joining", add_days(getdate(), -365 * 6))

		application = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"leave_type": leave_type.name,
				"from_date": getdate(),
				"to_date": add_days(getdate(), 2),
				"company": frappe.db.get_value("Employee", employee, "company"),
			}
		)
		# should not raise on the min-years check (other validations still apply
		# via HRMSTestSuite's seeded holiday/leave-period fixtures)
		application.insert()


class TestLeaveApplicationRequiresInsurance(HRMSTestSuite):
	def test_blocks_application_when_employee_not_insured(self):
		leave_type = frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": "Test Insured-Only Leave",
				"requires_insurance": 1,
				"allow_negative": 1,
			}
		).insert()

		employee = self.make_employee("egypt_uninsured@example.com")
		frappe.db.set_value("Employee", employee, "social_insurance_number", "")

		application = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"leave_type": leave_type.name,
				"from_date": getdate(),
				"to_date": add_days(getdate(), 2),
				"company": frappe.db.get_value("Employee", employee, "company"),
			}
		)
		with self.assertRaises(frappe.ValidationError):
			application.insert()

	def test_allows_application_when_employee_insured(self):
		leave_type = frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": "Test Insured-Only Leave 2",
				"requires_insurance": 1,
				"allow_negative": 1,
			}
		).insert()

		employee = self.make_employee("egypt_insured@example.com")
		frappe.db.set_value("Employee", employee, "social_insurance_number", "SI-12345")

		application = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"leave_type": leave_type.name,
				"from_date": getdate(),
				"to_date": add_days(getdate(), 2),
				"company": frappe.db.get_value("Employee", employee, "company"),
			}
		)
		application.insert()
