/**
 * Swarm Intelligence Client
 */

import { Swarm } from './swarm';
import { Task } from './task';
import { SwarmConfig, SwarmStatus, AgentType, CreateSwarmOptions } from './types';
import { AuthenticationError, RateLimitError, SwarmCreationError } from './errors';

export class SwarmClient {
  private apiKey: string;
  private baseUrl: string;
  private timeout: number;

  constructor(options: {
    apiKey: string;
    baseUrl?: string;
    timeout?: number;
  }) {
    this.apiKey = options.apiKey;
    this.baseUrl = options.baseUrl || 'https://api.swarm.dev';
    this.timeout = options.timeout || 30000;
  }

  /**
   * Create a new swarm
   */
  async createSwarm(params: {
    name: string;
    agentCount?: number;
    agentType?: AgentType;
    config?: SwarmConfig;
  }): Promise<Swarm> {
    const response = await this.request('/api/v1/swarms', {
      method: 'POST',
      body: JSON.stringify({
        name: params.name,
        agent_count: params.agentCount || 10,
        agent_type: params.agentType || AgentType.WORKER,
        config: params.config
      })
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new AuthenticationError('Invalid API key');
      }
      if (response.status === 429) {
        throw new RateLimitError('Rate limit exceeded');
      }
      throw new SwarmCreationError(`Failed to create swarm: ${response.statusText}`);
    }

    const data = await response.json();
    return new Swarm(this, data);
  }

  /**
   * Get swarm by ID
   */
  async getSwarm(swarmId: string): Promise<Swarm> {
    const response = await this.request(`/api/v1/swarms/${swarmId}`);
    const data = await response.json();
    return new Swarm(this, data);
  }

  /**
   * List all swarms
   */
  async listSwarms(filter?: {
    status?: SwarmStatus;
    limit?: number;
    offset?: number;
  }): Promise<Swarm[]> {
    const params = new URLSearchParams();
    if (filter?.status) params.append('status', filter.status);
    if (filter?.limit) params.append('limit', filter.limit.toString());
    if (filter?.offset) params.append('offset', filter.offset.toString());

    const response = await this.request(`/api/v1/swarms?${params}`);
    const data = await response.json();

    return data.swarms.map((swarmData: any) => new Swarm(this, swarmData));
  }

  /**
   * Get task by ID
   */
  async getTask(taskId: string): Promise<Task> {
    const response = await this.request(`/api/v1/tasks/${taskId}`);
    const data = await response.json();
    return new Task(this, data);
  }

  /**
   * Make HTTP request
   */
  async request(path: string, init?: RequestInit): Promise<Response> {
    const url = `${this.baseUrl}${path}`;
    const headers = {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json',
      ...init?.headers
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...init,
        headers,
        signal: controller.signal
      });
      return response;
    } finally {
      clearTimeout(timeoutId);
    }
  }
}
