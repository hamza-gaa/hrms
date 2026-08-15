import unicodedata
from datetime import date

import frappe
from frappe import _
from frappe.utils import ceil, floor, get_first_day, get_last_day, get_link_to_form, getdate, rounded


def sanitize_expression(string: str | None = None) -> str | None:
	"""
	Removes leading and trailing whitespace and merges multiline strings into a single line.

	Args:
	    string (str, None): The string expression to be sanitized. Defaults to None.

	Returns:
	    str or None: The sanitized string expression or None if the input string is None.

	Example:
	    expression = "\r\n    gross_pay > 10000\n    "
	    sanitized_expr = sanitize_expression(expression)

	"""

	if not string:
		return None

	parts = string.strip().splitlines()
	string = " ".join(parts)

	return string


COMPONENT_EVAL_GLOBALS = {
	"int": int,
	"float": float,
	"long": int,
	"round": round,
	"rounded": rounded,
	"date": date,
	"getdate": getdate,
	"get_first_day": get_first_day,
	"get_last_day": get_last_day,
	"ceil": ceil,
	"floor": floor,
	"min": min,
	"max": max,
}


def egypt_insurance_wage_bounds(date, company=None) -> tuple[float, float]:
	"""Return (min_insurance_wage, max_insurance_wage) from the active
	Egypt Statutory Settings record for the given date, or (0, 0) if none
	exists. Registered in COMPONENT_EVAL_GLOBALS so Salary Component
	formulas can call it directly by name."""
	from hrms.payroll.doctype.egypt_statutory_settings.egypt_statutory_settings import (
		get_active_settings,
	)

	settings = get_active_settings(date, company=company)
	if not settings:
		return (0, 0)
	return (settings.min_insurance_wage or 0, settings.max_insurance_wage or 0)


COMPONENT_EVAL_GLOBALS["egypt_insurance_wage_bounds"] = egypt_insurance_wage_bounds


def egypt_annual_bonus_amount(
	date_of_joining, company=None, date=None, insurance_wage=None
) -> float:
	"""Egypt Annual Bonus: max(rate% of Insurance Wage, minimum amount),
	only for employees with >= 1 full year of tenure as of January 1 of
	`date`'s year. Returns 0 if ineligible or no active settings exist.
	`insurance_wage` defaults to reading the "IW" component abbreviation
	from the eval globals cache if not passed explicitly (formula usage
	passes it as the IW variable already resolved in the eval context;
	direct Python callers, e.g. tests, pass it explicitly)."""
	from frappe.utils import date_diff, getdate

	from hrms.payroll.doctype.egypt_statutory_settings.egypt_statutory_settings import (
		get_active_settings,
	)

	date = getdate(date) if date else getdate()
	if not date_of_joining:
		return 0

	january_first = date.replace(month=1, day=1)
	years_of_service = date_diff(january_first, getdate(date_of_joining)) / 365.25
	if years_of_service < 1:
		return 0

	settings = get_active_settings(date, company=company)
	if not settings:
		return 0

	rate_based = (insurance_wage or 0) * (settings.annual_bonus_rate or 0) / 100
	return max(rate_based, settings.annual_bonus_minimum_amount or 0)


COMPONENT_EVAL_GLOBALS["egypt_annual_bonus_amount"] = egypt_annual_bonus_amount


def get_component_abbr_map() -> dict:
	"""Cached {salary_component_abbr: 0} map, seeded into the formula eval context
	so any component abbreviation referenced in a formula resolves (default 0).

	Cache key matches salary_slip.SALARY_COMPONENT_VALUES (shared entry, invalidated
	on Salary Component save)."""

	def _fetch_component_values():
		return {abbr: 0 for abbr in frappe.get_all("Salary Component", pluck="salary_component_abbr")}

	return frappe.cache().get_value("salary_component_values", generator=_fetch_component_values)


SALARY_SLIP_EVAL_DEFAULTS = {
	"gross_pay": 0,
	"net_pay": 0,
	"total_deduction": 0,
	"rounded_total": 0,
	"total_working_hours": 0,
	"hour_rate": 0,
	"year_to_date": 0,
	"month_to_date": 0,
	"gross_year_to_date": 0,
	"ctc": 0,
	"total_earnings": 0,
	"income_from_other_sources": 0,
	"non_taxable_earnings": 0,
	"deductions_before_tax_calculation": 0,
	"tax_exemption_declaration": 0,
	"standard_tax_exemption_amount": 0,
	"annual_taxable_amount": 0,
	"income_tax_deducted_till_date": 0,
	"future_income_tax_deductions": 0,
	"current_month_income_tax": 0,
	"total_income_tax": 0,
}


def get_component_eval_context(employee: str, ssa_as_dict: dict) -> frappe._dict:
	"""Build the base evaluation context for salary component formulas.

	Merges component abbreviation defaults, Salary Structure Assignment fields
	(base, variable, ...) and employee fields so that formulas can reference any
	of them by name.
	"""
	data = frappe._dict()
	data.update(get_component_abbr_map())
	data.update(SALARY_SLIP_EVAL_DEFAULTS)
	data.update(ssa_as_dict)
	data.update(frappe.get_cached_doc("Employee", employee).as_dict())
	return data


def _check_attributes(code: str) -> None:
	import ast

	from frappe.utils.safe_exec import UNSAFE_ATTRIBUTES

	unsafe_attrs = set(UNSAFE_ATTRIBUTES).union(["__"]) - {"format"}

	for attribute in unsafe_attrs:
		if attribute in code:
			raise SyntaxError(f'Illegal rule {frappe.bold(code)}. Cannot use "{attribute}"')

	BLOCKED_NODES = (ast.NamedExpr, ast.Lambda)

	tree = ast.parse(code, mode="eval")
	for node in ast.walk(tree):
		if isinstance(node, BLOCKED_NODES):
			raise SyntaxError(f"Operation not allowed: line {node.lineno} column {node.col_offset}")
		if isinstance(node, ast.Attribute) and isinstance(node.attr, str) and node.attr in UNSAFE_ATTRIBUTES:
			raise SyntaxError(f'Illegal rule {frappe.bold(code)}. Cannot use "{node.attr}"')


def _safe_eval(code: str, eval_globals: dict | None = None, eval_locals: dict | None = None):
	"""Safe eval for **trusted** salary component conditions and formulas only.

	Uses AST-based attribute checking instead of frappe.safe_eval to avoid
	recursion limit issues with the large/deeply-nested formulas some countries'
	payroll needs. It is a lighter (denylist-based) sandbox than frappe.safe_eval,
	so it is safe only for admin-authored salary-structure formulas, not arbitrary
	or end-user input. For anything else, use frappe.safe_eval.
	"""
	code = unicodedata.normalize("NFKC", code)

	_check_attributes(code)

	whitelisted_globals = {"int": int, "float": float, "long": int, "round": round}
	if not eval_globals:
		eval_globals = {}

	eval_globals["__builtins__"] = {}
	eval_globals.update(whitelisted_globals)
	return eval(code, eval_globals, eval_locals)  # nosemgrep


def throw_error_message(row, error, title, description=None):
	data = frappe._dict(
		{
			"doctype": row.parenttype,
			"name": row.parent,
			"doclink": get_link_to_form(row.parenttype, row.parent),
			"row_id": row.idx,
			"error": error,
			"title": title,
			"description": description or "",
		}
	)

	message = _(
		"Error while evaluating the {doctype} {doclink} at row {row_id}. <br><br> <b>Error:</b> {error} <br><br> <b>Hint:</b> {description}"
	).format(**data)

	frappe.throw(message, title=title)


@frappe.whitelist()
def get_payroll_settings_for_payment_days() -> dict:
	return frappe.get_cached_value(
		"Payroll Settings",
		None,
		[
			"payroll_based_on",
			"consider_unmarked_attendance_as",
			"include_holidays_in_total_working_days",
			"consider_marked_attendance_on_holidays",
		],
		as_dict=True,
	)
