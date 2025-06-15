package client

import (
	"context"
)

// DashboardService handles dashboard creation API calls
type DashboardService struct {
	client *Client
}

// DashboardSpec contains the dashboard specification
type DashboardSpec struct {
	Name        string              `json:"name"`
	Description string              `json:"description,omitempty"`
	Widgets     []WidgetSpec        `json:"widgets"`
	Layout      map[string]interface{} `json:"layout,omitempty"`
}

// WidgetSpec defines a dashboard widget
type WidgetSpec struct {
	Type       string                 `json:"type"`
	Title      string                 `json:"title"`
	Query      string                 `json:"query"`
	Properties map[string]interface{} `json:"properties,omitempty"`
}

// Dashboard represents a created dashboard
type Dashboard struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Description string    `json:"description,omitempty"`
	URL         string    `json:"url"`
	CreatedAt   string    `json:"createdAt"`
}

// CreateDashboard creates a new dashboard from specification
func (s *DashboardService) CreateDashboard(ctx context.Context, spec *DashboardSpec) (*Dashboard, error) {
	var dashboard Dashboard
	err := s.client.post(ctx, "/dashboard/create", spec, &dashboard)
	return &dashboard, err
}