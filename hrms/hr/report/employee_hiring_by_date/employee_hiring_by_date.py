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
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
		{"label": _("Date of Joining"), "fieldname": "date_of_joining", "fieldtype": "Date", "width": 120},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
			"width": 150,
		},
		{
			"label": _("Designation"),
			"fieldname": "designation",
			"fieldtype": "Link",
			"options": "Designation",
			"width": 150,
		},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
	]


def get_data(filters):
	conditions = [["date_of_joining", "is", "set"]]
	if filters.get("company"):
		conditions.append(["company", "=", filters.company])
	if filters.get("from_date"):
		conditions.append(["date_of_joining", ">=", filters.from_date])
	if filters.get("to_date"):
		conditions.append(["date_of_joining", "<=", filters.to_date])

	employees = frappe.get_all(
		"Employee",
		filters=conditions,
		fields=["name", "employee_name", "date_of_joining", "department", "designation", "company"],
		order_by="date_of_joining asc",
	)
	return [
		[e.name, e.employee_name, e.date_of_joining, e.department, e.designation, e.company]
		for e in employees
	]
