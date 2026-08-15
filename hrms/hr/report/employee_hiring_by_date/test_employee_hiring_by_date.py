# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from hrms.hr.report.employee_hiring_by_date.employee_hiring_by_date import execute
from hrms.tests.utils import HRMSTestSuite


class TestEmployeeHiringByDate(HRMSTestSuite):
	def test_execute_returns_columns_and_employee_row(self):
		employee = self.make_employee("egypt_report_hiring_date@example.com")
		frappe.db.set_value("Employee", employee, "date_of_joining", "2026-03-01")

		columns, data = execute(frappe._dict(from_date="2026-01-01", to_date="2026-12-31"))

		fieldnames = [c["fieldname"] for c in columns]
		self.assertIn("employee", fieldnames)
		self.assertIn("date_of_joining", fieldnames)

		employee_rows = [row for row in data if row[0] == employee]
		self.assertEqual(len(employee_rows), 1)
