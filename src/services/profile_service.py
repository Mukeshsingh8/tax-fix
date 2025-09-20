"""
Unified Profile Service - Consolidates profile management operations.
Combines ProfileNormalizer and ProfileValidator for better cohesion.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import re

from ..models.user import EmploymentStatus, FilingStatus, UserProfile
from ..core.helpers import extract_numbers
from ..utils import (
    normalize_employment_status, normalize_filing_status, 
    normalize_risk_tolerance, normalize_tax_goals, safe_float, safe_int,
    to_dict
)
from .base_service import BaseService, ValidationMixin


class ProfileService(BaseService, ValidationMixin):
    """
    Unified service for profile management, normalization, and validation.
    
    Consolidates the responsibilities of ProfileNormalizer and ProfileValidator:
    - Extract profile information from text
    - Normalize profile data to standard formats
    - Validate profile updates for consistency
    - Handle profile CRUD operations
    """
    
    def __init__(self, llm_service=None, database_service=None):
        super().__init__("ProfileService")
        self.llm_service = llm_service
        self.database_service = database_service
    
    # =============================
    # Profile Information Extraction
    # =============================
    
    async def extract_profile_info(self, text: str) -> Dict[str, Any]:
        """
        Extract profile information from user message text.
        
        Args:
            text: User message text to analyze
            
        Returns:
            Dictionary of extracted profile information
        """
        self.log_operation_start("extract_profile_info", text_length=len(text))
        
        try:
            extracted = {}
            text_lower = text.lower()
            
            # Extract income information
            income_info = self._extract_income_info(text_lower, text)
            if income_info:
                extracted.update(income_info)
            
            # Extract employment status
            employment = self._extract_employment_status(text_lower)
            if employment:
                extracted["employment_status"] = employment
            
            # Extract filing status
            filing = self._extract_filing_status(text_lower)
            if filing:
                extracted["filing_status"] = filing
            
            # Extract dependents
            dependents = self._extract_dependents(text_lower, text)
            if dependents is not None:
                extracted["dependents"] = dependents
            
            # Extract tax goals
            goals = self._extract_tax_goals(text_lower)
            if goals:
                extracted["tax_goals"] = goals
            
            # Extract risk tolerance
            risk = self._extract_risk_tolerance(text_lower)
            if risk:
                extracted["risk_tolerance"] = risk
            
            self.log_operation_success("extract_profile_info", f"extracted={len(extracted)} fields")
            return extracted
            
        except Exception as e:
            self.log_operation_error("extract_profile_info", e)
            return {}
    
    def _extract_income_info(self, text_lower: str, original_text: str) -> Dict[str, Any]:
        """Extract income-related information."""
        info = {}
        
        # Income patterns
        income_patterns = [
            r"(?:earn|make|income|salary).*?€?(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)",
            r"€(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)\s*(?:per\s+year|annually|yearly)",
            r"(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)\s*€?\s*(?:per\s+year|annually|yearly|income)"
        ]
        
        for pattern in income_patterns:
            match = re.search(pattern, text_lower)
            if match:
                income_str = match.group(1).replace(",", "").replace(" ", "")
                income = safe_float(income_str)
                if income and 10000 <= income <= 500000:  # Reasonable income range
                    info["annual_income"] = income
                    break
        
        return info
    
    def _extract_employment_status(self, text_lower: str) -> Optional[str]:
        """Extract employment status from text."""
        status_patterns = {
            "employed": ["employed", "work for", "employee", "job at"],
            "self_employed": ["self-employed", "freelancer", "own business", "entrepreneur", "consultant"],
            "unemployed": ["unemployed", "jobless", "between jobs"],
            "student": ["student", "studying", "university", "college"],
            "retired": ["retired", "pension", "retiree"]
        }
        
        for status, keywords in status_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                return normalize_employment_status(status)
        
        return None
    
    def _extract_filing_status(self, text_lower: str) -> Optional[str]:
        """Extract filing status from text."""
        if any(word in text_lower for word in ["married", "spouse", "husband", "wife"]):
            if "separate" in text_lower:
                return normalize_filing_status("married_separately")
            else:
                return normalize_filing_status("married_jointly")
        elif any(word in text_lower for word in ["single", "unmarried", "not married"]):
            return normalize_filing_status("single")
        
        return None
    
    def _extract_dependents(self, text_lower: str, original_text: str) -> Optional[int]:
        """Extract number of dependents."""
        dependents_patterns = [
            r"(\d+)\s*(?:child|children|kid|kids|dependent|dependents)",
            r"(?:have|with)\s*(\d+)\s*(?:child|children|kid|kids)"
        ]
        
        for pattern in dependents_patterns:
            match = re.search(pattern, text_lower)
            if match:
                count = safe_int(match.group(1))
                if count is not None and 0 <= count <= 10:  # Reasonable range
                    return count
        
        # Check for keywords indicating children
        if any(word in text_lower for word in ["no children", "no kids", "childless"]):
            return 0
        elif any(word in text_lower for word in ["child", "children", "kid", "kids"]) and "no" not in text_lower:
            return 1  # Default assumption if children mentioned without number
        
        return None
    
    def _extract_tax_goals(self, text_lower: str) -> List[str]:
        """Extract tax goals from text."""
        goals = []
        goal_patterns = {
            "minimize_taxes": ["minimize tax", "reduce tax", "lower tax", "save on tax"],
            "maximize_refund": ["maximize refund", "bigger refund", "larger refund"],
            "plan_retirement": ["retirement", "pension planning", "retirement saving"],
            "optimize_deductions": ["deductions", "optimize deductions", "claim deductions"]
        }
        
        for goal, keywords in goal_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                goals.append(goal)
        
        return normalize_tax_goals(goals)
    
    def _extract_risk_tolerance(self, text_lower: str) -> Optional[str]:
        """Extract risk tolerance from text."""
        if any(word in text_lower for word in ["conservative", "safe", "low risk", "cautious"]):
            return normalize_risk_tolerance("conservative")
        elif any(word in text_lower for word in ["aggressive", "high risk", "growth"]):
            return normalize_risk_tolerance("aggressive")
        elif any(word in text_lower for word in ["moderate", "balanced", "medium risk"]):
            return normalize_risk_tolerance("moderate")
        
        return None
    
    # =============================
    # Profile Data Normalization
    # =============================
    
    def normalize_profile_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize profile data to standard formats.
        
        Args:
            raw_data: Raw profile data dictionary
            
        Returns:
            Normalized profile data
        """
        self.log_operation_start("normalize_profile_data", fields=len(raw_data))
        
        try:
            normalized = {}
            
            # Normalize each field
            if "employment_status" in raw_data:
                normalized["employment_status"] = normalize_employment_status(raw_data["employment_status"])
            
            if "filing_status" in raw_data:
                normalized["filing_status"] = normalize_filing_status(raw_data["filing_status"])
            
            if "risk_tolerance" in raw_data:
                normalized["risk_tolerance"] = normalize_risk_tolerance(raw_data["risk_tolerance"])
            
            if "tax_goals" in raw_data:
                normalized["tax_goals"] = normalize_tax_goals(raw_data["tax_goals"])
            
            if "annual_income" in raw_data:
                normalized["annual_income"] = safe_float(raw_data["annual_income"])
            
            if "dependents" in raw_data:
                normalized["dependents"] = safe_int(raw_data["dependents"])
            
            # Copy other fields as-is
            for key, value in raw_data.items():
                if key not in normalized and value is not None:
                    normalized[key] = value
            
            self.log_operation_success("normalize_profile_data", f"normalized={len(normalized)} fields")
            return normalized
            
        except Exception as e:
            self.log_operation_error("normalize_profile_data", e)
            return raw_data
    
    # =============================
    # Profile Validation
    # =============================
    
    def validate_profile_updates(self, updates: Dict[str, Any], current_profile: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], List[str]]:
        """
        Validate profile updates for consistency and business rules.
        
        Args:
            updates: Profile updates to validate
            current_profile: Current profile for consistency checks
            
        Returns:
            Tuple of (validated_updates, warnings)
        """
        self.log_operation_start("validate_profile_updates", updates=len(updates))
        
        try:
            validated = {}
            warnings = []
            
            # Validate annual income
            if "annual_income" in updates:
                income = updates["annual_income"]
                if isinstance(income, (int, float)) and 0 <= income <= 1000000:
                    validated["annual_income"] = float(income)
                elif income is not None:
                    warnings.append(f"Invalid annual income: {income}. Must be between 0 and 1,000,000.")
            
            # Validate employment status
            if "employment_status" in updates:
                status = updates["employment_status"]
                try:
                    # Validate against enum
                    if isinstance(status, str):
                        EmploymentStatus(status)
                        validated["employment_status"] = status
                    else:
                        warnings.append(f"Invalid employment status: {status}")
                except ValueError:
                    warnings.append(f"Invalid employment status: {status}")
            
            # Validate filing status
            if "filing_status" in updates:
                status = updates["filing_status"]
                try:
                    if isinstance(status, str):
                        FilingStatus(status)
                        validated["filing_status"] = status
                    else:
                        warnings.append(f"Invalid filing status: {status}")
                except ValueError:
                    warnings.append(f"Invalid filing status: {status}")
            
            # Validate dependents
            if "dependents" in updates:
                deps = updates["dependents"]
                if isinstance(deps, int) and 0 <= deps <= 20:
                    validated["dependents"] = deps
                elif deps is not None:
                    warnings.append(f"Invalid dependents count: {deps}. Must be between 0 and 20.")
            
            # Validate risk tolerance
            if "risk_tolerance" in updates:
                risk = updates["risk_tolerance"]
                if risk in ["conservative", "moderate", "aggressive"]:
                    validated["risk_tolerance"] = risk
                elif risk is not None:
                    warnings.append(f"Invalid risk tolerance: {risk}. Must be conservative, moderate, or aggressive.")
            
            # Validate tax goals
            if "tax_goals" in updates:
                goals = updates["tax_goals"]
                if isinstance(goals, list):
                    valid_goals = ["minimize_taxes", "maximize_refund", "plan_retirement", "optimize_deductions"]
                    filtered_goals = [goal for goal in goals if goal in valid_goals]
                    validated["tax_goals"] = filtered_goals
                    if len(filtered_goals) != len(goals):
                        warnings.append("Some tax goals were invalid and filtered out.")
                elif goals is not None:
                    warnings.append(f"Tax goals must be a list, got: {type(goals)}")
            
            # Copy other valid fields
            for key, value in updates.items():
                if key not in validated and value is not None:
                    validated[key] = value
            
            self.log_operation_success("validate_profile_updates", f"validated={len(validated)} fields, warnings={len(warnings)}")
            return validated, warnings
            
        except Exception as e:
            self.log_operation_error("validate_profile_updates", e)
            return {}, [f"Validation error: {str(e)}"]
    
    # =============================
    # Profile CRUD Operations
    # =============================
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile from database."""
        if not self.database_service:
            self.logger.warning("Database service not available for profile retrieval")
            return None
        
        try:
            return await self.database_service.get_user_profile(user_id)
        except Exception as e:
            self.log_operation_error("get_user_profile", e)
            return None
    
    async def create_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Optional[UserProfile]:
        """Create new user profile."""
        if not self.database_service:
            self.logger.warning("Database service not available for profile creation")
            return None
        
        try:
            # Validate profile data first
            validated_data, warnings = self.validate_profile_updates(profile_data)
            
            if warnings:
                self.logger.warning(f"Profile creation warnings: {warnings}")
            
            # Create profile model
            profile = UserProfile(user_id=user_id, **validated_data)
            
            # Save to database
            result = await self.database_service.create_user_profile(profile)
            
            self.log_operation_success("create_user_profile", f"user_id={user_id}")
            return result
            
        except Exception as e:
            self.log_operation_error("create_user_profile", e)
            return None
    
    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Optional[UserProfile]:
        """Update existing user profile."""
        if not self.database_service:
            self.logger.warning("Database service not available for profile update")
            return None
        
        try:
            # Get current profile
            current_profile = await self.get_user_profile(user_id)
            current_dict = to_dict(current_profile) if current_profile else {}
            
            # Validate updates
            validated_updates, warnings = self.validate_profile_updates(updates, current_dict)
            
            if warnings:
                self.logger.warning(f"Profile update warnings: {warnings}")
            
            # Apply updates
            updated_data = {**current_dict, **validated_updates}
            
            # Save to database
            result = await self.database_service.update_user_profile(user_id, updated_data)
            
            self.log_operation_success("update_user_profile", f"user_id={user_id}, updated={len(validated_updates)} fields")
            return result
            
        except Exception as e:
            self.log_operation_error("update_user_profile", e)
            return None
    
    # =============================
    # Combined Operations
    # =============================
    
    async def extract_and_update_profile(self, user_id: str, message_text: str) -> Tuple[Optional[UserProfile], List[str]]:
        """
        Extract profile information from text and update user profile.
        
        Args:
            user_id: User ID to update
            message_text: Text to extract profile info from
            
        Returns:
            Tuple of (updated_profile, warnings)
        """
        self.log_operation_start("extract_and_update_profile", user_id=user_id)
        
        try:
            # Extract profile information
            extracted_info = await self.extract_profile_info(message_text)
            
            if not extracted_info:
                return None, ["No profile information found in message"]
            
            # Normalize extracted data
            normalized_data = self.normalize_profile_data(extracted_info)
            
            # Update profile
            updated_profile = await self.update_user_profile(user_id, normalized_data)
            
            warnings = []
            if not updated_profile:
                warnings.append("Failed to update profile in database")
            
            self.log_operation_success("extract_and_update_profile", f"extracted={len(extracted_info)} fields")
            return updated_profile, warnings
            
        except Exception as e:
            self.log_operation_error("extract_and_update_profile", e)
            return None, [f"Error: {str(e)}"]
