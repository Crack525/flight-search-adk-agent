import logging
from flight_agent.agent import FlightSearchAgent

logging.basicConfig(level=logging.INFO)
_agent_instance = None

def get_agent():
    """Provides a singleton instance of the FlightSearchAgent."""
    global _agent_instance
    if _agent_instance is None:
        try:
            _agent_instance = FlightSearchAgent()
            logging.info("FlightSearchAgent initialized for ADK.")
        except Exception as e:
            logging.error(f"Failed to initialize FlightSearchAgent for ADK: {e}", exc_info=True)
            raise
    return _agent_instance

async def adk_request_handler(payload: dict):
    """
    A hypothetical request handler that an ADK web server might call.
    The ADK would be responsible for parsing the incoming HTTP request
    into the 'payload' dictionary (e.g., from JSON body) and converting
    the returned dictionary into an HTTP response.

    Args:
        payload (dict): A dictionary representing the parsed request,
                        expected to contain a "query" key.

    Returns:
        dict: A dictionary representing the response to be sent to the client.
    """
    agent = get_agent() # Ensure agent is initialized
    user_query = payload.get("query")

    if not user_query:
        logging.warning("ADK Handler: Missing 'query' in payload.")
        return {"error": "Missing 'query' in payload", "status_code": 400}

    logging.info(f"ADK Handler received query: '{user_query}'")
    try:
        response_text = await agent.process_query(user_query)
        logging.info(f"ADK Handler - Agent response: {response_text}")
        return {"response": response_text}
    except Exception as e:
        logging.error(f"Error processing query via ADK Handler: {e}", exc_info=True)
        return {"error": f"An internal error occurred: {str(e)}", "status_code": 500}
