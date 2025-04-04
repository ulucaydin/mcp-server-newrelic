import requests
import json
from typing import Optional, Dict, Any
import config # Use direct import as it's top-level

def execute_nerdgraph_query(query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes a NerdGraph query and returns the JSON response dictionary.

    Args:
        query: The GraphQL query string.
        variables: Optional dictionary of variables for parameterized queries.

    Returns:
        A dictionary representing the JSON response from NerdGraph, including potential 'errors'.
    """
    if not config.API_KEY: # Check API key again just in case
        return {"errors": [{"message": "Configuration error: API_KEY is not set."}]}

    headers = {
        "Content-Type": "application/json",
        "API-Key": config.API_KEY,
        "Accept": "application/json", # Ensure we get JSON back
    }
    payload: Dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables

    print(f"Executing NerdGraph Query:\nQuery: {query}\nVariables: {variables}")

    try:
        # Use constants from config module
        response = requests.post(config.NERDGRAPH_URL, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        error_message = "NerdGraph API request timed out."
        print(error_message)
        return {"errors": [{"message": error_message}]}
    except requests.exceptions.RequestException as e:
        error_message = f"NerdGraph API request failed: {e}"
        # Try to get more detail from response if available
        if e.response is not None:
            error_message += f" Status Code: {e.response.status_code}. Response: {e.response.text[:500]}" # Limit response length
        print(error_message)
        return {"errors": [{"message": error_message}]}
    except json.JSONDecodeError as e_json:
        error_message = f"Failed to decode NerdGraph API JSON response: {e_json}"
        # Attempt to access response text even if JSON decoding failed
        raw_response_text = ""
        if 'response' in locals() and hasattr(response, 'text'):
            raw_response_text = response.text[:500] # Limit response length
        print(error_message)
        return {"errors": [{"message": error_message, "raw_response": raw_response_text}]}

def format_json_response(result: Dict[str, Any]) -> str:
    """Formats the result dictionary as a JSON string for MCP return."""
    # Handle potential GraphQL errors reported within the JSON payload
    if "errors" in result and result["errors"]: # Check if errors list is not empty
        print(f"NerdGraph query returned errors: {json.dumps(result['errors'], indent=2)}")
        # Pass errors through in the JSON string
    elif "data" not in result and "errors" not in result:
         # If no 'data' and no 'errors', it might be an unexpected response format
         print(f"Warning: NerdGraph response missing 'data' and 'errors' fields: {json.dumps(result, indent=2)}")

    try:
        # Return the full result (including data and/or errors)
        return json.dumps(result, indent=2)
    except TypeError as e:
        error_message = f"Failed to serialize NerdGraph response to JSON: {e}"
        print(error_message)
        # Return an error structure if serialization fails
        return json.dumps({"errors": [{"message": error_message, "original_result_type": str(type(result))}]}) 