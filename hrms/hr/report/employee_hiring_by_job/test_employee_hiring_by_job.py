# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.hr.report.employee_hiring_by_job.employee_hiring_by_job import execute
from hrms.tests.utils import HRMSTestSuite


class TestEmployeeHiringByJob(HRMSTestSuite):
	def test_execute_groups_by_designation(self):
		employee = self.make_employee("egypt_report_hiring_job@example.com")
		designation = frappe.db.get_value("Employee", employee, "designation")

		columns, data = execute(frappe._dict())

		fieldnames = [c["fieldname"] for c in columns]
		self.assertIn("designation", fieldnames)
		self.assertIn("employee_count", fieldnames)

		if designation:
			designation_rows = [row for row in data if row[0] == designation]
			self.assertEqual(len(designation_rows), 1)
			self.assertGreaterEqual(designation_rows[0][1], 1)
