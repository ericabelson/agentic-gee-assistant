from google.adk.agents import Agent
import requests
import os
import json
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn # Although not directly used in code, good practice to have if running via script

# ==============================================================================
# Tools
# ==============================================================================

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CATALOG_URL = "https://raw.githubusercontent.com/samapriya/awesome-gee-community-datasets/master/community_datasets.json"
CATALOG_CACHE = None

def fetch_gee_catalog():
    """Fetches the GEE community catalog JSON from GitHub."""
    global CATALOG_CACHE
    if CATALOG_CACHE is None:
        try:
            logger.info(f"Fetching GEE catalog from {CATALOG_URL}...")
            response = requests.get(CATALOG_URL, timeout=30)
            response.raise_for_status()  # Raise an exception for bad status codes
            CATALOG_CACHE = response.json()
            # Ensure the fetched data is a list
            if not isinstance(CATALOG_CACHE, list):
                 # If the top level is a dict with a 'datasets' key (like some catalog formats)
                 if isinstance(CATALOG_CACHE, dict) and 'datasets' in CATALOG_CACHE and isinstance(CATALOG_CACHE['datasets'], list):
                     CATALOG_CACHE = CATALOG_CACHE['datasets']
                 else:
                     logger.error("Fetched catalog is not in the expected list format.")
                     CATALOG_CACHE = [] # Set to empty list on format error
                     # Or raise an error: raise ValueError("Fetched catalog is not a list")
            logger.info(f"Successfully fetched and cached {len(CATALOG_CACHE)} datasets.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching GEE catalog: {e}")
            # Fallback or error handling: return empty list or raise exception
            # For now, return empty list to allow agent to report failure
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding GEE catalog JSON: {e}")
            return []
    return CATALOG_CACHE

def search_gee_catalog(query: str):
    """
    Searches the fetched GEE catalog based on a query string.

    Args:
        query: The search term provided by the user or agent.

    Returns:
        A list of dictionaries, each containing 'id', 'title', and 'url'
        for matching datasets, limited to a maximum of 5 results.
        Returns an empty list if the catalog couldn't be fetched or no matches are found.
    """
    catalog = fetch_gee_catalog()
    if not catalog: # Handle case where catalog fetch failed
        logger.warning("Search failed: GEE catalog is empty or could not be fetched.")
        return []

    results = []
    query_lower = query.lower()
    logger.info(f"Searching through {len(catalog)} fetched datasets for query: '{query}'")

    for item in catalog:
        # Search in title, description, and potentially keywords if available
        title = item.get("title", "")
        description = item.get("description", "")
        # Use 'sample_code_url' as the link to the dataset page from the community catalog
        url = item.get("sample_code_url", "")

        # Combine text for searching
        searchable_text = f"{title} {description}".lower()

        # Simple search: check if query is in the combined text
        # More sophisticated matching (like checking all terms) could be added here
        if query_lower in searchable_text:
             # Ensure we have the essential fields, especially the URL for the next step
            if item.get("id") and title and url:
                results.append({
                    "id": item.get("id"),
                    "title": title,
                    "url": url # Add the URL field
                })
                if len(results) >= 5: # Limit results
                    logger.info("Reached maximum result limit (5).")
                    break
            else:
                # Log if a potential match is skipped due to missing essential info
                logger.debug(f"Skipping dataset due to missing id, title, or url: {item.get('id') or 'N/A'}")

    logger.info(f"Found {len(results)} datasets matching query '{query}'.")
    return results

# --- New Tool ---
def fetch_webpage_text(url: str) -> str:
    """
    Fetches the text content of a given webpage URL.

    Args:
        url: The URL of the webpage to fetch.

    Returns:
        The text content of the page, or an error message if fetching fails.
        Note: This currently returns raw HTML. Further processing (e.g., using
        BeautifulSoup) might be needed for cleaner text extraction, but we rely
        on the LLM's ability to parse HTML for now.
    """
    if not url or not url.startswith(('http://', 'https://')):
        logger.warning(f"Invalid URL provided to fetch_webpage_text: {url}")
        return "Error: Invalid or missing URL."
    try:
        logger.info(f"Fetching webpage content from: {url}")
        headers = {'User-Agent': 'Mozilla/5.0'} # Add a user-agent
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        # TODO: Consider adding HTML parsing (e.g., BeautifulSoup) here
        # for cleaner text, but let's rely on the LLM for now.
        logger.info(f"Successfully fetched content from: {url}")
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching URL {url}: {e}")
        return f"Error: Could not fetch content from {url}. Reason: {e}"
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching {url}: {e}")
        return f"Error: An unexpected error occurred while fetching {url}."

# ==============================================================================
# Sub-agents
# ==============================================================================

gee_search_agent = Agent(
    name="gee_search_agent",
    model="gemini-2.0-flash",
    description="Searches the Google Earth Engine catalog for datasets based on user needs.",
    instruction="""
        You are an agent that helps users find relevant datasets in Google Earth Engine.
        Given a user's research topic or description, use the search_gee_catalog tool to find up to 5 relevant datasets.
        Return the list of datasets to the next agent.
    """,
    tools=[search_gee_catalog],
)

gee_dataset_details_agent = Agent(
    name="gee_dataset_details_agent",
    model="gemini-2.0-flash", # Or consider a more powerful model if needed for analysis
    description="Fetches and analyzes GEE dataset pages to extract key metadata.",
    instruction="""
        You are an agent specialized in extracting information from Google Earth Engine dataset web pages.
        Given a URL to a dataset's page provided by the previous agent:
        1. Use the `fetch_webpage_text` tool to get the HTML content of the page.
        2. Analyze the fetched text (HTML) to find the following details for the dataset:
            - A brief description of what the dataset measures or represents.
            - Spatial resolution (e.g., "30 meters", "1 degree").
            - Temporal resolution or frequency (e.g., "Daily", "Monthly", "Every 16 days").
            - Geographic coverage (e.g., "Global", "USA", "Specific region").
            - Update frequency or date range (e.g., "Updated monthly", "2000-present").
            - A short explanation of *why* someone might use this dataset (use case).
        3. If you cannot find a specific piece of information after analyzing the text, clearly state "Information not found". Do not guess.
        4. Return the extracted information as a JSON dictionary with keys: "description", "spatial_resolution", "temporal_resolution", "coverage", "update_frequency", "use_case".
        5. If the webpage fetch fails or the content is unusable, return a JSON dictionary with an "error" key explaining the problem.
    """,
    tools=[fetch_webpage_text],
)

# ==============================================================================
# Root Agent
# ==============================================================================

root_agent = Agent(
    name="gee_discovery_agent", # Keep the name for identification unless asked to change
    model="gemini-2.0-flash",
    description="""
        Coordinates the process of helping users discover and understand Google Earth Engine datasets.
        Asks the user for their needs, coordinates search and details agents, and presents the findings.
    """,
    instruction="""
        You are the primary coordinator for helping users find and understand GEE datasets.
        1. Start by asking the user to describe what they want to study, what kind of data they need, or the geographic area and time period they are interested in.
        2. Take the user's description and pass it as a query to the `gee_search_agent`.
        3. The search agent will return a list of potential datasets, each with an 'id', 'title', and 'url'.
        4. If the search agent returns no results, inform the user.
        5. If results are found, iterate through the list (up to 5 results). For each dataset, take its 'url' and pass it to the `gee_dataset_details_agent`.
        6. The details agent will return a JSON dictionary containing extracted metadata (description, resolutions, coverage, etc.) or an error message.
        7. Compile the information received from the details agent for all datasets processed.
        8. Present a final summary to the user. For each dataset, clearly list:
            - Its title.
            - The extracted details (description, spatial/temporal resolution, coverage, update frequency, use case).
            - Explicitly mention if any specific detail was "Information not found".
            - If the details agent returned an error for a specific dataset (e.g., couldn't fetch URL), report that error.
        9. Format the final output clearly and make it easy for a beginner to understand which datasets might be relevant to their initial request.
    """,
    sub_agents=[gee_search_agent, gee_dataset_details_agent], # Updated sub_agents
)

# ==============================================================================
# FastAPI Web Server
# ==============================================================================

app = FastAPI(
    title="GEE Dataset Discovery Agent API",
    description="API endpoint to interact with the GEE Discovery Agent.",
    version="0.1.0",
)

# Define the request body model using Pydantic
class DiscoveryRequest(BaseModel):
    user_need: str

# Define the API endpoint
@app.post("/discover", summary="Discover GEE Datasets")
async def discover_datasets(request: DiscoveryRequest):
    """
    Receives a user's need, runs the GEE discovery agent, and returns the result.
    """
    logger.info(f"Received discovery request for: {request.user_need}")
    try:
        # Start a conversation with the root agent
        # Note: Depending on google-adk's design, creating a new conversation
        # per request might be necessary or inefficient. Consider agent lifecycle.
        conversation = root_agent.start_conversation()
        # Send the user's need as the first message
        response = conversation.send_message(request.user_need)
        logger.info("Agent conversation completed successfully.")
        # The response from the agent is expected to be a string summarizing the findings
        return {"result": response}
    except Exception as e:
        logger.error(f"Error during agent execution via API: {str(e)}", exc_info=True)
        # Return an HTTP exception if something goes wrong
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")

# Optional: Add a root endpoint for basic health check or info
@app.get("/", summary="API Root/Health Check")
async def read_root():
    return {"message": "GEE Discovery Agent API is running."}


# Note: The `if __name__ == "__main__":` block for direct script execution
# has been removed. To run the server, use Uvicorn:
# uvicorn agent:app --reload --port 8000
