"""
Tax Search Engine - Handles intelligent search and retrieval of tax information.
Extracted from TaxKnowledgeService to follow single responsibility principle.
"""

from typing import Dict, List, Optional, Any, Tuple
from ...models.tax_knowledge import TaxRule, Deduction
from ...utils import to_dict
from ..base_service import BaseService
from .tax_data_loader import TaxDataLoader


class TaxSearchEngine(BaseService):
    """
    Intelligent search engine for tax rules and deductions.
    
    Responsibilities:
    - Semantic search across tax rules and deductions
    - Profile-aware result ranking
    - Relevance scoring and result filtering
    """
    
    def __init__(self, data_loader: TaxDataLoader):
        super().__init__("TaxSearchEngine")
        self.data_loader = data_loader
    
    def search_tax_rules(self, query: str) -> List[TaxRule]:
        """
        Search tax rules by query with intelligent matching.
        
        Args:
            query: Search query string
            
        Returns:
            List of relevant tax rules, ranked by relevance
        """
        self.log_operation_start("search_tax_rules", query=query[:50])
        
        try:
            rules = self.data_loader.get_tax_rules()
            if not rules:
                return []
            
            query_lower = query.lower()
            scored_rules = []
            
            for rule in rules:
                score = self._score_rule_relevance(rule, query_lower)
                if score > 0:
                    scored_rules.append((score, rule))
            
            # Sort by score descending and return top 10
            scored_rules.sort(key=lambda x: x[0], reverse=True)
            result = [rule for _, rule in scored_rules[:10]]
            
            self.log_operation_success("search_tax_rules", f"found={len(result)}")
            return result
            
        except Exception as e:
            self.log_operation_error("search_tax_rules", e)
            return []
    
    def search_deductions(self, query: str) -> List[Deduction]:
        """
        Search deductions by query with intelligent matching.
        
        Args:
            query: Search query string
            
        Returns:
            List of relevant deductions, ranked by relevance
        """
        self.log_operation_start("search_deductions", query=query[:50])
        
        try:
            deductions = self.data_loader.get_deductions()
            if not deductions:
                return []
            
            query_lower = query.lower()
            scored_deductions = []
            
            for deduction in deductions:
                score = self._score_deduction_relevance(deduction, query_lower)
                if score > 0:
                    scored_deductions.append((score, deduction))
            
            # Sort by score descending and return top 10
            scored_deductions.sort(key=lambda x: x[0], reverse=True)
            result = [ded for _, ded in scored_deductions[:10]]
            
            self.log_operation_success("search_deductions", f"found={len(result)}")
            return result
            
        except Exception as e:
            self.log_operation_error("search_deductions", e)
            return []
    
    def retrieve(self, query: str, profile: Optional[Dict[str, Any]] = None) -> Dict[str, List[Any]]:
        """
        Comprehensive search across rules and deductions with profile awareness.
        
        Args:
            query: Search query string
            profile: Optional user profile for personalized ranking
            
        Returns:
            Dictionary with 'rules' and 'deductions' keys containing relevant results
        """
        self.log_operation_start("retrieve", query=query[:50], has_profile=profile is not None)
        
        try:
            rules = self.search_tax_rules(query)
            deductions = self.search_deductions(query)
            
            # Apply profile-based boosting if profile provided
            if profile:
                deductions = self._apply_profile_boosting(deductions, profile)
            
            result = {"rules": rules, "deductions": deductions}
            
            self.log_operation_success(
                "retrieve", 
                f"rules={len(rules)}, deductions={len(deductions)}"
            )
            return result
            
        except Exception as e:
            self.log_operation_error("retrieve", e)
            return {"rules": [], "deductions": []}
    
    def _score_rule_relevance(self, rule: TaxRule, query_lower: str) -> float:
        """
        Score relevance of a tax rule for the query.
        
        Args:
            rule: Tax rule to score
            query_lower: Lowercase query string
            
        Returns:
            Relevance score (0.0 to 1.0+)
        """
        score = 0.0
        
        # Convert rule to dict for easier access
        rule_dict = to_dict(rule)
        
        # Name matching (highest weight)
        name = (rule_dict.get("name") or "").lower()
        if query_lower in name:
            score += 1.0
        
        # Description matching
        description = (rule_dict.get("description") or "").lower()
        if query_lower in description:
            score += 0.7
        
        # Category matching
        category = (rule_dict.get("category") or "").lower()
        if query_lower in category:
            score += 0.5
        
        # Rule type matching
        rule_type = (rule_dict.get("rule_type") or "").lower()
        if query_lower in rule_type:
            score += 0.3
        
        # Keywords matching
        keywords = rule_dict.get("keywords", [])
        for keyword in keywords:
            if query_lower in keyword.lower():
                score += 0.2
        
        return score
    
    def _score_deduction_relevance(self, deduction: Deduction, query_lower: str) -> float:
        """
        Score relevance of a deduction for the query.
        
        Args:
            deduction: Deduction to score
            query_lower: Lowercase query string
            
        Returns:
            Relevance score (0.0 to 1.0+)
        """
        score = 0.0
        
        # Convert deduction to dict for easier access
        ded_dict = to_dict(deduction)
        
        # Name matching (highest weight)
        name = (ded_dict.get("name") or "").lower()
        if query_lower in name:
            score += 1.0
        
        # Description matching
        description = (ded_dict.get("description") or "").lower()
        if query_lower in description:
            score += 0.7
        
        # Category matching
        category = (ded_dict.get("category") or "").lower()
        if query_lower in category:
            score += 0.5
        
        # Deduction type matching
        deduction_type = (ded_dict.get("deduction_type") or "").lower()
        if query_lower in deduction_type:
            score += 0.4
        
        # Eligibility criteria matching
        criteria = ded_dict.get("eligibility_criteria", [])
        for criterion in criteria:
            if query_lower in criterion.lower():
                score += 0.3
        
        return score
    
    def _apply_profile_boosting(self, deductions: List[Deduction], profile: Dict[str, Any]) -> List[Deduction]:
        """
        Apply profile-based boosting to deduction results.
        
        Args:
            deductions: List of deductions to boost
            profile: User profile for boosting context
            
        Returns:
            Reordered list of deductions with profile boosting applied
        """
        try:
            emp = str(profile.get("employment_status") or "").lower()
            deps = int(profile.get("dependents") or 0)
            
            def boost_score(d: Deduction) -> float:
                dd = to_dict(d)
                name = (dd.get("name") or "").lower()
                desc = (dd.get("description") or "").lower()
                boost = 0.0
                
                # Boost for self-employed business deductions
                if emp == "self_employed" and ("business" in name or "betrieb" in desc):
                    boost += 0.2
                
                # Boost for child-related deductions if user has dependents
                if deps > 0 and ("child" in name or "kinder" in desc):
                    boost += 0.2
                
                # Boost for employment-related deductions
                if emp == "employed" and ("work" in name or "arbeit" in desc):
                    boost += 0.1
                
                return boost
            
            # Sort deductions by boost score
            return sorted(deductions, key=boost_score, reverse=True)
            
        except Exception as e:
            self.logger.warning(f"Profile boosting failed: {e}")
            return deductions
