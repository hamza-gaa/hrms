# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from hrms.overrides.company import make_salary_components
from hrms.regional.egypt.setup import setup, uninstall


class TestEgyptArea3Integration(IntegrationTestCase):
	def tearDown(self):
		uninstall()
		frappe.db.rollback()

	def test_setup_creates_all_area3_fixtures(self):
		# setup() seeds Income Tax Slab / Gratuity Rule; Salary Component fixtures
		# are seeded separately via make_salary_components(), the same path
		# make_company_fixtures() drives on a Company country change to Egypt
		# (see hrms/overrides/company.py).
		setup()
		make_salary_components("Egypt")

		self.assertTrue(frappe.db.exists("Salary Component", "Insurance Wage"))
		self.assertTrue(frappe.db.exists("Salary Component", "Social Insurance Contribution"))
		self.assertTrue(frappe.db.exists("Income Tax Slab", "Egypt Income Tax Slab - Standard"))
		self.assertTrue(frappe.db.exists("Income Tax Slab", "Egypt Income Tax Slab - Disability"))
		self.assertTrue(frappe.db.exists("Gratuity Rule", "Egypt Standard Gratuity Rule"))
