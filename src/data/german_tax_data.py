"""German tax knowledge data for the system (2024-focused, enriched)."""

from typing import List
from datetime import datetime
from ..models.tax_knowledge import TaxRule, Deduction, TaxCategory, DeductionType


# ---------------------------
# Tax Rules (Regeln)
# ---------------------------

def get_german_tax_rules() -> List[TaxRule]:
    """Get curated German tax rules (2024)."""
    return [
        TaxRule(
            id="rule_de_001",
            title="Grundfreibetrag 2024 (Basic Allowance)",
            description=(
                "Tax-free basic allowance (Grundfreibetrag): €11,604 for single filers, "
                "€23,208 for married couples filing jointly."
            ),
            category=TaxCategory.DEDUCTIONS,
            applicable_conditions=["German tax resident"],
            requirements=["File a German tax return if required"],
            limitations=["Cannot exceed taxable income"],
            examples=["Single: €11,604", "Married joint: €23,208"],
            year_applicable=2024,
            priority=1
        ),
        TaxRule(
            id="rule_de_002",
            title="Werbungskosten-Pauschbetrag (Employee Expenses Lump Sum)",
            description=(
                "Employee lump-sum deduction for work-related expenses (Werbungskosten-Pauschbetrag): "
                "€1,230 without receipts. Higher actual costs require documentation."
            ),
            category=TaxCategory.DEDUCTIONS,
            applicable_conditions=["Employment income"],
            requirements=["Actual costs require receipts if above the lump sum"],
            limitations=["Pauschbetrag is automatic if no higher itemization"],
            examples=["Tools, office supplies, professional dues, training"],
            year_applicable=2024,
            priority=2
        ),
        TaxRule(
            id="rule_de_003",
            title="Home-Office-Pauschale (Home Office Lump Sum)",
            description=(
                "Home office lump sum: €6 per day up to €1,260 per year if work is done primarily from home."
            ),
            category=TaxCategory.DEDUCTIONS,
            applicable_conditions=["Work performed from home on eligible days"],
            requirements=["Track days worked from home"],
            limitations=["Annual cap €1,260"],
            examples=["210 days × €6 = €1,260"],
            year_applicable=2024,
            priority=2
        ),
        TaxRule(
            id="rule_de_004",
            title="Pendlerpauschale (Commuter Allowance)",
            description=(
                "Distance allowance for commuting to work: €0.30 per km (one way) up to 20 km; "
                "€0.38 per km from the 21st kilometer onward."
            ),
            category=TaxCategory.DEDUCTIONS,
            applicable_conditions=["Commuting to regular workplace"],
            requirements=["Distance (one-way) and number of workdays"],
            limitations=["Applies per workday, one-way distance only"],
            examples=["25 km one way → 20 km × 0.30 + 5 km × 0.38 per day"],
            year_applicable=2024,
            priority=2
        ),
        TaxRule(
            id="rule_de_005",
            title="Sparer-Pauschbetrag (Savings Allowance)",
            description=(
                "Tax-free allowance for investment income: €1,000 (single) / €2,000 (married joint)."
            ),
            category=TaxCategory.INVESTMENTS,
            applicable_conditions=["Capital gains, interest, dividends"],
            requirements=["Investment income reported"],
            limitations=["Applies to investment income only"],
            examples=["Single investor with €900 dividends → fully covered"],
            year_applicable=2024,
            priority=3
        ),
        TaxRule(
            id="rule_de_006",
            title="Kinderfreibetrag (Child Allowance)",
            description=(
                "Tax-free allowance per child; interacts with child benefits. Typical benchmark amounts "
                "used for guidance (allowance plus related components)."
            ),
            category=TaxCategory.CREDITS,
            applicable_conditions=["Qualifying child"],
            requirements=["Child < 18, or other qualifying conditions"],
            limitations=["Per child, subject to eligibility and comparisons vs. Kindergeld"],
            examples=["Allowance per child; child care amounts may be separately deductible."],
            year_applicable=2024,
            priority=1
        ),
        TaxRule(
            id="rule_de_007",
            title="Sonderausgaben (Special Expenses)",
            description=(
                "Special expenses include health insurance, pension contributions, and donations; "
                "deductible within legal limits."
            ),
            category=TaxCategory.DEDUCTIONS,
            applicable_conditions=["Qualifying expense types"],
            requirements=["Receipts and documentation"],
            limitations=["Annual limits and caps apply"],
            examples=["Health insurance, Riester, charitable donations"],
            year_applicable=2024,
            priority=2
        ),
        TaxRule(
            id="rule_de_008",
            title="Riester-Rente (Riester Pension)",
            description="Tax benefits and government bonuses for Riester contracts; contributions up to €2,100 p.a.",
            category=TaxCategory.CREDITS,
            applicable_conditions=["Eligible taxpayer with Riester contract"],
            requirements=["Active Riester contract, required minimum contribution"],
            limitations=["€2,100 annual cap on deductible contributions"],
            examples=["Employee contributing 4% of gross income up to the cap"],
            year_applicable=2024,
            priority=3
        ),
        TaxRule(
            id="rule_de_009",
            title="Gesetzliche Krankenversicherung (Statutory Health Insurance)",
            description=(
                "Statutory health insurance: 14.6% general rate + additional rate (avg ~2.5%), "
                "split between employer and employee; contribution ceiling €66,150 p.a."
            ),
            category=TaxCategory.DEDUCTIONS,
            applicable_conditions=["Member of statutory health insurance"],
            requirements=["Employment income subject to social security"],
            limitations=["Assessment ceiling applies; private insurance different rules"],
            examples=["Employee share ~7.3% + ~1.25% additional (avg) up to ceiling"],
            year_applicable=2024,
            priority=1
        ),
        TaxRule(
            id="rule_de_010",
            title="Pflegeversicherung (Long-term Care Insurance)",
            description=(
                "Long-term care insurance: total ~3.6%, employee share ~1.8% (+0.25% surcharge if childless > 23). "
                "Same assessment ceiling as health insurance."
            ),
            category=TaxCategory.DEDUCTIONS,
            applicable_conditions=["Member of long-term care insurance"],
            requirements=["Employment income subject to social security"],
            limitations=["Assessment ceiling applies; childless surcharge where applicable"],
            examples=["Employee share 1.8% (+0.25% surcharge if applicable) up to ceiling"],
            year_applicable=2024,
            priority=1
        ),
        TaxRule(
            id="rule_de_011",
            title="Beitragsbemessungsgrenze (Contribution Assessment Ceiling)",
            description=(
                "Social security assessment ceiling (2024) for health/long-term care: €66,150 p.a. "
                "(income above is not subject to these contributions)."
            ),
            category=TaxCategory.DEDUCTIONS,
            applicable_conditions=["Employment income subject to social security"],
            requirements=["Statutory system participation"],
            limitations=["Applies to statutory schemes; private insurance differs"],
            examples=["Annual ceiling €66,150 (approx. €5,512.50 monthly)"],
            year_applicable=2024,
            priority=1
        ),
    ]


# ---------------------------
# Deductions (Aufwendungen)
# ---------------------------

def get_german_deductions() -> List[Deduction]:
    """Get enriched German tax deductions (2024)."""
    now = datetime.utcnow()
    return [
        Deduction(
            id="ded_de_001",
            name="Werbungskosten (Work-related Expenses)",
            description=(
                "Work-related expenses for employees, including commuting, equipment, and training. "
                "€1,230 lump sum without receipts; higher amounts require documentation."
            ),
            deduction_type=DeductionType.ABOVE_THE_LINE,
            category=TaxCategory.DEDUCTIONS,
            max_amount=10000.0,  # generic soft cap for guidance
            eligibility_criteria=["Employment income", "Work nexus required"],
            required_documents=["Receipts for amounts above €1,230"],
            common_expenses=["Commuting (Pendlerpauschale)", "Laptop", "Courses", "Professional dues"],
            tips=["Track receipts over the lump sum", "Use calendar for commuting days"],
            year_applicable=2024,
            is_commonly_used=True,
            metadata={
                "applicable_filing_status": ["single", "married_joint", "married_separate"],
                "notes": ["€1,230 lump sum (Pauschbetrag) applies automatically"]
            },
            created_at=now,
            updated_at=now
        ),
        Deduction(
            id="ded_de_002",
            name="Home-Office-Pauschale (Home Office Lump Sum)",
            description="€6 per home-office day, up to €1,260 per year.",
            deduction_type=DeductionType.HOME_OFFICE,
            category=TaxCategory.DEDUCTIONS,
            max_amount=1260.0,
            eligibility_criteria=["Regular home working days"],
            required_documents=["Day count or planner records"],
            common_expenses=["Electricity, internet (if itemizing instead)"],
            tips=["Keep a simple day log", "Combine with work equipment if applicable"],
            year_applicable=2024,
            is_commonly_used=True,
            metadata={
                "applicable_filing_status": ["single", "married_joint", "married_separate"],
                "per_day_rate": 6.0
            },
            created_at=now,
            updated_at=now
        ),
        Deduction(
            id="ded_de_003",
            name="Pendlerpauschale (Commuter Allowance)",
            description=(
                "€0.30/km (one way) up to 20 km; €0.38/km from the 21st km. Applies per workday."
            ),
            deduction_type=DeductionType.ABOVE_THE_LINE,
            category=TaxCategory.DEDUCTIONS,
            max_amount=15000.0,  # soft guidance; actual is distance × days
            eligibility_criteria=["Commute to primary workplace"],
            required_documents=["Distance proof, workday estimate"],
            common_expenses=["Fuel not required (flat-rate per km)"],
            tips=["Only one-way distance counts", "Multiply by actual workdays"],
            year_applicable=2024,
            is_commonly_used=True,
            metadata={
                "rates": {"first_20_km": 0.30, "from_21_km": 0.38},
                "applicable_filing_status": ["single", "married_joint", "married_separate"]
            },
            created_at=now,
            updated_at=now
        ),
        Deduction(
            id="ded_de_004",
            name="Sparer-Pauschbetrag (Savings Allowance)",
            description="Tax-free allowance for investment income: €1,000 (single) / €2,000 (married joint).",
            deduction_type=DeductionType.ABOVE_THE_LINE,
            category=TaxCategory.INVESTMENTS,
            max_amount=2000.0,  # highest allowance (married joint)
            eligibility_criteria=["Investment income (interest, dividends, gains)"],
            required_documents=["Annual tax certificate (Jahressteuerbescheinigung)"],
            common_expenses=["Bank fees generally not deductible against the allowance"],
            tips=["Use Freistellungsauftrag at your bank(s)"],
            year_applicable=2024,
            is_commonly_used=True,
            metadata={
                "single_amount": 1000.0,
                "married_joint_amount": 2000.0,
                "applicable_filing_status": ["single", "married_joint"]
            },
            created_at=now,
            updated_at=now
        ),
        Deduction(
            id="ded_de_005",
            name="Sonderausgaben (Special Expenses)",
            description=(
                "Special expenses such as health insurance, pension contributions, and charitable donations."
            ),
            deduction_type=DeductionType.ABOVE_THE_LINE,
            category=TaxCategory.DEDUCTIONS,
            max_amount=50000.0,  # broad guidance cap
            eligibility_criteria=["Qualifying expense categories"],
            required_documents=["Receipts, insurance statements"],
            common_expenses=["Charitable donations, church tax, pension contributions"],
            tips=["Aggregate annual statements for accuracy"],
            year_applicable=2024,
            is_commonly_used=True,
            metadata={"applicable_filing_status": ["single", "married_joint", "married_separate"]},
            created_at=now,
            updated_at=now
        ),
        Deduction(
            id="ded_de_006",
            name="Riester-Rente (Riester Pension)",
            description="Contributions up to €2,100 per year with possible government bonuses.",
            deduction_type=DeductionType.CREDIT,
            category=TaxCategory.RETIREMENT,
            max_amount=2100.0,
            eligibility_criteria=["Eligible contributor with valid Riester contract"],
            required_documents=["Riester provider annual statement"],
            common_expenses=["Annual contributions"],
            tips=["Ensure minimum contribution (4% of gross) to maximize benefits"],
            year_applicable=2024,
            is_commonly_used=False,
            metadata={"applicable_filing_status": ["single", "married_joint"]},
            created_at=now,
            updated_at=now
        ),
        Deduction(
            id="ded_de_007",
            name="Gesetzliche Krankenversicherung (Statutory Health Insurance)",
            description=(
                "Employee share ~7.3% + ~1.25% additional (avg) of income up to the €66,150 ceiling."
            ),
            deduction_type=DeductionType.ABOVE_THE_LINE,
            category=TaxCategory.DEDUCTIONS,
            max_amount=5000.0,  # typical employee annual ballpark at/near ceiling
            eligibility_criteria=["Member of statutory health insurance"],
            required_documents=["Lohnsteuerbescheinigung / payroll statements"],
            common_expenses=["Core and additional contribution rates"],
            tips=["Employer pays the other half; your share is deductible"],
            year_applicable=2024,
            is_commonly_used=True,
            metadata={
                "income_limit": 66150.0,
                "applicable_filing_status": ["single", "married_joint", "married_separate"]
            },
            created_at=now,
            updated_at=now
        ),
        Deduction(
            id="ded_de_008",
            name="Pflegeversicherung (Long-term Care Insurance)",
            description="Employee share ~1.8% (+0.25% childless surcharge > 23) up to the assessment ceiling.",
            deduction_type=DeductionType.ABOVE_THE_LINE,
            category=TaxCategory.DEDUCTIONS,
            max_amount=1200.0,  # typical employee annual ballpark
            eligibility_criteria=["Member of long-term care insurance"],
            required_documents=["Lohnsteuerbescheinigung / payroll statements"],
            common_expenses=["Employee share, potential surcharge if childless"],
            tips=["Surcharge applies if childless and older than 23"],
            year_applicable=2024,
            is_commonly_used=True,
            metadata={
                "income_limit": 66150.0,
                "applicable_filing_status": ["single", "married_joint", "married_separate"]
            },
            created_at=now,
            updated_at=now
        ),
        Deduction(
            id="ded_de_009",
            name="Private Krankenversicherung (Private Health Insurance)",
            description=(
                "Private health insurance premiums are generally deductible as Sonderausgaben "
                "(extent depends on policy coverage)."
            ),
            deduction_type=DeductionType.ABOVE_THE_LINE,
            category=TaxCategory.DEDUCTIONS,
            max_amount=50000.0,  # generous cap for guidance
            eligibility_criteria=["Private health insurance policy"],
            required_documents=["Annual premium statement from insurer"],
            common_expenses=["Base premium, eligible riders"],
            tips=["Actual deduction equals share of basic coverage components"],
            year_applicable=2024,
            is_commonly_used=False,
            metadata={"applicable_filing_status": ["single", "married_joint", "married_separate"]},
            created_at=now,
            updated_at=now
        ),
    ]


# ---------------------------
# Sample Data (optional dev fixtures)
# ---------------------------

def get_german_user_profiles() -> List[dict]:
    """Sample German user profiles for testing/personas."""
    return [
        {
            "user_id": "user_de_001",
            "employment_status": "employed",
            "filing_status": "single",
            "annual_income": 45000.0,
            "dependents": 0,
            "tax_goals": ["maximize_deductions", "understand_credits"],
            "risk_tolerance": "conservative",
            "tax_complexity_level": "beginner",
            "country": "Germany",
            "currency": "EUR",
            "health_insurance_type": "statutory",
            "age": 29
        },
        {
            "user_id": "user_de_002",
            "employment_status": "self_employed",
            "filing_status": "married_joint",
            "annual_income": 75000.0,
            "dependents": 2,
            "tax_goals": ["maximize_deductions", "optimize_retirement", "plan_for_future"],
            "risk_tolerance": "moderate",
            "tax_complexity_level": "intermediate",
            "country": "Germany",
            "currency": "EUR",
            "health_insurance_type": "statutory",
            "age": 38
        },
        {
            "user_id": "user_de_003",
            "employment_status": "retired",
            "filing_status": "married_joint",
            "annual_income": 35000.0,
            "dependents": 0,
            "tax_goals": ["reduce_tax_liability", "compliance_help"],
            "risk_tolerance": "conservative",
            "tax_complexity_level": "beginner",
            "country": "Germany",
            "currency": "EUR",
            "health_insurance_type": "private",
            "age": 67
        }
    ]


def get_german_conversations() -> List[dict]:
    """Sample German conversations for testing (kept small, illustrative)."""
    return [
        {
            "user_id": "user_de_001",
            "messages": [
                {
                    "role": "user",
                    "content": "Hallo! Ich bin neu in Deutschland und brauche Hilfe bei der Steuererklärung.",
                    "timestamp": "2024-01-15T10:00:00Z"
                },
                {
                    "role": "assistant",
                    "content": (
                        "Willkommen! Starten wir mit dem Grundfreibetrag (€11,604) "
                        "und deinen Werbungskosten. Arbeitest du bereits in Deutschland?"
                    ),
                    "timestamp": "2024-01-15T10:01:00Z"
                }
            ]
        },
        {
            "user_id": "user_de_002",
            "messages": [
                {
                    "role": "user",
                    "content": "Ich bin selbstständig und arbeite oft von zu Hause. Was kann ich absetzen?",
                    "timestamp": "2024-01-16T14:30:00Z"
                },
                {
                    "role": "assistant",
                    "content": (
                        "Für Selbstständige kommen viele Kosten in Frage: Home-Office-Pauschale (bis €1,260), "
                        "Arbeitsmittel, und Sonderausgaben wie Krankenversicherung. Hast du ein Arbeitszimmer?"
                    ),
                    "timestamp": "2024-01-16T14:31:00Z"
                }
            ]
        }
    ]
