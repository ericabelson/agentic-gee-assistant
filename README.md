# Agent-Driven Exploration of Google Earth Engine Datasets

This repository contains an example multi-agent system built using [Agent
Development Kit (ADK)](https://google.github.io/adk-docs/), a free and open
source agent framework.

## Scope

This repo demonstrates how one can build a team of AI agents to augment the
process of discovering and understanding Earth Engine datasets.

Specifically, this system aims to:

- Search for relevant datasets in the EE catalog based on user queries
- Retrieve detailed information about specific datasets
- Provide agentic assistance in finding the most suitable datasets for research needs
- Help users understand dataset characteristics and usage

## Architecture

We used a multi-agent architecture in ADK:

- Root Agent (`gee_agent`): Acts as the supervisor, coordinating the overall workflow
- GEE Search Agent (`gee_search_agent`): Specializes in searching and filtering datasets in the GEE catalog
- Web Search Agent (`web_search_agent`): Specializes in performing web searches with Google to augment the GEE catalog
- Info Retrieval Agent (`web_fetch_agent`): Retrieves detailed information from URLs in any response

## Running the Agent

### Prerequisites

- Python 3.8 or higher
- [Agent Development Kit (ADK)](https://google.github.io/adk-docs/)

### Installation

1. Clone the Repository:
```bash
git clone https://github.com/ericabelson/agentic-gee-assistant.git
cd agentic-gee-assistant
```

2. Install Dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your [desired model settings](https://google.github.io/adk-docs/get-started/quickstart/#set-up-the-model) in the file `gee-agent/.env`.

4. Authenticate with the [Earth Engine CLI](https://developers.google.com/earth-engine/guides/auth):
```bash
earthengine authenticate
```

### Running with ADK

#### Web UI:
```bash
adk web
```
Navigate to http://localhost:8000 in your browser and select gee-discovery-agent.

#### Command Line:
```bash
adk run gee-agent
```
This starts an interactive chat session in your terminal.

## Contributing

This is a sample project built with Agent Development Kit. To join the ADK open
source movement, visit the
[Google ADK Python repository](https://github.com/google/adk-python)
to get started, talk with other agent builders, or make your contribution!


