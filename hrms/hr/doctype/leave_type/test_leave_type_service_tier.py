# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestLeaveTypeServiceTier(IntegrationTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_leave_type_accepts_service_tiers(self):
		doc = frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": "Test Egypt Regular Leave",
				"service_tiers": [
					{"min_years": 0, "max_years": 1, "days": 15},
					{"min_years": 1, "max_years": None, "days": 21},
				],
			}
		).insert()

		self.assertEqual(len(doc.service_tiers), 2)
		self.assertEqual(doc.service_tiers[0].days, 15)
		self.assertEqual(doc.service_tiers[1].max_years, None)
