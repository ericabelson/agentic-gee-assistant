from google.adk.agents import Agent
import requests
import os
import json
import logging
import re # Add this import
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
CATALOG_KEYWORDS_CACHE = None # Add near line 18


def extract_catalog_keywords(catalog_data: list) -> list[str]:
    """
    Extracts potential keywords from titles and descriptions in the catalog data.

    Args:
        catalog_data: The list of dataset dictionaries from the fetched catalog.

    Returns:
        A sorted list of unique potential keywords (lowercase, > 2 chars, not numeric).
    """
    if not catalog_data:
        return []

    keywords = set()
    logger.info(f"Extracting keywords from {len(catalog_data)} catalog items...")

    for item in catalog_data:
        text_to_process = []
        title = item.get("title", "")
        description = item.get("description", "")
        if title:
            text_to_process.append(title)
        if description:
            text_to_process.append(description)

        full_text = " ".join(text_to_process).lower()
        # Use regex to find words (alphanumeric sequences)
        potential_words = re.findall(r'\b[a-z0-9]+\b', full_text)

        for word in potential_words:
            # Filter: length > 2 and not purely numeric
            if len(word) > 2 and not word.isdigit():
                keywords.add(word)

    sorted_keywords = sorted(list(keywords))
    logger.info(f"Extracted {len(sorted_keywords)} unique potential keywords.")
    return sorted_keywords


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
                     CATALOG_CACHE = []
            logger.info(f"Successfully fetched and cached {len(CATALOG_CACHE)} datasets.")

            # Extract and cache keywords immediately after fetching
            global CATALOG_KEYWORDS_CACHE
            CATALOG_KEYWORDS_CACHE = extract_catalog_keywords(CATALOG_CACHE)
            # --- End Modification ---

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching GEE catalog: {e}")
            # Fallback or error handling: return empty list or raise exception
            # For now, return empty list to allow agent to report failure
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding GEE catalog JSON: {e}")
            return []
    return CATALOG_CACHE


def get_catalog_keywords() -> list[str]:
    """Returns the cached list of extracted keywords from the GEE catalog."""
    global CATALOG_KEYWORDS_CACHE
    if CATALOG_KEYWORDS_CACHE is None:
        logger.warning("Catalog keywords requested before they were extracted.")
        # Attempt to fetch and extract if not done yet
        fetch_gee_catalog() # This will trigger extraction if needed
        if CATALOG_KEYWORDS_CACHE is None: # Check again if fetch/extract failed
             return ["Error: Keywords not available"]
    # Return a copy to prevent modification? For now, return directly.
    return CATALOG_KEYWORDS_CACHE


# Change signature from query: str to matched_keywords: list[str]
def search_gee_catalog(matched_keywords: list[str]):
    """
    Searches the fetched GEE catalog based on a list of matched keywords.

    Args:
        matched_keywords: A list of keywords identified as relevant to the user's query.

    Returns:
        A list of dictionaries, each containing 'id', 'title', and 'url'
        for matching datasets, limited to a maximum of 5 results.
        Returns an empty list if the catalog couldn't be fetched or no matches are found.
    """
    catalog = fetch_gee_catalog()
    if not catalog: # Handle case where catalog fetch failed
        logger.warning("Search failed: GEE catalog is empty or could not be fetched.")
        return [{"error": "Catalog unavailable"}]

    # --- Remove Keyword Extraction Block ---
    # --- End Removal ---

    # --- Use matched_keywords directly ---
    if not matched_keywords or not isinstance(matched_keywords, list) or not all(isinstance(k, str) for k in matched_keywords):
         logger.warning(f"Invalid or empty matched_keywords received: {matched_keywords}")
         # Return specific info message
         return [{"info": "No valid keywords were provided for searching the catalog."}]

    # Ensure keywords are lowercase (matcher agent should ideally provide them lowercase)
    search_terms = [k.lower() for k in matched_keywords]
    logger.info(f"Searching through {len(catalog)} fetched datasets for matched keywords: {search_terms}")
    # --- End Use matched_keywords ---


    results = []
    processed_ids = set()

    for item in catalog:
        # Search in title, description
        title = item.get("title", "")
        description = item.get("description", "")
        # url = item.get("sample_code_url", "") # Keep url retrieval for later

        # Combine text for searching (already lowercased during extraction)
        title_lower = title.lower()
        description_lower = description.lower()

        # Check if ANY extracted keyword matches title or description
        match_found = False
        for term in search_terms:
            if term in title_lower or term in description_lower:
                match_found = True
                break # Found a match for this item with one keyword

        if match_found:
            # ... (rest of the result appending logic remains the same) ...
            dataset_id = item.get("id")
            url = item.get("sample_code_url", "") # Get URL here
            # Ensure we have essential fields and haven't added this dataset already
            if dataset_id and title and url and dataset_id not in processed_ids:
                results.append({
                    "id": dataset_id,
                    "title": title,
                    "url": url
                })
                processed_ids.add(dataset_id) # Mark as added
                if len(results) >= 5: # Limit results
                    logger.info("Reached maximum result limit (5).")
                    break
            # else: # Optional logging for skipped items
            #    logger.debug(f"Skipping dataset due to missing info or duplicate: {dataset_id or 'N/A'}")


    # Update final log message
    logger.info(f"Found {len(results)} datasets matching keywords {search_terms}.")
    if not results:
         # Update info message
         return [{"info": f"No datasets found matching the provided keywords: {', '.join(search_terms)}"}]
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

gee_keyword_matcher_agent = Agent(
    name="gee_keyword_matcher_agent",
    model="gemini-2.0-flash", # Or a model good at classification/matching
    description="Matches a user's query against a pre-defined list of GEE catalog keywords.",
    instruction="""
        You are an expert at understanding user needs related to geospatial data and matching them to relevant technical keywords.
        Your task is to identify the most relevant keywords from a specific list, based on the user's query.
        1. Use the `get_catalog_keywords` tool to retrieve the list of valid keywords extracted from the GEE community catalog. Handle potential errors if the list is unavailable.
        2. Analyze the user's query provided to you.
        3. Compare the user's query against the retrieved list of valid keywords.
        4. Identify and select the keywords from the list that best represent the concepts, topics, or data types mentioned in the user's query.
        5. Prioritize keywords that seem most specific and relevant.
        6. Return ONLY a JSON list of the selected keyword strings. For example: ["ndvi", "sentinel-2", "precipitation", "california"].
        7. If no relevant keywords are found in the list, return an empty list [].
        8. Do not add any keywords that are not present in the list obtained from the tool.
        9. Do not add explanations or introductory text, just the JSON list of strings.
    """,
    tools=[get_catalog_keywords], # Provide the tool to access the keywords
)


gee_search_agent = Agent(
    name="gee_search_agent",
    model="gemini-2.0-flash",
    # --- Start Modification ---
    description="Searches the GEE catalog using a pre-defined list of relevant keywords.",
    instruction="""
        You are an agent that searches the GEE community catalog.
        You will receive a list of relevant keywords that have already been matched to the user's request.
        1. Take the provided list of keywords exactly as given.
        2. Pass this list directly as the 'matched_keywords' argument to the 'search_gee_catalog' tool.
        3. Return the results from the tool (which will be a list of found datasets or an info/error message).
    """,
    # The tool function name is the same, but its signature changed.
    # The framework should handle passing the list input if the root agent orchestrates correctly.
    tools=[search_gee_catalog],
    # --- End Modification ---
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
    name="gee_discovery_agent",
    model="gemini-2.0-flash",
    description="""
        Coordinates the process of helping users discover and understand Google Earth Engine datasets.
        Asks the user for their needs, coordinates keyword matching, search, and details agents, and presents the findings.
    """, # Updated description
    instruction="""
        You are the primary coordinator for helping users find and understand GEE datasets.
        1. Start by asking the user to describe what they want to study, what kind of data they need, or the geographic area and time period they are interested in.
        2. Take the user's description and pass it as input to the `gee_keyword_matcher_agent`.
        3. The matcher agent will return a JSON list of relevant keywords found in the catalog's pre-extracted list.
        4. If the matcher agent returns an empty list or an error, inform the user that no relevant keywords could be identified for their query in the catalog. Do not proceed further with the search.
        5. If relevant keywords are returned, take this list of keywords and pass it to the `gee_search_agent`.
        6. The search agent will use these keywords to search the catalog and return a list of potential datasets (each with 'id', 'title', 'url') or an info/error message.
        7. If the search agent returns no results (or an info message indicating no datasets found), inform the user based on the keywords used.
        8. If search results are found, iterate through the list (up to 5 results). For each dataset, take its 'url' and pass it to the `gee_dataset_details_agent`.
        9. The details agent will return a JSON dictionary containing extracted metadata or an error message.
        10. Compile the information received from the details agent for all datasets processed.
        11. Present a final summary to the user. For each dataset found by the search agent, clearly list:
            - Its title.
            - The extracted details (description, spatial/temporal resolution, coverage, update frequency, use case).
            - Explicitly mention if any specific detail was "Information not found".
            - If the details agent returned an error for a specific dataset (e.g., couldn't fetch URL), report that error.
        12. Format the final output clearly and make it easy for a beginner to understand which datasets might be relevant to their initial request. Mention the keywords that were used for the search.
    """,
    # --- Start Modification ---
    sub_agents=[gee_keyword_matcher_agent, gee_search_agent, gee_dataset_details_agent], # Add matcher agent
    # --- End Modification ---
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
