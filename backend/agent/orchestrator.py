"""
AI Agent Orchestrator — the brain that connects Azure OpenAI with the MCP Client Hub.
Implements the tool-calling loop with human-in-the-loop confirmation.
"""

import json
import logging
from openai import AzureOpenAI
from backend.config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_API_VERSION,
)
from backend.agent.prompts import SYSTEM_PROMPT
from backend.mcp_client.hub import MCPClientHub

logger = logging.getLogger(__name__)


class MediTriageAgent:
    """
    The AI orchestrator that:
    1. Takes patient messages
    2. Calls Azure OpenAI with all MCP tools available
    3. Routes tool calls through the MCP Client Hub
    4. Returns responses (with optional confirmation pauses)
    """

    def __init__(self, hub: MCPClientHub):
        self.hub = hub
        self.llm = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
        )
        self.deployment = AZURE_OPENAI_DEPLOYMENT
        # Conversation history per session
        self.conversations: dict[str, list] = {}

    def _get_history(self, session_id: str) -> list:
        """Get or create conversation history for a session."""
        if session_id not in self.conversations:
            self.conversations[session_id] = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
        return self.conversations[session_id]

    async def process_message(self, session_id: str, user_message: str) -> dict:
        """
        Process a user message through the full agent loop.
        
        Returns:
            {
                "response": "AI's text response",
                "tool_calls_made": [{"server": "...", "tool": "...", "result_preview": "..."}],
                "needs_confirmation": bool,
                "doctors": [...] or None  # If doctor selection is needed
            }
        """
        history = self._get_history(session_id)
        history.append({"role": "user", "content": user_message})

        tools = self.hub.get_openai_tools()
        tool_calls_made = []
        slot_data = None      # Populated when get_available_slots is called
        doctor_data = None    # Populated when find_doctors is called

        # Agent loop — keep running until the LLM gives a final text response
        max_iterations = 15  # Safety limit
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            try:
                response = self.llm.chat.completions.create(
                    model=self.deployment,
                    messages=history,
                    tools=tools if tools else None,
                    temperature=0.3,
                )
            except Exception as e:
                logger.error(f"[Agent] LLM call failed: {e}")
                return {
                    "response": f"I'm having trouble connecting to the AI service. Please try again. Error: {str(e)}",
                    "tool_calls_made": tool_calls_made,
                    "needs_confirmation": False,
                    "doctors": doctor_data,
                    "slots": slot_data,
                }

            message = response.choices[0].message

            # If no tool calls, we have a final response
            if not message.tool_calls:
                final_text = message.content or "I'm not sure how to help with that. Could you describe your symptoms?"
                history.append({"role": "assistant", "content": final_text})

                return {
                    "response": final_text,
                    "tool_calls_made": tool_calls_made,
                    "needs_confirmation": False,
                    "doctors": doctor_data,
                    "slots": slot_data,
                }

            # Process tool calls
            history.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                # Identify which server this tool belongs to
                server_name = self.hub.tool_map.get(tool_name, "unknown")
                logger.info(f"[Agent] Calling {server_name}.{tool_name}({json.dumps(arguments)[:200]})")

                # Execute the tool via MCP Hub
                result = await self.hub.call_tool(tool_name, arguments)

                # Extract structured data for the frontend
                if tool_name == "get_available_slots":
                    try:
                        slot_data = json.loads(result)
                    except (json.JSONDecodeError, TypeError):
                        pass

                if tool_name == "find_doctors":
                    try:
                        doctor_data = json.loads(result)
                    except (json.JSONDecodeError, TypeError):
                        pass

                # Track the call for UI display
                tool_calls_made.append({
                    "server": server_name,
                    "tool": tool_name,
                    "arguments": arguments,
                    "result_preview": result[:300] if result else "empty",
                })

                # Add tool result to conversation history
                history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        # If we hit max iterations, return what we have
        return {
            "response": "I've completed my analysis. Is there anything else you'd like to know?",
            "tool_calls_made": tool_calls_made,
            "needs_confirmation": False,
            "doctors": doctor_data,
            "slots": slot_data,
        }

    def clear_session(self, session_id: str):
        """Clear conversation history for a session."""
        if session_id in self.conversations:
            del self.conversations[session_id]
