import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export interface Template {
  id: string;
  title: string;
  content: string;
  category: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface PromptState {
  currentPrompt: string;
  templates: Template[];
  selectedTemplate: Template | null;
  categories: string[];
}

const defaultCategories = ['일반', '코딩', '창작', '분석', '번역', '요약'];

const initialState: PromptState = {
  currentPrompt: '',
  templates: [],
  selectedTemplate: null,
  categories: defaultCategories
};

// Load from localStorage if available
function loadFromStorage(): PromptState {
  if (!browser) return initialState;
  
  try {
    const stored = localStorage.getItem('prompt-studio-data');
    if (stored) {
      const parsed = JSON.parse(stored);
      return {
        ...initialState,
        ...parsed,
        templates: parsed.templates?.map((t: any) => ({
          ...t,
          createdAt: new Date(t.createdAt),
          updatedAt: new Date(t.updatedAt)
        })) || []
      };
    }
  } catch (error) {
    console.error('Failed to load from localStorage:', error);
  }
  
  return initialState;
}

export const promptStore = writable<PromptState>(loadFromStorage());

// Save to localStorage whenever store changes
if (browser) {
  promptStore.subscribe((state) => {
    try {
      localStorage.setItem('prompt-studio-data', JSON.stringify(state));
    } catch (error) {
      console.error('Failed to save to localStorage:', error);
    }
  });
}

// Helper functions
export const promptActions = {
  updatePrompt: (content: string) => {
    promptStore.update(state => ({ ...state, currentPrompt: content }));
  },
  
  saveTemplate: (title: string, category: string, content?: string) => {
    promptStore.update(state => {
      const newTemplate: Template = {
        id: crypto.randomUUID(),
        title,
        category,
        content: content || state.currentPrompt,
        createdAt: new Date(),
        updatedAt: new Date()
      };
      
      return {
        ...state,
        templates: [...state.templates, newTemplate]
      };
    });
  },
  
  loadTemplate: (template: Template) => {
    promptStore.update(state => ({
      ...state,
      currentPrompt: template.content,
      selectedTemplate: template
    }));
  },
  
  deleteTemplate: (templateId: string) => {
    promptStore.update(state => ({
      ...state,
      templates: state.templates.filter(t => t.id !== templateId),
      selectedTemplate: state.selectedTemplate?.id === templateId ? null : state.selectedTemplate
    }));
  },
  
  updateTemplate: (templateId: string, updates: Partial<Template>) => {
    promptStore.update(state => ({
      ...state,
      templates: state.templates.map(t => 
        t.id === templateId 
          ? { ...t, ...updates, updatedAt: new Date() }
          : t
      )
    }));
  },
  
  addCategory: (category: string) => {
    promptStore.update(state => ({
      ...state,
      categories: [...state.categories, category]
    }));
  },
  
  clearPrompt: () => {
    promptStore.update(state => ({
      ...state,
      currentPrompt: '',
      selectedTemplate: null
    }));
  }
};