# 🛫 Smart Flight Search Agent

Hey there! Welcome to the Flight Search Agent project. This is a smart AI assistant that helps you find the best flight deals by combining the power of Google's ADK (Agent Development Kit) with Vertex AI's Gemini model.

## What does it do?

This little genius will:
- Chat with you about your flight needs through a friendly web interface
- Search for flights using not one, but TWO different search engines (Sky Scrapper and Google Flights via SerpApi)
- Compare all the options it finds to give you the best deals
- Show you nicely formatted results with all the details you need

Think of it as having your own AI travel agent that's always ready to help!

## Cool features

- **Works with Google ADK**: Built on Google's Agent Development Kit for a smooth experience
- **Smart conversation**: Understands what you're asking even when queries come in different formats
- **Double-checks flights**: Uses two different flight search tools and compares the results
- **Developer-friendly**: Easy to extend with more tools or customize for your needs
- **Helpful logging**: Keeps track of what's happening to make debugging a breeze

## Getting started

### 1. Set up your environment

First, clone this repo to your local machine, then:

```sh
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install the requirements
pip install -r requirements.txt
```

### 2. Set up your credentials

Create a `.env` file in the project root with these variables:

```
# Required settings
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1  # or your preferred region
GEMINI_MODEL_NAME=gemini-2.5-flash-preview-04-17  # or your preferred Gemini model

# API keys (required)
FLIGHTS_SCRAPER_SKY_API_KEY=your-key-here  # for the Sky Scrapper API
SERPAPI_KEY=your-key-here  # for Google Flights via SerpApi
```

You can copy these from the included `.env.example` file.

### 3. Run the agent

It's as simple as:

```sh
adk web
```

The ADK web interface will open, and you can start chatting with your flight agent!

## Using your flight agent

Just type queries like:
- "Find me a cheap flight from New York to London next week"
- "I need a round trip from San Francisco to Tokyo in June"
- "What are the best flight options from Berlin to Italy between August 10-15, 2025?"

The agent will do the rest - searching multiple sources and presenting you with the best options.

## Troubleshooting

Running into issues? Here are some common fixes:

- **Getting "No user query found"**: This usually means there's an issue with how the ADK is passing user input to the agent. Check the logs for details on the context object.

- **Seeing tool call errors**: Make sure both tools are provided in `send_message_async` calls - the model needs to know what tools are available.

- **API errors**: Check your Sky Scrapper and SerpApi API keys and usage limits. The free tiers have pretty strict quotas.

- **Issues with ADK web UI**: If the ADK web UI doesn't appear to be working correctly:
  - Make sure you have the latest version of the Google ADK
  - Try restarting the service with `adk web --restart`
  - Check the console for any error messages

## Project structure

- `flight_agent/agent.py` - The brains of the operation
- `flight_agent/tools/search_flights_tool.py` - The flight search tools
- `flight_agent/config.py` - Configuration settings
- `requirements.txt` - All the Python packages you need


## Want to extend it?

This agent is designed to be modular - you can easily:
- Add more flight search tools
- Change how results are displayed
- Modify the system prompt to handle different kinds of travel queries

For local testing without the ADK web interface, check out the `test_agent()` function in `agent.py`.

## License

MIT - Feel free to use this code however you'd like!