# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from hrms.regional.egypt.setup import uninstall


class TestEgyptCompanyIntegration(IntegrationTestCase):
	def tearDown(self):
		uninstall()
		frappe.db.rollback()

	def test_setting_company_country_to_egypt_creates_custom_fields(self):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "Test Egypt Co",
				"abbr": "TEC",
				"default_currency": "EGP",
				"country": "United Arab Emirates",
			}
		).insert(ignore_if_duplicate=True)

		company.country = "Egypt"
		frappe.flags.country_change = True
		company.save()
		frappe.flags.country_change = False

		self.assertTrue(frappe.db.exists("Custom Field", "Employee-national_id"))
		self.assertTrue(
			frappe.db.exists("Custom Field", "Employee-social_insurance_number")
		)

		company.delete()
