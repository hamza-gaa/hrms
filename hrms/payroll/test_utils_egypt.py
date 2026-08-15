# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

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


class TestEgyptAnnualBonusAmount(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_returns_zero_when_no_settings_exist(self):
		from hrms.payroll.utils import egypt_annual_bonus_amount

		amount = egypt_annual_bonus_amount(
			date_of_joining="1990-01-01", company=None, date=getdate("1999-01-01")
		)
		self.assertEqual(amount, 0)

	def test_returns_zero_when_tenure_under_one_year(self):
		from hrms.payroll.utils import egypt_annual_bonus_amount

		frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"name": "Test Egypt Statutory Settings Bonus 1",
				"effective_from": "2026-01-01",
				"annual_bonus_rate": 3,
				"annual_bonus_minimum_amount": 250,
			}
		).insert(ignore_if_duplicate=True)

		amount = egypt_annual_bonus_amount(
			date_of_joining=add_days(getdate("2026-06-01"), -100), company=None, date=getdate("2026-06-01")
		)
		self.assertEqual(amount, 0)

	def test_returns_minimum_when_rate_based_amount_is_lower(self):
		from hrms.payroll.utils import egypt_annual_bonus_amount

		frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"name": "Test Egypt Statutory Settings Bonus 2",
				"effective_from": "2026-01-01",
				"annual_bonus_rate": 3,
				"annual_bonus_minimum_amount": 250,
			}
		).insert(ignore_if_duplicate=True)

		# 3% of an insurance wage of 5000 is 150, below the 250 minimum
		amount = egypt_annual_bonus_amount(
			date_of_joining=add_days(getdate("2026-06-01"), -365 * 2),
			company=None,
			date=getdate("2026-06-01"),
			insurance_wage=5000,
		)
		self.assertEqual(amount, 250)

	def test_returns_rate_based_amount_when_above_minimum(self):
		from hrms.payroll.utils import egypt_annual_bonus_amount

		frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"name": "Test Egypt Statutory Settings Bonus 3",
				"effective_from": "2026-01-01",
				"annual_bonus_rate": 3,
				"annual_bonus_minimum_amount": 250,
			}
		).insert(ignore_if_duplicate=True)

		# 3% of an insurance wage of 15000 is 450, above the 250 minimum
		amount = egypt_annual_bonus_amount(
			date_of_joining=add_days(getdate("2026-06-01"), -365 * 2),
			company=None,
			date=getdate("2026-06-01"),
			insurance_wage=15000,
		)
		self.assertEqual(amount, 450)

	def test_returns_nonzero_amount_when_tenure_is_exactly_one_year(self):
		from hrms.payroll.utils import egypt_annual_bonus_amount

		frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"name": "Test Egypt Statutory Settings Bonus Boundary",
				"effective_from": "2026-01-01",
				"annual_bonus_rate": 3,
				"annual_bonus_minimum_amount": 250,
			}
		).insert(ignore_if_duplicate=True)

		# joined exactly one year before the reference date (2026-01-01) —
		# 365 days in a non-leap year, which the old date_diff/365.25
		# arithmetic incorrectly treated as under one year of tenure
		amount = egypt_annual_bonus_amount(
			date_of_joining="2025-01-01", company=None, date=getdate("2026-06-01"), insurance_wage=15000
		)
		self.assertEqual(amount, 450)  # 15000 * 3/100 = 450, above the 250 minimum
