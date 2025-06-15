import axios, { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios';
import { ClientConfig, APIError, HealthStatus } from './types';
import { configureRetry, exponentialBackoffWithJitter } from './utils/retry';
import { DiscoveryService } from './services/discovery';
import { PatternsService } from './services/patterns';
import { QueryService } from './services/query';
import { DashboardService } from './services/dashboard';

export class UDSClient {
  private readonly client: AxiosInstance;
  private readonly config: Required<ClientConfig>;
  
  public readonly discovery: DiscoveryService;
  public readonly patterns: PatternsService;
  public readonly query: QueryService;
  public readonly dashboard: DashboardService;

  constructor(config: ClientConfig = {}) {
    // Set defaults
    this.config = {
      baseURL: config.baseURL ?? 'http://localhost:8080/api/v1',
      apiKey: config.apiKey ?? '',
      timeout: config.timeout ?? 30000,
      retryMax: config.retryMax ?? 3,
      retryWait: config.retryWait ?? 1000,
      userAgent: config.userAgent ?? '@newrelic/uds-client/1.0.0'
    };

    // Create axios instance
    this.client = axios.create({
      baseURL: this.config.baseURL,
      timeout: this.config.timeout,
      headers: {
        'User-Agent': this.config.userAgent,
        'Content-Type': 'application/json'
      }
    });

    // Configure authentication
    if (this.config.apiKey) {
      this.client.defaults.headers.common['Authorization'] = `Bearer ${this.config.apiKey}`;
    }

    // Configure retry logic
    if (this.config.retryMax > 0) {
      configureRetry(this.client, {
        retries: this.config.retryMax,
        retryDelay: (retryCount) => exponentialBackoffWithJitter(retryCount, this.config.retryWait)
      });
    }

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response && error.response.data) {
          const apiError = error.response.data as APIError;
          apiError.statusCode = error.response.status;
          return Promise.reject(apiError);
        }
        return Promise.reject(error);
      }
    );

    // Initialize services
    this.discovery = new DiscoveryService(this.client);
    this.patterns = new PatternsService(this.client);
    this.query = new QueryService(this.client);
    this.dashboard = new DashboardService(this.client);
  }

  /**
   * Check the health status of the API
   */
  async health(): Promise<HealthStatus> {
    const response = await this.client.get<HealthStatus>('/health');
    return response.data;
  }

  /**
   * Make a custom request to the API
   */
  async request<T>(config: AxiosRequestConfig): Promise<T> {
    const response = await this.client.request<T>(config);
    return response.data;
  }

  /**
   * Update the API key
   */
  setApiKey(apiKey: string): void {
    this.config.apiKey = apiKey;
    if (apiKey) {
      this.client.defaults.headers.common['Authorization'] = `Bearer ${apiKey}`;
    } else {
      delete this.client.defaults.headers.common['Authorization'];
    }
  }

  /**
   * Get the current configuration
   */
  getConfig(): Readonly<Required<ClientConfig>> {
    return { ...this.config };
  }
}