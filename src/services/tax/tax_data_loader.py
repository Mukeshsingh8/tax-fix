"""
Tax Data Loader - Responsible for loading and managing German tax data.
Extracted from TaxKnowledgeService to follow single responsibility principle.
"""

from typing import List, Optional
from ...models.tax_knowledge import TaxRule, Deduction
from ...data.german_tax_data import get_german_tax_rules, get_german_deductions
from ...utils import to_dict
from ..base_service import BaseService


class TaxDataLoader(BaseService):
    """
    Handles loading and caching of German tax data.
    
    Responsibilities:
    - Load tax rules and deductions from data sources
    - Normalize and validate tax data
    - Provide cached access to tax data
    """
    
    def __init__(self):
        super().__init__("TaxDataLoader")
        self.tax_rules: List[TaxRule] = []
        self.deductions: List[Deduction] = []
        self._data_loaded = False
        self.load_tax_data()
    
    def load_tax_data(self) -> None:
        """Load German tax data into memory."""
        if self._data_loaded:
            self.logger.debug("Tax data already loaded, skipping")
            return
            
        self.log_operation_start("load_tax_data")
        try:
            # Load raw data
            self.tax_rules = get_german_tax_rules() or []
            source_deductions = get_german_deductions() or []

            # Process and normalize deductions
            self.deductions = self.normalize_deductions(source_deductions)
            
            self._data_loaded = True
            self.log_operation_success(
                "load_tax_data", 
                f"rules={len(self.tax_rules)}, deductions={len(self.deductions)}"
            )
            
        except Exception as e:
            self.log_operation_error("load_tax_data", e)
            self.tax_rules = []
            self.deductions = []
            self._data_loaded = False
    
    def normalize_deductions(self, source_deductions: List[Deduction]) -> List[Deduction]:
        """
        Normalize and validate deduction data.
        
        Args:
            source_deductions: Raw deduction data from data source
            
        Returns:
            List of normalized Deduction objects
        """
        normalized = []
        
        for d in source_deductions:
            try:
                dd = to_dict(d)
                meta = dict(dd.get("metadata") or {})

                # Preserve extra fields from source data into metadata
                for k in ("applicable_filing_status", "income_limit", "requirements", "rates", "per_day_rate"):
                    if k in dd and k not in meta:
                        meta[k] = dd[k]

                # Map common legacy keys -> typed fields where possible
                required_docs = dd.get("required_documents")
                if not required_docs and "requirements" in dd:
                    required_docs = dd["requirements"]

                # Create normalized deduction object
                normalized_deduction = Deduction(
                    id=dd["id"],
                    name=dd["name"],
                    description=dd.get("description", ""),
                    deduction_type=dd["deduction_type"],
                    category=dd["category"],
                    max_amount=dd.get("max_amount"),
                    min_amount=dd.get("min_amount"),
                    rate=dd.get("rate"),
                    required_documents=required_docs,
                    eligibility_criteria=dd.get("eligibility_criteria", []),
                    year_applicable=dd.get("year_applicable", 2024),  # Default to 2024
                    metadata=meta,
                    created_at=dd.get("created_at"),
                    updated_at=dd.get("updated_at"),
                )
                normalized.append(normalized_deduction)
                
            except Exception as e:
                self.logger.warning(f"Failed to normalize deduction {getattr(d, 'id', 'unknown')}: {e}")
                # Fall back to original if reconstruction fails
                normalized.append(d)
        
        return normalized
    
    def get_tax_rules(self, category: Optional[str] = None) -> List[TaxRule]:
        """
        Get tax rules, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of tax rules matching criteria
        """
        if not self._data_loaded:
            self.load_tax_data()
            
        if not category:
            return self.tax_rules.copy()
        
        return [rule for rule in self.tax_rules if rule.category == category]
    
    def get_deductions(self, category: Optional[str] = None) -> List[Deduction]:
        """
        Get deductions, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of deductions matching criteria
        """
        if not self._data_loaded:
            self.load_tax_data()
            
        if not category:
            return self.deductions.copy()
        
        return [ded for ded in self.deductions if ded.category == category]
    
    def reload_data(self) -> None:
        """Force reload of tax data from sources."""
        self._data_loaded = False
        self.load_tax_data()
    
    def get_stats(self) -> dict:
        """Get statistics about loaded tax data."""
        return {
            "tax_rules_count": len(self.tax_rules),
            "deductions_count": len(self.deductions),
            "data_loaded": self._data_loaded,
            "rule_categories": list(set(rule.category for rule in self.tax_rules)),
            "deduction_categories": list(set(ded.category for ded in self.deductions))
        }
