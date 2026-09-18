import { render, screen, fireEvent, waitFor } from '@testing-library/jest-dom';
import { results } from '../../src/app/ui/results.js';

describe('Results Service', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    localStorage.clear();
  });

  afterEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  describe('loadResults', () => {
    test('should load results from storage', async () => {
      const mockResults = [
        {
          id: 'run-1',
          name: 'First Run',
          modelId: 'model-1',
          engineId: 'engine-1',
          temperature: 0.7,
          maxTokens: 512,
          qualityScore: 0.85,
          completionTimeMs: 2340,
          numFwdOps: 1024,
          numParams: 7B,
          numTokens: 256,
          throughputTokensPerSec: 109,
          throughputTokensPerMs: 0.000109,
          qualityMetrics: {
            coherence: 0.8,
            relevance: 0.9,
            fluency: 0.85,
          },
        },
      ];
      localStorage.setItem('benchmark_results', JSON.stringify(mockResults));
      
      await results.loadResults();
      
      expect(results.results).toEqual(mockResults);
    });

    test('should initialize empty results array', async () => {
      localStorage.clear();
      await results.loadResults();
      
      expect(results.results).toEqual([]);
    });

    test('should persist results to storage', async () => {
      const mockResult = {
        id: 'run-1',
        name: 'Test Run',
        modelId: 'model-1',
        engineId: 'engine-1',
        temperature: 0.7,
        maxTokens: 512,
        qualityScore: 0.85,
        completionTimeMs: 2340,
        numFwdOps: 1024,
        numParams: 7B,
        numTokens: 256,
        throughputTokensPerSec: 109,
        throughputTokensPerMs: 0.000109,
        qualityMetrics: {
          coherence: 0.8,
          relevance: 0.9,
          fluency: 0.85,
        },
      };
      
      results.saveResult(mockResult);
      localStorage.setItem('benchmark_results', JSON.stringify(mockResults));
      
      await results.loadResults();
      
      expect(results.results).toHaveLength(1);
      expect(results.results[0]).toEqual(mockResult);
    });
  });

  describe('saveResult', () => {
    test('should save new result', () => {
      const mockResult = {
        id: 'run-1',
        name: 'New Run',
        modelId: 'model-1',
        engineId: 'engine-1',
        temperature: 0.7,
        maxTokens: 512,
        qualityScore: 0.85,
        completionTimeMs: 2340,
        numFwdOps: 1024,
        numParams: 7B,
        numTokens: 256,
        throughputTokensPerSec: 109,
        throughputTokensPerMs: 0.000109,
        qualityMetrics: {
          coherence: 0.8,
          relevance: 0.9,
          fluency: 0.85,
        },
      };
      
      results.saveResult(mockResult);
      
      expect(results.results).toHaveLength(1);
      expect(results.results[0]).toEqual(mockResult);
    });

    test('should update existing result by ID', () => {
      const mockResult = {
        id: 'run-1',
        name: 'Original Name',
        modelId: 'model-1',
        engineId: 'engine-1',
        temperature: 0.7,
        maxTokens: 512,
        qualityScore: 0.85,
        completionTimeMs: 2340,
        numFwdOps: 1024,
        numParams: 7B,
        numTokens: 256,
        throughputTokensPerSec: 109,
        throughputTokensPerMs: 0.000109,
        qualityMetrics: {
          coherence: 0.8,
          relevance: 0.9,
          fluency: 0.85,
        },
      };
      
      results.saveResult(mockResult);
      
      const updatedResult = {
        id: 'run-1',
        name: 'Updated Name',
        modelId: 'model-1',
        engineId: 'engine-1',
        temperature: 0.7,
        maxTokens: 512,
        qualityScore: 0.9,
        completionTimeMs: 2000,
        numFwdOps: 1024,
        numParams: 7B,
        numTokens: 256,
        throughputTokensPerSec: 112,
        throughputTokensPerMs: 0.000112,
        qualityMetrics: {
          coherence: 0.85,
          relevance: 0.95,
          fluency: 0.9,
        },
      };
      
      results.saveResult(updatedResult);
      
      expect(results.results[0].name).toBe('Updated Name');
      expect(results.results[0].qualityScore).toBe(0.9);
    });

    test('should remove result by ID', () => {
      const mockResult = {
        id: 'run-1',
        name: 'Run to Delete',
        modelId: 'model-1',
        engineId: 'engine-1',
        temperature: 0.7,
        maxTokens: 512,
        qualityScore: 0.85,
        completionTimeMs: 2340,
        numFwdOps: 1024,
        numParams: 7B,
        numTokens: 256,
        throughputTokensPerSec: 109,
        throughputTokensPerMs: 0.000109,
        qualityMetrics: {
          coherence: 0.8,
          relevance: 0.9,
          fluency: 0.85,
        },
      };
      
      results.saveResult(mockResult);
      
      expect(results.results).toHaveLength(1);
      
      results.removeResult('run-1');
      
      expect(results.results).toHaveLength(0);
    });
  });

  describe('clearResults', () => {
    test('should clear all results', () => {
      const mockResult = {
        id: 'run-1',
        name: 'Run to Clear',
        modelId: 'model-1',
        engineId: 'engine-1',
        temperature: 0.7,
        maxTokens: 512,
        qualityScore: 0.85,
        completionTimeMs: 2340,
        numFwdOps: 1024,
        numParams: 7B,
        numTokens: 256,
        throughputTokensPerSec: 109,
        throughputTokensPerMs: 0.000109,
        qualityMetrics: {
          coherence: 0.8,
          relevance: 0.9,
          fluency: 0.85,
        },
      };
      
      results.saveResult(mockResult);
      
      expect(results.results).toHaveLength(1);
      
      results.clearResults();
      
      expect(results.results).toHaveLength(0);
    });
  });

  describe('results', () => {
    test('should return empty array initially', () => {
      localStorage.clear();
      
      expect(results.results).toEqual([]);
    });

    test('should return results array', () => {
      const mockResults = [
        {
          id: 'run-1',
          name: 'Run 1',
          modelId: 'model-1',
          engineId: 'engine-1',
          temperature: 0.7,
          maxTokens: 512,
          qualityScore: 0.85,
          completionTimeMs: 2340,
          numFwdOps: 1024,
          numParams: 7B,
          numTokens: 256,
          throughputTokensPerSec: 109,
          throughputTokensPerMs: 0.000109,
          qualityMetrics: {
            coherence: 0.8,
            relevance: 0.9,
            fluency: 0.85,
          },
        },
      ];
      
      results.results = mockResults;
      
      expect(results.results).toEqual(mockResults);
    });

    test('should update results array', () => {
      results.results = [
        {
          id: 'run-1',
          name: 'Run 1',
          modelId: 'model-1',
          engineId: 'engine-1',
          temperature: 0.7,
          maxTokens: 512,
          qualityScore: 0.85,
          completionTimeMs: 2340,
          numFwdOps: 1024,
          numParams: 7B,
          numTokens: 256,
          throughputTokensPerSec: 109,
          throughputTokensPerMs: 0.000109,
          qualityMetrics: {
            coherence: 0.8,
            relevance: 0.9,
            fluency: 0.85,
          },
        },
      ];
      
      results.results = [
        {
          id: 'run-2',
          name: 'Run 2',
          modelId: 'model-2',
          engineId: 'engine-2',
          temperature: 0.8,
          maxTokens: 1024,
          qualityScore: 0.9,
          completionTimeMs: 2000,
          numFwdOps: 2048,
          numParams: 13B,
          numTokens: 512,
          throughputTokensPerSec: 153,
          throughputTokensPerMs: 0.000153,
          qualityMetrics: {
            coherence: 0.85,
            relevance: 0.95,
            fluency: 0.9,
          },
        },
      ];
      
      expect(results.results).toHaveLength(1);
      expect(results.results[0].id).toBe('run-2');
    });
  });

  describe('getResults', () => {
    test('should return filtered results', () => {
      const mockResults = [
        {
          id: 'run-1',
          name: 'Run 1',
          modelId: 'model-1',
          engineId: 'engine-1',
          temperature: 0.7,
          maxTokens: 512,
          qualityScore: 0.85,
          completionTimeMs: 2340,
          numFwdOps: 1024,
          numParams: 7B,
          numTokens: 256,
          throughputTokensPerSec: 109,
          throughputTokensPerMs: 0.000109,
          qualityMetrics: {
            coherence: 0.8,
            relevance: 0.9,
            fluency: 0.85,
          },
        },
        {
          id: 'run-2',
          name: 'Run 2',
          modelId: 'model-2',
          engineId: 'engine-2',
          temperature: 0.8,
          maxTokens: 1024,
          qualityScore: 0.9,
          completionTimeMs: 2000,
          numFwdOps: 2048,
          numParams: 13B,
          numTokens: 512,
          throughputTokensPerSec: 153,
          throughputTokensPerMs: 0.000153,
          qualityMetrics: {
            coherence: 0.85,
            relevance: 0.95,
            fluency: 0.9,
          },
        },
      ];
      
      results.results = mockResults;
      
      expect(results.getResults()).toEqual(mockResults);
    });

    test('should return empty array when no results', () => {
      results.results = [];
      
      expect(results.getResults()).toEqual([]);
    });
  });
});
