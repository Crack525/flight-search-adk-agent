import asyncio
import logging
import json
from pydantic import PrivateAttr
from google.adk.events.event import Event

from vertexai.generative_models import GenerativeModel, Part, Tool
from flight_agent.config import get_config, AGENT_SYSTEM_INSTRUCTION 
from flight_agent.tools.search_flights_tool import SEARCH_FLIGHTS_VERTEX_TOOL, SEARCH_GOOGLE_FLIGHTS_VERTEX_TOOL, AVAILABLE_FLIGHT_TOOLS

try:
    from google.adk.agents import BaseAgent
except ImportError:
    # Fallback or placeholder if direct import fails.
    # The ADK might have it in a submodule like google.adk.agents.BaseAgent
    # For now, we'll define a placeholder to allow type hinting and structure, 
    # but this will likely need to be the actual ADK BaseAgent for full compatibility.
    logging.warning("Could not import BaseAgent from google.adk. Using a placeholder. Ensure google-adk is installed and provides BaseAgent.")
    class BaseAgent:
        pass 

logger = logging.getLogger(__name__)

class FlightSearchAgent(BaseAgent):
    _config: dict = PrivateAttr()
    _model: GenerativeModel = PrivateAttr()
    _chat: object = PrivateAttr(default=None)

    def __init__(self, name="flight_agent"):
        super().__init__(name=name)  
        self._config = get_config()
        if not self._config.get("GOOGLE_CLOUD_PROJECT") or not self._config.get("GOOGLE_CLOUD_LOCATION"):
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION must be set in environment or .env file for Vertex AI."
            )
        
        self._model = GenerativeModel(
            self._config["GEMINI_MODEL_NAME"],
            system_instruction=[Part.from_text(AGENT_SYSTEM_INSTRUCTION)],
        )
        self._chat = None # Initialize chat session later
        logger.info(f"FlightSearchAgent initialized with model: {self._config['GEMINI_MODEL_NAME']}")

    async def start_session(self):
        """Starts a new chat session with the model."""
        self._chat = self._model.start_chat(history=[]) 
        logger.info("Chat session started with Vertex AI Gemini model.")

    async def process_query(self, user_query: str):
        if not self._chat:
            await self.start_session()

        logger.info(f"Sending user query to Vertex AI: '{user_query}'")
        
        try:
            # Initial query: Make the first tool (search_flights) available
            tools_for_this_call = [SEARCH_FLIGHTS_VERTEX_TOOL]
            response = await self._chat.send_message_async(user_query, tools=tools_for_this_call)
            
            while (
                response.candidates
                and response.candidates[0].content.parts
                and getattr(response.candidates[0].content.parts[0], "function_call", None)
            ):
                function_call_part = response.candidates[0].content.parts[0]
                function_name = function_call_part.function_call.name
                
                if function_name in AVAILABLE_FLIGHT_TOOLS:
                    function_to_call = AVAILABLE_FLIGHT_TOOLS[function_name]
                    function_args = {key: value for key, value in function_call_part.function_call.args.items()}
                    
                    logger.info(f"Calling tool function: {function_name} with args: {function_args}")
                    tool_response_data = await function_to_call(**function_args)
                    logger.info(f"Tool function {function_name} response: {tool_response_data}")

                    response_content_part = Part.from_function_response(
                        name=function_name,
                        response=tool_response_data
                    )

                    # Determine tools for the *next* call based on the function just called
                    if function_name == "search_flights":
                        # After search_flights, make search_google_flights available
                        tools_for_this_call = [SEARCH_GOOGLE_FLIGHTS_VERTEX_TOOL]
                        response = await self._chat.send_message_async(response_content_part, tools=tools_for_this_call)
                    elif function_name == "search_google_flights":
                        # After search_google_flights, no more tools expected in this sequence
                        response = await self._chat.send_message_async(response_content_part) # No 'tools' arg
                    else:
                        # Should not be reached if system prompt is followed for known tools
                        logger.warn(f"Unexpected function {function_name} called in sequence.")
                        response = await self._chat.send_message_async(response_content_part) # No 'tools' arg
                else:
                    logger.error(f"Unknown function call requested by model: {function_name}")
                    response_content_part = Part.from_function_response(
                        name=function_name,
                        response={"error": f"Unknown function {function_name}"} 
                    )
                    # When sending an error for an unknown function, we might not need to suggest further tools,
                    # or we could pass the last `tools_for_this_call` if the model was supposed to use one of them.
                    # For now, send without tools.
                    response = await self._chat.send_message_async(response_content_part)
                    break 
            
            # Extract and return the final text response
            if response.candidates and response.candidates[0].content.parts:
                text_parts = []
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "text") and part.text:
                        text_parts.append(part.text)
                    if hasattr(part, "function_response") and part.function_response and isinstance(part.function_response.response, dict):
                        flights = part.function_response.response.get("flights")
                        summary = part.function_response.response.get("summary")
                        error = part.function_response.response.get("error")
                        if error:
                            text_parts.append(f"Sorry, there was a problem: {error}")
                        elif flights:
                            text_parts.append("\nHere are the best flight options I found for you:")
                            for idx, f in enumerate(flights, 1):
                                text_parts.append(
                                    f"{idx}. Airline: {f['airline']}\n   Route: {f['origin']} → {f['destination']}\n   Departure: {f['departure_time']}\n   Arrival: {f['arrival_time']}\n   Stops: {f['stops']}\n   Price: ${f['price_usd']} {f['currency']}\n   Flight Number: {f['notes']}"
                                )
                            if summary:
                                text_parts.append(f"\nSummary: {summary}")
                        elif summary:
                            text_parts.append(f"{summary}")
                if text_parts:
                    final_response_text = "\n\n".join(text_parts)
                    logger.info(f"Final response from Vertex AI: {final_response_text}")
                    return final_response_text
                else:
                    logger.error("No text part found in the final response from Vertex AI.")
                    return "Sorry, I couldn't generate a response for that query after processing."
        except Exception as e:
            logger.error(f"Error during Vertex AI interaction: {e}", exc_info=True)
            return f"An error occurred while processing your request: {e}"

    async def _run_async_impl(self, ctx):
        """
        Required by google-adk BaseAgent. Handles a single invocation context.
        Yields events as required by the ADK event protocol.
        """
        # Debug: log the full context and its dict (if any)
        logger.info(f"ADK context object: {ctx}")
        if hasattr(ctx, "__dict__"):
            logger.info(f"ADK context __dict__: {ctx.__dict__}")
        else:
            logger.info(f"ADK context dir: {dir(ctx)}")

        user_query = getattr(ctx, "user_input", None)
        if not user_query and hasattr(ctx, "input"):
            user_query = ctx.input
        if not user_query and hasattr(ctx, "query"):
            user_query = ctx.query
        # Try extracting from user_content.parts[0].text (ADK web UI pattern)
        if not user_query and hasattr(ctx, "user_content"):
            user_content = getattr(ctx, "user_content")
            if hasattr(user_content, "parts") and user_content.parts:
                # Try to concatenate all text parts, or just use the first
                texts = [getattr(part, "text", None) for part in user_content.parts if hasattr(part, "text") and part.text]
                if texts:
                    user_query = "\n".join(texts)
                    logger.info(f"Extracted user query from ctx.user_content.parts: {user_query}")
        # Try extracting from __dict__ as a fallback
        if not user_query and hasattr(ctx, "__dict__"):
            for k, v in ctx.__dict__.items():
                if isinstance(v, str) and v.strip():
                    logger.info(f"Found possible user query in ctx.__dict__: {k} = {v}")
                    user_query = v
                    break
        if not user_query:
            yield Event(author=self.name, content={"parts": [{"text": "No user query found in context."}]}, partial=False)
            return

        response = await self.process_query(user_query)
        yield Event(author=self.name, content={"parts": [{"text": response}]}, partial=False)

if __name__ == '__main__':
    # This is for basic testing of the agent class itself.
    # The main entry point will be in main.py
    async def test_agent():
        logging.basicConfig(level=logging.INFO)
        logger.info("Starting FlightSearchAgent test...")
        try:
            agent = FlightSearchAgent()
            test_query = "Find me a cheap flight from New York to London next week."
            print(f"\nUser Query: {test_query}")
            assistant_response = await agent.process_query(test_query)
            print("\n--- Assistant's Response ---")
            print(assistant_response)
            print("---------------------------")
        except ValueError as ve:
            logger.error(f"Configuration error: {ve}")
            print(f"Configuration error: {ve}. Please ensure GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION are set.")
        except Exception as ex:
            logger.error(f"Test agent failed: {ex}", exc_info=True)

    asyncio.run(test_agent())

# For Google ADK: an instance of the agent that the ADK can discover.
# Ensure environment variables are loaded if FlightSearchAgent() relies on them at init.
# The ADK's loading mechanism should ideally handle .env loading or provide a way to do it early.
# From the logs, it seems .env is loaded before this part is hit by the ADK.
try:
    root_agent = FlightSearchAgent(name="flight_agent")
except Exception as e:
    logger.error(f"Failed to instantiate root_agent in flight_agent.agent: {e}", exc_info=True)
    root_agent = None # Or raise the exception
