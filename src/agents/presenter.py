"""Presenter agent for synthesizing multiple agent responses."""

from typing import Dict, List, Optional, Any, Tuple

from ..core.state import Message, AgentResponse, AgentType
from .base import BaseAgent


class PresenterAgent(BaseAgent):
    """
    Synthesizes multiple agent outputs into a cohesive, user-friendly response.
    
    Design principles:
    - Takes outputs from specialized agents (Action, Profile, Tax Knowledge)
    - Creates one unified response that answers the user's question directly
    - Integrates information intelligently (e.g., expenses inform tax advice)
    - Removes redundancy and contradictions
    - Maintains natural conversational flow
    - Never mentions "agents" or "systems" to the user
    """

    def __init__(self, *args, **kwargs):
        super().__init__(AgentType.PRESENTER, *args, **kwargs)

    async def get_system_prompt(self) -> str:
        return (
            "You are a Presenter Agent for a German tax assistance platform. "
            "Your job is to synthesize multiple specialized agent outputs into ONE cohesive, "
            "helpful response for the user. CRITICAL: Use ONLY the exact data provided by agents - "
            "never hallucinate, estimate, or create fake details. Always respond in English with German tax terms "
            "explained briefly. Never mention 'agents' or 'systems' - speak as one unified assistant."
        )

    # ---------------------------
    # Entry point
    # ---------------------------
    async def process(
        self,
        message: Message,
        context: Dict[str, Any],
        session_id: str,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> AgentResponse:
        """
        This method won't be used in the typical flow since the Presenter Agent
        is called directly with agent results, but we implement it for consistency.
        """
        return await self.create_response(
            content="Presenter Agent should be called with synthesize_responses method.",
            confidence=0.0,
            reasoning="Direct process call not supported for Presenter Agent"
        )

    # ---------------------------
    # Main synthesis method
    # ---------------------------
    async def synthesize_responses(
        self,
        agent_results: List[Tuple[str, AgentResponse, float]],
        user_message: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Synthesize multiple agent outputs into a cohesive response.
        
        Args:
            agent_results: List of (agent_name, response, runtime_seconds) tuples
            user_message: Original user question
            context: Full conversation context
            
        Returns:
            Synthesized response content as string
        """
        try:
            if not agent_results:
                return "I couldn't process your request. Could you please try again?"

            # If only one agent responded, return its content directly (but cleaned up)
            if len(agent_results) == 1:
                _, response, _ = agent_results[0]
                return response.content.strip()

            # Prepare agent outputs for synthesis
            agent_outputs = []
            for agent_name, response, runtime in agent_results:
                agent_outputs.append({
                    "agent": agent_name,
                    "content": response.content,
                    "confidence": response.confidence,
                    "reasoning": response.reasoning,
                    "runtime_seconds": runtime
                })

            # Get conversation history for context
            conversation_history = context.get("conversation_history", [])
            recent_history = conversation_history[-5:] if conversation_history else []

            # Build the synthesis prompt
            prompt = self.build_synthesis_prompt(
                user_message=user_message,
                agent_outputs=agent_outputs,
                conversation_history=recent_history,
                context=context
            )

            # Generate the synthesized response
            messages = [{"role": "user", "content": prompt}]
            synthesized_response = await self.llm_service.generate_response(
                messages=messages,
                system_prompt=await self.get_system_prompt(),
                max_tokens=2000,
                temperature=0.7
            )

            self.logger.info(f"🎨 PRESENTER SYNTHESIS: Generated {len(synthesized_response)} character response")
            return synthesized_response.strip()

        except Exception as e:
            self.logger.error(f"Presenter Agent synthesis error: {e}")
            # Fallback to simple concatenation
            fallback_content = "\n\n".join([
                f"**{agent_name.replace('_', ' ').title()}:**\n{resp.content}"
                for agent_name, resp, _ in agent_results
                if resp.content.strip()
            ])
            return fallback_content

    def build_synthesis_prompt(
        self,
        user_message: str,
        agent_outputs: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
        context: Dict[str, Any]
    ) -> str:
        """Build the prompt for synthesizing agent outputs."""
        
        # Format conversation history
        history_text = ""
        if conversation_history:
            history_text = "\n".join([
                f"- {msg.get('role', 'unknown')}: {msg.get('content', '')[:150]}..."
                for msg in conversation_history[-3:]
            ])

        # Format agent outputs and detect expense suggestions
        outputs_text = ""
        has_expense_suggestion = False
        
        for output in agent_outputs:
            outputs_text += f"\n**{output['agent'].upper()} AGENT** (confidence: {output['confidence']:.2f}):\n"
            outputs_text += f"{output['content']}\n"
            outputs_text += f"Reasoning: {output['reasoning']}\n"
            outputs_text += "---\n"
            
            # Check if Action Agent suggested an expense
            if (output['agent'] == 'action' and 
                output['reasoning'] and 
                ('suggested expense' in output['reasoning'].lower() or 
                 'cached as pending' in output['reasoning'].lower())):
                has_expense_suggestion = True

        prompt = f"""
You are synthesizing multiple specialized responses into ONE cohesive answer for a German tax assistance user.

**IMPORTANT**: You MUST use only the information provided by the agents below. DO NOT create, estimate, or hallucinate any data, numbers, or details not explicitly provided.

**USER'S ORIGINAL QUESTION:**
"{user_message}"

**RECENT CONVERSATION:**
{history_text if history_text else "This is the start of the conversation."}

**SPECIALIZED AGENT OUTPUTS (USE EXACT DATA FROM HERE):**
{outputs_text}

**EXPENSE SUGGESTION DETECTED:** {"YES - The Action Agent suggested adding an expense to track!" if has_expense_suggestion else "No expense suggestions detected."}

**YOUR TASK:**
Create a single, well-structured response that:
1. Directly answers the user's question
2. **PRESERVE EXACT DATA**: Use the exact expenses, amounts, dates, and details provided by agents - DO NOT modify, estimate, or create new details
3. Combines information from multiple agents without contradictions
4. Uses a natural, conversational tone
5. Prioritizes the most relevant information first
6. If expenses are mentioned by the Action Agent, ensure tax advice accounts for them
7. **CRITICAL**: If an expense suggestion was detected above, ALWAYS end your response asking the user to provide the expense details and confirm adding it to their tracking

**CRITICAL GUIDELINES:**
- Don't mention "agents", "systems", or "outputs" - speak as one unified tax assistant
- **NEVER HALLUCINATE DATA**: If Action Agent says "no expenses", don't create fake expenses. If it provides specific expenses, use the EXACT details provided
- **PRESERVE EXACT NUMBERS**: Use the exact amounts, dates, categories provided - don't round, estimate, or modify them
- If the Action Agent found expenses, use their exact data in tax calculations/advice
- **EXPENSE SUGGESTIONS**: If an expense suggestion was detected, add a section like:
  "Would you like me to add this German course to your expense tracking? Please provide:
  - Amount: €[ask for amount]
  - Purchase date: [ask for date]
  - Confirm it's work-related: [ask for confirmation]
  Just say 'yes' and provide the details, and I'll add it for you!"
- Keep the user's specific question as the primary focus
- Use clear headings ONLY if they improve readability
- Ensure the response flows naturally as one coherent conversation
- Answer in English but use German tax terms (with brief explanations)
- Be helpful, accurate, and concise

Generate your synthesized response:
"""
        return prompt
