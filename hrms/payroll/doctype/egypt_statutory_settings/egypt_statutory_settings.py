# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.model.document import Document


class EgyptStatutorySettings(Document):
	pass


def get_active_settings(date, company=None):
	"""Return the Egypt Statutory Settings record with the latest
	effective_from <= date. Prefers a company-specific record over a
	company-less default when both exist for the same date."""
	filters = {"effective_from": ["<=", date], "disabled": 0}

	name = None
	if company:
		name = frappe.db.get_value(
			"Egypt Statutory Settings",
			{**filters, "company": company},
			"name",
			order_by="effective_from desc",
		)
	if not name:
		name = frappe.db.get_value(
			"Egypt Statutory Settings",
			{**filters, "company": ["in", ["", None]]},
			"name",
			order_by="effective_from desc",
		)

	return frappe.get_doc("Egypt Statutory Settings", name) if name else None
