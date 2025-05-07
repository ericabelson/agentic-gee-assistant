from google.adk.agents import Agent
from google.adk.tools import agent_tool
from google.adk.tools import google_search
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
    response = requests.get(url, timeout=5)
    return str(response.content)


# ==============================================================================
# Sub-agents
# ==============================================================================

gee_search_agent = Agent(
    name="gee_search_agent",
    model="gemini-2.5-pro-preview-05-06",
    description="Passes user requests to the Google Earth Engine catalog search tool.",
    instruction="""
        You are an agent that helps users find relevant datasets in Google Earth Engine.
    """,
    tools=[search_gee_catalog],
)

web_search_agent = Agent(
    name="web_search_agent",
    model="gemini-2.5-pro-preview-05-06",
    description="Performs a web search to find additional information about maps and datasets",
    instruction="""
        You are an agent that helps users perform web searches to find additional information about maps and datasets in Google Earth Engine.
    """,
    tools=[google_search],
)

web_fetch_agent = Agent(
    name="web_search_agent",
    model="gemini-2.5-pro-preview-05-06",
    description="Gets the content of a webpage given a URL",
    instruction="""
        You are an agent that fetches information from a web page.
    """,
    tools=[fetch_webpage_text],
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

        Use the GEE search agent to search the Google Earth Engine catalog.
        Use the web search agent to perform searches and find additional information.
        Use the web page retrieval agent to fetch content from a URL.

        Your top goal is to indicate and "check" off as many items from the top priority list and secondary priority list as possible.
        The user will provide more information in additional conversation turns if needed.
        You should ALWAYS output the summary of every message in the following format:

        ## Plain-English Summary

        A concise explanation of what the dataset measures and typical use cases (e.g., “Vegetation indices from MODIS, useful for NDVI-based land cover change”).

        ## Top priority list

        Dataset Title and GEE ID
        e.g. MODIS/006/MOD13Q1 with a short human-readable label.

        Temporal Coverage
        Start and end dates of data availability, update frequency (e.g., daily, 8-day composite, monthly), and any known delays or gaps.

        Spatial Resolution and Coverage
        Pixel size (e.g., 250m, 30m), and global vs. regional coverage.

        Usage Recommendations
        Situations where the dataset is especially valuable, and caveats (e.g., “Better for large-area trends; noisy in cloudy regions”).

        Comparison Notes
        When multiple datasets match the query, side-by-side notes highlight tradeoffs (e.g., “Use VIIRS for finer nightlight detail, but MODIS for longer historical range”).

        Direct GEE Catalog Link
        A clickable link to the dataset’s page in the Earth Engine Data Catalog for further exploration or manual use.

        ## Second priority list

        Band Information
        List of available bands with descriptions (e.g., NDVI, EVI, red, nir), data types, and common band-specific quirks.

        Access and Filtering Fields
        Metadata fields commonly used for filtering (e.g., system:time_start, CLOUD_COVER, QA bands) with guidance on how to use them effectively.

        Preview Guidance
        Recommendations on how to visualize the dataset quickly in Earth Engine (e.g., Map.addLayer() code snippet with good defaults).
    """,
    tools=[agent_tool.AgentTool(agent=gee_search_agent), agent_tool.AgentTool(agent=web_search_agent)],
)
