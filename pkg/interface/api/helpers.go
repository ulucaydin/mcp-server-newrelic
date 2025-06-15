package api

import (
	"encoding/json"
	"net/http"
)

// writeJSON writes a JSON response
func writeJSON(w http.ResponseWriter, status int, data interface{}) error {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	return json.NewEncoder(w).Encode(data)
}

// writeError writes an error response
func writeError(w http.ResponseWriter, status int, message string, details interface{}) {
	response := map[string]interface{}{
		"error":   message,
		"message": message,
	}
	
	if details != nil {
		response["details"] = details
	}
	
	writeJSON(w, status, response)
}