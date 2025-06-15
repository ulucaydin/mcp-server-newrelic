import nock from 'nock';
import { UDSClient } from '../src/client';
import { Schema, ListSchemasResponse } from '../src/types';

describe('DiscoveryService', () => {
  let client: UDSClient;
  const baseURL = 'http://localhost:8080';
  const apiPath = '/api/v1';

  beforeEach(() => {
    client = new UDSClient({ baseURL: baseURL + apiPath });
    nock.cleanAll();
  });

  afterEach(() => {
    nock.cleanAll();
  });

  describe('listSchemas', () => {
    it('should list schemas without options', async () => {
      const response: ListSchemasResponse = {
        schemas: [
          {
            name: 'Transaction',
            eventType: 'Transaction',
            attributes: [],
            recordCount: 1000000,
            firstSeen: '2024-01-01T00:00:00Z',
            lastSeen: '2024-12-01T00:00:00Z',
            quality: {
              overallScore: 0.85,
              completeness: 0.9,
              consistency: 0.85,
              validity: 0.8,
              uniqueness: 0.85
            }
          }
        ]
      };

      nock(baseURL)
        .get(`${apiPath}/discovery/schemas`)
        .reply(200, response);

      const result = await client.discovery.listSchemas();
      expect(result).toEqual(response);
    });

    it('should list schemas with options', async () => {
      const response: ListSchemasResponse = {
        schemas: [],
        metadata: {
          totalSchemas: 1,
          executionTime: '100ms',
          cacheHit: false
        }
      };

      nock(baseURL)
        .get(`${apiPath}/discovery/schemas`)
        .query({
          eventType: 'Transaction',
          minRecordCount: '1000',
          maxSchemas: '10',
          sortBy: 'recordCount',
          includeMetadata: 'true'
        })
        .reply(200, response);

      const result = await client.discovery.listSchemas({
        eventType: 'Transaction',
        minRecordCount: 1000,
        maxSchemas: 10,
        sortBy: 'recordCount',
        includeMetadata: true
      });
      expect(result).toEqual(response);
    });
  });

  describe('getSchema', () => {
    it('should get a specific schema', async () => {
      const schema: Schema = {
        name: 'Transaction',
        eventType: 'Transaction',
        attributes: [
          {
            name: 'timestamp',
            dataType: 'timestamp',
            nullable: false,
            cardinality: 1000000
          }
        ],
        recordCount: 1000000,
        firstSeen: '2024-01-01T00:00:00Z',
        lastSeen: '2024-12-01T00:00:00Z',
        quality: {
          overallScore: 0.85,
          completeness: 0.9,
          consistency: 0.85,
          validity: 0.8,
          uniqueness: 0.85
        }
      };

      nock(baseURL)
        .get(`${apiPath}/discovery/schemas/Transaction`)
        .reply(200, schema);

      const result = await client.discovery.getSchema('Transaction');
      expect(result).toEqual(schema);
    });

    it('should handle schema names with special characters', async () => {
      const schemaName = 'My Schema/With Special+Chars';
      const schema: Schema = {
        name: schemaName,
        eventType: schemaName,
        attributes: [],
        recordCount: 100,
        firstSeen: '2024-01-01T00:00:00Z',
        lastSeen: '2024-12-01T00:00:00Z',
        quality: {
          overallScore: 0.7,
          completeness: 0.7,
          consistency: 0.7,
          validity: 0.7,
          uniqueness: 0.7
        }
      };

      nock(baseURL)
        .get(`${apiPath}/discovery/schemas/${encodeURIComponent(schemaName)}`)
        .reply(200, schema);

      const result = await client.discovery.getSchema(schemaName);
      expect(result).toEqual(schema);
    });
  });

  describe('analyzeQuality', () => {
    it('should analyze schema quality', async () => {
      const quality = {
        overallScore: 0.85,
        completeness: 0.9,
        consistency: 0.85,
        validity: 0.8,
        uniqueness: 0.85,
        details: {
          missingAttributes: ['userId'],
          inconsistentTypes: []
        }
      };

      nock(baseURL)
        .post(`${apiPath}/discovery/schemas/Transaction/analyze`)
        .reply(200, quality);

      const result = await client.discovery.analyzeQuality('Transaction');
      expect(result).toEqual(quality);
    });
  });

  describe('compareSchemas', () => {
    it('should compare two schemas', async () => {
      const comparison = {
        differences: [
          {
            type: 'attribute_added',
            attribute: 'newField',
            details: { dataType: 'string' }
          }
        ],
        similarity: 0.95
      };

      nock(baseURL)
        .post(`${apiPath}/discovery/schemas/compare`, {
          schema1: 'Transaction',
          schema2: 'TransactionV2'
        })
        .reply(200, comparison);

      const result = await client.discovery.compareSchemas('Transaction', 'TransactionV2');
      expect(result).toEqual(comparison);
    });
  });

  describe('getRecommendations', () => {
    it('should get recommendations without event type', async () => {
      const recommendations = {
        recommendations: [
          {
            type: 'add_index',
            priority: 'high',
            description: 'Add index on timestamp field',
            impact: 'Improve query performance by 50%'
          }
        ]
      };

      nock(baseURL)
        .get(`${apiPath}/discovery/recommendations`)
        .reply(200, recommendations);

      const result = await client.discovery.getRecommendations();
      expect(result).toEqual(recommendations);
    });

    it('should get recommendations for specific event type', async () => {
      const recommendations = {
        recommendations: [
          {
            type: 'normalize_field',
            priority: 'medium',
            description: 'Normalize userAgent field',
            impact: 'Reduce storage by 20%',
            details: {
              field: 'userAgent',
              currentCardinality: 10000,
              expectedCardinality: 100
            }
          }
        ]
      };

      nock(baseURL)
        .get(`${apiPath}/discovery/recommendations`)
        .query({ eventType: 'Transaction' })
        .reply(200, recommendations);

      const result = await client.discovery.getRecommendations('Transaction');
      expect(result).toEqual(recommendations);
    });
  });
});