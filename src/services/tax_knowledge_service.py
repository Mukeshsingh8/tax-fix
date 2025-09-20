"""
Simplified Tax Knowledge Service - Orchestrates specialized tax services.
This replaces the monolithic TaxKnowledgeService with a focused orchestrator.
"""

from typing import Dict, List, Optional, Any
from ..models.tax_knowledge import TaxRule, Deduction
from .base_service import BaseService
from .tax.tax_data_loader import TaxDataLoader
from .tax.tax_search_engine import TaxSearchEngine
from .tax.tax_calculation_engine import TaxCalculationEngine


class TaxKnowledgeService(BaseService):
    """
    Simplified tax knowledge service that orchestrates specialized components.
    
    This service follows the orchestrator pattern, delegating to specialized services:
    - TaxDataLoader: Manages tax data loading and caching
    - TaxSearchEngine: Handles intelligent search and retrieval
    - TaxCalculationEngine: Performs tax calculations and computations
    
    Benefits of this approach:
    - Single Responsibility Principle: Each service has one clear purpose
    - Easier testing: Can test components in isolation
    - Better maintainability: Changes are localized to specific services
    - Improved performance: Can optimize each service independently
    """
    
    def __init__(self):
        super().__init__("TaxKnowledgeService")
        
        # Initialize specialized services
        self.data_loader = TaxDataLoader()
        self.search_engine = TaxSearchEngine(self.data_loader)
        self.calculation_engine = TaxCalculationEngine()
        
        self.logger.info("Tax knowledge service initialized with specialized components")
    
    # -----------------------------
    # Data Access Methods
    # -----------------------------
    
    def get_tax_rules(self, category: Optional[str] = None) -> List[TaxRule]:
        """Get tax rules, optionally filtered by category."""
        return self.data_loader.get_tax_rules(category)
    
    def get_deductions(self, category: Optional[str] = None) -> List[Deduction]:
        """Get deductions, optionally filtered by category."""
        return self.data_loader.get_deductions(category)
    
    def reload_tax_data(self) -> None:
        """Force reload of tax data from sources."""
        self.data_loader.reload_data()
    
    def get_data_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded tax data."""
        return self.data_loader.get_stats()
    
    # -----------------------------
    # Search Methods
    # -----------------------------
    
    def search_tax_rules(self, query: str) -> List[TaxRule]:
        """Search tax rules by query with intelligent matching."""
        return self.search_engine.search_tax_rules(query)
    
    def search_deductions(self, query: str) -> List[Deduction]:
        """Search deductions by query with intelligent matching."""
        return self.search_engine.search_deductions(query)
    
    def retrieve(self, query: str, profile: Optional[Dict[str, Any]] = None) -> Dict[str, List[Any]]:
        """
        Comprehensive search across rules and deductions with profile awareness.
        
        Args:
            query: Search query string
            profile: Optional user profile for personalized ranking
            
        Returns:
            Dictionary with 'rules' and 'deductions' keys containing relevant results
        """
        return self.search_engine.retrieve(query, profile)
    
    # -----------------------------
    # Calculation Methods
    # -----------------------------
    
    def calculate_german_tax(
        self,
        income: float,
        filing_status: str = "single",
        dependents: int = 0,
        health_insurance_type: str = "statutory",
        age: int = 30,
        has_children: bool = False,
    ) -> Dict[str, Any]:
        """Calculate comprehensive German tax breakdown."""
        return self.calculation_engine.calculate_german_tax(
            income=income,
            filing_status=filing_status,
            dependents=dependents,
            health_insurance_type=health_insurance_type,
            age=age,
            has_children=has_children
        )
    
    def calculate_net_income(self, gross_income: float, **kwargs) -> float:
        """Quick calculation of net income from gross."""
        return self.calculation_engine.calculate_net_income(gross_income, **kwargs)
    
    def calculate_tax_savings(self, current_income: float, deduction_amount: float) -> Dict[str, float]:
        """Calculate potential tax savings from a deduction."""
        return self.calculation_engine.calculate_tax_savings(current_income, deduction_amount)
    
    # -----------------------------
    # Combined Operations
    # -----------------------------
    
    def get_personalized_tax_advice(
        self, 
        query: str, 
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get comprehensive tax advice combining search and calculations.
        
        Args:
            query: User's tax question
            profile: User profile with income, status, etc.
            
        Returns:
            Combined advice with relevant rules, deductions, and calculations
        """
        self.log_operation_start("get_personalized_tax_advice", query=query[:50])
        
        try:
            # Search for relevant information
            search_results = self.search_engine.retrieve(query, profile)
            
            # Perform calculations if profile has sufficient data
            calculations = None
            if profile.get("annual_income"):
                calculations = self.calculate_german_tax(
                    income=profile["annual_income"],
                    filing_status=profile.get("filing_status", "single"),
                    dependents=profile.get("dependents", 0),
                    age=profile.get("age", 30),
                    has_children=profile.get("dependents", 0) > 0
                )
            
            # Calculate potential savings for relevant deductions
            deduction_savings = []
            if calculations and search_results.get("deductions"):
                for deduction in search_results["deductions"][:3]:  # Top 3 deductions
                    if hasattr(deduction, 'max_amount') and deduction.max_amount:
                        savings = self.calculate_tax_savings(
                            profile["annual_income"], 
                            deduction.max_amount
                        )
                        deduction_savings.append({
                            "deduction_name": deduction.name,
                            "max_amount": deduction.max_amount,
                            **savings
                        })
            
            result = {
                "query": query,
                "search_results": search_results,
                "tax_calculation": calculations,
                "deduction_savings": deduction_savings,
                "advice_type": "comprehensive" if calculations else "informational"
            }
            
            self.log_operation_success(
                "get_personalized_tax_advice",
                f"rules={len(search_results.get('rules', []))}, deductions={len(search_results.get('deductions', []))}"
            )
            
            return result
            
        except Exception as e:
            self.log_operation_error("get_personalized_tax_advice", e)
            return {
                "query": query,
                "search_results": {"rules": [], "deductions": []},
                "tax_calculation": None,
                "deduction_savings": [],
                "advice_type": "error",
                "error": str(e)
            }
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get health status of all tax knowledge components."""
        return {
            "data_loader": {
                "status": "healthy" if self.data_loader._data_loaded else "error",
                "stats": self.data_loader.get_stats()
            },
            "search_engine": {
                "status": "healthy",
                "service_name": self.search_engine.service_name
            },
            "calculation_engine": {
                "status": "healthy", 
                "service_name": self.calculation_engine.service_name
            },
            "overall_status": "healthy" if self.data_loader._data_loaded else "degraded"
        }
