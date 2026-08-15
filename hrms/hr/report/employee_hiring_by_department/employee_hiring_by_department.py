# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or frappe._dict()
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 220},
		{"label": _("Employee Count"), "fieldname": "employee_count", "fieldtype": "Int", "width": 130},
	]


def get_data(filters):
	conditions = {"status": "Active"}
	if filters.get("company"):
		conditions["company"] = filters.company

	employees = frappe.get_all("Employee", filters=conditions, fields=["department"])

	counts = {}
	for e in employees:
		department = e.department or _("No Department")
		counts[department] = counts.get(department, 0) + 1

	return [[department, count] for department, count in sorted(counts.items())]
