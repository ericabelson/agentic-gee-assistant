from google.adk.agents import Agent
import requests

# ==============================================================================
# Tools
# ==============================================================================

CATALOG_URL = "https://raw.githubusercontent.com/samapriya/awesome-gee-community-datasets/master/community_datasets.json"


def search_gee_catalog(query: str) -> str:
    """Searches the GEE catalog online based on a query string."""
    search_url = f"https://developers.google.com/s/results/earth-engine/datasets?q={query}"
    response = requests.get(search_url)
    return str(response.content)


def fetch_gee_catalog():
    """Fetches the GEE community catalog JSON from GitHub."""
    response = requests.get(CATALOG_URL, timeout=30)
    CATALOG_CACHE = response.json()
    return CATALOG_CACHE


def fetch_webpage_text(url: str) -> str:
    """
    Fetches the text content of a given webpage URL.

    Args:
        url: The URL of the webpage to fetch.
    """
    return None

# ==============================================================================
# Sub-agents
# ==============================================================================

gee_search_agent = Agent(
    name="gee_search_agent",
    model="gemini-2.5-pro-preview-05-06",
    description="Passes user requests to the GEE catalog search tool, which handles keyword extraction and searching.", # Slightly updated description
    instruction="""
        You are an agent that helps users find relevant datasets in Google Earth Engine.
        Take the user's research topic or description exactly as provided and pass it directly as the 'query' argument to the 'search_gee_catalog' tool.
        The tool itself will handle keyword extraction and searching.
        Return the results from the tool.
    """,
    tools=[search_gee_catalog],
)

# gee_dataset_details_agent = Agent(
#     name="gee-dataset-details-agent",
#     model="gemini-2.0-flash",
#     description="Fetches and analyzes GEE dataset pages to extract key metadata.",
#     instruction="""
#         You are an agent specialized in extracting information from Google Earth Engine dataset web pages.
#         Given a URL to a dataset's page provided by the previous agent:
#         1. Use the `fetch_webpage_text` tool to get the HTML content of the page.
#         2. Analyze the fetched text (HTML) to find the following details for the dataset:
#             - A brief description of what the dataset measures or represents.
#             - Spatial resolution (e.g., "30 meters", "1 degree").
#             - Temporal resolution or frequency (e.g., "Daily", "Monthly", "Every 16 days").
#             - Geographic coverage (e.g., "Global", "USA", "Specific region").
#             - Update frequency or date range (e.g., "Updated monthly", "2000-present").
#             - A short explanation of *why* someone might use this dataset (use case).
#         3. If you cannot find a specific piece of information after analyzing the text, clearly state "Information not found". Do not guess.
#         4. Return the extracted information as a JSON dictionary with keys: "description", "spatial_resolution", "temporal_resolution", "coverage", "update_frequency", "use_case".
#         5. If the webpage fetch fails or the content is unusable, return a JSON dictionary with an "error" key explaining the problem.
#     """,
#     tools=[fetch_webpage_text],
# )

# ==============================================================================
# Root Agent
# ==============================================================================

root_agent = Agent(
    name="gee_agent",
    model="gemini-2.5-pro-preview-05-06",
    description="""
        Coordinates the process of helping users discover and understand Google Earth Engine datasets.
        Asks the user for their needs, coordinates search and details agents, and presents the findings.
    """,
    instruction="""
        You are the primary coordinator for helping users find and understand GEE datasets.
        1. Take the user's description and pass it as a query to the search agent.
        2. The search agent will return a list of potential datasets, each with an 'id', 'title', and 'url'.
        3. If the search agent returns no results, inform the user.
        4. If results are found, iterate through the list (up to 5 results). For each dataset, take its 'url' and pass it to the `gee_dataset_details_agent`.
        5. The details agent will return a JSON dictionary containing extracted metadata (description, resolutions, coverage, etc.) or an error message.
        6. Compile the information received from the details agent for all datasets processed.
        7. Present a final summary to the user. For each dataset, clearly list:
            - Its title.
            - The extracted details (description, spatial/temporal resolution, coverage, update frequency, use case).
            - Explicitly mention if any specific detail was "Information not found".
            - If the details agent returned an error for a specific dataset (e.g., couldn't fetch URL), report that error.
        8. Format the final output clearly and make it easy for a beginner to understand which datasets might be relevant to their initial request.
    """,
    sub_agents=[gee_search_agent],
)
