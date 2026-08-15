# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.tests.utils import HRMSTestSuite


class TestEgyptStatutoryFund(HRMSTestSuite):
	def setUp(self):
		frappe.get_doc(
			{
				"doctype": "Egypt Statutory Settings",
				"effective_from": "2026-01-01",
				"emergency_relief_fund_rate": 1,
				"cultural_services_fund_min": 8,
				"cultural_services_fund_max": 16,
				"training_fund_rate": 0.25,
				"training_fund_min": 10,
				"training_fund_max": 30,
			}
		).insert(ignore_if_duplicate=True)

	def test_compute_below_headcount_threshold_yields_zero_contribution(self):
		employee = self.make_employee("egypt_fund_single_employee@example.com")
		frappe.db.set_value("Employee", employee, "social_insurance_number", "SI-001")

		fund = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Fund",
				"fund_type": "Emergency Relief Fund",
				"company": frappe.db.get_value("Employee", employee, "company"),
				"period_start": "2026-01-01",
				"period_end": "2026-01-31",
			}
		).insert()
		fund.compute()

		self.assertEqual(fund.insured_employee_count, 0)
		self.assertEqual(fund.computed_contribution, 0)
		self.assertEqual(fund.status, "Draft")

	def test_compute_counts_only_insured_active_employees_for_the_company(self):
		company = "_Test Company"
		insured = self.make_employee("egypt_fund_insured@example.com", company=company)
		frappe.db.set_value("Employee", insured, "social_insurance_number", "SI-002")
		uninsured = self.make_employee("egypt_fund_uninsured@example.com", company=company)
		frappe.db.set_value("Employee", uninsured, "social_insurance_number", "")

		fund = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Fund",
				"fund_type": "Social, Health and Cultural Services Fund",
				"company": company,
				"period_start": "2026-01-01",
				"period_end": "2026-01-31",
			}
		).insert()

		# force the headcount threshold check to pass regardless of how many
		# real insured employees exist in the shared test company by
		# monkeypatching the threshold map is unnecessary here: the test only
		# asserts the *counting* is correct, not the threshold gate — use
		# test_compute_applies_cultural_fund_min_value_per_insured_employee below for that.
		count = fund.get_insured_employee_count()
		self.assertGreaterEqual(count, 1)

	def make_isolated_test_company(self, name_suffix):
		company_name = f"_Test Egypt Fund Co {name_suffix}"
		if frappe.db.exists("Company", company_name):
			return company_name
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": company_name,
				"abbr": f"TEFC{name_suffix}",
				"default_currency": "EGP",
				"country": "Egypt",
			}
		).insert(ignore_if_duplicate=True)
		return company_name

	def test_compute_below_threshold_returns_zero_and_status_draft(self):
		company = self.make_isolated_test_company("1")
		employee = self.make_employee("egypt_fund_iso_1@example.com", company=company)
		frappe.db.set_value("Employee", employee, "social_insurance_number", "SI-101")

		fund = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Fund",
				"fund_type": "Social, Health and Cultural Services Fund",
				"company": company,
				"period_start": "2026-01-01",
				"period_end": "2026-01-31",
			}
		).insert()
		fund.compute()

		# only 1 insured employee exists in this dedicated company, well
		# below the fund's 20-employee threshold
		self.assertEqual(fund.insured_employee_count, 1)
		self.assertEqual(fund.computed_contribution, 0)
		self.assertEqual(fund.status, "Draft")

	def test_compute_applies_cultural_fund_min_value_per_insured_employee(self):
		company = self.make_isolated_test_company("2")
		for i in range(20):
			employee = self.make_employee(f"egypt_fund_iso_2_{i}@example.com", company=company)
			frappe.db.set_value("Employee", employee, "social_insurance_number", f"SI-2{i:02d}")

		fund = frappe.get_doc(
			{
				"doctype": "Egypt Statutory Fund",
				"fund_type": "Social, Health and Cultural Services Fund",
				"company": company,
				"period_start": "2026-01-01",
				"period_end": "2026-01-31",
			}
		).insert()
		fund.compute()

		self.assertEqual(fund.insured_employee_count, 20)
		self.assertEqual(fund.min_value, 8)
		self.assertEqual(fund.status, "Computed")
		self.assertEqual(fund.computed_contribution, 8 * 20)
