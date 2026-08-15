# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _

MIN_OVERTIME_DURATION_HOURS = 0.5
GROSS_SALARY_OVERTIME_CAP = 25000
LEAVE_ENCASHMENT_ELIGIBILITY_YEARS = 3
LEAVE_ENCASHMENT_GROSS_SALARY_FACTOR = 0.75


def validate_overtime_detail(overtime_slip, detail):
	"""Egypt-specific Overtime Slip row validation:
	- no overtime below the 30-minute threshold, except on rest days/holidays
	- no overtime for manager-grade employees, except on rest days/holidays
	- no overtime for employees with gross salary > 25,000 EGP, except on
	  rest days/holidays
	Registered via regional_overrides["Egypt"] against
	hrms.hr.doctype.overtime_slip.overtime_slip.validate_overtime_detail_hook.
	"""
	employee = overtime_slip.get("employee")
	is_rest_day_or_holiday = _is_rest_day_or_holiday(employee, detail.get("date"))

	if not is_rest_day_or_holiday and detail.get("overtime_duration", 0) < MIN_OVERTIME_DURATION_HOURS:
		frappe.throw(
			_("Overtime of less than {0} hours is not allowed except on rest days or holidays").format(
				MIN_OVERTIME_DURATION_HOURS
			)
		)

	if is_rest_day_or_holiday or not employee:
		return

	if _is_manager_grade(employee):
		frappe.throw(_("Overtime is not allowed for manager-grade employees except on rest days or holidays"))

	if _get_gross_salary(employee) > GROSS_SALARY_OVERTIME_CAP:
		frappe.throw(
			_("Overtime is not allowed for employees with gross salary above {0} EGP").format(
				GROSS_SALARY_OVERTIME_CAP
			)
		)


def _is_rest_day_or_holiday(employee, date):
	"""Whether `date` is a weekly off or public holiday for `employee`,
	using the employee's assigned Holiday List (same lookup Overtime Slip
	itself uses in get_holiday_map())."""
	if not employee or not date:
		return False

	from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

	from hrms.utils.holiday_list import get_holiday_dates_between

	holiday_list = get_holiday_list_for_employee(employee, raise_exception=False)
	if not holiday_list:
		return False

	holiday_dates = get_holiday_dates_between(
		holiday_list, date, date, select_weekly_off=True, as_dict=True
	)
	return bool(holiday_dates)


def _is_manager_grade(employee):
	"""An employee is manager-grade if they have at least one direct report."""
	return bool(frappe.db.exists("Employee", {"reports_to": employee, "status": "Active"}))


def _get_gross_salary(employee):
	from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
		get_assigned_salary_structure,
	)

	salary_structure = get_assigned_salary_structure(employee, frappe.utils.getdate())
	if not salary_structure:
		return 0

	amount = frappe.db.get_value(
		"Salary Detail",
		{
			"parent": salary_structure,
			"parentfield": "earnings",
			"salary_component": "Gross Salary",
		},
		"amount",
	)
	return amount or 0


def calculate_leave_encashment_amount(leave_encashment, default_amount):
	"""Egypt leave-encashment formula: Gross Salary * 0.75 * encashment_days / 30,
	only after 3 consecutive years of service; falls back to default_amount
	(the flat leave_encashment_amount_per_day result) otherwise.
	Registered via regional_overrides["Egypt"] against
	hrms.hr.doctype.leave_encashment.leave_encashment.calculate_encashment_amount_hook.
	"""
	from frappe.utils import date_diff, getdate

	employee = leave_encashment.get("employee")
	encashment_date = leave_encashment.get("encashment_date") or getdate()

	date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
	if not date_of_joining:
		return default_amount

	years_of_service = date_diff(encashment_date, date_of_joining) / 365.25
	if years_of_service < LEAVE_ENCASHMENT_ELIGIBILITY_YEARS:
		return default_amount

	gross_salary = _get_gross_salary(employee)
	if not gross_salary:
		return default_amount

	encashment_days = leave_encashment.get("encashment_days") or 0
	return gross_salary * LEAVE_ENCASHMENT_GROSS_SALARY_FACTOR * encashment_days / 30


LOAN_MONTHLY_INSTALLMENT_CAP_RATIO = 0.10


def validate_egypt_loan_cap(doc):
	"""Egypt-specific Loan validation: interest-free, monthly installment
	capped at 10% of the employee's gross salary. Registered via
	regional_overrides["Egypt"] against hrms.hr.utils.validate_loan_cap.
	"""
	if doc.applicant_type != "Employee" or not doc.repay_from_salary:
		return

	if doc.rate_of_interest:
		frappe.throw(_("Loans to employees must be interest-free"))

	gross_salary = _get_gross_salary(doc.applicant)
	if gross_salary and doc.monthly_repayment_amount > gross_salary * LOAN_MONTHLY_INSTALLMENT_CAP_RATIO:
		frappe.throw(
			_("Monthly loan installment cannot exceed {0}% of the employee's gross salary").format(
				LOAN_MONTHLY_INSTALLMENT_CAP_RATIO * 100
			)
		)
