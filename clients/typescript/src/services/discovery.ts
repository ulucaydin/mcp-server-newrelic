import { AxiosInstance } from 'axios';
import { Schema, ListSchemasOptions, ListSchemasResponse } from '../types';

export class DiscoveryService {
  constructor(private readonly client: AxiosInstance) {}

  /**
   * List discovered schemas
   */
  async listSchemas(options?: ListSchemasOptions): Promise<ListSchemasResponse> {
    const params = new URLSearchParams();
    
    if (options?.eventType) {
      params.append('eventType', options.eventType);
    }
    if (options?.minRecordCount !== undefined) {
      params.append('minRecordCount', options.minRecordCount.toString());
    }
    if (options?.maxSchemas !== undefined) {
      params.append('maxSchemas', options.maxSchemas.toString());
    }
    if (options?.sortBy) {
      params.append('sortBy', options.sortBy);
    }
    if (options?.includeMetadata !== undefined) {
      params.append('includeMetadata', options.includeMetadata.toString());
    }

    const response = await this.client.get<ListSchemasResponse>('/discovery/schemas', {
      params: Object.fromEntries(params)
    });
    return response.data;
  }

  /**
   * Get a specific schema by name
   */
  async getSchema(name: string): Promise<Schema> {
    const response = await this.client.get<Schema>(`/discovery/schemas/${encodeURIComponent(name)}`);
    return response.data;
  }

  /**
   * Analyze schema quality
   */
  async analyzeQuality(name: string): Promise<Schema['quality']> {
    const response = await this.client.post<Schema['quality']>(
      `/discovery/schemas/${encodeURIComponent(name)}/analyze`
    );
    return response.data;
  }

  /**
   * Compare two schemas
   */
  async compareSchemas(schema1: string, schema2: string): Promise<{
    differences: Array<{
      type: string;
      attribute?: string;
      details: Record<string, unknown>;
    }>;
    similarity: number;
  }> {
    const response = await this.client.post<{
      differences: Array<{
        type: string;
        attribute?: string;
        details: Record<string, unknown>;
      }>;
      similarity: number;
    }>('/discovery/schemas/compare', {
      schema1,
      schema2
    });
    return response.data;
  }

  /**
   * Get schema recommendations
   */
  async getRecommendations(eventType?: string): Promise<{
    recommendations: Array<{
      type: string;
      priority: string;
      description: string;
      impact: string;
      details?: Record<string, unknown>;
    }>;
  }> {
    const params = eventType ? { eventType } : undefined;
    const response = await this.client.get<{
      recommendations: Array<{
        type: string;
        priority: string;
        description: string;
        impact: string;
        details?: Record<string, unknown>;
      }>;
    }>('/discovery/recommendations', { params });
    return response.data;
  }
}