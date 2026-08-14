# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from hrms.payroll.doctype.egypt_statutory_settings.egypt_statutory_settings import (
	get_active_settings,
)


class TestEgyptStatutorySettings(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_create_and_fetch_active_settings(self):
		doc = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"name": "_Test Egypt Statutory Settings 2026-01-01",
				"effective_from": "2026-01-01",
				"min_basic_wage": 2400,
				"max_basic_wage": 12000,
				"min_insurance_wage": 2000,
				"max_insurance_wage": 14500,
				"social_insurance_employee_rate": 11,
				"social_insurance_employer_rate": 18.75,
				"overtime_day_multiplier": 1.35,
				"overtime_night_multiplier": 1.70,
				"overtime_rest_day_multiplier": 2.0,
			}
		).insert()

		active = get_active_settings(getdate("2026-06-01"))
		self.assertEqual(active.name, doc.name)
		self.assertEqual(active.min_insurance_wage, 2000)

	def test_get_active_settings_picks_latest_effective_record(self):
		older = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"name": "_Test Egypt Statutory Settings Older",
				"effective_from": "2025-01-01",
				"min_insurance_wage": 1500,
				"max_insurance_wage": 12000,
			}
		).insert()
		newer = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"name": "_Test Egypt Statutory Settings Newer",
				"effective_from": "2026-01-01",
				"min_insurance_wage": 2000,
				"max_insurance_wage": 14500,
			}
		).insert()

		active = get_active_settings(getdate("2026-06-01"))
		self.assertEqual(active.name, newer.name)

		active_before_newer = get_active_settings(getdate(add_days("2026-01-01", -1)))
		self.assertEqual(active_before_newer.name, older.name)

	def test_get_active_settings_returns_none_when_no_record(self):
		active = get_active_settings(getdate("1999-01-01"))
		self.assertIsNone(active)

	def test_get_active_settings_prefers_company_specific_record(self):
		default = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"name": "_Test Egypt Statutory Settings Default",
				"effective_from": "2026-01-01",
				"min_insurance_wage": 2000,
				"max_insurance_wage": 14500,
			}
		).insert()
		company_specific = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"name": "_Test Egypt Statutory Settings Company",
				"effective_from": "2026-01-01",
				"company": "_Test Company",
				"min_insurance_wage": 2500,
				"max_insurance_wage": 15000,
			}
		).insert()

		active_for_company = get_active_settings(getdate("2026-06-01"), company="_Test Company")
		self.assertEqual(active_for_company.name, company_specific.name)
		self.assertEqual(active_for_company.min_insurance_wage, 2500)
		self.assertEqual(active_for_company.max_insurance_wage, 15000)

		active_default = get_active_settings(getdate("2026-06-01"))
		self.assertEqual(active_default.name, default.name)
		self.assertEqual(active_default.min_insurance_wage, 2000)
		self.assertEqual(active_default.max_insurance_wage, 14500)

		active_other_company = get_active_settings(getdate("2026-06-01"), company="_Test Company 2")
		self.assertEqual(active_other_company.name, default.name)
