export { UDSClient } from './client';
export * from './types';
export { configureRetry, exponentialBackoffWithJitter } from './utils/retry';

// Re-export service classes for advanced usage
export { DiscoveryService } from './services/discovery';
export { PatternsService } from './services/patterns';
export { QueryService } from './services/query';
export { DashboardService } from './services/dashboard';