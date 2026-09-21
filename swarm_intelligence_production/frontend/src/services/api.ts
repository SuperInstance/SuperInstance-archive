import axios, { AxiosInstance } from 'axios';
import type {
  Swarm,
  SwarmTemplate,
  DeploymentConfig,
  Task,
  Agent,
  NaturalLanguageQuery,
} from '../types';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: '/api/v1',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add auth token interceptor
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });
  }

  // Swarm Management
  async getSwarms(): Promise<Swarm[]> {
    const response = await this.client.get<Swarm[]>('/swarms');
    return response.data;
  }

  async getSwarm(id: string): Promise<Swarm> {
    const response = await this.client.get<Swarm>(`/swarms/${id}`);
    return response.data;
  }

  async deploySwarm(config: DeploymentConfig): Promise<Swarm> {
    const response = await this.client.post<Swarm>('/deploy', config);
    return response.data;
  }

  async pauseSwarm(id: string): Promise<void> {
    await this.client.post(`/swarms/${id}/pause`);
  }

  async resumeSwarm(id: string): Promise<void> {
    await this.client.post(`/swarms/${id}/resume`);
  }

  async stopSwarm(id: string): Promise<void> {
    await this.client.post(`/swarms/${id}/stop`);
  }

  async deleteSwarm(id: string): Promise<void> {
    await this.client.delete(`/swarms/${id}`);
  }

  // Template Management
  async getTemplates(): Promise<SwarmTemplate[]> {
    const response = await this.client.get<SwarmTemplate[]>('/templates');
    return response.data;
  }

  async getTemplate(id: string): Promise<SwarmTemplate> {
    const response = await this.client.get<SwarmTemplate>(`/templates/${id}`);
    return response.data;
  }

  // Task Management
  async getTasks(swarmId: string): Promise<Task[]> {
    const response = await this.client.get<Task[]>(`/swarms/${swarmId}/tasks`);
    return response.data;
  }

  async createTask(swarmId: string, task: Partial<Task>): Promise<Task> {
    const response = await this.client.post<Task>(
      `/swarms/${swarmId}/tasks`,
      task
    );
    return response.data;
  }

  // Agent Management
  async getAgents(swarmId: string): Promise<Agent[]> {
    const response = await this.client.get<Agent[]>(
      `/swarms/${swarmId}/agents`
    );
    return response.data;
  }

  // Natural Language Interface
  async processNaturalLanguage(
    query: string
  ): Promise<NaturalLanguageQuery> {
    const response = await this.client.post<NaturalLanguageQuery>(
      '/nl/process',
      { query }
    );
    return response.data;
  }

  async getSuggestions(partial: string): Promise<string[]> {
    const response = await this.client.get<string[]>('/nl/suggestions', {
      params: { q: partial },
    });
    return response.data;
  }

  // Analytics
  async getMetrics(swarmId: string, timeRange?: string) {
    const response = await this.client.get(`/swarms/${swarmId}/metrics`, {
      params: { timeRange },
    });
    return response.data;
  }

  // Export
  async exportSwarm(swarmId: string, format: 'json' | 'yaml'): Promise<Blob> {
    const response = await this.client.get(`/swarms/${swarmId}/export`, {
      params: { format },
      responseType: 'blob',
    });
    return response.data;
  }
}

export const api = new ApiService();
