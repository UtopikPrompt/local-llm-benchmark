import { render, screen, waitFor } from '@testing-library/jest-dom';
import { state } from '../../src/app/ui/state.js';

describe('UI State Management', () => {
  beforeEach(() => {
    // Reset state before each test
    Object.defineProperty(window, 'localStorage', {
      writable: true,
      value: {
        getItem: jest.fn(() => null),
        setItem: jest.fn(),
        removeItem: jest.fn(),
      },
    });
  });

  afterEach(() => {
    // Cleanup after each test
    jest.clearAllMocks();
  });

  describe('Initial State', () => {
    test('should initialize with default values', () => {
      expect(state).toEqual({
        selectedEngine: null,
        selectedChallenge: null,
        selectedModel: null,
        selectedEnvironment: null,
        selectedRun: null,
        selectedMetrics: null,
        selectedRunType: null,
        selectedResults: null,
        selectedView: null,
        selectedDifficulty: null,
        selectedMaxRuns: null,
        showSidebar: true,
      });
    });

    test('should have all 11 contract fields', () => {
      const requiredFields = [
        'selectedEngine',
        'selectedChallenge',
        'selectedModel',
        'selectedEnvironment',
        'selectedRun',
        'selectedMetrics',
        'selectedRunType',
        'selectedResults',
        'selectedView',
        'selectedDifficulty',
        'selectedMaxRuns',
      ];

      requiredFields.forEach((field) => {
        expect(state).toHaveProperty(field);
        expect(state[field]).toBeDefined();
      });
    });
  });

  describe('State Updates', () => {
    test('should allow setting selectedEngine', () => {
      const engineId = 'test-engine';
      state.selectedEngine = engineId;
      expect(state.selectedEngine).toBe(engineId);
    });

    test('should allow setting selectedChallenge', () => {
      const challengeId = 'test-challenge';
      state.selectedChallenge = challengeId;
      expect(state.selectedChallenge).toBe(challengeId);
    });

    test('should allow setting selectedModel', () => {
      const modelId = 'test-model';
      state.selectedModel = modelId;
      expect(state.selectedModel).toBe(modelId);
    });

    test('should allow setting selectedEnvironment', () => {
      const envId = 'test-env';
      state.selectedEnvironment = envId;
      expect(state.selectedEnvironment).toBe(envId);
    });

    test('should allow setting selectedRun', () => {
      const runId = 'test-run';
      state.selectedRun = runId;
      expect(state.selectedRun).toBe(runId);
    });

    test('should allow setting selectedMetrics', () => {
      const metrics = ['speed'];
      state.selectedMetrics = metrics;
      expect(state.selectedMetrics).toEqual(metrics);
    });

    test('should allow setting selectedRunType', () => {
      const runType = 'benchmark';
      state.selectedRunType = runType;
      expect(state.selectedRunType).toBe(runType);
    });

    test('should allow setting selectedResults', () => {
      const results = { speed: 100 };
      state.selectedResults = results;
      expect(state.selectedResults).toEqual(results);
    });

    test('should allow setting selectedView', () => {
      const view = 'dashboard';
      state.selectedView = view;
      expect(state.selectedView).toBe(view);
    });

    test('should allow setting selectedDifficulty', () => {
      const difficulty = 'easy';
      state.selectedDifficulty = difficulty;
      expect(state.selectedDifficulty).toBe(difficulty);
    });

    test('should allow setting selectedMaxRuns', () => {
      const maxRuns = 10;
      state.selectedMaxRuns = maxRuns;
      expect(state.selectedMaxRuns).toBe(maxRuns);
    });
  });

  describe('State Persistence', () => {
    test('should persist state to localStorage', () => {
      const testState = { selectedEngine: 'test-engine', selectedChallenge: 'test-challenge' };
      Object.assign(state, testState);

      localStorage.setItem('benchmark-state', JSON.stringify(state));

      expect(localStorage.getItem('benchmark-state')).toEqual(JSON.stringify(testState));
    });

    test('should load state from localStorage', () => {
      const savedState = JSON.stringify({ selectedEngine: 'test-engine', selectedChallenge: 'test-challenge' });
      localStorage.setItem('benchmark-state', savedState);

      const loadedState = JSON.parse(localStorage.getItem('benchmark-state'));
      expect(loadedState).toEqual({ selectedEngine: 'test-engine', selectedChallenge: 'test-challenge' });
    });
  });
});
