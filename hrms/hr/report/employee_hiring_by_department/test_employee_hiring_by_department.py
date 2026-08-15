# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.hr.report.employee_hiring_by_department.employee_hiring_by_department import execute
from hrms.tests.utils import HRMSTestSuite


class TestEmployeeHiringByDepartment(HRMSTestSuite):
	def test_execute_groups_by_department(self):
		employee = self.make_employee("egypt_report_hiring_dept@example.com")
		department = frappe.db.get_value("Employee", employee, "department")

		columns, data = execute(frappe._dict())

		fieldnames = [c["fieldname"] for c in columns]
		self.assertIn("department", fieldnames)
		self.assertIn("employee_count", fieldnames)

		if department:
			department_rows = [row for row in data if row[0] == department]
			self.assertEqual(len(department_rows), 1)
			self.assertGreaterEqual(department_rows[0][1], 1)
