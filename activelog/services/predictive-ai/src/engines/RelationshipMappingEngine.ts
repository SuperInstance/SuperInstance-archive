import { UserAction, RelationshipNode, RelationshipEdge } from '../types';
import { v4 as uuidv4 } from 'uuid';
import { differenceInMinutes, differenceInDays, isAfter, subDays } from 'date-fns';
import { groupBy, orderBy, uniqBy } from 'lodash';

export class RelationshipMappingEngine {
  private nodes: Map<string, Map<string, RelationshipNode>> = new Map();
  private edges: Map<string, Map<string, RelationshipEdge[]>> = new Map();
  private cooccurrenceMatrix: Map<string, Map<string, number>> = new Map();
  private semanticClusters: Map<string, SemanticCluster[]> = new Map();

  async buildRelationshipGraph(userId: string, actions: UserAction[]): Promise<void> {
    this.initializeUserMaps(userId);
    
    // Extract entities from actions
    const nodes = this.extractNodes(actions);
    const edges = this.extractEdges(actions, nodes);
    
    // Store nodes and edges
    for (const node of nodes) {
      this.addNode(userId, node);
    }
    
    for (const edge of edges) {
      this.addEdge(userId, edge);
    }
    
    // Build semantic clusters
    await this.buildSemanticClusters(userId);
    
    // Calculate relationship strengths
    await this.calculateRelationshipStrengths(userId);
  }

  async findRelatedItems(
    userId: string,
    resourcePath: string,
    maxResults: number = 10
  ): Promise<RelatedItem[]> {
    const userNodes = this.nodes.get(userId);
    const userEdges = this.edges.get(userId);
    
    if (!userNodes || !userEdges) {
      return [];
    }
    
    const sourceNode = this.findNodeByPath(userId, resourcePath);
    if (!sourceNode) {
      return [];
    }
    
    const related: RelatedItem[] = [];
    
    // Find directly connected items
    const directlyConnected = this.findDirectlyConnected(userId, sourceNode.id);
    related.push(...directlyConnected);
    
    // Find items in the same semantic cluster
    const clusterRelated = this.findClusterRelated(userId, sourceNode);
    related.push(...clusterRelated);
    
    // Find items with temporal proximity
    const temporallyRelated = this.findTemporallyRelated(userId, sourceNode);
    related.push(...temporallyRelated);
    
    // Find items with co-occurrence patterns
    const cooccurring = this.findCooccurringItems(userId, sourceNode);
    related.push(...cooccurring);
    
    // Deduplicate and rank by relevance score
    const uniqueRelated = uniqBy(related, 'id');
    return orderBy(uniqueRelated, 'relevanceScore', 'desc').slice(0, maxResults);
  }

  async findPeopleRelated(userId: string, resourcePath: string): Promise<PersonRelation[]> {
    const node = this.findNodeByPath(userId, resourcePath);
    if (!node) return [];
    
    const userEdges = this.edges.get(userId);
    if (!userEdges) return [];
    
    const personRelations: PersonRelation[] = [];
    const edgeMap = userEdges.get(node.id) || [];
    
    for (const edge of edgeMap) {
      const relatedNode = this.getNode(userId, edge.to);
      if (relatedNode && relatedNode.type === 'person') {
        personRelations.push({
          personId: relatedNode.id,
          personName: relatedNode.properties.name || 'Unknown',
          relationship: edge.relationship,
          strength: edge.weight,
          lastInteraction: relatedNode.lastAccessed,
          sharedItems: await this.countSharedItems(userId, node.id, relatedNode.id)
        });
      }
    }
    
    return orderBy(personRelations, 'strength', 'desc');
  }

  async findProjectNetwork(userId: string, projectPath: string): Promise<ProjectNetwork> {
    const projectNode = this.findNodeByPath(userId, projectPath);
    if (!projectNode || projectNode.type !== 'project') {
      return { files: [], people: [], events: [], tags: [] };
    }
    
    const network: ProjectNetwork = {
      files: [],
      people: [],
      events: [],
      tags: []
    };
    
    const connected = this.findDirectlyConnected(userId, projectNode.id);
    
    for (const item of connected) {
      const node = this.getNode(userId, item.id);
      if (!node) continue;
      
      switch (node.type) {
        case 'file':
          network.files.push({
            path: node.properties.path,
            relevance: item.relevanceScore,
            lastModified: node.lastAccessed
          });
          break;
        case 'person':
          network.people.push({
            name: node.properties.name,
            role: node.properties.role || 'contributor',
            involvement: item.relevanceScore
          });
          break;
        case 'event':
          network.events.push({
            description: node.properties.description,
            date: new Date(node.properties.date),
            importance: item.relevanceScore
          });
          break;
        case 'tag':
          network.tags.push({
            name: node.properties.name,
            frequency: node.properties.frequency || 1,
            relevance: item.relevanceScore
          });
          break;
      }
    }
    
    return network;
  }

  async updateFromAction(userId: string, action: UserAction): Promise<void> {
    this.initializeUserMaps(userId);
    
    // Extract new relationships from this action
    const newNodes = this.extractNodesFromAction(action);
    const newEdges = this.extractEdgesFromAction(action);
    
    // Update or create nodes
    for (const node of newNodes) {
      const existing = this.getNode(userId, node.id);
      if (existing) {
        this.updateNode(userId, node);
      } else {
        this.addNode(userId, node);
      }
    }
    
    // Update or strengthen edges
    for (const edge of newEdges) {
      this.strengthenEdge(userId, edge);
    }
    
    // Update co-occurrence matrix
    this.updateCooccurrence(userId, action);
  }

  async getRelationshipSummary(userId: string): Promise<RelationshipSummary> {
    const userNodes = this.nodes.get(userId) || new Map();
    const userEdges = this.edges.get(userId) || new Map();
    
    const summary: RelationshipSummary = {
      totalNodes: userNodes.size,
      totalEdges: Array.from(userEdges.values()).reduce((sum, edges) => sum + edges.length, 0),
      nodeTypes: {},
      strongestConnections: [],
      clusters: this.semanticClusters.get(userId) || []
    };
    
    // Count node types
    for (const node of userNodes.values()) {
      summary.nodeTypes[node.type] = (summary.nodeTypes[node.type] || 0) + 1;
    }
    
    // Find strongest connections
    const allEdges: RelationshipEdge[] = [];
    for (const edges of userEdges.values()) {
      allEdges.push(...edges);
    }
    
    summary.strongestConnections = orderBy(allEdges, 'weight', 'desc')
      .slice(0, 10)
      .map(edge => ({
        from: this.getNode(userId, edge.from)?.properties.name || edge.from,
        to: this.getNode(userId, edge.to)?.properties.name || edge.to,
        relationship: edge.relationship,
        strength: edge.weight
      }));
    
    return summary;
  }

  private initializeUserMaps(userId: string): void {
    if (!this.nodes.has(userId)) {
      this.nodes.set(userId, new Map());
    }
    if (!this.edges.has(userId)) {
      this.edges.set(userId, new Map());
    }
    if (!this.cooccurrenceMatrix.has(userId)) {
      this.cooccurrenceMatrix.set(userId, new Map());
    }
  }

  private extractNodes(actions: UserAction[]): RelationshipNode[] {
    const nodes: RelationshipNode[] = [];
    const nodeMap = new Map<string, RelationshipNode>();
    
    for (const action of actions) {
      const extractedNodes = this.extractNodesFromAction(action);
      for (const node of extractedNodes) {
        if (!nodeMap.has(node.id)) {
          nodeMap.set(node.id, node);
        }
      }
    }
    
    return Array.from(nodeMap.values());
  }

  private extractNodesFromAction(action: UserAction): RelationshipNode[] {
    const nodes: RelationshipNode[] = [];
    
    // File/folder node
    const resourceNode: RelationshipNode = {
      id: this.generateNodeId(action.resourcePath),
      type: this.determineResourceType(action.resourcePath, action.actionType),
      properties: {
        path: action.resourcePath,
        name: this.extractNameFromPath(action.resourcePath),
        actionType: action.actionType
      },
      weight: 1,
      lastAccessed: action.timestamp
    };
    nodes.push(resourceNode);
    
    // Person nodes (if mentioned in metadata)
    if (action.metadata?.collaborators) {
      for (const collaborator of action.metadata.collaborators) {
        nodes.push({
          id: `person_${collaborator}`,
          type: 'person',
          properties: { name: collaborator },
          weight: 1,
          lastAccessed: action.timestamp
        });
      }
    }
    
    // Tag nodes
    if (action.metadata?.tags) {
      for (const tag of action.metadata.tags) {
        nodes.push({
          id: `tag_${tag}`,
          type: 'tag',
          properties: { name: tag },
          weight: 1,
          lastAccessed: action.timestamp
        });
      }
    }
    
    // Project node (inferred from path)
    const projectPath = this.extractProjectPath(action.resourcePath);
    if (projectPath) {
      nodes.push({
        id: `project_${projectPath}`,
        type: 'project',
        properties: {
          path: projectPath,
          name: this.extractNameFromPath(projectPath)
        },
        weight: 1,
        lastAccessed: action.timestamp
      });
    }
    
    return nodes;
  }

  private extractEdges(actions: UserAction[], nodes: RelationshipNode[]): RelationshipEdge[] {
    const edges: RelationshipEdge[] = [];
    
    // Temporal co-occurrence edges (files accessed within 10 minutes)
    for (let i = 0; i < actions.length - 1; i++) {
      const current = actions[i];
      const next = actions[i + 1];
      
      if (differenceInMinutes(new Date(next.timestamp), new Date(current.timestamp)) <= 10) {
        edges.push({
          from: this.generateNodeId(current.resourcePath),
          to: this.generateNodeId(next.resourcePath),
          relationship: 'precedes',
          weight: 1,
          confidence: 0.6,
          metadata: { timeDifference: differenceInMinutes(new Date(next.timestamp), new Date(current.timestamp)) }
        });
      }
    }
    
    // Hierarchical edges (folder contains file)
    for (const node of nodes) {
      if (node.type === 'file' || node.type === 'folder') {
        const parentPath = this.getParentPath(node.properties.path);
        if (parentPath) {
          const parentNodeId = this.generateNodeId(parentPath);
          edges.push({
            from: parentNodeId,
            to: node.id,
            relationship: 'contains',
            weight: 1,
            confidence: 1.0,
            metadata: { hierarchical: true }
          });
        }
      }
    }
    
    return edges;
  }

  private extractEdgesFromAction(action: UserAction): RelationshipEdge[] {
    const edges: RelationshipEdge[] = [];
    const resourceNodeId = this.generateNodeId(action.resourcePath);
    
    // Connect to collaborators
    if (action.metadata?.collaborators) {
      for (const collaborator of action.metadata.collaborators) {
        edges.push({
          from: resourceNodeId,
          to: `person_${collaborator}`,
          relationship: 'collaborates_with',
          weight: 1,
          confidence: 0.8,
          metadata: { action: action.actionType }
        });
      }
    }
    
    // Connect to tags
    if (action.metadata?.tags) {
      for (const tag of action.metadata.tags) {
        edges.push({
          from: resourceNodeId,
          to: `tag_${tag}`,
          relationship: 'tagged_with',
          weight: 1,
          confidence: 0.9,
          metadata: { action: action.actionType }
        });
      }
    }
    
    // Connect to project
    const projectPath = this.extractProjectPath(action.resourcePath);
    if (projectPath) {
      edges.push({
        from: `project_${projectPath}`,
        to: resourceNodeId,
        relationship: 'contains',
        weight: 1,
        confidence: 0.8,
        metadata: { inferred: true }
      });
    }
    
    return edges;
  }

  private async buildSemanticClusters(userId: string): Promise<void> {
    const userNodes = this.nodes.get(userId);
    if (!userNodes) return;
    
    const clusters: SemanticCluster[] = [];
    const processedNodes = new Set<string>();
    
    for (const node of userNodes.values()) {
      if (processedNodes.has(node.id)) continue;
      
      const cluster = this.findSemanticCluster(userId, node, processedNodes);
      if (cluster.nodes.length > 1) {
        clusters.push(cluster);
      }
    }
    
    this.semanticClusters.set(userId, clusters);
  }

  private findSemanticCluster(
    userId: string,
    seedNode: RelationshipNode,
    processedNodes: Set<string>
  ): SemanticCluster {
    const cluster: SemanticCluster = {
      id: uuidv4(),
      name: this.generateClusterName(seedNode),
      nodes: [seedNode.id],
      centerNode: seedNode.id,
      coherenceScore: 0
    };
    
    processedNodes.add(seedNode.id);
    
    const userNodes = this.nodes.get(userId)!;
    
    // Find semantically similar nodes
    for (const node of userNodes.values()) {
      if (processedNodes.has(node.id)) continue;
      
      const similarity = this.calculateSemanticSimilarity(seedNode, node);
      if (similarity > 0.6) {
        cluster.nodes.push(node.id);
        processedNodes.add(node.id);
      }
    }
    
    cluster.coherenceScore = this.calculateClusterCoherence(userId, cluster);
    return cluster;
  }

  private calculateSemanticSimilarity(node1: RelationshipNode, node2: RelationshipNode): number {
    let similarity = 0;
    
    // Type similarity
    if (node1.type === node2.type) {
      similarity += 0.3;
    }
    
    // Name similarity
    const name1 = (node1.properties.name || '').toLowerCase();
    const name2 = (node2.properties.name || '').toLowerCase();
    
    if (name1.includes(name2) || name2.includes(name1)) {
      similarity += 0.4;
    }
    
    // Path similarity (for files/folders)
    if (node1.properties.path && node2.properties.path) {
      const path1Parts = node1.properties.path.split('/');
      const path2Parts = node2.properties.path.split('/');
      const commonParts = path1Parts.filter(part => path2Parts.includes(part));
      similarity += (commonParts.length / Math.max(path1Parts.length, path2Parts.length)) * 0.3;
    }
    
    return similarity;
  }

  private calculateClusterCoherence(userId: string, cluster: SemanticCluster): number {
    const userEdges = this.edges.get(userId);
    if (!userEdges) return 0;
    
    let totalConnections = 0;
    let actualConnections = 0;
    
    for (let i = 0; i < cluster.nodes.length; i++) {
      for (let j = i + 1; j < cluster.nodes.length; j++) {
        totalConnections++;
        
        const edges1 = userEdges.get(cluster.nodes[i]) || [];
        const edges2 = userEdges.get(cluster.nodes[j]) || [];
        
        if (edges1.some(e => e.to === cluster.nodes[j]) || 
            edges2.some(e => e.to === cluster.nodes[i])) {
          actualConnections++;
        }
      }
    }
    
    return totalConnections > 0 ? actualConnections / totalConnections : 0;
  }

  private async calculateRelationshipStrengths(userId: string): Promise<void> {
    const userEdges = this.edges.get(userId);
    if (!userEdges) return;
    
    for (const [nodeId, edges] of userEdges.entries()) {
      for (const edge of edges) {
        edge.weight = this.calculateEdgeWeight(userId, edge);
      }
    }
  }

  private calculateEdgeWeight(userId: string, edge: RelationshipEdge): number {
    let weight = 1;
    
    // Base weight from relationship type
    const relationshipWeights = {
      'contains': 0.8,
      'related_to': 0.6,
      'precedes': 0.4,
      'triggers': 0.7,
      'collaborates_with': 0.9
    };
    
    weight *= relationshipWeights[edge.relationship] || 0.5;
    
    // Boost based on confidence
    weight *= edge.confidence;
    
    // Boost based on co-occurrence frequency
    const cooccurrenceMatrix = this.cooccurrenceMatrix.get(userId);
    if (cooccurrenceMatrix) {
      const fromMatrix = cooccurrenceMatrix.get(edge.from);
      if (fromMatrix) {
        const cooccurrenceCount = fromMatrix.get(edge.to) || 0;
        weight *= Math.min(1 + (cooccurrenceCount * 0.1), 2.0);
      }
    }
    
    return weight;
  }

  private findDirectlyConnected(userId: string, nodeId: string): RelatedItem[] {
    const userEdges = this.edges.get(userId);
    if (!userEdges) return [];
    
    const edges = userEdges.get(nodeId) || [];
    const related: RelatedItem[] = [];
    
    for (const edge of edges) {
      const relatedNode = this.getNode(userId, edge.to);
      if (relatedNode) {
        related.push({
          id: edge.to,
          type: relatedNode.type,
          name: relatedNode.properties.name || '',
          path: relatedNode.properties.path,
          relationship: edge.relationship,
          relevanceScore: edge.weight * 100,
          lastAccessed: relatedNode.lastAccessed
        });
      }
    }
    
    return related;
  }

  private findClusterRelated(userId: string, node: RelationshipNode): RelatedItem[] {
    const clusters = this.semanticClusters.get(userId) || [];
    const nodeCluster = clusters.find(c => c.nodes.includes(node.id));
    
    if (!nodeCluster) return [];
    
    const related: RelatedItem[] = [];
    
    for (const nodeId of nodeCluster.nodes) {
      if (nodeId !== node.id) {
        const relatedNode = this.getNode(userId, nodeId);
        if (relatedNode) {
          related.push({
            id: nodeId,
            type: relatedNode.type,
            name: relatedNode.properties.name || '',
            path: relatedNode.properties.path,
            relationship: 'clustered_with',
            relevanceScore: nodeCluster.coherenceScore * 70,
            lastAccessed: relatedNode.lastAccessed
          });
        }
      }
    }
    
    return related;
  }

  private findTemporallyRelated(userId: string, node: RelationshipNode): RelatedItem[] {
    const userNodes = this.nodes.get(userId);
    if (!userNodes) return [];
    
    const related: RelatedItem[] = [];
    const nodeTime = new Date(node.lastAccessed);
    
    for (const candidateNode of userNodes.values()) {
      if (candidateNode.id === node.id) continue;
      
      const timeDiff = Math.abs(differenceInMinutes(
        new Date(candidateNode.lastAccessed),
        nodeTime
      ));
      
      if (timeDiff <= 60) { // Within 1 hour
        const relevanceScore = Math.max(0, 60 - timeDiff);
        
        related.push({
          id: candidateNode.id,
          type: candidateNode.type,
          name: candidateNode.properties.name || '',
          path: candidateNode.properties.path,
          relationship: 'temporal_proximity',
          relevanceScore,
          lastAccessed: candidateNode.lastAccessed
        });
      }
    }
    
    return related;
  }

  private findCooccurringItems(userId: string, node: RelationshipNode): RelatedItem[] {
    const cooccurrenceMatrix = this.cooccurrenceMatrix.get(userId);
    if (!cooccurrenceMatrix) return [];
    
    const nodeMatrix = cooccurrenceMatrix.get(node.id);
    if (!nodeMatrix) return [];
    
    const related: RelatedItem[] = [];
    
    for (const [relatedNodeId, count] of nodeMatrix.entries()) {
      if (count >= 2) { // At least 2 co-occurrences
        const relatedNode = this.getNode(userId, relatedNodeId);
        if (relatedNode) {
          related.push({
            id: relatedNodeId,
            type: relatedNode.type,
            name: relatedNode.properties.name || '',
            path: relatedNode.properties.path,
            relationship: 'co_occurs',
            relevanceScore: Math.min(count * 10, 100),
            lastAccessed: relatedNode.lastAccessed
          });
        }
      }
    }
    
    return related;
  }

  private updateCooccurrence(userId: string, action: UserAction): void {
    const cooccurrenceMatrix = this.cooccurrenceMatrix.get(userId)!;
    const resourceNodeId = this.generateNodeId(action.resourcePath);
    
    // Get recent actions (last 10 minutes) to build co-occurrence
    // This would need to be implemented based on your action history storage
  }

  // Helper methods
  private addNode(userId: string, node: RelationshipNode): void {
    const userNodes = this.nodes.get(userId)!;
    userNodes.set(node.id, node);
  }

  private addEdge(userId: string, edge: RelationshipEdge): void {
    const userEdges = this.edges.get(userId)!;
    
    if (!userEdges.has(edge.from)) {
      userEdges.set(edge.from, []);
    }
    
    userEdges.get(edge.from)!.push(edge);
  }

  private updateNode(userId: string, node: RelationshipNode): void {
    const userNodes = this.nodes.get(userId)!;
    const existing = userNodes.get(node.id);
    
    if (existing) {
      existing.lastAccessed = node.lastAccessed;
      existing.weight += 1;
      Object.assign(existing.properties, node.properties);
    }
  }

  private strengthenEdge(userId: string, edge: RelationshipEdge): void {
    const userEdges = this.edges.get(userId)!;
    const edges = userEdges.get(edge.from) || [];
    
    const existing = edges.find(e => e.to === edge.to && e.relationship === edge.relationship);
    
    if (existing) {
      existing.weight += 0.1;
      existing.confidence = Math.min(existing.confidence + 0.05, 1.0);
    } else {
      this.addEdge(userId, edge);
    }
  }

  private getNode(userId: string, nodeId: string): RelationshipNode | undefined {
    return this.nodes.get(userId)?.get(nodeId);
  }

  private findNodeByPath(userId: string, path: string): RelationshipNode | undefined {
    const userNodes = this.nodes.get(userId);
    if (!userNodes) return undefined;
    
    for (const node of userNodes.values()) {
      if (node.properties.path === path) {
        return node;
      }
    }
    
    return undefined;
  }

  private generateNodeId(path: string): string {
    return `node_${path.replace(/[\/\\]/g, '_')}`;
  }

  private determineResourceType(path: string, actionType: string): 'file' | 'folder' | 'project' {
    if (actionType === 'folder_create') return 'folder';
    if (path.includes('.')) return 'file';
    return 'folder';
  }

  private extractNameFromPath(path: string): string {
    return path.split('/').pop() || path;
  }

  private extractProjectPath(path: string): string | null {
    const parts = path.split('/').filter(p => p);
    
    // Look for common project indicators
    const projectIndicators = ['project', 'projects', 'work', 'code', 'dev'];
    
    for (let i = 0; i < parts.length - 1; i++) {
      if (projectIndicators.some(indicator => 
        parts[i].toLowerCase().includes(indicator)
      )) {
        return parts.slice(0, i + 2).join('/');
      }
    }
    
    return null;
  }

  private getParentPath(path: string): string | null {
    const lastSlash = path.lastIndexOf('/');
    return lastSlash > 0 ? path.substring(0, lastSlash) : null;
  }

  private generateClusterName(node: RelationshipNode): string {
    if (node.type === 'project') {
      return `${node.properties.name} Project`;
    }
    if (node.type === 'folder') {
      return `${node.properties.name} Files`;
    }
    return `${node.properties.name} Cluster`;
  }

  private async countSharedItems(userId: string, nodeId1: string, nodeId2: string): Promise<number> {
    // This would count items that both nodes are connected to
    return 0; // Placeholder
  }
}

interface RelatedItem {
  id: string;
  type: string;
  name: string;
  path?: string;
  relationship: string;
  relevanceScore: number;
  lastAccessed: Date;
}

interface PersonRelation {
  personId: string;
  personName: string;
  relationship: string;
  strength: number;
  lastInteraction: Date;
  sharedItems: number;
}

interface ProjectNetwork {
  files: Array<{
    path: string;
    relevance: number;
    lastModified: Date;
  }>;
  people: Array<{
    name: string;
    role: string;
    involvement: number;
  }>;
  events: Array<{
    description: string;
    date: Date;
    importance: number;
  }>;
  tags: Array<{
    name: string;
    frequency: number;
    relevance: number;
  }>;
}

interface SemanticCluster {
  id: string;
  name: string;
  nodes: string[];
  centerNode: string;
  coherenceScore: number;
}

interface RelationshipSummary {
  totalNodes: number;
  totalEdges: number;
  nodeTypes: Record<string, number>;
  strongestConnections: Array<{
    from: string;
    to: string;
    relationship: string;
    strength: number;
  }>;
  clusters: SemanticCluster[];
}