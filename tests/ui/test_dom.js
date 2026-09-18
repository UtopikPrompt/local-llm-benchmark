import { render, screen, waitFor } from '@testing-library/jest-dom';
import { dom } from '../../src/app/ui/dom.js';

describe('DOM Utilities', () => {
  beforeEach(() => {
    // Mock document.createElement to prevent DOM pollution
    const mockElement = {
      style: {
        display: 'none',
        position: 'absolute',
        top: '0',
        left: '0',
      },
      className: '',
      id: '',
      textContent: '',
      appendChild: jest.fn(),
      removeChild: jest.fn(),
      replaceChild: jest.fn(),
      setAttribute: jest.fn(),
      removeAttribute: jest.fn(),
    };
    Object.defineProperty(document, 'createElement', {
      value: () => mockElement,
      writable: true,
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('createElement', () => {
    test('should create a div element', () => {
      const element = dom.createElement('div');
      expect(element.tagName).toBe('DIV');
      expect(element.style.display).toBe('none');
      expect(element.style.position).toBe('absolute');
    });

    test('should create a span element', () => {
      const element = dom.createElement('span');
      expect(element.tagName).toBe('SPAN');
    });

    test('should create a custom element', () => {
      const element = dom.createElement('custom-element');
      expect(element.tagName).toBe('CUSTOM-ELEMENT');
    });

    test('should set default attributes', () => {
      const element = dom.createElement('div', { id: 'test-id', class: 'test-class' });
      expect(element.id).toBe('test-id');
      expect(element.className).toBe('test-class');
    });
  });

  describe('appendChild', () => {
    test('should append element to parent', () => {
      const parent = document.createElement('div');
      const child = document.createElement('span');
      
      parent.appendChild(child);
      
      expect(parent.appendChild).toHaveBeenCalledWith(child);
    });
  });

  describe('removeChild', () => {
    test('should remove child from parent', () => {
      const parent = document.createElement('div');
      const child = document.createElement('span');
      const grandchild = document.createElement('p');
      
      parent.appendChild(child);
      child.appendChild(grandchild);
      
      parent.removeChild(grandchild);
      
      expect(parent.removeChild).toHaveBeenCalledWith(grandchild);
    });
  });

  describe('replaceChild', () => {
    test('should replace child with new element', () => {
      const parent = document.createElement('div');
      const oldChild = document.createElement('span');
      const newChild = document.createElement('p');
      
      parent.appendChild(oldChild);
      parent.replaceChild(newChild, oldChild);
      
      expect(parent.replaceChild).toHaveBeenCalledWith(newChild, oldChild);
      expect(oldChild.parentNode).toBeNull();
      expect(newChild.parentNode).toBe(parent);
    });
  });

  describe('setAttribute', () => {
    test('should set element attribute', () => {
      const element = document.createElement('div');
      dom.setAttribute(element, 'data-test', 'value');
      
      expect(element.setAttribute).toHaveBeenCalledWith('data-test', 'value');
    });

    test('should handle boolean attributes', () => {
      const element = document.createElement('div');
      dom.setAttribute(element, 'disabled', true);
      
      expect(element.setAttribute).toHaveBeenCalledWith('disabled', '');
    });
  });

  describe('removeAttribute', () => {
    test('should remove element attribute', () => {
      const element = document.createElement('div');
      dom.setAttribute(element, 'data-test', 'value');
      dom.removeAttribute(element, 'data-test');
      
      expect(element.removeAttribute).toHaveBeenCalledWith('data-test');
    });
  });

  describe('querySelector', () => {
    test('should return first matching element', () => {
      const mockElements = [
        { tagName: 'DIV', id: 'container' },
        { tagName: 'DIV', class: 'item' },
        { tagName: 'SPAN', class: 'item' },
      ];
      
      Object.defineProperty(document, 'querySelector', {
        value: (selector) => {
          if (selector === '.item') {
            return mockElements[1];
          }
          return null;
        },
      });
      
      const element = dom.querySelector('.item');
      expect(element.tagName).toBe('DIV');
      expect(element.id).toBeNull();
    });
  });

  describe('querySelectorAll', () => {
    test('should return NodeList of matching elements', () => {
      const mockElements = [
        { tagName: 'DIV', id: 'item1' },
        { tagName: 'DIV', id: 'item2' },
        { tagName: 'SPAN', id: 'item3' },
      ];
      
      Object.defineProperty(document, 'querySelectorAll', {
        value: (selector) => {
          if (selector === '.item') {
            return mockElements.slice(0, 2);
          }
          return null;
        },
      });
      
      const elements = dom.querySelectorAll('.item');
      expect(elements.length).toBe(2);
      expect(elements[0].tagName).toBe('DIV');
      expect(elements[1].tagName).toBe('DIV');
    });
  });

  describe('getEl', () => {
    test('should return element by id', () => {
      const mockElement = { tagName: 'DIV' };
      Object.defineProperty(document, 'getElementById', {
        value: (id) => {
          if (id === 'test-container') {
            return mockElement;
          }
          return null;
        },
      });
      
      const element = dom.getEl('test-container');
      expect(element.tagName).toBe('DIV');
    });

    test('should return element by class', () => {
      const mockElements = [
        { tagName: 'DIV', class: 'item' },
        { tagName: 'SPAN', class: 'item' },
      ];
      Object.defineProperty(document, 'querySelector', {
        value: (selector) => {
          if (selector === '.item') {
            return mockElements[0];
          }
          return null;
        },
      });
      
      const element = dom.getEl('.item');
      expect(element.tagName).toBe('DIV');
    });

    test('should return null for non-existent element', () => {
      const element = dom.getEl('non-existent');
      expect(element).toBeNull();
    });
  });
});
