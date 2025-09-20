"""Tax Knowledge Service for managing German tax data."""

from typing import Dict, List, Optional, Any
from dataclasses import asdict, is_dataclass

from ..models.tax_knowledge import (
    TaxRule,
    Deduction,
    TaxCategory,
    GermanTaxBreakdown,  # optional typed result
)
from ..data.german_tax_data import get_german_tax_rules, get_german_deductions
from ..core.logging import get_logger
from ..utils import val_to_str

logger = get_logger(__name__)


def _to_dict(obj: Any) -> Dict[str, Any]:
    """Convert pydantic/dataclass/objects to dict safely."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    # Pydantic v1/v2
    for fn_name in ("dict", "model_dump"):
        fn = getattr(obj, fn_name, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    if is_dataclass(obj):
        try:
            return asdict(obj)
        except Exception:
            pass
    # Very last resort best-effort
    try:
        return {k: getattr(obj, k) for k in dir(obj) if not k.startswith("_")}
    except Exception:
        return {}


class TaxKnowledgeService:
    """Service for managing tax knowledge and providing tax calculations."""

    def __init__(self):
        self.tax_rules: List[TaxRule] = []
        self.deductions: List[Deduction] = []
        self._load_tax_data()
        logger.info("Tax knowledge service initialized")

    # -----------------------------
    # Data loading
    # -----------------------------
    def _load_tax_data(self):
        """Load German tax data into memory."""
        try:
            self.tax_rules = get_german_tax_rules() or []
            source_deductions = get_german_deductions() or []

            fixed: List[Deduction] = []
            for d in source_deductions:
                dd = _to_dict(d)
                meta = dict(dd.get("metadata") or {})

                # Preserve extra fields from source data into metadata if present
                for k in ("applicable_filing_status", "income_limit", "requirements", "rates", "per_day_rate"):
                    if k in dd and k not in meta:
                        meta[k] = dd[k]

                # Map common legacy keys -> typed fields where possible
                required_docs = dd.get("required_documents")
                if not required_docs and "requirements" in dd:
                    required_docs = dd["requirements"]  # our model prefers required_documents

                try:
                    fixed.append(
                        Deduction(
                            id=dd["id"],
                            name=dd["name"],
                            description=dd.get("description", ""),
                            deduction_type=dd["deduction_type"],
                            category=dd["category"],
                            max_amount=dd.get("max_amount"),
                            percentage=dd.get("percentage"),
                            eligibility_criteria=dd.get("eligibility_criteria", []),
                            required_documents=required_docs or [],
                            common_expenses=dd.get("common_expenses", []),
                            tips=dd.get("tips", []),
                            year_applicable=dd.get("year_applicable"),
                            is_commonly_used=dd.get("is_commonly_used", False),
                            # If your Deduction model has these typed fields, they'll be used;
                            # otherwise they’ll be ignored and still live in metadata.
                            metadata=meta,
                            created_at=dd.get("created_at"),
                            updated_at=dd.get("updated_at"),
                        )
                    )
                except Exception:
                    # Fall back to original if reconstruction fails
                    fixed.append(d)

            self.deductions = fixed
            logger.info(f"Loaded {len(self.tax_rules)} tax rules and {len(self.deductions)} deductions")
        except Exception as e:
            logger.error(f"Error loading tax data: {e}")
            self.tax_rules = []
            self.deductions = []

    # -----------------------------
    # Retrieval APIs
    # -----------------------------
    def get_tax_rules(self, category: Optional[str] = None) -> List[TaxRule]:
        """Get tax rules, optionally filtered by category (string or TaxCategory)."""
        if category:
            cat_val = val_to_str(category)
            return [r for r in self.tax_rules if val_to_str(r.category) == cat_val]
        return self.tax_rules

    def get_deductions(self, category: Optional[str] = None) -> List[Deduction]:
        """Get deductions, optionally filtered by category (string or TaxCategory)."""
        if category:
            cat_val = val_to_str(category)
            return [d for d in self.deductions if val_to_str(d.category) == cat_val]
        return self.deductions

    def search_tax_rules(self, query: str) -> List[TaxRule]:
        """Lightweight keyword search over rules, ordered by priority then simple score."""
        q = (query or "").lower().strip()
        if not q:
            return sorted(self.tax_rules, key=lambda r: getattr(r, "priority", 0))

        scored: List[tuple[float, TaxRule]] = []
        tokens = [t for t in q.replace(",", " ").split() if t]
        for rule in self.tax_rules:
            s = 0.0
            rd = _to_dict(rule)
            title = (rd.get("title") or "").lower()
            desc = (rd.get("description") or "").lower()
            conds = " ".join(rd.get("applicable_conditions", [])).lower()
            for t in tokens:
                if t in title:
                    s += 0.5
                if t in desc:
                    s += 0.3
                if t in conds:
                    s += 0.2
            s += max(0.0, 1.0 - (getattr(rule, "priority", 0) * 0.1))  # priority bonus
            scored.append((s, rule))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored][:10]

    def search_deductions(self, query: str) -> List[Deduction]:
        """Lightweight keyword search over deductions, ordered by a simple score."""
        q = (query or "").lower().strip()
        if not q:
            return self.deductions[:10]

        tokens = [t for t in q.replace(",", " ").split() if t]
        scored: List[tuple[float, Deduction]] = []
        for d in self.deductions:
            dd = _to_dict(d)
            name = (dd.get("name") or "").lower()
            desc = (dd.get("description") or "").lower()
            cat = val_to_str(dd.get("category") or "")
            s = 0.0
            for t in tokens:
                if t in name:
                    s += 0.6
                if t in desc:
                    s += 0.3
                if t in str(cat):
                    s += 0.1
            if dd.get("is_commonly_used"):
                s += 0.2
            try:
                if int(dd.get("year_applicable") or 0) == 2024:
                    s += 0.1
            except Exception:
                pass
            scored.append((s, d))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored][:10]

    def retrieve(self, query: str, profile: Optional[Dict[str, Any]] = None) -> Dict[str, List[Any]]:
        """Convenience: returns top relevant rules & deductions for a query (optionally profile-aware)."""
        rules = self.search_tax_rules(query)
        deds = self.search_deductions(query)

        if profile:
            emp = str(profile.get("employment_status") or "").lower()
            deps = int(profile.get("dependents") or 0)

            def boost(d: Deduction) -> float:
                dd = _to_dict(d)
                name = (dd.get("name") or "").lower()
                desc = (dd.get("description") or "").lower()
                b = 0.0
                if emp == "self_employed" and ("business" in name or "betrieb" in desc):
                    b += 0.2
                if deps > 0 and ("child" in name or "kinder" in desc):
                    b += 0.2
                return b

            deds = sorted(deds, key=lambda d: boost(d), reverse=True)

        return {"rules": rules, "deductions": deds}

    # -----------------------------
    # German 2024 calculation (simplified)
    # -----------------------------
    def calculate_german_tax(
        self,
        income: float,
        filing_status: str,
        dependents: int = 0,
        health_insurance_type: str = "statutory",
        age: int = 30,
        has_children: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculate 2024 German tax + social contributions (simplified).

        Notes:
        - Uses basic allowance (Grundfreibetrag): €11,604 (single), €23,208 (married_joint).
        - Child allowance (Kinderfreibetrag) approximated at €5,460 per child.
        - Health & long-term care contributions use employee shares and the 2024 assessment ceiling (€66,150).
        - Income tax uses a simplified piecewise approximation (not the exact EStG formula).
        """
        try:
            income = float(income or 0.0)
            fs = (filing_status or "single").lower()

            basic_allowance = 23208 if fs == "married_joint" else 11604
            child_allowance = int(dependents or 0) * 5460

            # Social contributions (employee share)
            health = self._calculate_health_insurance_contributions(
                income, health_insurance_type, int(age or 30), bool(has_children)
            )
            care = self._calculate_long_term_care_contributions(
                income, int(age or 30), bool(has_children)
            )
            total_social = float(health.get("employee_contribution", 0.0)) + float(
                care.get("employee_contribution", 0.0)
            )

            total_allowances = basic_allowance + child_allowance + total_social
            taxable_income = max(0.0, income - total_allowances)

            # Simplified progressive tax
            t = taxable_income
            if t <= 11604:
                tax_liability = 0.0
            elif t <= 66760:
                tax_liability = 0.14 * (t - 11604)
            elif t <= 277825:
                tax_liability = (0.14 * (66760 - 11604)) + 0.42 * (t - 66760)
            else:
                tax_liability = (
                    (0.14 * (66760 - 11604))
                    + (0.42 * (277825 - 66760))
                    + 0.45 * (t - 277825)
                )

            solidarity_surcharge = tax_liability * 0.055  # simplified
            church_tax = tax_liability * 0.08  # 8% default assumption
            total_tax = tax_liability + solidarity_surcharge + church_tax

            total_deductions = total_tax + total_social
            net_income = income - total_deductions

            return {
                "gross_income": income,
                "basic_allowance": basic_allowance,
                "child_allowance": child_allowance,
                "health_insurance_contribution": float(health.get("employee_contribution", 0.0)),
                "long_term_care_contribution": float(care.get("employee_contribution", 0.0)),
                "total_social_contributions": total_social,
                "total_allowances": total_allowances,
                "taxable_income": taxable_income,
                "income_tax": tax_liability,
                "solidarity_surcharge": solidarity_surcharge,
                "church_tax": church_tax,
                "total_tax": total_tax,
                "total_deductions": total_deductions,
                "effective_tax_rate": (total_tax / income * 100) if income > 0 else 0.0,
                "total_effective_rate": (total_deductions / income * 100) if income > 0 else 0.0,
                "net_income": net_income,
                "health_insurance_details": health,
                "long_term_care_details": care,
            }
        except Exception as e:
            logger.error(f"Error calculating German tax: {e}")
            return {}

    def calculate_german_tax_typed(
        self,
        income: float,
        filing_status: str,
        dependents: int = 0,
        health_insurance_type: str = "statutory",
        age: int = 30,
        has_children: bool = False,
    ) -> GermanTaxBreakdown:
        """Typed convenience wrapper around calculate_german_tax()."""
        raw = self.calculate_german_tax(
            income=income,
            filing_status=filing_status,
            dependents=dependents,
            health_insurance_type=health_insurance_type,
            age=age,
            has_children=has_children,
        )
        return GermanTaxBreakdown(
            gross_income=raw.get("gross_income", 0.0),
            basic_allowance=raw.get("basic_allowance", 0.0),
            child_allowance=raw.get("child_allowance", 0.0),
            total_allowances=raw.get("total_allowances", 0.0),
            health_insurance_contribution=raw.get("health_insurance_contribution", 0.0),
            long_term_care_contribution=raw.get("long_term_care_contribution", 0.0),
            total_social_contributions=raw.get("total_social_contributions", 0.0),
            taxable_income=raw.get("taxable_income", 0.0),
            income_tax=raw.get("income_tax", 0.0),
            solidarity_surcharge=raw.get("solidarity_surcharge", 0.0),
            church_tax=raw.get("church_tax", 0.0),
            total_tax=raw.get("total_tax", 0.0),
            total_deductions=raw.get("total_deductions", 0.0),
            effective_tax_rate=raw.get("effective_tax_rate", 0.0),
            total_effective_rate=raw.get("total_effective_rate", 0.0),
            net_income=raw.get("net_income", 0.0),
            health_insurance_details=raw.get("health_insurance_details", {}),
            long_term_care_details=raw.get("long_term_care_details", {}),
        )

    # -----------------------------
    # Deduction relevance & savings
    # -----------------------------
    def get_relevant_deductions(self, user_profile: Dict[str, Any]) -> List[Deduction]:
        """
        Return deductions plausibly relevant to the user profile.

        Uses metadata.applicable_filing_status and simple profile-based signals.
        """
        try:
            if not user_profile:
                return self.deductions[:5]

            filing = str(user_profile.get("filing_status") or "").lower()
            emp = str(user_profile.get("employment_status") or "").lower()
            deps = int(user_profile.get("dependents") or 0)

            relevant: List[Deduction] = []
            for d in self.deductions:
                dd = _to_dict(d)
                meta = dd.get("metadata") or {}
                applies = True

                afs = [str(x).lower() for x in (meta.get("applicable_filing_status") or [])]
                if afs:
                    applies = filing in afs
                if not applies:
                    continue

                cat = val_to_str(dd.get("category") or "")
                name = (dd.get("name") or "").lower()
                desc = (dd.get("description") or "").lower()

                # Profile-aligned inclusion
                if emp in ("employed", "self_employed") and "deductions" in str(cat):
                    relevant.append(d)
                elif deps > 0 and ("credit" in str(cat) or "kinder" in desc or "child" in name):
                    relevant.append(d)
                elif "retire" in desc or "riester" in name:
                    relevant.append(d)

            # De-dup, keep order
            seen = set()
            out: List[Deduction] = []
            for d in relevant:
                if d.id not in seen:
                    out.append(d)
                    seen.add(d.id)
            return out[:8]
        except Exception as e:
            logger.error(f"Error getting relevant deductions: {e}")
            return []

    def calculate_deduction_savings(self, income: float, deductions: List[Deduction]) -> Dict[str, Any]:
        """Very rough savings estimate: sum max amounts and apply an approximate marginal rate."""
        try:
            income = float(income or 0.0)
            total_deductions = 0.0
            breakdown: Dict[str, Dict[str, Any]] = {}

            for d in deductions or []:
                dd = _to_dict(d)
                max_amount = dd.get("max_amount") or 0.0
                try:
                    amt = float(max_amount or 0.0)
                except Exception:
                    amt = 0.0
                total_deductions += max(0.0, amt)
                breakdown[dd.get("name", "Deduction")] = {
                    "amount": amt,
                    "description": dd.get("description", ""),
                }

            # Super-simplified marginal rate guess
            if income > 277825:
                marginal_rate = 0.45
            elif income > 66760:
                marginal_rate = 0.42
            elif income > 11604:
                marginal_rate = 0.14
            else:
                marginal_rate = 0.0

            tax_savings = total_deductions * marginal_rate

            return {
                "total_deductions": total_deductions,
                "deduction_breakdown": breakdown,
                "estimated_tax_savings": tax_savings,
                "marginal_tax_rate": marginal_rate,
            }
        except Exception as e:
            logger.error(f"Error calculating deduction savings: {e}")
            return {}

    # -----------------------------
    # Social contributions (helpers)
    # -----------------------------
    def _calculate_health_insurance_contributions(
        self, income: float, insurance_type: str, age: int, has_children: bool
    ) -> Dict[str, Any]:
        """Employee-side health insurance contributions."""
        try:
            contribution_ceiling = 66150.0  # 2024
            base = min(float(income or 0.0), contribution_ceiling)

            if (insurance_type or "statutory").lower() == "statutory":
                general_rate = 0.146
                additional_rate = 0.025  # average
                employee_general_rate = general_rate / 2.0  # 7.3%
                employee_additional_rate = additional_rate / 2.0  # 1.25%

                general_contribution = base * employee_general_rate
                additional_contribution = base * employee_additional_rate
                total_employee = general_contribution + additional_contribution
                employer_contribution = total_employee  # split 50/50 (approx)

                return {
                    "insurance_type": "statutory",
                    "income_subject_to_contribution": base,
                    "general_rate": general_rate,
                    "additional_rate": additional_rate,
                    "employee_general_contribution": general_contribution,
                    "employee_additional_contribution": additional_contribution,
                    "employee_contribution": total_employee,
                    "employer_contribution": employer_contribution,
                    "total_contribution": total_employee + employer_contribution,
                    "contribution_ceiling_applied": float(income or 0.0) > contribution_ceiling,
                }
            else:
                # Private insurance (very rough proxy)
                base_rate = 0.12
                age_factor = 1.0 + max(0, age - 30) * 0.01
                family_factor = 1.5 if has_children else 1.0
                total = base * base_rate * age_factor * family_factor
                return {
                    "insurance_type": "private",
                    "income_subject_to_contribution": base,
                    "base_rate": base_rate,
                    "age_factor": age_factor,
                    "family_factor": family_factor,
                    "employee_contribution": total,
                    "employer_contribution": 0.0,
                    "total_contribution": total,
                    "contribution_ceiling_applied": float(income or 0.0) > contribution_ceiling,
                    "note": "Private insurance varies by provider and coverage.",
                }
        except Exception as e:
            logger.error(f"Error calculating health insurance contributions: {e}")
            return {"employee_contribution": 0.0, "employer_contribution": 0.0, "total_contribution": 0.0}

    def _calculate_long_term_care_contributions(
        self, income: float, age: int, has_children: bool
    ) -> Dict[str, Any]:
        """Employee-side long-term care insurance contributions."""
        try:
            contribution_ceiling = 66150.0  # 2024
            base = min(float(income or 0.0), contribution_ceiling)

            base_rate_total = 0.036  # 3.6% total
            employee_rate = 0.018    # 1.8% employee
            surcharge_rate = 0.0025  # +0.25% if childless over 23
            surcharge_applied = age > 23 and not has_children
            if surcharge_applied:
                employee_rate += surcharge_rate

            employee_contrib = base * employee_rate
            employer_contrib = base * 0.018
            total = employee_contrib + employer_contrib

            return {
                "income_subject_to_contribution": base,
                "base_rate": base_rate_total,
                "employee_rate": employee_rate,
                "surcharge_applied": surcharge_applied,
                "surcharge_rate": surcharge_rate if surcharge_applied else 0.0,
                "employee_contribution": employee_contrib,
                "employer_contribution": employer_contrib,
                "total_contribution": total,
                "contribution_ceiling_applied": float(income or 0.0) > contribution_ceiling,
            }
        except Exception as e:
            logger.error(f"Error calculating long-term care contributions: {e}")
            return {"employee_contribution": 0.0, "employer_contribution": 0.0, "total_contribution": 0.0}
