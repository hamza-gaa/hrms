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
