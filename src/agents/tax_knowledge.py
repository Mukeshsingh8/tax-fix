"""Tax knowledge agent for providing tax guidance and calculations."""
# number calculation by different type of LLM are causing different sort of hallucination. 
# cannot keep updating prompt for every LLM A/B testing and maintaining the prompt.
# simply implement our own function for tax calculation.

from typing import Dict, List, Optional, Any
from datetime import datetime

from ..core.state import Message, AgentResponse, AgentType
from ..models.user import UserProfile as DBUserProfile
from ..services.tax_knowledge_service import TaxKnowledgeService
from ..utils import to_dict, val_to_str, safe_agent_method
from .base import BaseAgent
from ..services.tax.tax_calculations import TaxCalculator
from ..services.tax.tax_deductions import TaxDeductionAnalyzer


class TaxKnowledgeAgent(BaseAgent):
    """Provides German tax guidance, deduction ideas, and quick calculations."""

    def __init__(self, *args, **kwargs):
        super().__init__(AgentType.TAX_KNOWLEDGE, *args, **kwargs)
        self.tax_service = TaxKnowledgeService()
        self.calculator = TaxCalculator(self.tax_service)
        self.deduction_analyzer = TaxDeductionAnalyzer(self.tax_service, self.llm_service)

    async def get_system_prompt(self) -> str:
        return """
        You are the Tax Knowledge Agent for a German tax assistant.

        Your goals:
        - Give accurate, up-to-date German tax info (focus on 2024 figures).
        - Be concise (2–4 sentences), actionable, and in English.
        - Use German tax terminology with brief English explanations where helpful.
        - If calculation is needed and possible with known profile data, do it.
        - Don't suggest consulting tax professionals.

        Style:
        - Direct, clear, specific. Use € amounts when applicable.
        - Mention relevant rules (e.g., Grundfreibetrag, Werbungskosten).
        - When data is missing for a calculation, ask 2–3 smart questions.
        """

    @safe_agent_method(
        fallback_content="I can help with German tax questions like deductions, allowances, or tax calculations. What specific topic interests you?",
        fallback_confidence=0.5
    )
    async def process(
        self,
        message: Message,
        context: Dict[str, Any],
        session_id: str,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """Process tax knowledge requests."""
        # Load fresh profile for personalization
        user_id = context.get("user_id")
        db_profile: Optional[DBUserProfile] = (
            await self.database_service.get_user_profile(user_id) if user_id else None
        )

        # Check if we're missing critical info
        missing_info = await self.detect_missing_information(message, db_profile, context)
        if missing_info:
            return await self.ask_clarifying_questions(missing_info, message, context)

        # Retrieve relevant knowledge
        relevant_rules = self.tax_service.search_tax_rules(message.content) or []
        relevant_deductions = self.tax_service.search_deductions(message.content) or []

        # Generate guidance
        guidance = await self.generate_tax_guidance(
            message=message,
            relevant_rules=relevant_rules,
            relevant_deductions=relevant_deductions,
            user_profile=db_profile,
            context=context,
        )

        # Get relevant deductions
        top_deductions = await self.deduction_analyzer.identify_relevant_deductions(
            message=message,
            user_profile=db_profile,
            relevant_content={"deductions": [to_dict(d) for d in relevant_deductions]},
        )

        # Perform calculations if requested
        calculations = await self.calculator.perform_calculations(
            message=message, user_profile=db_profile, context=context
        )

        # Create response
        response_content = await self.create_guidance_response(
            guidance=guidance,
            deductions=top_deductions,
            calculations=calculations,
            user_profile=db_profile,
        )

        return await self.create_response(
            content=response_content,
            reasoning="Provided German tax guidance with relevant rules, deductions, and optional calculation.",
            confidence=0.88,
            suggested_actions=[
                {"action": "review_deductions", "description": "Review suggested deductions"},
                {"action": "calculate_taxes", "description": "Run a full tax estimate"},
                {"action": "track_expense", "description": "Add a work expense to track"}
            ],
            metadata={
                "agent_type": "tax_knowledge",
                "tax_topics": self.extract_tax_topics(message.content),
                "relevant_deductions": top_deductions,
                "calculations": calculations,
            },
        )

    async def detect_missing_information(
        self,
        message: Message,
        user_profile: Optional[DBUserProfile],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect missing information needed for comprehensive tax advice."""
        try:
            # Simple heuristic-based detection for now
            missing = []
            text_lower = message.content.lower()

            # Check for calculation requests without profile data
            if any(term in text_lower for term in ["calculate", "how much", "estimate"]):
                if not user_profile or not user_profile.annual_income:
                    missing.append({
                        "field": "annual_income",
                        "reason": "Needed for tax calculation",
                        "priority": "high",
                        "context": "tax_calculation"
                    })

            return missing

        except Exception as e:
            self.logger.error(f"Missing information detection error: {e}")
            return []

    async def ask_clarifying_questions(
        self,
        missing_info: List[Dict[str, Any]],
        message: Message,
        context: Dict[str, Any]
    ) -> AgentResponse:
        """Ask clarifying questions for missing information."""
        try:
            high_priority = [info for info in missing_info if info["priority"] == "high"]
            
            if high_priority:
                field = high_priority[0]["field"]
                reason = high_priority[0]["reason"]
                
                questions = {
                    "annual_income": "To provide accurate tax calculations, I'll need to know your annual gross income. What's your yearly salary before taxes?",
                    "filing_status": "Are you filing as single, married filing jointly, or have another filing status?",
                    "dependents": "Do you have any dependents (children under 18 or other qualifying dependents)?",
                    "employment_status": "Are you employed, self-employed, or currently unemployed?"
                }
                
                content = questions.get(field, f"I need some additional information: {reason}")
                
                return await self.create_response(
                    content=content,
                    confidence=0.9,
                    reasoning=f"Missing required field: {field}",
                    metadata={"missing_fields": [field], "requires_followup": True}
                )

        except Exception as e:
            self.logger.error(f"Clarifying questions error: {e}")

        # Fallback
        return await self.create_response(
            content="I can provide better tax advice with more information about your situation. What's your annual income and employment status?",
            confidence=0.7,
            reasoning="General information request"
        )

    async def generate_tax_guidance(
        self,
        message: Message,
        relevant_rules: List[Any],
        relevant_deductions: List[Any],
        user_profile: Optional[DBUserProfile],
        context: Dict[str, Any],
    ) -> str:
        """Generate tax guidance using LLM."""
        try:
            # Build context for LLM
            rules_context = ""
            if relevant_rules:
                rules_context = f"Relevant tax rules: {'; '.join([str(rule) for rule in relevant_rules[:3]])}"

            profile_context = ""
            if user_profile:
                profile_context = f"User profile: Income: €{user_profile.annual_income or 'unknown'}, Filing: {user_profile.filing_status or 'unknown'}"

            prompt = f"""Answer this German tax question clearly and concisely (2-3 sentences max).

Question: "{message.content}"
{rules_context}
{profile_context}

Focus on:
1. Direct answer to the question
2. Specific amounts/limits if applicable  
3. Actionable next steps

Always respond in English. Use German tax terms with brief explanations."""

            return await self.generate_llm_response(
                messages=[{"role": "user", "content": prompt}],
                model="groq",
                conversation_id=context.get("conversation_id"),
                include_history=False,
            )

        except Exception as e:
            self.logger.error(f"Tax guidance generation error: {e}")
            return "I can help with German tax questions. Please ask about specific deductions, tax rates, or calculations."

    async def create_guidance_response(
        self,
        guidance: str,
        deductions: List[Dict[str, Any]],
        calculations: Optional[Dict[str, Any]],
        user_profile: Optional[DBUserProfile],
    ) -> str:
        """Create the final guidance response."""
        try:
            response_parts = [guidance.strip()]

            # Add calculation results if available
            if calculations:
                calc_section = self.format_calculation_section(calculations)
                if calc_section:
                    response_parts.append(calc_section)

            # Add relevant deductions
            if deductions:
                deduction_section = self.format_deduction_section(deductions[:3])
                if deduction_section:
                    response_parts.append(deduction_section)

            return "\n\n".join(response_parts)

        except Exception as e:
            self.logger.error(f"Response creation error: {e}")
            return guidance.strip()

    def format_calculation_section(self, calculations: Dict[str, Any]) -> str:
        """Format calculation results."""
        try:
            calc_type = calculations.get("type", "")
            
            if calc_type == "net_income":
                gross = calculations.get("gross_income", 0)
                net = calculations.get("net_income", 0)
                tax_rate = calculations.get("effective_tax_rate", 0)
                return f"**Calculation:** With €{gross:,.0f} gross income, your estimated net income is €{net:,.0f} (effective tax rate: {tax_rate:.1f}%)."
            
            elif calc_type == "tax_liability":
                liability = calculations.get("tax_liability", 0)
                rate = calculations.get("marginal_tax_rate", 0)
                return f"**Tax Liability:** Estimated annual tax: €{liability:,.0f} (marginal rate: {rate:.1f}%)."
            
            elif calc_type == "deduction_savings":
                savings = calculations.get("estimated_tax_savings", 0)
                additional = calculations.get("additional_deductions", 0)
                return f"**Potential Savings:** By claiming €{additional:,.0f} in additional deductions, you could save approximately €{savings:,.0f} in taxes."

        except Exception as e:
            self.logger.error(f"Calculation formatting error: {e}")
        
        return ""

    def format_deduction_section(self, deductions: List[Dict[str, Any]]) -> str:
        """Format deduction recommendations."""
        try:
            if not deductions:
                return ""

            deduction_lines = []
            for deduction in deductions:
                name = deduction.get("name", "Unknown")
                desc = deduction.get("description", "")
                max_amount = deduction.get("max_amount")
                
                line = f"• **{name}**"
                if max_amount:
                    line += f" (up to €{max_amount:,.0f})"
                if desc:
                    line += f": {desc[:80]}{'...' if len(desc) > 80 else ''}"
                
                deduction_lines.append(line)

            return "**Relevant Deductions:**\n" + "\n".join(deduction_lines)

        except Exception as e:
            self.logger.error(f"Deduction formatting error: {e}")
            return ""

    def extract_tax_topics(self, content: str) -> List[str]:
        """Extract tax-related topics from the message."""
        topics = []
        content_lower = content.lower()
        
        topic_keywords = {
            "deductions": ["deduction", "werbungskosten", "expenses"],
            "allowances": ["allowance", "freibetrag", "exemption"],
            "rates": ["rate", "tax rate", "percentage"],
            "calculations": ["calculate", "estimate", "how much"],
            "childcare": ["child", "kinder", "daycare"],
            "home_office": ["home office", "homeoffice", "remote work"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                topics.append(topic)
        
        return topics

    def val(self, enum_or_str: Any) -> Optional[str]:
        """Convert enum or string to string value."""
        return val_to_str(enum_or_str)
