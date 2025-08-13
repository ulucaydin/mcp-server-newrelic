import os

# Load API Key (Required)
API_KEY = os.getenv("NEW_RELIC_API_KEY")
if not API_KEY:
    raise ValueError("NEW_RELIC_API_KEY environment variable not set.")

# Load Account ID (Optional, but needed for many features)
ACCOUNT_ID_STR = os.getenv("NEW_RELIC_ACCOUNT_ID")
ACCOUNT_ID: int | None = None
if ACCOUNT_ID_STR:
    try:
        ACCOUNT_ID = int(ACCOUNT_ID_STR)
        print(f"Using New Relic Account ID: {ACCOUNT_ID}")
    except ValueError:
        # Don't raise immediately, let features that require it handle the None case
        print(f"Warning: NEW_RELIC_ACCOUNT_ID ('{ACCOUNT_ID_STR}') is not a valid integer. Features requiring an Account ID may fail.")
else:
    print("Warning: NEW_RELIC_ACCOUNT_ID environment variable not set. Some features require it.")


# NerdGraph API Endpoint
NERDGRAPH_URL = os.getenv("NERDGRAPH_URL")
if not NERDGRAPH_URL:
    NERDGRAPH_URL = "https://api.newrelic.com/graphql" 
