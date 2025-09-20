"""
Tax-specific formatting utilities.
"""

from typing import Dict, Any, List, Optional
from .data_conversion import format_currency


def format_deductions_section(deductions: List[Dict[str, Any]]) -> List[str]:
    """Format deductions into readable strings."""
    if not deductions:
        return []
    
    parts = ["\n**Relevant deductions you could consider:**"]
    for d in deductions[:3]:
        row = f"• {d.get('name')}: {d.get('description')}"
        if d.get("max_amount") is not None:
            try:
                row += f" (max {format_currency(d['max_amount'])})"
            except Exception:
                pass
        parts.append(row)
    
    return parts


def format_tax_calculation_section(calculations: Dict[str, Any]) -> List[str]:
    """Format tax calculations into readable sections."""
    if not calculations:
        return []
    
    parts = ["\n**German tax & social security overview (2024):**"]
    
    def add_value(label: str, key: str, money: bool = True, pct: bool = False):
        if key in calculations and calculations[key] is not None:
            val = calculations[key]
            if pct:
                try:
                    parts.append(f"{label}: {float(val):.1f}%")
                except Exception:
                    parts.append(f"{label}: {val}")
            elif money:
                parts.append(f"{label}: {format_currency(val)}")
            else:
                parts.append(f"{label}: {val}")

    # Income
    add_value("Gross income", "gross_income")
    
    # Social security
    parts.append("\n**Social security contributions:**")
    add_value("Health insurance (Krankenversicherung)", "health_insurance_contribution")
    add_value("Long-term care (Pflegeversicherung)", "long_term_care_contribution")
    add_value("Total social security", "total_social_contributions")

    # Tax allowances
    parts.append("\n**Tax allowances:**")
    add_value("Basic allowance (Grundfreibetrag)", "basic_allowance")
    if calculations.get("child_allowance", 0) > 0:
        add_value("Child allowance (Kinderfreibetrag)", "child_allowance")

    # Tax calculation
    parts.append("\n**Tax calculation:**")
    add_value("Taxable income", "taxable_income")
    add_value("Income tax", "income_tax")
    add_value("Solidarity surcharge", "solidarity_surcharge")
    add_value("Church tax", "church_tax")
    add_value("Total tax liability", "total_tax")

    # Summary
    parts.append("\n**Summary:**")
    add_value("Total deductions (tax + social)", "total_deductions")
    add_value("Tax rate", "effective_tax_rate", money=False, pct=True)
    add_value("Total effective rate", "total_effective_rate", money=False, pct=True)
    add_value("Net income", "net_income")

    return parts


def format_insurance_details(calculations: Dict[str, Any]) -> List[str]:
    """Format insurance details section."""
    parts = []
    
    # Health insurance details
    if "health_insurance_details" in calculations:
        hid = calculations["health_insurance_details"] or {}
        parts.append("\n**Health insurance details:**")
        insurance_type = (hid.get("insurance_type") or "statutory").title()
        parts.append(f"Type: {insurance_type}")
        
        if hid.get("contribution_ceiling_applied"):
            parts.append("Contribution assessment ceiling applied: €66,150")
            
        if hid.get("insurance_type") == "statutory":
            try:
                general_rate = float(hid.get('general_rate', 0)) * 100
                additional_rate = float(hid.get('additional_rate', 0)) * 100
                parts.append(f"General rate: {general_rate:.1f}%")
                parts.append(f"Additional rate: {additional_rate:.1f}%")
            except Exception:
                pass

    # Long-term care details
    if "long_term_care_details" in calculations:
        lcd = calculations["long_term_care_details"] or {}
        if lcd.get("surcharge_applied"):
            parts.append("Long-term care surcharge: +0.25% (childless over 23)")

    return parts


def format_deduction_savings(calculations: Dict[str, Any]) -> List[str]:
    """Format deduction savings section."""
    if "deduction_savings" not in calculations:
        return []
    
    ds = calculations["deduction_savings"]
    parts = ["\n**Potential tax savings from deductions:**"]
    
    try:
        total_deductions = format_currency(ds.get('total_deductions', 0))
        tax_savings = format_currency(ds.get('estimated_tax_savings', 0))
        parts.append(f"Total deductions: {total_deductions}")
        parts.append(f"Estimated tax savings: {tax_savings}")
    except Exception:
        pass
    
    return parts
