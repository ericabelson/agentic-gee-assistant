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
    return None

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
    """,
    tools=[agent_tool.AgentTool(agent=gee_search_agent), agent_tool.AgentTool(agent=web_search_agent)],
)
