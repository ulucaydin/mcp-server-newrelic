import { AxiosInstance } from 'axios';
import { Dashboard, ListDashboardsOptions, ListDashboardsResponse } from '../types';

export class DashboardService {
  constructor(private readonly client: AxiosInstance) {}

  /**
   * List all dashboards
   */
  async list(options?: ListDashboardsOptions): Promise<ListDashboardsResponse> {
    const params = new URLSearchParams();
    
    if (options?.search) {
      params.append('search', options.search);
    }
    if (options?.tags && options.tags.length > 0) {
      options.tags.forEach(tag => params.append('tags', tag));
    }
    if (options?.limit !== undefined) {
      params.append('limit', options.limit.toString());
    }
    if (options?.offset !== undefined) {
      params.append('offset', options.offset.toString());
    }

    const response = await this.client.get<ListDashboardsResponse>('/dashboards', {
      params: Object.fromEntries(params)
    });
    return response.data;
  }

  /**
   * Get a specific dashboard by ID
   */
  async get(id: string): Promise<Dashboard> {
    const response = await this.client.get<Dashboard>(`/dashboards/${encodeURIComponent(id)}`);
    return response.data;
  }

  /**
   * Create a new dashboard
   */
  async create(dashboard: Omit<Dashboard, 'id' | 'createdAt' | 'updatedAt'>): Promise<Dashboard> {
    const response = await this.client.post<Dashboard>('/dashboards', dashboard);
    return response.data;
  }

  /**
   * Update an existing dashboard
   */
  async update(id: string, updates: Partial<Omit<Dashboard, 'id' | 'createdAt' | 'updatedAt'>>): Promise<Dashboard> {
    const response = await this.client.put<Dashboard>(`/dashboards/${encodeURIComponent(id)}`, updates);
    return response.data;
  }

  /**
   * Delete a dashboard
   */
  async delete(id: string): Promise<void> {
    await this.client.delete(`/dashboards/${encodeURIComponent(id)}`);
  }

  /**
   * Clone a dashboard
   */
  async clone(id: string, newName: string): Promise<Dashboard> {
    const response = await this.client.post<Dashboard>(`/dashboards/${encodeURIComponent(id)}/clone`, {
      name: newName
    });
    return response.data;
  }

  /**
   * Export a dashboard
   */
  async export(id: string, format: 'json' | 'yaml'): Promise<string> {
    const response = await this.client.get<string>(`/dashboards/${encodeURIComponent(id)}/export`, {
      params: { format },
      responseType: 'text'
    });
    return response.data;
  }

  /**
   * Import a dashboard
   */
  async import(data: string, format: 'json' | 'yaml'): Promise<Dashboard> {
    const response = await this.client.post<Dashboard>('/dashboards/import', data, {
      headers: {
        'Content-Type': format === 'json' ? 'application/json' : 'application/x-yaml'
      }
    });
    return response.data;
  }

  /**
   * Get dashboard tags
   */
  async getTags(): Promise<string[]> {
    const response = await this.client.get<string[]>('/dashboards/tags');
    return response.data;
  }

  /**
   * Render a dashboard widget
   */
  async renderWidget(dashboardId: string, widgetId: string, variables?: Record<string, unknown>): Promise<{
    data: unknown;
    visualization: Record<string, unknown>;
    metadata?: Record<string, unknown>;
  }> {
    const response = await this.client.post<{
      data: unknown;
      visualization: Record<string, unknown>;
      metadata?: Record<string, unknown>;
    }>(`/dashboards/${encodeURIComponent(dashboardId)}/widgets/${encodeURIComponent(widgetId)}/render`, {
      variables
    });
    return response.data;
  }
}