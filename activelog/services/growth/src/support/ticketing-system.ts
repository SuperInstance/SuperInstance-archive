import crypto from 'crypto';
import { marked } from 'marked';

export interface SupportTicket {
  id: string;
  ticketNumber: string;
  subject: string;
  description: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'open' | 'in-progress' | 'waiting' | 'resolved' | 'closed';
  category: 'technical' | 'billing' | 'feature-request' | 'bug-report' | 'general' | 'account';
  subcategory?: string;
  appVariant?: 'PersonalLog' | 'BusinessLog' | 'FamilyLog' | 'FitnessLog' | 'TravelLog' | 'EducationLog';
  customerId: string;
  assignedAgentId?: string;
  tags: string[];
  createdAt: Date;
  updatedAt: Date;
  resolvedAt?: Date;
  closedAt?: Date;
  firstResponseAt?: Date;
  lastCustomerMessageAt?: Date;
  satisfaction?: SatisfactionRating;
  attachments: TicketAttachment[];
  relatedTickets: string[];
}

export interface TicketMessage {
  id: string;
  ticketId: string;
  authorId: string;
  authorType: 'customer' | 'agent' | 'system';
  content: string;
  isInternal: boolean;
  createdAt: Date;
  editedAt?: Date;
  attachments: TicketAttachment[];
  messageType: 'reply' | 'note' | 'status-change' | 'assignment' | 'escalation';
}

export interface TicketAttachment {
  id: string;
  filename: string;
  fileSize: number;
  mimeType: string;
  url: string;
  uploadedAt: Date;
  uploadedBy: string;
}

export interface SupportAgent {
  id: string;
  name: string;
  email: string;
  role: 'agent' | 'senior-agent' | 'team-lead' | 'manager';
  avatar?: string;
  isActive: boolean;
  skills: string[];
  languages: string[];
  maxConcurrentTickets: number;
  currentTicketCount: number;
  totalTicketsHandled: number;
  averageResolutionTime: number;
  satisfactionScore: number;
  specializations: string[];
  workingHours: WorkingHours;
  lastActiveAt: Date;
}

export interface WorkingHours {
  timezone: string;
  schedule: {
    monday: { start: string; end: string; available: boolean };
    tuesday: { start: string; end: string; available: boolean };
    wednesday: { start: string; end: string; available: boolean };
    thursday: { start: string; end: string; available: boolean };
    friday: { start: string; end: string; available: boolean };
    saturday: { start: string; end: string; available: boolean };
    sunday: { start: string; end: string; available: boolean };
  };
}

export interface SatisfactionRating {
  rating: number;
  feedback?: string;
  ratedAt: Date;
  aspects: {
    responsiveness: number;
    helpfulness: number;
    knowledge: number;
    resolution: number;
  };
}

export interface KnowledgeBaseArticle {
  id: string;
  title: string;
  content: string;
  summary: string;
  category: string;
  tags: string[];
  appVariant?: string;
  isPublic: boolean;
  isHelpful: number;
  viewCount: number;
  createdAt: Date;
  updatedAt: Date;
  author: string;
}

export interface SupportAnalytics {
  totalTickets: number;
  openTickets: number;
  resolvedTickets: number;
  averageResolutionTime: number;
  averageFirstResponseTime: number;
  satisfactionScore: number;
  ticketsByPriority: { priority: string; count: number }[];
  ticketsByCategory: { category: string; count: number }[];
  ticketsByStatus: { status: string; count: number }[];
  agentPerformance: {
    agent: SupportAgent;
    ticketsHandled: number;
    avgResolutionTime: number;
    satisfactionScore: number;
  }[];
  trendsData: {
    date: string;
    opened: number;
    resolved: number;
    satisfaction: number;
  }[];
  escalationRate: number;
  reopenRate: number;
}

export interface AutomationRule {
  id: string;
  name: string;
  description: string;
  isActive: boolean;
  trigger: {
    type: 'ticket-created' | 'keyword-match' | 'time-based' | 'status-change';
    conditions: Record<string, any>;
  };
  actions: {
    type: 'assign' | 'tag' | 'priority' | 'status' | 'notify' | 'template-response';
    parameters: Record<string, any>;
  }[];
  createdAt: Date;
  updatedAt: Date;
}

export class CustomerSupportTicketingSystem {
  private tickets: Map<string, SupportTicket> = new Map();
  private messages: Map<string, TicketMessage> = new Map();
  private agents: Map<string, SupportAgent> = new Map();
  private knowledgeBase: Map<string, KnowledgeBaseArticle> = new Map();
  private automationRules: Map<string, AutomationRule> = new Map();
  private ticketCounter: number = 1000;

  constructor() {
    this.initializeDefaultData();
  }

  private initializeDefaultData(): void {
    this.createDefaultAgents();
    this.createKnowledgeBaseArticles();
    this.createAutomationRules();
    this.createSampleTickets();
  }

  private createDefaultAgents(): void {
    const agents: Omit<SupportAgent, 'currentTicketCount' | 'totalTicketsHandled' | 'averageResolutionTime' | 'satisfactionScore' | 'lastActiveAt'>[] = [
      {
        id: crypto.randomUUID(),
        name: 'Sarah Johnson',
        email: 'sarah@activelogapp.com',
        role: 'senior-agent',
        isActive: true,
        skills: ['technical', 'billing', 'troubleshooting'],
        languages: ['en', 'es'],
        maxConcurrentTickets: 15,
        specializations: ['PersonalLog', 'BusinessLog'],
        workingHours: {
          timezone: 'America/New_York',
          schedule: {
            monday: { start: '09:00', end: '17:00', available: true },
            tuesday: { start: '09:00', end: '17:00', available: true },
            wednesday: { start: '09:00', end: '17:00', available: true },
            thursday: { start: '09:00', end: '17:00', available: true },
            friday: { start: '09:00', end: '17:00', available: true },
            saturday: { start: '00:00', end: '00:00', available: false },
            sunday: { start: '00:00', end: '00:00', available: false }
          }
        }
      },
      {
        id: crypto.randomUUID(),
        name: 'Mike Chen',
        email: 'mike@activelogapp.com',
        role: 'agent',
        isActive: true,
        skills: ['technical', 'feature-requests'],
        languages: ['en', 'zh'],
        maxConcurrentTickets: 12,
        specializations: ['FitnessLog', 'TravelLog'],
        workingHours: {
          timezone: 'America/Los_Angeles',
          schedule: {
            monday: { start: '08:00', end: '16:00', available: true },
            tuesday: { start: '08:00', end: '16:00', available: true },
            wednesday: { start: '08:00', end: '16:00', available: true },
            thursday: { start: '08:00', end: '16:00', available: true },
            friday: { start: '08:00', end: '16:00', available: true },
            saturday: { start: '00:00', end: '00:00', available: false },
            sunday: { start: '00:00', end: '00:00', available: false }
          }
        }
      },
      {
        id: crypto.randomUUID(),
        name: 'Emma Wilson',
        email: 'emma@activelogapp.com',
        role: 'team-lead',
        isActive: true,
        skills: ['billing', 'account-management', 'escalations'],
        languages: ['en', 'fr'],
        maxConcurrentTickets: 10,
        specializations: ['billing', 'enterprise'],
        workingHours: {
          timezone: 'Europe/London',
          schedule: {
            monday: { start: '09:00', end: '17:00', available: true },
            tuesday: { start: '09:00', end: '17:00', available: true },
            wednesday: { start: '09:00', end: '17:00', available: true },
            thursday: { start: '09:00', end: '17:00', available: true },
            friday: { start: '09:00', end: '17:00', available: true },
            saturday: { start: '00:00', end: '00:00', available: false },
            sunday: { start: '00:00', end: '00:00', available: false }
          }
        }
      }
    ];

    agents.forEach(agentData => {
      const agent: SupportAgent = {
        ...agentData,
        currentTicketCount: Math.floor(Math.random() * agentData.maxConcurrentTickets),
        totalTicketsHandled: Math.floor(Math.random() * 500) + 100,
        averageResolutionTime: Math.random() * 48 + 4,
        satisfactionScore: Math.random() * 2 + 3,
        lastActiveAt: new Date(Date.now() - Math.random() * 2 * 60 * 60 * 1000)
      };
      this.agents.set(agent.id, agent);
    });
  }

  private createKnowledgeBaseArticles(): void {
    const articles: Omit<KnowledgeBaseArticle, 'id' | 'isHelpful' | 'viewCount' | 'createdAt' | 'updatedAt'>[] = [
      {
        title: 'How to Reset Your Password',
        content: `# Resetting Your Password

If you've forgotten your password, follow these steps:

1. Go to the login page
2. Click "Forgot Password"
3. Enter your email address
4. Check your email for a reset link
5. Click the link and create a new password

## Password Requirements

- At least 8 characters long
- Include uppercase and lowercase letters
- Include at least one number
- Include at least one special character

## Troubleshooting

If you don't receive the reset email:
- Check your spam folder
- Make sure you entered the correct email
- Wait 5-10 minutes for delivery
- Contact support if the issue persists`,
        summary: 'Step-by-step guide to reset your password',
        category: 'account',
        tags: ['password', 'reset', 'login', 'security'],
        isPublic: true,
        author: 'Support Team'
      },
      {
        title: 'Data Sync Issues Between Devices',
        content: `# Fixing Data Sync Issues

If your entries aren't syncing between devices, try these solutions:

## Quick Fixes

1. **Force Sync**
   - Pull down on the main screen to refresh
   - Or go to Settings > Sync > Manual Sync

2. **Check Internet Connection**
   - Ensure you have a stable connection
   - Try switching between WiFi and mobile data

3. **Restart the App**
   - Close the app completely
   - Reopen and check if sync works

## Advanced Solutions

1. **Sign Out and Back In**
   - Go to Settings > Account > Sign Out
   - Sign back in with your credentials

2. **Clear App Cache** (Android only)
   - Go to Settings > Apps > ActiveLog
   - Tap "Storage" then "Clear Cache"

3. **Reinstall the App**
   - As a last resort, uninstall and reinstall
   - Your data is safely stored in the cloud`,
        summary: 'Solutions for data synchronization problems',
        category: 'technical',
        tags: ['sync', 'devices', 'troubleshooting', 'data'],
        isPublic: true,
        author: 'Technical Team'
      },
      {
        title: 'Billing and Subscription Management',
        content: `# Managing Your Subscription

## Viewing Your Current Plan

1. Open Settings
2. Navigate to Account > Subscription
3. View your current plan details and billing cycle

## Upgrading Your Plan

1. Go to Settings > Subscription
2. Click "Upgrade Plan"
3. Choose your desired plan
4. Enter payment information
5. Confirm the upgrade

## Canceling Your Subscription

1. Go to Settings > Subscription
2. Click "Cancel Subscription"
3. Follow the prompts to confirm
4. Your subscription will remain active until the current billing period ends

## Managing Payment Methods

- Add, edit, or remove payment methods
- Update billing address
- View payment history
- Download receipts

## Refund Policy

We offer refunds within 30 days of purchase for annual subscriptions and within 7 days for monthly subscriptions.`,
        summary: 'Complete guide to subscription and billing management',
        category: 'billing',
        tags: ['billing', 'subscription', 'payment', 'refund'],
        isPublic: true,
        author: 'Billing Team'
      }
    ];

    articles.forEach(articleData => {
      const article: KnowledgeBaseArticle = {
        ...articleData,
        id: crypto.randomUUID(),
        isHelpful: Math.floor(Math.random() * 50),
        viewCount: Math.floor(Math.random() * 1000),
        createdAt: new Date(Date.now() - Math.random() * 90 * 24 * 60 * 60 * 1000),
        updatedAt: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000)
      };
      this.knowledgeBase.set(article.id, article);
    });
  }

  private createAutomationRules(): void {
    const rules: Omit<AutomationRule, 'id' | 'createdAt' | 'updatedAt'>[] = [
      {
        name: 'Auto-assign Technical Issues',
        description: 'Automatically assign technical tickets to available technical specialists',
        isActive: true,
        trigger: {
          type: 'ticket-created',
          conditions: { category: 'technical' }
        },
        actions: [
          {
            type: 'assign',
            parameters: { skill: 'technical' }
          },
          {
            type: 'tag',
            parameters: { tags: ['auto-assigned'] }
          }
        ]
      },
      {
        name: 'Urgent Priority Alert',
        description: 'Send immediate notifications for urgent tickets',
        isActive: true,
        trigger: {
          type: 'ticket-created',
          conditions: { priority: 'urgent' }
        },
        actions: [
          {
            type: 'notify',
            parameters: { channel: 'slack', message: 'Urgent ticket created' }
          },
          {
            type: 'assign',
            parameters: { role: 'team-lead' }
          }
        ]
      },
      {
        name: 'First Response Template',
        description: 'Send acknowledgment template for new tickets',
        isActive: true,
        trigger: {
          type: 'ticket-created',
          conditions: {}
        },
        actions: [
          {
            type: 'template-response',
            parameters: {
              template: 'acknowledgment',
              delay: 5
            }
          }
        ]
      }
    ];

    rules.forEach(ruleData => {
      const rule: AutomationRule = {
        ...ruleData,
        id: crypto.randomUUID(),
        createdAt: new Date(),
        updatedAt: new Date()
      };
      this.automationRules.set(rule.id, rule);
    });
  }

  private createSampleTickets(): void {
    const customers = ['customer1', 'customer2', 'customer3'];
    const agents = Array.from(this.agents.keys());

    for (let i = 0; i < 10; i++) {
      const ticket = this.createTicketInternal({
        subject: `Sample Ticket ${i + 1}`,
        description: `This is a sample support ticket for testing purposes. Issue details...`,
        priority: ['low', 'medium', 'high'][Math.floor(Math.random() * 3)] as any,
        category: ['technical', 'billing', 'general'][Math.floor(Math.random() * 3)] as any,
        customerId: customers[Math.floor(Math.random() * customers.length)],
        assignedAgentId: Math.random() > 0.3 ? agents[Math.floor(Math.random() * agents.length)] : undefined,
        tags: ['sample', 'test']
      });

      if (Math.random() > 0.5) {
        ticket.status = ['in-progress', 'resolved', 'closed'][Math.floor(Math.random() * 3)] as any;
        if (ticket.status === 'resolved' || ticket.status === 'closed') {
          ticket.resolvedAt = new Date(Date.now() - Math.random() * 10 * 24 * 60 * 60 * 1000);
        }
        if (ticket.status === 'closed') {
          ticket.closedAt = new Date();
        }
      }
    }
  }

  async createTicket(ticketData: Omit<SupportTicket, 'id' | 'ticketNumber' | 'createdAt' | 'updatedAt' | 'attachments' | 'relatedTickets' | 'status'>): Promise<SupportTicket> {
    return this.createTicketInternal({ ...ticketData, status: 'open' });
  }

  private createTicketInternal(ticketData: Omit<SupportTicket, 'id' | 'ticketNumber' | 'createdAt' | 'updatedAt' | 'attachments' | 'relatedTickets'>): SupportTicket {
    const ticket: SupportTicket = {
      ...ticketData,
      id: crypto.randomUUID(),
      ticketNumber: `TK-${this.ticketCounter++}`,
      createdAt: new Date(),
      updatedAt: new Date(),
      attachments: [],
      relatedTickets: []
    };

    this.tickets.set(ticket.id, ticket);
    this.processAutomationRules(ticket);
    return ticket;
  }

  async addMessage(messageData: Omit<TicketMessage, 'id' | 'createdAt' | 'attachments'>): Promise<TicketMessage> {
    const message: TicketMessage = {
      ...messageData,
      id: crypto.randomUUID(),
      createdAt: new Date(),
      attachments: []
    };

    this.messages.set(message.id, message);

    const ticket = this.tickets.get(message.ticketId);
    if (ticket) {
      ticket.updatedAt = new Date();
      
      if (message.authorType === 'customer') {
        ticket.lastCustomerMessageAt = new Date();
        if (ticket.status === 'waiting') {
          ticket.status = 'open';
        }
      } else if (message.authorType === 'agent' && !ticket.firstResponseAt) {
        ticket.firstResponseAt = new Date();
      }

      if (message.messageType === 'status-change') {
        // Handle status changes
        const statusMatch = message.content.match(/status changed to (\w+)/i);
        if (statusMatch) {
          const newStatus = statusMatch[1].toLowerCase() as SupportTicket['status'];
          ticket.status = newStatus;
          
          if (newStatus === 'resolved') {
            ticket.resolvedAt = new Date();
          } else if (newStatus === 'closed') {
            ticket.closedAt = new Date();
          }
        }
      }
    }

    return message;
  }

  async assignTicket(ticketId: string, agentId: string): Promise<boolean> {
    const ticket = this.tickets.get(ticketId);
    const agent = this.agents.get(agentId);
    
    if (!ticket || !agent || agent.currentTicketCount >= agent.maxConcurrentTickets) {
      return false;
    }

    if (ticket.assignedAgentId) {
      const previousAgent = this.agents.get(ticket.assignedAgentId);
      if (previousAgent) {
        previousAgent.currentTicketCount--;
      }
    }

    ticket.assignedAgentId = agentId;
    ticket.updatedAt = new Date();
    if (ticket.status === 'open') {
      ticket.status = 'in-progress';
    }

    agent.currentTicketCount++;

    await this.addMessage({
      ticketId,
      authorId: 'system',
      authorType: 'system',
      content: `Ticket assigned to ${agent.name}`,
      isInternal: true,
      messageType: 'assignment'
    });

    return true;
  }

  async updateTicketStatus(ticketId: string, status: SupportTicket['status'], agentId?: string): Promise<boolean> {
    const ticket = this.tickets.get(ticketId);
    if (!ticket) return false;

    const oldStatus = ticket.status;
    ticket.status = status;
    ticket.updatedAt = new Date();

    if (status === 'resolved' && !ticket.resolvedAt) {
      ticket.resolvedAt = new Date();
    } else if (status === 'closed' && !ticket.closedAt) {
      ticket.closedAt = new Date();
      
      if (ticket.assignedAgentId) {
        const agent = this.agents.get(ticket.assignedAgentId);
        if (agent) {
          agent.currentTicketCount--;
          agent.totalTicketsHandled++;
        }
      }
    }

    if (agentId) {
      await this.addMessage({
        ticketId,
        authorId: agentId,
        authorType: 'agent',
        content: `Ticket status changed from ${oldStatus} to ${status}`,
        isInternal: false,
        messageType: 'status-change'
      });
    }

    return true;
  }

  async escalateTicket(ticketId: string, reason: string, escalatedBy: string): Promise<boolean> {
    const ticket = this.tickets.get(ticketId);
    if (!ticket) return false;

    const teamLead = Array.from(this.agents.values())
      .find(agent => agent.role === 'team-lead' && agent.isActive && agent.currentTicketCount < agent.maxConcurrentTickets);

    if (teamLead) {
      await this.assignTicket(ticketId, teamLead.id);
    }

    ticket.priority = ticket.priority === 'high' ? 'urgent' : 'high';
    ticket.tags.push('escalated');

    await this.addMessage({
      ticketId,
      authorId: escalatedBy,
      authorType: 'agent',
      content: `Ticket escalated. Reason: ${reason}`,
      isInternal: true,
      messageType: 'escalation'
    });

    return true;
  }

  async addSatisfactionRating(ticketId: string, rating: SatisfactionRating): Promise<boolean> {
    const ticket = this.tickets.get(ticketId);
    if (!ticket || ticket.status !== 'resolved') return false;

    ticket.satisfaction = rating;
    
    if (ticket.assignedAgentId) {
      const agent = this.agents.get(ticket.assignedAgentId);
      if (agent) {
        const totalRatings = agent.totalTicketsHandled;
        agent.satisfactionScore = ((agent.satisfactionScore * (totalRatings - 1)) + rating.rating) / totalRatings;
      }
    }

    return true;
  }

  async searchTickets(query: string, filters?: {
    status?: string;
    priority?: string;
    category?: string;
    assignedAgentId?: string;
    customerId?: string;
    tags?: string[];
  }): Promise<SupportTicket[]> {
    const queryLower = query.toLowerCase();
    
    return Array.from(this.tickets.values())
      .filter(ticket => {
        if (filters?.status && ticket.status !== filters.status) return false;
        if (filters?.priority && ticket.priority !== filters.priority) return false;
        if (filters?.category && ticket.category !== filters.category) return false;
        if (filters?.assignedAgentId && ticket.assignedAgentId !== filters.assignedAgentId) return false;
        if (filters?.customerId && ticket.customerId !== filters.customerId) return false;
        if (filters?.tags && !filters.tags.every(tag => ticket.tags.includes(tag))) return false;
        
        return (
          ticket.subject.toLowerCase().includes(queryLower) ||
          ticket.description.toLowerCase().includes(queryLower) ||
          ticket.ticketNumber.toLowerCase().includes(queryLower) ||
          ticket.tags.some(tag => tag.toLowerCase().includes(queryLower))
        );
      })
      .sort((a, b) => {
        if (a.priority === 'urgent' && b.priority !== 'urgent') return -1;
        if (b.priority === 'urgent' && a.priority !== 'urgent') return 1;
        if (a.priority === 'high' && b.priority !== 'high') return -1;
        if (b.priority === 'high' && a.priority !== 'high') return 1;
        return b.updatedAt.getTime() - a.updatedAt.getTime();
      });
  }

  async getTicketMessages(ticketId: string, includeInternal: boolean = false): Promise<TicketMessage[]> {
    return Array.from(this.messages.values())
      .filter(message => {
        if (message.ticketId !== ticketId) return false;
        if (!includeInternal && message.isInternal) return false;
        return true;
      })
      .sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime());
  }

  async getAgentWorkload(): Promise<{ agent: SupportAgent; workload: number; availability: string }[]> {
    return Array.from(this.agents.values())
      .filter(agent => agent.isActive)
      .map(agent => ({
        agent,
        workload: (agent.currentTicketCount / agent.maxConcurrentTickets) * 100,
        availability: agent.currentTicketCount < agent.maxConcurrentTickets ? 'available' : 'busy'
      }))
      .sort((a, b) => a.workload - b.workload);
  }

  async getSupportAnalytics(days: number = 30): Promise<SupportAnalytics> {
    const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
    const tickets = Array.from(this.tickets.values())
      .filter(ticket => ticket.createdAt >= startDate);

    const totalTickets = tickets.length;
    const openTickets = tickets.filter(t => t.status === 'open' || t.status === 'in-progress' || t.status === 'waiting').length;
    const resolvedTickets = tickets.filter(t => t.status === 'resolved' || t.status === 'closed').length;

    const resolutionTimes = tickets
      .filter(t => t.resolvedAt)
      .map(t => t.resolvedAt!.getTime() - t.createdAt.getTime());
    const averageResolutionTime = resolutionTimes.length > 0
      ? resolutionTimes.reduce((sum, time) => sum + time, 0) / resolutionTimes.length / (60 * 60 * 1000)
      : 0;

    const firstResponseTimes = tickets
      .filter(t => t.firstResponseAt)
      .map(t => t.firstResponseAt!.getTime() - t.createdAt.getTime());
    const averageFirstResponseTime = firstResponseTimes.length > 0
      ? firstResponseTimes.reduce((sum, time) => sum + time, 0) / firstResponseTimes.length / (60 * 60 * 1000)
      : 0;

    const satisfactionRatings = tickets
      .filter(t => t.satisfaction)
      .map(t => t.satisfaction!.rating);
    const satisfactionScore = satisfactionRatings.length > 0
      ? satisfactionRatings.reduce((sum, rating) => sum + rating, 0) / satisfactionRatings.length
      : 0;

    const ticketsByPriority = [
      { priority: 'urgent', count: tickets.filter(t => t.priority === 'urgent').length },
      { priority: 'high', count: tickets.filter(t => t.priority === 'high').length },
      { priority: 'medium', count: tickets.filter(t => t.priority === 'medium').length },
      { priority: 'low', count: tickets.filter(t => t.priority === 'low').length }
    ];

    const ticketsByCategory = [
      { category: 'technical', count: tickets.filter(t => t.category === 'technical').length },
      { category: 'billing', count: tickets.filter(t => t.category === 'billing').length },
      { category: 'feature-request', count: tickets.filter(t => t.category === 'feature-request').length },
      { category: 'bug-report', count: tickets.filter(t => t.category === 'bug-report').length },
      { category: 'general', count: tickets.filter(t => t.category === 'general').length },
      { category: 'account', count: tickets.filter(t => t.category === 'account').length }
    ];

    const ticketsByStatus = [
      { status: 'open', count: tickets.filter(t => t.status === 'open').length },
      { status: 'in-progress', count: tickets.filter(t => t.status === 'in-progress').length },
      { status: 'waiting', count: tickets.filter(t => t.status === 'waiting').length },
      { status: 'resolved', count: tickets.filter(t => t.status === 'resolved').length },
      { status: 'closed', count: tickets.filter(t => t.status === 'closed').length }
    ];

    const agentPerformance = Array.from(this.agents.values())
      .map(agent => {
        const agentTickets = tickets.filter(t => t.assignedAgentId === agent.id);
        const agentResolutionTimes = agentTickets
          .filter(t => t.resolvedAt)
          .map(t => t.resolvedAt!.getTime() - t.createdAt.getTime());
        const avgResolutionTime = agentResolutionTimes.length > 0
          ? agentResolutionTimes.reduce((sum, time) => sum + time, 0) / agentResolutionTimes.length / (60 * 60 * 1000)
          : 0;

        return {
          agent,
          ticketsHandled: agentTickets.length,
          avgResolutionTime,
          satisfactionScore: agent.satisfactionScore
        };
      })
      .sort((a, b) => b.ticketsHandled - a.ticketsHandled);

    const escalatedTickets = tickets.filter(t => t.tags.includes('escalated')).length;
    const escalationRate = totalTickets > 0 ? (escalatedTickets / totalTickets) * 100 : 0;

    const reopenedTickets = tickets.filter(t => t.tags.includes('reopened')).length;
    const reopenRate = resolvedTickets > 0 ? (reopenedTickets / resolvedTickets) * 100 : 0;

    const trendsData = [];
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(Date.now() - i * 24 * 60 * 60 * 1000);
      const dayStart = new Date(date.setHours(0, 0, 0, 0));
      const dayEnd = new Date(date.setHours(23, 59, 59, 999));
      
      const dayTickets = tickets.filter(t => t.createdAt >= dayStart && t.createdAt <= dayEnd);
      const dayResolved = tickets.filter(t => t.resolvedAt && t.resolvedAt >= dayStart && t.resolvedAt <= dayEnd);
      const daySatisfaction = dayResolved
        .filter(t => t.satisfaction)
        .reduce((sum, t) => sum + t.satisfaction!.rating, 0) / Math.max(dayResolved.filter(t => t.satisfaction).length, 1);

      trendsData.push({
        date: dayStart.toISOString().split('T')[0],
        opened: dayTickets.length,
        resolved: dayResolved.length,
        satisfaction: daySatisfaction || 0
      });
    }

    return {
      totalTickets,
      openTickets,
      resolvedTickets,
      averageResolutionTime: Math.round(averageResolutionTime * 100) / 100,
      averageFirstResponseTime: Math.round(averageFirstResponseTime * 100) / 100,
      satisfactionScore: Math.round(satisfactionScore * 100) / 100,
      ticketsByPriority,
      ticketsByCategory,
      ticketsByStatus,
      agentPerformance,
      trendsData,
      escalationRate: Math.round(escalationRate * 100) / 100,
      reopenRate: Math.round(reopenRate * 100) / 100
    };
  }

  private processAutomationRules(ticket: SupportTicket): void {
    Array.from(this.automationRules.values())
      .filter(rule => rule.isActive)
      .forEach(rule => {
        if (this.shouldTriggerRule(rule, ticket)) {
          rule.actions.forEach(action => {
            this.executeAction(action, ticket);
          });
        }
      });
  }

  private shouldTriggerRule(rule: AutomationRule, ticket: SupportTicket): boolean {
    if (rule.trigger.type !== 'ticket-created') return false;

    const conditions = rule.trigger.conditions;
    
    if (conditions.category && ticket.category !== conditions.category) return false;
    if (conditions.priority && ticket.priority !== conditions.priority) return false;
    if (conditions.tags && !conditions.tags.every((tag: string) => ticket.tags.includes(tag))) return false;

    return true;
  }

  private executeAction(action: any, ticket: SupportTicket): void {
    switch (action.type) {
      case 'assign':
        if (action.parameters.skill) {
          const availableAgent = Array.from(this.agents.values())
            .find(agent => 
              agent.isActive && 
              agent.skills.includes(action.parameters.skill) &&
              agent.currentTicketCount < agent.maxConcurrentTickets
            );
          if (availableAgent) {
            this.assignTicket(ticket.id, availableAgent.id);
          }
        }
        break;

      case 'tag':
        if (action.parameters.tags) {
          ticket.tags.push(...action.parameters.tags);
        }
        break;

      case 'priority':
        if (action.parameters.priority) {
          ticket.priority = action.parameters.priority;
        }
        break;

      case 'template-response':
        setTimeout(() => {
          this.addMessage({
            ticketId: ticket.id,
            authorId: 'system',
            authorType: 'system',
            content: 'Thank you for contacting support. We have received your ticket and will respond soon.',
            isInternal: false,
            messageType: 'reply'
          });
        }, (action.parameters.delay || 0) * 60 * 1000);
        break;
    }
  }

  getTicket(ticketId: string): SupportTicket | undefined {
    return this.tickets.get(ticketId);
  }

  getAgent(agentId: string): SupportAgent | undefined {
    return this.agents.get(agentId);
  }

  getAllAgents(): SupportAgent[] {
    return Array.from(this.agents.values());
  }

  getActiveAgents(): SupportAgent[] {
    return Array.from(this.agents.values()).filter(agent => agent.isActive);
  }

  getKnowledgeBaseArticle(articleId: string): KnowledgeBaseArticle | undefined {
    return this.knowledgeBase.get(articleId);
  }

  async searchKnowledgeBase(query: string): Promise<KnowledgeBaseArticle[]> {
    const queryLower = query.toLowerCase();
    
    return Array.from(this.knowledgeBase.values())
      .filter(article => {
        if (!article.isPublic) return false;
        
        return (
          article.title.toLowerCase().includes(queryLower) ||
          article.content.toLowerCase().includes(queryLower) ||
          article.summary.toLowerCase().includes(queryLower) ||
          article.tags.some(tag => tag.toLowerCase().includes(queryLower))
        );
      })
      .sort((a, b) => b.viewCount - a.viewCount);
  }
}

export const supportTicketing = new CustomerSupportTicketingSystem();