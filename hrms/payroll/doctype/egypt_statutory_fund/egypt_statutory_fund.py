# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

# minimum insured headcount required before a fund applies to a company,
# per docs/Payroll System.rtf.doc "Special Funds Calculation Screen" table
FUND_HEADCOUNT_THRESHOLDS = {
	"Emergency Relief Fund": 30,
	"Martyrs' Families Fund": 0,  # document states no explicit headcount minimum
	"Training and Rehabilitation Fund": 30,
	"Social, Health and Cultural Services Fund": 20,
}


class EgyptStatutoryFund(Document):
	def validate(self):
		if (
			self.period_start
			and self.period_end
			and getdate(self.period_end) < getdate(self.period_start)
		):
			frappe.throw(_("Period End cannot be before Period Start"))

	@frappe.whitelist()
	def compute(self):
		if self.status == "Paid":
			frappe.throw(
				_("Cannot recompute a fund contribution that has already been marked Paid")
			)

		self.insured_employee_count = self.get_insured_employee_count()

		threshold = FUND_HEADCOUNT_THRESHOLDS.get(self.fund_type, 0)
		if self.insured_employee_count < threshold:
			self.rate_or_amount = 0
			self.min_value = 0
			self.max_value = 0
			self.computed_contribution = 0
			self.status = "Draft"
			self.save()
			return

		self._apply_fund_rate()
		self.status = "Computed"
		self.save()

	def get_insured_employee_count(self):
		return frappe.db.count(
			"Employee",
			{
				"company": self.company,
				"status": "Active",
				"social_insurance_number": ["not in", ["", None]],
			},
		)

	def _apply_fund_rate(self):
		if self.fund_type == "Martyrs' Families Fund":
			# rate and inputs are self-contained (hardcoded rate + gross salary
			# total); no Egypt Statutory Settings fields are consumed, so no
			# settings record is required for this fund type
			gross_salary_total = self._get_total_gross_salary()
			self.rate_or_amount = 0.05  # 0.05% per document ("0.0005 of monthly gross salaries")
			self.min_value = 0
			self.max_value = 0
			self.computed_contribution = gross_salary_total * (self.rate_or_amount / 100)
			return

		from hrms.payroll.doctype.egypt_statutory_settings.egypt_statutory_settings import (
			get_active_settings,
		)

		settings = get_active_settings(self.period_start, company=self.company)
		if not settings:
			frappe.throw(
				_("No Egypt Statutory Settings found effective on or before {0}").format(
					self.period_start
				)
			)

		if self.fund_type == "Emergency Relief Fund":
			basic_wage_total = self._get_total_basic_salary()
			self.rate_or_amount = settings.emergency_relief_fund_rate or 0
			self.min_value = 0
			self.max_value = 0
			self.computed_contribution = basic_wage_total * (self.rate_or_amount / 100)
		elif self.fund_type == "Training and Rehabilitation Fund":
			self.rate_or_amount = settings.training_fund_rate or 0
			self.min_value = settings.training_fund_min or 0
			self.max_value = settings.training_fund_max or 0
			per_employee = (settings.min_insurance_wage or 0) * (self.rate_or_amount / 100)
			per_employee = max(per_employee, self.min_value)
			if self.max_value:
				per_employee = min(per_employee, self.max_value)
			self.computed_contribution = per_employee * self.insured_employee_count
		elif self.fund_type == "Social, Health and Cultural Services Fund":
			self.rate_or_amount = 0
			self.min_value = settings.cultural_services_fund_min or 0
			self.max_value = settings.cultural_services_fund_max or 0
			per_employee = self.min_value
			self.computed_contribution = per_employee * self.insured_employee_count

	def _get_total_basic_salary(self):
		from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
			get_assigned_salary_structure,
		)

		employees = frappe.get_all(
			"Employee",
			filters={
				"company": self.company,
				"status": "Active",
				"social_insurance_number": ["not in", ["", None]],
			},
			pluck="name",
		)
		total = 0
		for employee in employees:
			salary_structure = get_assigned_salary_structure(employee, self.period_start)
			if not salary_structure:
				continue
			amount = frappe.db.get_value(
				"Salary Detail",
				{
					"parent": salary_structure,
					"parentfield": "earnings",
					"salary_component": "Basic Salary",
				},
				"amount",
			)
			total += amount or 0
		return total

	def _get_total_gross_salary(self):
		from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
			get_assigned_salary_structure,
		)

		employees = frappe.get_all(
			"Employee",
			filters={
				"company": self.company,
				"status": "Active",
				"social_insurance_number": ["not in", ["", None]],
			},
			pluck="name",
		)
		total = 0
		for employee in employees:
			salary_structure = get_assigned_salary_structure(employee, self.period_start)
			if not salary_structure:
				continue
			amount = frappe.db.get_value(
				"Salary Detail",
				{
					"parent": salary_structure,
					"parentfield": "earnings",
					"salary_component": "Gross Salary",
				},
				"amount",
			)
			total += amount or 0
		return total
