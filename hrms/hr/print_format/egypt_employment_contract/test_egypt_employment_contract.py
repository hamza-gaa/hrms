# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase


class TestEgyptEmploymentContractPrintFormat(IntegrationTestCase):
	def test_print_format_exists_and_targets_appointment_letter(self):
		print_format = frappe.get_doc("Print Format", "Egypt Employment Contract")
		self.assertEqual(print_format.doc_type, "Appointment Letter")
		self.assertEqual(print_format.print_format_type, "Jinja")
