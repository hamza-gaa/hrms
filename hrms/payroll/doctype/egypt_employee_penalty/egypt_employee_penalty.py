# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_first_day, get_last_day

# reason_category -> maximum fraction of monthly gross salary this
# category's cumulative penalty amount may reach in one calendar month,
# per docs/Payroll System.rtf.doc's employee-deductions table
REASON_CAP_RATIOS = {
	"Violation": 0.10,
	"Damage": 0.25,
	"Alimony": 0.50,
}

MAX_DAYS_DEDUCTED_PER_MONTH = 5


class EgyptEmployeePenalty(Document):
	def validate(self):
		self.validate_monthly_caps()

	def validate_monthly_caps(self):
		if not self.employee or not self.penalty_date:
			return

		month_start = get_first_day(self.penalty_date)
		month_end = get_last_day(self.penalty_date)

		other_records = frappe.get_all(
			"Egypt Employee Penalty",
			filters={
				"employee": self.employee,
				"penalty_date": ["between", [month_start, month_end]],
				"name": ["!=", self.name or ""],
			},
			fields=["amount", "days_deducted", "reason_category"],
		)

		total_days = self.days_deducted + sum(r.days_deducted for r in other_records)
		if total_days > MAX_DAYS_DEDUCTED_PER_MONTH:
			frappe.throw(
				_("Cannot deduct more than {0} days off per month for {1}").format(
					MAX_DAYS_DEDUCTED_PER_MONTH, self.employee
				)
			)

		cap_ratio = REASON_CAP_RATIOS.get(self.reason_category)
		if not cap_ratio:
			return

		same_category_total = self.amount + sum(
			r.amount for r in other_records if r.reason_category == self.reason_category
		)

		from hrms.regional.egypt.utils import _get_gross_salary

		gross_salary = _get_gross_salary(self.employee)
		if gross_salary and same_category_total > gross_salary * cap_ratio:
			frappe.throw(
				_(
					"Total {0} deductions for {1} this month ({2}) cannot exceed {3}% of gross salary"
				).format(
					self.reason_category, self.employee, same_category_total, cap_ratio * 100
				)
			)
