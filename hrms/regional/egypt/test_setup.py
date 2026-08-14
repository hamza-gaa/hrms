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

	def test_salary_components_fixture_has_expected_components(self):
		import json
		import os

		fixture_path = os.path.join(
			os.path.dirname(__file__), "data", "salary_components.json"
		)
		with open(fixture_path) as f:
			components = json.load(f)

		names = {c["salary_component"] for c in components}
		expected = {
			"Basic Salary",
			"Meal Allowance",
			"Grants",
			"Living Cost",
			"Wage Supplement",
			"Performance Motivation",
			"Production Motivation",
			"Transportation Allowance",
			"Gross Salary",
			"Insurance Wage",
			"Social Insurance Contribution",
		}
		self.assertEqual(expected, names)

		insurance_wage = next(c for c in components if c["salary_component"] == "Insurance Wage")
		self.assertTrue(insurance_wage["amount_based_on_formula"])
		self.assertIn("egypt_insurance_wage_bounds", insurance_wage["formula"])

		social_insurance = next(
			c for c in components if c["salary_component"] == "Social Insurance Contribution"
		)
		self.assertEqual(social_insurance["type"], "Deduction")
		self.assertTrue(social_insurance["exempted_from_income_tax"])

	def test_setup_creates_income_tax_slabs(self):
		setup()
		self.assertTrue(frappe.db.exists("Income Tax Slab", "Egypt Income Tax Slab - Standard"))
		self.assertTrue(frappe.db.exists("Income Tax Slab", "Egypt Income Tax Slab - Disability"))

		standard = frappe.get_doc("Income Tax Slab", "Egypt Income Tax Slab - Standard")
		self.assertEqual(standard.standard_tax_exemption_amount, 20000)
		self.assertEqual(len(standard.slabs), 7)

		disability = frappe.get_doc("Income Tax Slab", "Egypt Income Tax Slab - Disability")
		self.assertEqual(disability.standard_tax_exemption_amount, 30000)
