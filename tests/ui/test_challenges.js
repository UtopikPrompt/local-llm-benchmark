import { render, screen, fireEvent, waitFor } from '@testing-library/jest-dom';
import { challenges } from '../../src/app/ui/challenges.js';

describe('Challenges Service', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    localStorage.clear();
  });

  afterEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  describe('loadChallenges', () => {
    test('should load challenges from storage', async () => {
      const mockChallenges = [
        {
          id: 'challenge-1',
          name: 'Speed Challenge',
          description: 'Benchmark model speed',
          type: 'speed',
          metrics: ['throughput', 'latency'],
          active: true,
          createdAt: new Date('2024-01-01').toISOString(),
        },
        {
          id: 'challenge-2',
          name: 'Quality Challenge',
          description: 'Evaluate model quality',
          type: 'quality',
          metrics: ['coherence', 'relevance'],
          active: true,
          createdAt: new Date('2024-01-02').toISOString(),
        },
      ];
      localStorage.setItem('benchmark_challenges', JSON.stringify(mockChallenges));
      
      await challenges.loadChallenges();
      
      expect(challenges.challenges).toEqual(mockChallenges);
    });

    test('should initialize empty challenges array', async () => {
      localStorage.clear();
      await challenges.loadChallenges();
      
      expect(challenges.challenges).toEqual([]);
    });

    test('should persist challenges to storage', async () => {
      const mockChallenge = {
        id: 'challenge-1',
        name: 'Test Challenge',
        description: 'Test description',
        type: 'speed',
        metrics: ['throughput'],
        active: true,
        createdAt: new Date('2024-01-01').toISOString(),
      };
      
      challenges.saveChallenge(mockChallenge);
      localStorage.setItem('benchmark_challenges', JSON.stringify(mockChallenges));
      
      await challenges.loadChallenges();
      
      expect(challenges.challenges).toHaveLength(1);
      expect(challenges.challenges[0]).toEqual(mockChallenge);
    });
  });

  describe('saveChallenge', () => {
    test('should save new challenge', () => {
      const mockChallenge = {
        id: 'challenge-1',
        name: 'New Challenge',
        description: 'New description',
        type: 'speed',
        metrics: ['throughput'],
        active: true,
        createdAt: new Date('2024-01-01').toISOString(),
      };
      
      challenges.saveChallenge(mockChallenge);
      
      expect(challenges.challenges).toHaveLength(1);
      expect(challenges.challenges[0]).toEqual(mockChallenge);
    });

    test('should update existing challenge by ID', () => {
      const mockChallenge = {
        id: 'challenge-1',
        name: 'Original Name',
        description: 'Original description',
        type: 'speed',
        metrics: ['throughput'],
        active: true,
        createdAt: new Date('2024-01-01').toISOString(),
      };
      
      challenges.saveChallenge(mockChallenge);
      
      const updatedChallenge = {
        id: 'challenge-1',
        name: 'Updated Name',
        description: 'Updated description',
        type: 'quality',
        metrics: ['coherence', 'relevance'],
        active: false,
        createdAt: new Date('2024-01-01').toISOString(),
      };
      
      challenges.saveChallenge(updatedChallenge);
      
      expect(challenges.challenges[0].name).toBe('Updated Name');
      expect(challenges.challenges[0].type).toBe('quality');
    });

    test('should remove challenge by ID', () => {
      const mockChallenge = {
        id: 'challenge-1',
        name: 'Challenge to Delete',
        description: 'Description',
        type: 'speed',
        metrics: ['throughput'],
        active: true,
        createdAt: new Date('2024-01-01').toISOString(),
      };
      
      challenges.saveChallenge(mockChallenge);
      
      expect(challenges.challenges).toHaveLength(1);
      
      challenges.removeChallenge('challenge-1');
      
      expect(challenges.challenges).toHaveLength(0);
    });
  });

  describe('clearChallenges', () => {
    test('should clear all challenges', () => {
      const mockChallenge = {
        id: 'challenge-1',
        name: 'Challenge to Clear',
        description: 'Description',
        type: 'speed',
        metrics: ['throughput'],
        active: true,
        createdAt: new Date('2024-01-01').toISOString(),
      };
      
      challenges.saveChallenge(mockChallenge);
      
      expect(challenges.challenges).toHaveLength(1);
      
      challenges.clearChallenges();
      
      expect(challenges.challenges).toHaveLength(0);
    });
  });

  describe('challenges', () => {
    test('should return empty array initially', () => {
      localStorage.clear();
      
      expect(challenges.challenges).toEqual([]);
    });

    test('should return challenges array', () => {
      const mockChallenges = [
        {
          id: 'challenge-1',
          name: 'Challenge 1',
          description: 'Description 1',
          type: 'speed',
          metrics: ['throughput'],
          active: true,
          createdAt: new Date('2024-01-01').toISOString(),
        },
      ];
      
      challenges.challenges = mockChallenges;
      
      expect(challenges.challenges).toEqual(mockChallenges);
    });

    test('should update challenges array', () => {
      challenges.challenges = [
        {
          id: 'challenge-1',
          name: 'Challenge 1',
          description: 'Description 1',
          type: 'speed',
          metrics: ['throughput'],
          active: true,
          createdAt: new Date('2024-01-01').toISOString(),
        },
      ];
      
      challenges.challenges = [
        {
          id: 'challenge-2',
          name: 'Challenge 2',
          description: 'Description 2',
          type: 'quality',
          metrics: ['coherence', 'relevance'],
          active: true,
          createdAt: new Date('2024-01-02').toISOString(),
        },
      ];
      
      expect(challenges.challenges).toHaveLength(1);
      expect(challenges.challenges[0].id).toBe('challenge-2');
    });
  });

  describe('getChallenges', () => {
    test('should return filtered challenges', () => {
      const mockChallenges = [
        {
          id: 'challenge-1',
          name: 'Challenge 1',
          description: 'Description 1',
          type: 'speed',
          metrics: ['throughput'],
          active: true,
          createdAt: new Date('2024-01-01').toISOString(),
        },
        {
          id: 'challenge-2',
          name: 'Challenge 2',
          description: 'Description 2',
          type: 'quality',
          metrics: ['coherence', 'relevance'],
          active: true,
          createdAt: new Date('2024-01-02').toISOString(),
        },
      ];
      
      challenges.challenges = mockChallenges;
      
      expect(challenges.getChallenges()).toEqual(mockChallenges);
    });

    test('should return empty array when no challenges', () => {
      challenges.challenges = [];
      
      expect(challenges.getChallenges()).toEqual([]);
    });
  });

  describe('filterChallenges', () => {
    test('should filter by type', () => {
      const mockChallenges = [
        {
          id: 'challenge-1',
          name: 'Speed Challenge',
          type: 'speed',
          active: true,
        },
        {
          id: 'challenge-2',
          name: 'Quality Challenge',
          type: 'quality',
          active: true,
        },
      ];
      
      challenges.challenges = mockChallenges;
      
      const speedChallenges = challenges.filterChallenges('speed');
      
      expect(speedChallenges).toHaveLength(1);
      expect(speedChallenges[0].name).toBe('Speed Challenge');
    });

    test('should filter by active status', () => {
      const mockChallenges = [
        {
          id: 'challenge-1',
          name: 'Active Challenge',
          type: 'speed',
          active: true,
        },
        {
          id: 'challenge-2',
          name: 'Inactive Challenge',
          type: 'quality',
          active: false,
        },
      ];
      
      challenges.challenges = mockChallenges;
      
      const activeChallenges = challenges.filterChallenges(true);
      
      expect(activeChallenges).toHaveLength(1);
      expect(activeChallenges[0].name).toBe('Active Challenge');
    });
  });
});
