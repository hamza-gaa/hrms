# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.setup import delete_custom_fields

# anchor confirmed against Employee meta on 2026-08-13: date_of_birth


def setup():
	make_custom_fields()


def uninstall():
	custom_fields = get_custom_fields()
	delete_custom_fields(custom_fields)


def make_custom_fields(update=True):
	custom_fields = get_custom_fields()
	create_custom_fields(custom_fields, update=update)


def get_custom_fields():
	return {
		"Employee": [
			{
				"fieldname": "egypt_compliance_section",
				"label": "Egypt Compliance",
				"fieldtype": "Section Break",
				"insert_after": "date_of_birth",
				"collapsible": 1,
			},
			{
				"fieldname": "national_id",
				"label": "National ID",
				"fieldtype": "Data",
				"insert_after": "egypt_compliance_section",
				"translatable": 0,
			},
			{
				"fieldname": "national_id_issue_date",
				"label": "National ID Issue Date",
				"fieldtype": "Date",
				"insert_after": "national_id",
			},
			{
				"fieldname": "national_id_expiry_date",
				"label": "National ID Expiry Date",
				"fieldtype": "Date",
				"insert_after": "national_id_issue_date",
			},
			{
				"fieldname": "egypt_compliance_column_break_1",
				"fieldtype": "Column Break",
				"insert_after": "national_id_expiry_date",
			},
			{
				"fieldname": "social_insurance_number",
				"label": "Social Insurance Number",
				"fieldtype": "Data",
				"insert_after": "egypt_compliance_column_break_1",
				"translatable": 0,
				"description": "Presence of this field marks the employee as insured for leave eligibility and statutory fund headcount purposes.",
			},
			{
				"fieldname": "social_insurance_date",
				"label": "Social Insurance Date",
				"fieldtype": "Date",
				"insert_after": "social_insurance_number",
			},
			{
				"fieldname": "insurance_id",
				"label": "Insurance ID",
				"fieldtype": "Data",
				"insert_after": "social_insurance_date",
				"translatable": 0,
			},
			{
				"fieldname": "egypt_compliance_section_2",
				"label": "Identity & Travel Documents",
				"fieldtype": "Section Break",
				"insert_after": "insurance_id",
				"collapsible": 1,
			},
			{
				"fieldname": "passport_id",
				"label": "Passport ID",
				"fieldtype": "Data",
				"insert_after": "egypt_compliance_section_2",
				"translatable": 0,
			},
			{
				"fieldname": "passport_issue_date",
				"label": "Passport Issue Date",
				"fieldtype": "Date",
				"insert_after": "passport_id",
			},
			{
				"fieldname": "passport_expiry_date",
				"label": "Passport Expiry Date",
				"fieldtype": "Date",
				"insert_after": "passport_issue_date",
			},
			{
				"fieldname": "egypt_compliance_column_break_2",
				"fieldtype": "Column Break",
				"insert_after": "passport_expiry_date",
			},
			{
				"fieldname": "work_permit_start_date",
				"label": "Work Permit Start Date",
				"fieldtype": "Date",
				"insert_after": "egypt_compliance_column_break_2",
				"description": "For foreign employees only.",
			},
			{
				"fieldname": "work_permit_expiry_date",
				"label": "Work Permit Expiry Date",
				"fieldtype": "Date",
				"insert_after": "work_permit_start_date",
			},
			{
				"fieldname": "military_status",
				"label": "Military Status",
				"fieldtype": "Select",
				"options": "\nExempt\nCompleted\nPostponed\nServing",
				"insert_after": "work_permit_expiry_date",
			},
			{
				"fieldname": "egypt_compliance_section_3",
				"label": "Additional Personal Details",
				"fieldtype": "Section Break",
				"insert_after": "military_status",
				"collapsible": 1,
			},
			{
				"fieldname": "religion",
				"label": "Religion",
				"fieldtype": "Data",
				"insert_after": "egypt_compliance_section_3",
			},
			{
				"fieldname": "place_of_birth",
				"label": "Place of Birth",
				"fieldtype": "Data",
				"insert_after": "religion",
			},
			{
				"fieldname": "mothers_name",
				"label": "Mother's Name",
				"fieldtype": "Data",
				"insert_after": "place_of_birth",
			},
			{
				"fieldname": "egypt_compliance_column_break_3",
				"fieldtype": "Column Break",
				"insert_after": "mothers_name",
			},
			{
				"fieldname": "educational_specialization",
				"label": "Educational Specialization",
				"fieldtype": "Data",
				"insert_after": "egypt_compliance_column_break_3",
			},
			{
				"fieldname": "graduation_year",
				"label": "Graduation Year",
				"fieldtype": "Int",
				"insert_after": "educational_specialization",
			},
			{
				"fieldname": "is_person_of_determination",
				"label": "Is Person of Determination",
				"fieldtype": "Check",
				"insert_after": "graduation_year",
				"description": "Drives the extended leave tier, disability income tax slab selection, and higher personal tax exemption.",
			},
			{
				"fieldname": "relatives_section",
				"label": "Relatives Working at the Company",
				"fieldtype": "Section Break",
				"insert_after": "is_person_of_determination",
				"collapsible": 1,
			},
			{
				"fieldname": "relatives_at_company",
				"fieldtype": "Table",
				"options": "Egypt Employee Relative",
				"insert_after": "relatives_section",
			},
			{
				"fieldname": "family_data_section",
				"label": "Family Data",
				"fieldtype": "Section Break",
				"insert_after": "relatives_at_company",
				"collapsible": 1,
			},
			{
				"fieldname": "spouse_details",
				"fieldtype": "Table",
				"options": "Egypt Employee Spouse",
				"insert_after": "family_data_section",
			},
			{
				"fieldname": "children_details",
				"fieldtype": "Table",
				"options": "Egypt Employee Child",
				"insert_after": "spouse_details",
			},
		],
	}
