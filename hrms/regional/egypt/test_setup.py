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
