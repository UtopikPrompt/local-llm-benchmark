import { render, screen, fireEvent, waitFor } from '@testing-library/jest-dom';
import { models } from '../../src/app/ui/models.js';

describe('Models Service', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    localStorage.clear();
  });

  afterEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  describe('loadModels', () => {
    test('should load models from endpoint and set default', async () => {
      const mockModels = [
        { id: 'model-1', name: 'Test Model 1', capabilities: ['text-generation'] },
        { id: 'model-2', name: 'Test Model 2', capabilities: ['text-generation', 'text-classification'] },
      ];
      
      const mockResponse = { models: mockModels };
      global.fetch = jest.fn().mockResolvedValue({ json: () => Promise.resolve(mockResponse) });
      
      await models.loadModels();
      
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/models', { method: 'POST', body: expect.any(Object) });
      expect(models.defaultModelId).toBe(mockModels[0].id);
      expect(models.modelList).toEqual(mockModels);
    });

    test('should handle empty model list', async () => {
      const mockResponse = { models: [] };
      global.fetch = jest.fn().mockResolvedValue({ json: () => Promise.resolve(mockResponse) });
      
      await models.loadModels();
      
      expect(models.defaultModelId).toBeNull();
      expect(models.modelList).toEqual([]);
    });

    test('should set default model to first model when list is not empty', async () => {
      const mockModels = [
        { id: 'model-1', name: 'First Model' },
        { id: 'model-2', name: 'Second Model' },
      ];
      const mockResponse = { models: mockModels };
      global.fetch = jest.fn().mockResolvedValue({ json: () => Promise.resolve(mockResponse) });
      
      await models.loadModels();
      
      expect(models.defaultModelId).toBe(mockModels[0].id);
    });
  });

  describe('loadModelById', () => {
    test('should set default model by ID', async () => {
      const mockModels = [
        { id: 'model-1', name: 'Test Model 1' },
        { id: 'model-2', name: 'Test Model 2' },
      ];
      const mockResponse = { models: mockModels };
      global.fetch = jest.fn().mockResolvedValue({ json: () => Promise.resolve(mockResponse) });
      
      await models.loadModels();
      
      await models.setActiveModel('model-2');
      
      expect(models.defaultModelId).toBe('model-2');
      expect(models.modelList).toEqual(mockModels);
    });

    test('should throw error for non-existent model', async () => {
      const mockModels = [
        { id: 'model-1', name: 'Test Model 1' },
      ];
      const mockResponse = { models: mockModels };
      global.fetch = jest.fn().mockResolvedValue({ json: () => Promise.resolve(mockResponse) });
      
      await models.loadModels();
      
      await expect(models.setActiveModel('non-existent')).rejects.toThrow('Model not found');
    });
  });

  describe('createModel', () => {
    test('should create new model and return it', async () => {
      const mockModels = [
        { id: 'model-1', name: 'Existing Model' },
      ];
      const mockResponse = { models: [...mockModels, { id: 'model-2', name: 'New Model' }] };
      global.fetch = jest.fn().mockResolvedValue({ json: () => Promise.resolve(mockResponse) });
      
      const newModel = {
        id: 'model-2',
        name: 'New Model',
        capabilities: ['text-generation'],
      };
      
      const createdModel = await models.createModel(newModel);
      
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/models', {
        method: 'POST',
        body: JSON.stringify(newModel),
        headers: expect.any(Object),
      });
      expect(createdModel).toEqual(mockResponse.models[1]);
    });

    test('should handle creation error', async () => {
      const mockModels = [
        { id: 'model-1', name: 'Existing Model' },
      ];
      global.fetch = jest.fn().mockRejectedValue(new Error('Failed to create model'));
      
      const newModel = {
        id: 'model-2',
        name: 'New Model',
        capabilities: ['text-generation'],
      };
      
      await expect(models.createModel(newModel)).rejects.toThrow('Failed to create model');
    });
  });

  describe('updateModel', () => {
    test('should update existing model', async () => {
      const mockModels = [
        { id: 'model-1', name: 'Original Name', capabilities: ['text-generation'] },
      ];
      const mockResponse = { models: mockModels };
      global.fetch = jest.fn().mockResolvedValue({ json: () => Promise.resolve(mockResponse) });
      
      await models.loadModels();
      
      const updatedModel = {
        id: 'model-1',
        name: 'Updated Name',
        capabilities: ['text-generation', 'text-classification'],
      };
      
      const updatedModelData = await models.updateModel('model-1', updatedModel);
      
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/models/model-1', {
        method: 'PUT',
        body: JSON.stringify(updatedModel),
        headers: expect.any(Object),
      });
      expect(updatedModelData).toEqual(mockResponse.models[0]);
    });

    test('should handle update error', async () => {
      const mockModels = [
        { id: 'model-1', name: 'Original Name' },
      ];
      global.fetch = jest.fn().mockRejectedValue(new Error('Failed to update model'));
      
      await models.loadModels();
      
      const updatedModel = {
        id: 'model-1',
        name: 'Updated Name',
      };
      
      await expect(models.updateModel('model-1', updatedModel)).rejects.toThrow('Failed to update model');
    });
  });

  describe('deleteModel', () => {
    test('should delete model and remove from list', async () => {
      const mockModels = [
        { id: 'model-1', name: 'Model to Delete' },
        { id: 'model-2', name: 'Keep This' },
      ];
      const mockResponse = { models: mockModels };
      global.fetch = jest.fn().mockResolvedValue({ json: () => Promise.resolve(mockResponse) });
      
      await models.loadModels();
      
      await models.deleteModel('model-1');
      
      expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/models/model-1', { method: 'DELETE' });
      expect(models.modelList).toEqual(mockModels.slice(1));
    });

    test('should handle deletion error', async () => {
      const mockModels = [
        { id: 'model-1', name: 'Model to Delete' },
      ];
      global.fetch = jest.fn().mockRejectedValue(new Error('Failed to delete model'));
      
      await models.loadModels();
      
      await expect(models.deleteModel('model-1')).rejects.toThrow('Failed to delete model');
    });
  });

  describe('modelList', () => {
    test('should return current model list', () => {
      const mockModels = [
        { id: 'model-1', name: 'Model 1' },
        { id: 'model-2', name: 'Model 2' },
      ];
      
      models.modelList = mockModels;
      
      expect(models.modelList).toEqual(mockModels);
    });

    test('should update model list', () => {
      models.modelList = [
        { id: 'model-1', name: 'Model 1' },
      ];
      
      models.setActiveModel('model-1');
      
      expect(models.modelList).toEqual([{ id: 'model-1', name: 'Model 1' }]);
      expect(models.defaultModelId).toBe('model-1');
    });
  });

  describe('defaultModelId', () => {
    test('should store default model ID', () => {
      models.defaultModelId = 'model-1';
      
      expect(models.defaultModelId).toBe('model-1');
    });

    test('should reset default model ID', () => {
      models.defaultModelId = 'model-1';
      models.defaultModelId = null;
      
      expect(models.defaultModelId).toBeNull();
    });
  });
});
