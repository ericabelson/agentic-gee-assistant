import pymupdf
import requests
from biorxiv_retriever import BiorxivRetriever
from google.adk.agents import Agent

# ==============================================================================
# Tools
# ==============================================================================


def search_biorxiv(query: str):
    """Search for scientific publications on biorXiv"""
    br = BiorxivRetriever()
    papers = br.query(query)
    return papers


def download_biorxiv_paper(biorxiv_url: str):
    """Download a paper from biorXiv"""
    url = biorxiv_url + ".full.pdf"
    r = requests.get(url, allow_redirects=True)
    open("paper.pdf", "wb").write(r.content)
    return("Downloads complete!")


def load_pdf():
    """Load downloaded PDF file as text"""
    doc = pymupdf.open("downloads/paper.pdf")
    out = []
    for page in doc:
        text = page.get_text()
        out.append(text)
    print(out)
    return(" ".join(out))

# ==============================================================================
# Sub-agents
# ==============================================================================

search_agent = Agent(
    name="search_agent",
    model="gemini-2.5-pro-preview-03-25",
    description=("Look up and answer questions about research on biorXiv."),
    instruction=(
        """
        You are a helpful agent who can search papers on biorXiv. Given input from
        the user, rewrite their query to search for papers on biorXiv.
        """
    ),
    tools=[search_biorxiv],
)

methodologies_agent = Agent(
    name="methodologies_agent",
    model="gemini-2.5-pro-preview-03-25",
    description=("""
                 You are a helpful agent who extracts research methodologies
                 used in scientific papers.
                 """),
    instruction=(
        """
        1. You'll receive a list of papers
        2. Download a random paper from the list
        3. Load a PDF of the paper and extract all methodologies used
        4. Repeat this process until you've downloaded and extracted 3 papers
        """
    ),
    tools=[download_biorxiv_paper, load_pdf]
)

# ==============================================================================
# Root Agent
# ==============================================================================

root_agent = Agent(
    name="research_agent",
    model="gemini-2.5-pro-preview-03-25",
    description=(
        """
        Agent that coordinates literature searches, extracts research
        methodologies, and summarizes them.
        """
    ),
    instruction=(
        """
        1. Receive user input
        2. Coordinate a literature searches
        3. Coordinate research methodology extraction
        4. Summarize your findings and include a table of the methodologies used
        """
    ),
    sub_agents=[search_agent, methodologies_agent],
)
