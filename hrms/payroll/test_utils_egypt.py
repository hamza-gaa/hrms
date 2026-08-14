# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from hrms.payroll.utils import COMPONENT_EVAL_GLOBALS, egypt_insurance_wage_bounds


class TestEgyptInsuranceWageBounds(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_registered_in_component_eval_globals(self):
		self.assertIn("egypt_insurance_wage_bounds", COMPONENT_EVAL_GLOBALS)
		self.assertIs(
			COMPONENT_EVAL_GLOBALS["egypt_insurance_wage_bounds"], egypt_insurance_wage_bounds
		)

	def test_returns_bounds_from_active_settings(self):
		frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"name": "_Test Egypt Statutory Settings Insurance Wage",
				"effective_from": "2026-01-01",
				"min_insurance_wage": 2000,
				"max_insurance_wage": 14500,
			}
		).insert()

		bounds = egypt_insurance_wage_bounds(getdate("2026-06-01"))
		self.assertEqual(bounds, (2000, 14500))

	def test_returns_zero_bounds_when_no_settings_exist(self):
		bounds = egypt_insurance_wage_bounds(getdate("1999-01-01"))
		self.assertEqual(bounds, (0, 0))
