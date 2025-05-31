import asyncio
import logging
from flight_agent.agent import FlightSearchAgent

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    setup_logging()
    agent = FlightSearchAgent()
    print("Welcome to the Flight Search Assistant! Type 'exit' to quit.")
    while True:
        user_query = input("\nPlease enter your flight search query: ")
        if user_query.strip().lower() in ("exit", "quit"): 
            print("Goodbye!")
            break
        response = await agent.process_query(user_query)
        print("\n--- Assistant's Response ---")
        print(response)
        print("---------------------------")

if __name__ == "__main__":
    asyncio.run(main())
