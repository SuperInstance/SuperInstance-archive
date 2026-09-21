const { EventEmitter } = require('events');
const crypto = require('crypto');

class LineageTracker extends EventEmitter {
    constructor(options = {}) {
        super();
        this.lineageGraph = new Map(); // entityId -> lineage record
        this.relationships = new Map(); // relationshipId -> relationship details
        this.transformations = new Map(); // transformationId -> transformation details
        this.dataFlows = new Map(); // flowId -> data flow information
        this.impactAnalysis = new Map(); // entityId -> impact analysis
        this.lineageQueries = [];
        
        this.maxLineageDepth = options.maxLineageDepth || 10;
        this.retentionPeriod = options.retentionPeriod || 86400000 * 365; // 1 year
        this.trackingLevel = options.trackingLevel || 'detailed'; // basic, detailed, comprehensive
        
        this.setupEventHandlers();
    }

    trackEntityCreation(entityId, entityInfo) {
        const lineageRecord = {
            entityId,
            type: entityInfo.type,
            source: entityInfo.source,
            createdAt: new Date(),
            createdBy: entityInfo.createdBy,
            originalSource: entityInfo.originalSource || entityInfo.source,
            upstream: new Set(),
            downstream: new Set(),
            transformations: [],
            metadata: entityInfo.metadata || {},
            qualityMetrics: {
                completeness: 1.0,
                accuracy: 1.0,
                timeliness: 1.0,
                consistency: 1.0
            },
            versions: [{
                version: '1.0.0',
                timestamp: new Date(),
                changes: ['initial_creation'],
                changeBy: entityInfo.createdBy
            }],
            tags: entityInfo.tags || [],
            businessContext: entityInfo.businessContext || {}
        };

        this.lineageGraph.set(entityId, lineageRecord);
        this.emit('entity:created', lineageRecord);
        return lineageRecord;
    }

    trackDataTransformation(sourceEntityId, targetEntityId, transformationInfo) {
        const transformationId = crypto.randomUUID();
        const transformation = {
            id: transformationId,
            sourceEntityId,
            targetEntityId,
            transformationType: transformationInfo.type || 'unknown',
            transformationName: transformationInfo.name || 'Unnamed Transformation',
            description: transformationInfo.description,
            logic: transformationInfo.logic,
            parameters: transformationInfo.parameters || {},
            appliedAt: new Date(),
            appliedBy: transformationInfo.appliedBy,
            tool: transformationInfo.tool,
            version: transformationInfo.version,
            qualityImpact: transformationInfo.qualityImpact || {},
            businessRules: transformationInfo.businessRules || [],
            metadata: transformationInfo.metadata || {}
        };

        this.transformations.set(transformationId, transformation);

        // Update lineage records
        const sourceRecord = this.lineageGraph.get(sourceEntityId);
        const targetRecord = this.lineageGraph.get(targetEntityId);

        if (sourceRecord) {
            sourceRecord.downstream.add(targetEntityId);
            sourceRecord.transformations.push({
                transformationId,
                direction: 'downstream',
                targetEntity: targetEntityId,
                appliedAt: new Date()
            });
        }

        if (targetRecord) {
            targetRecord.upstream.add(sourceEntityId);
            targetRecord.transformations.push({
                transformationId,
                direction: 'upstream',
                sourceEntity: sourceEntityId,
                appliedAt: new Date()
            });

            // Update quality metrics based on transformation
            this.updateQualityMetrics(targetRecord, transformation);

            // Add version record
            targetRecord.versions.push({
                version: this.incrementVersion(targetRecord.versions),
                timestamp: new Date(),
                changes: [`transformation_applied:${transformation.transformationType}`],
                changeBy: transformation.appliedBy,
                transformationId
            });
        }

        // Create relationship record
        const relationshipId = crypto.randomUUID();
        const relationship = {
            id: relationshipId,
            sourceEntityId,
            targetEntityId,
            relationshipType: 'transformation',
            transformationId,
            strength: this.calculateRelationshipStrength(transformation),
            createdAt: new Date(),
            metadata: {
                transformationType: transformation.transformationType,
                tool: transformation.tool
            }
        };

        this.relationships.set(relationshipId, relationship);

        this.emit('transformation:tracked', {
            transformation,
            relationship,
            sourceRecord,
            targetRecord
        });

        return transformationId;
    }

    trackDataFlow(flowInfo) {
        const flowId = crypto.randomUUID();
        const dataFlow = {
            id: flowId,
            name: flowInfo.name || 'Unnamed Flow',
            description: flowInfo.description,
            sourceSystem: flowInfo.sourceSystem,
            targetSystem: flowInfo.targetSystem,
            entities: flowInfo.entities || [],
            flowType: flowInfo.flowType || 'batch', // batch, streaming, realtime
            frequency: flowInfo.frequency,
            schedule: flowInfo.schedule,
            dataVolume: flowInfo.dataVolume,
            latency: flowInfo.latency,
            errorRate: flowInfo.errorRate || 0,
            sla: flowInfo.sla,
            owner: flowInfo.owner,
            businessPurpose: flowInfo.businessPurpose,
            complianceRequirements: flowInfo.complianceRequirements || [],
            startTime: flowInfo.startTime || new Date(),
            endTime: flowInfo.endTime,
            status: flowInfo.status || 'active',
            metadata: flowInfo.metadata || {}
        };

        this.dataFlows.set(flowId, dataFlow);

        // Link entities to this flow
        if (flowInfo.entities) {
            for (const entityId of flowInfo.entities) {
                const record = this.lineageGraph.get(entityId);
                if (record) {
                    if (!record.dataFlows) {
                        record.dataFlows = [];
                    }
                    record.dataFlows.push(flowId);
                }
            }
        }

        this.emit('dataflow:tracked', dataFlow);
        return flowId;
    }

    trackEntityUpdate(entityId, updateInfo) {
        const record = this.lineageGraph.get(entityId);
        if (!record) {
            throw new Error(`Entity not found in lineage: ${entityId}`);
        }

        // Add version record
        record.versions.push({
            version: this.incrementVersion(record.versions),
            timestamp: new Date(),
            changes: updateInfo.changes || ['data_updated'],
            changeBy: updateInfo.updatedBy,
            description: updateInfo.description,
            fieldChanges: updateInfo.fieldChanges || {}
        });

        // Update metadata
        if (updateInfo.metadata) {
            record.metadata = { ...record.metadata, ...updateInfo.metadata };
        }

        // Update quality metrics if provided
        if (updateInfo.qualityMetrics) {
            record.qualityMetrics = { ...record.qualityMetrics, ...updateInfo.qualityMetrics };
        }

        // Update tags
        if (updateInfo.tags) {
            record.tags = [...new Set([...record.tags, ...updateInfo.tags])];
        }

        this.emit('entity:updated', { entityId, record, updateInfo });
        return record;
    }

    getLineage(entityId, options = {}) {
        const record = this.lineageGraph.get(entityId);
        if (!record) {
            return null;
        }

        const direction = options.direction || 'both'; // upstream, downstream, both
        const maxDepth = Math.min(options.maxDepth || this.maxLineageDepth, this.maxLineageDepth);
        const includeTransformations = options.includeTransformations !== false;
        
        const lineage = {
            entity: record,
            upstream: direction === 'downstream' ? [] : this.traverseUpstream(entityId, maxDepth, new Set()),
            downstream: direction === 'upstream' ? [] : this.traverseDownstream(entityId, maxDepth, new Set()),
            transformations: includeTransformations ? this.getEntityTransformations(entityId) : [],
            dataFlows: this.getEntityDataFlows(entityId),
            qualityScore: this.calculateOverallQuality(record.qualityMetrics),
            depth: {
                upstream: direction === 'downstream' ? 0 : this.calculateUpstreamDepth(entityId, new Set()),
                downstream: direction === 'upstream' ? 0 : this.calculateDownstreamDepth(entityId, new Set())
            }
        };

        // Track lineage query
        this.lineageQueries.push({
            entityId,
            direction,
            maxDepth,
            timestamp: new Date(),
            resultSize: lineage.upstream.length + lineage.downstream.length
        });

        this.emit('lineage:queried', {
            entityId,
            options,
            resultSize: lineage.upstream.length + lineage.downstream.length
        });

        return lineage;
    }

    traverseUpstream(entityId, maxDepth, visited) {
        if (maxDepth <= 0 || visited.has(entityId)) {
            return [];
        }

        visited.add(entityId);
        const record = this.lineageGraph.get(entityId);
        if (!record) {
            return [];
        }

        const upstream = [];
        for (const upstreamId of record.upstream) {
            const upstreamRecord = this.lineageGraph.get(upstreamId);
            if (upstreamRecord) {
                upstream.push({
                    entity: upstreamRecord,
                    relationship: this.findRelationship(upstreamId, entityId),
                    upstream: this.traverseUpstream(upstreamId, maxDepth - 1, new Set(visited))
                });
            }
        }

        return upstream;
    }

    traverseDownstream(entityId, maxDepth, visited) {
        if (maxDepth <= 0 || visited.has(entityId)) {
            return [];
        }

        visited.add(entityId);
        const record = this.lineageGraph.get(entityId);
        if (!record) {
            return [];
        }

        const downstream = [];
        for (const downstreamId of record.downstream) {
            const downstreamRecord = this.lineageGraph.get(downstreamId);
            if (downstreamRecord) {
                downstream.push({
                    entity: downstreamRecord,
                    relationship: this.findRelationship(entityId, downstreamId),
                    downstream: this.traverseDownstream(downstreamId, maxDepth - 1, new Set(visited))
                });
            }
        }

        return downstream;
    }

    calculateUpstreamDepth(entityId, visited) {
        if (visited.has(entityId)) {
            return 0;
        }

        visited.add(entityId);
        const record = this.lineageGraph.get(entityId);
        if (!record || record.upstream.size === 0) {
            return 0;
        }

        let maxDepth = 0;
        for (const upstreamId of record.upstream) {
            const depth = 1 + this.calculateUpstreamDepth(upstreamId, new Set(visited));
            maxDepth = Math.max(maxDepth, depth);
        }

        return maxDepth;
    }

    calculateDownstreamDepth(entityId, visited) {
        if (visited.has(entityId)) {
            return 0;
        }

        visited.add(entityId);
        const record = this.lineageGraph.get(entityId);
        if (!record || record.downstream.size === 0) {
            return 0;
        }

        let maxDepth = 0;
        for (const downstreamId of record.downstream) {
            const depth = 1 + this.calculateDownstreamDepth(downstreamId, new Set(visited));
            maxDepth = Math.max(maxDepth, depth);
        }

        return maxDepth;
    }

    findRelationship(sourceEntityId, targetEntityId) {
        for (const [relationshipId, relationship] of this.relationships) {
            if (relationship.sourceEntityId === sourceEntityId && 
                relationship.targetEntityId === targetEntityId) {
                return relationship;
            }
        }
        return null;
    }

    getEntityTransformations(entityId) {
        const transformations = [];
        const record = this.lineageGraph.get(entityId);
        
        if (record && record.transformations) {
            for (const transformationRef of record.transformations) {
                const transformation = this.transformations.get(transformationRef.transformationId);
                if (transformation) {
                    transformations.push({
                        ...transformation,
                        direction: transformationRef.direction
                    });
                }
            }
        }

        return transformations;
    }

    getEntityDataFlows(entityId) {
        const flows = [];
        const record = this.lineageGraph.get(entityId);
        
        if (record && record.dataFlows) {
            for (const flowId of record.dataFlows) {
                const flow = this.dataFlows.get(flowId);
                if (flow) {
                    flows.push(flow);
                }
            }
        }

        return flows;
    }

    performImpactAnalysis(entityId, changeType = 'data_change') {
        const analysisId = crypto.randomUUID();
        const analysis = {
            id: analysisId,
            entityId,
            changeType,
            analysisDate: new Date(),
            directImpacts: [],
            indirectImpacts: [],
            totalImpactedEntities: 0,
            highPriorityImpacts: [],
            recommendations: []
        };

        // Get downstream lineage
        const downstreamLineage = this.traverseDownstream(entityId, this.maxLineageDepth, new Set());
        
        // Analyze direct impacts (immediate downstream)
        const record = this.lineageGraph.get(entityId);
        if (record) {
            for (const downstreamId of record.downstream) {
                const downstreamRecord = this.lineageGraph.get(downstreamId);
                const relationship = this.findRelationship(entityId, downstreamId);
                
                if (downstreamRecord) {
                    const impact = {
                        entityId: downstreamId,
                        entityType: downstreamRecord.type,
                        impactType: this.determineImpactType(changeType, relationship),
                        severity: this.calculateImpactSeverity(downstreamRecord, relationship),
                        estimatedEffort: this.estimateRemediationEffort(downstreamRecord, changeType),
                        businessCriticality: this.assessBusinessCriticality(downstreamRecord),
                        dataFlows: downstreamRecord.dataFlows || []
                    };
                    
                    analysis.directImpacts.push(impact);
                    
                    if (impact.severity >= 3) {
                        analysis.highPriorityImpacts.push(impact);
                    }
                }
            }
        }

        // Analyze indirect impacts (cascade effects)
        this.analyzeIndirectImpacts(downstreamLineage, analysis, changeType);
        
        analysis.totalImpactedEntities = analysis.directImpacts.length + analysis.indirectImpacts.length;
        
        // Generate recommendations
        analysis.recommendations = this.generateImpactRecommendations(analysis);
        
        this.impactAnalysis.set(analysisId, analysis);
        
        this.emit('impact:analyzed', analysis);
        return analysis;
    }

    analyzeIndirectImpacts(lineage, analysis, changeType) {
        const processNode = (node, depth = 1) => {
            if (node.entity && depth > 1) {
                const impact = {
                    entityId: node.entity.entityId,
                    entityType: node.entity.type,
                    impactType: 'indirect',
                    depth,
                    severity: Math.max(1, 3 - depth), // Severity decreases with depth
                    propagationPath: this.buildPropagationPath(node),
                    estimatedEffort: this.estimateRemediationEffort(node.entity, changeType, depth)
                };
                
                analysis.indirectImpacts.push(impact);
            }
            
            if (node.downstream) {
                for (const downstream of node.downstream) {
                    processNode(downstream, depth + 1);
                }
            }
        };

        for (const downstreamNode of lineage) {
            if (downstreamNode.downstream) {
                for (const node of downstreamNode.downstream) {
                    processNode(node, 2);
                }
            }
        }
    }

    buildPropagationPath(node) {
        const path = [node.entity.entityId];
        let current = node;
        
        while (current.upstream && current.upstream.length > 0) {
            current = current.upstream[0]; // Take first upstream for path
            path.unshift(current.entity.entityId);
        }
        
        return path;
    }

    determineImpactType(changeType, relationship) {
        const mapping = {
            'schema_change': 'structural',
            'data_change': 'data_quality',
            'deletion': 'availability',
            'transformation_change': 'business_logic'
        };
        
        return mapping[changeType] || 'unknown';
    }

    calculateImpactSeverity(entity, relationship) {
        let severity = 1;
        
        // Increase severity based on business criticality
        if (entity.businessContext?.criticality === 'high') {
            severity += 2;
        } else if (entity.businessContext?.criticality === 'medium') {
            severity += 1;
        }
        
        // Increase severity based on relationship strength
        if (relationship?.strength >= 0.8) {
            severity += 1;
        }
        
        // Increase severity based on data flows
        if (entity.dataFlows?.length > 0) {
            severity += 1;
        }
        
        return Math.min(severity, 5); // Cap at 5
    }

    estimateRemediationEffort(entity, changeType, depth = 1) {
        const baseEffort = {
            'schema_change': 8, // hours
            'data_change': 4,
            'deletion': 2,
            'transformation_change': 6
        };
        
        let effort = baseEffort[changeType] || 4;
        
        // Adjust based on entity complexity
        const complexityFactor = (entity.transformations?.length || 0) * 0.5 + 1;
        effort *= complexityFactor;
        
        // Adjust based on depth (indirect impacts take less effort)
        if (depth > 1) {
            effort *= (0.7 ** (depth - 1));
        }
        
        return Math.round(effort);
    }

    assessBusinessCriticality(entity) {
        if (entity.businessContext?.criticality) {
            return entity.businessContext.criticality;
        }
        
        // Infer from data flows and usage
        const flowCount = entity.dataFlows?.length || 0;
        if (flowCount >= 5) return 'high';
        if (flowCount >= 2) return 'medium';
        return 'low';
    }

    generateImpactRecommendations(analysis) {
        const recommendations = [];
        
        // High priority impacts
        if (analysis.highPriorityImpacts.length > 0) {
            recommendations.push({
                type: 'immediate_action',
                priority: 'high',
                description: `Address ${analysis.highPriorityImpacts.length} high-severity impacts immediately`,
                entities: analysis.highPriorityImpacts.map(i => i.entityId)
            });
        }
        
        // Testing recommendations
        if (analysis.totalImpactedEntities > 5) {
            recommendations.push({
                type: 'testing',
                priority: 'medium',
                description: 'Implement comprehensive testing strategy due to wide impact',
                estimatedEffort: analysis.totalImpactedEntities * 2 // hours
            });
        }
        
        // Communication recommendations
        if (analysis.directImpacts.some(i => i.businessCriticality === 'high')) {
            recommendations.push({
                type: 'communication',
                priority: 'high',
                description: 'Notify stakeholders of business-critical system impacts',
                stakeholders: 'business_owners'
            });
        }
        
        return recommendations;
    }

    updateQualityMetrics(record, transformation) {
        const qualityImpact = transformation.qualityImpact;
        
        if (qualityImpact.completeness !== undefined) {
            record.qualityMetrics.completeness *= qualityImpact.completeness;
        }
        if (qualityImpact.accuracy !== undefined) {
            record.qualityMetrics.accuracy *= qualityImpact.accuracy;
        }
        if (qualityImpact.timeliness !== undefined) {
            record.qualityMetrics.timeliness *= qualityImpact.timeliness;
        }
        if (qualityImpact.consistency !== undefined) {
            record.qualityMetrics.consistency *= qualityImpact.consistency;
        }
        
        // Ensure metrics stay within valid range
        for (const metric in record.qualityMetrics) {
            record.qualityMetrics[metric] = Math.max(0, Math.min(1, record.qualityMetrics[metric]));
        }
    }

    calculateOverallQuality(qualityMetrics) {
        const weights = {
            completeness: 0.3,
            accuracy: 0.3,
            timeliness: 0.2,
            consistency: 0.2
        };
        
        let weightedSum = 0;
        let totalWeight = 0;
        
        for (const [metric, score] of Object.entries(qualityMetrics)) {
            if (weights[metric] && score !== undefined) {
                weightedSum += score * weights[metric];
                totalWeight += weights[metric];
            }
        }
        
        return totalWeight > 0 ? weightedSum / totalWeight : 0;
    }

    calculateRelationshipStrength(transformation) {
        let strength = 0.5; // Base strength
        
        // Increase strength for direct transformations
        if (transformation.transformationType === 'direct_copy') {
            strength = 0.9;
        } else if (transformation.transformationType === 'aggregation') {
            strength = 0.8;
        } else if (transformation.transformationType === 'filter') {
            strength = 0.7;
        } else if (transformation.transformationType === 'join') {
            strength = 0.6;
        }
        
        return Math.min(1.0, Math.max(0.1, strength));
    }

    incrementVersion(versions) {
        if (versions.length === 0) {
            return '1.0.0';
        }
        
        const latest = versions[versions.length - 1].version;
        const parts = latest.split('.').map(Number);
        parts[2] += 1; // Increment patch version
        
        return parts.join('.');
    }

    searchLineage(query, options = {}) {
        const results = [];
        const searchTerm = query.toLowerCase();
        
        for (const [entityId, record] of this.lineageGraph) {
            let matches = false;
            
            // Search in entity metadata
            if (record.type?.toLowerCase().includes(searchTerm) ||
                record.source?.toLowerCase().includes(searchTerm) ||
                entityId.toLowerCase().includes(searchTerm)) {
                matches = true;
            }
            
            // Search in tags
            if (record.tags.some(tag => tag.toLowerCase().includes(searchTerm))) {
                matches = true;
            }
            
            // Search in business context
            if (record.businessContext && 
                JSON.stringify(record.businessContext).toLowerCase().includes(searchTerm)) {
                matches = true;
            }
            
            if (matches) {
                results.push({
                    entityId,
                    record,
                    lineage: options.includeLineage ? this.getLineage(entityId, { maxDepth: 2 }) : null
                });
            }
        }
        
        return results;
    }

    exportLineage(entityIds, format = 'json') {
        const exportData = {
            timestamp: new Date().toISOString(),
            entities: {},
            relationships: {},
            transformations: {},
            dataFlows: {},
            metadata: {
                exportedBy: 'LineageTracker',
                version: '1.0.0',
                totalEntities: entityIds.length
            }
        };
        
        // Export entities and their lineage
        for (const entityId of entityIds) {
            const lineage = this.getLineage(entityId);
            if (lineage) {
                exportData.entities[entityId] = lineage.entity;
                
                // Include related transformations
                for (const transformation of lineage.transformations) {
                    exportData.transformations[transformation.id] = transformation;
                }
                
                // Include related data flows
                for (const flow of lineage.dataFlows) {
                    exportData.dataFlows[flow.id] = flow;
                }
            }
        }
        
        // Export relevant relationships
        for (const [relationshipId, relationship] of this.relationships) {
            if (entityIds.includes(relationship.sourceEntityId) || 
                entityIds.includes(relationship.targetEntityId)) {
                exportData.relationships[relationshipId] = relationship;
            }
        }
        
        if (format === 'json') {
            return JSON.stringify(exportData, null, 2);
        }
        
        // Add other export formats as needed
        return exportData;
    }

    cleanup() {
        const now = new Date();
        const cutoff = new Date(now.getTime() - this.retentionPeriod);
        
        let cleanedEntities = 0;
        let cleanedTransformations = 0;
        let cleanedRelationships = 0;
        
        // Clean old lineage records
        for (const [entityId, record] of this.lineageGraph) {
            if (record.createdAt < cutoff) {
                this.lineageGraph.delete(entityId);
                cleanedEntities++;
            }
        }
        
        // Clean old transformations
        for (const [transformationId, transformation] of this.transformations) {
            if (transformation.appliedAt < cutoff) {
                this.transformations.delete(transformationId);
                cleanedTransformations++;
            }
        }
        
        // Clean old relationships
        for (const [relationshipId, relationship] of this.relationships) {
            if (relationship.createdAt < cutoff) {
                this.relationships.delete(relationshipId);
                cleanedRelationships++;
            }
        }
        
        this.emit('cleanup:completed', {
            cleanedEntities,
            cleanedTransformations,
            cleanedRelationships,
            timestamp: now
        });
        
        return {
            cleanedEntities,
            cleanedTransformations,
            cleanedRelationships
        };
    }

    setupEventHandlers() {
        this.on('entity:created', (record) => {
            console.log(`Entity lineage tracked: ${record.entityId} (${record.type})`);
        });

        this.on('transformation:tracked', (info) => {
            console.log(`Transformation tracked: ${info.transformation.sourceEntityId} -> ${info.transformation.targetEntityId}`);
        });

        this.on('impact:analyzed', (analysis) => {
            console.log(`Impact analysis completed: ${analysis.totalImpactedEntities} entities affected`);
        });
    }

    getStats() {
        return {
            totalEntities: this.lineageGraph.size,
            totalRelationships: this.relationships.size,
            totalTransformations: this.transformations.size,
            totalDataFlows: this.dataFlows.size,
            lineageQueries: this.lineageQueries.length,
            impactAnalyses: this.impactAnalysis.size
        };
    }

    getLineageReport() {
        const report = {
            summary: this.getStats(),
            topSources: this.getTopDataSources(),
            qualityOverview: this.getQualityOverview(),
            complexityMetrics: this.getComplexityMetrics(),
            recentActivity: this.getRecentActivity()
        };
        
        return report;
    }

    getTopDataSources() {
        const sources = {};
        for (const [entityId, record] of this.lineageGraph) {
            const source = record.originalSource;
            sources[source] = (sources[source] || 0) + 1;
        }
        
        return Object.entries(sources)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 10)
            .map(([source, count]) => ({ source, count }));
    }

    getQualityOverview() {
        let totalQuality = 0;
        let count = 0;
        const qualityDistribution = { high: 0, medium: 0, low: 0 };
        
        for (const [entityId, record] of this.lineageGraph) {
            const quality = this.calculateOverallQuality(record.qualityMetrics);
            totalQuality += quality;
            count++;
            
            if (quality >= 0.8) qualityDistribution.high++;
            else if (quality >= 0.6) qualityDistribution.medium++;
            else qualityDistribution.low++;
        }
        
        return {
            averageQuality: count > 0 ? totalQuality / count : 0,
            distribution: qualityDistribution,
            totalEntities: count
        };
    }

    getComplexityMetrics() {
        let totalUpstream = 0;
        let totalDownstream = 0;
        let maxDepth = 0;
        let totalTransformations = 0;
        
        for (const [entityId, record] of this.lineageGraph) {
            totalUpstream += record.upstream.size;
            totalDownstream += record.downstream.size;
            totalTransformations += record.transformations.length;
            
            const upstreamDepth = this.calculateUpstreamDepth(entityId, new Set());
            const downstreamDepth = this.calculateDownstreamDepth(entityId, new Set());
            maxDepth = Math.max(maxDepth, upstreamDepth, downstreamDepth);
        }
        
        const entityCount = this.lineageGraph.size;
        
        return {
            averageUpstreamConnections: entityCount > 0 ? totalUpstream / entityCount : 0,
            averageDownstreamConnections: entityCount > 0 ? totalDownstream / entityCount : 0,
            maximumLineageDepth: maxDepth,
            averageTransformationsPerEntity: entityCount > 0 ? totalTransformations / entityCount : 0
        };
    }

    getRecentActivity() {
        const now = new Date();
        const last24Hours = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        
        const recentQueries = this.lineageQueries
            .filter(q => q.timestamp >= last24Hours)
            .length;
            
        const recentAnalyses = Array.from(this.impactAnalysis.values())
            .filter(a => a.analysisDate >= last24Hours)
            .length;
            
        return {
            recentQueries,
            recentAnalyses,
            timeframe: '24 hours'
        };
    }

    reset() {
        this.lineageGraph.clear();
        this.relationships.clear();
        this.transformations.clear();
        this.dataFlows.clear();
        this.impactAnalysis.clear();
        this.lineageQueries.length = 0;
        this.emit('reset');
    }
}

module.exports = LineageTracker;