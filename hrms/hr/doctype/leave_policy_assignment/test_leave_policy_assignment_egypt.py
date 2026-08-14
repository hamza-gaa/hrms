# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import (
	get_tiered_annual_allocation,
)


class TestTieredAnnualAllocation(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_returns_none_when_no_tiers_configured(self):
		leave_type = frappe.get_doc(
			{"doctype": "Leave Type", "leave_type_name": "Test No Tiers Leave"}
		).insert()

		self.assertIsNone(get_tiered_annual_allocation(leave_type.name, years_of_service=5))

	def test_returns_matching_tier_days(self):
		leave_type = frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": "Test Tiered Leave",
				"service_tiers": [
					{"min_years": 0, "max_years": 1, "days": 15},
					{"min_years": 1, "max_years": 10, "days": 21},
					{"min_years": 10, "max_years": None, "days": 30},
				],
			}
		).insert()

		self.assertEqual(get_tiered_annual_allocation(leave_type.name, years_of_service=0), 15)
		self.assertEqual(get_tiered_annual_allocation(leave_type.name, years_of_service=1), 21)
		self.assertEqual(get_tiered_annual_allocation(leave_type.name, years_of_service=9), 21)
		self.assertEqual(get_tiered_annual_allocation(leave_type.name, years_of_service=10), 30)
		self.assertEqual(get_tiered_annual_allocation(leave_type.name, years_of_service=100), 30)
