const { EventEmitter } = require('events');
const crypto = require('crypto');

class EventSourcing extends EventEmitter {
    constructor(options = {}) {
        super();
        this.eventStore = new Map(); // streamId -> events array
        this.snapshots = new Map(); // streamId -> snapshot
        this.projections = new Map(); // projectionId -> projection
        this.eventHandlers = new Map(); // eventType -> handlers array
        this.aggregates = new Map(); // aggregateId -> aggregate state
        this.commandHandlers = new Map(); // commandType -> handler
        this.sagas = new Map(); // sagaId -> saga state
        
        this.snapshotThreshold = options.snapshotThreshold || 100;
        this.maxEventsPerStream = options.maxEventsPerStream || 10000;
        this.retentionPeriod = options.retentionPeriod || 86400000 * 365; // 1 year
        this.enableProjections = options.enableProjections !== false;
        this.enableSnapshots = options.enableSnapshots !== false;
        
        this.setupEventHandlers();
    }

    async appendEvents(streamId, events, expectedVersion = -1) {
        if (!Array.isArray(events)) {
            events = [events];
        }

        // Get current stream
        let stream = this.eventStore.get(streamId);
        if (!stream) {
            stream = {
                streamId,
                events: [],
                version: -1,
                createdAt: new Date(),
                lastEventAt: null
            };
            this.eventStore.set(streamId, stream);
        }

        // Check expected version for optimistic concurrency control
        if (expectedVersion !== -1 && stream.version !== expectedVersion) {
            throw new Error(`Concurrency conflict: expected version ${expectedVersion}, but stream is at version ${stream.version}`);
        }

        // Prepare events for storage
        const processedEvents = [];
        for (let i = 0; i < events.length; i++) {
            const event = {
                eventId: events[i].eventId || crypto.randomUUID(),
                eventType: events[i].eventType,
                streamId,
                eventNumber: stream.version + i + 1,
                data: events[i].data || {},
                metadata: {
                    ...events[i].metadata,
                    timestamp: new Date(),
                    causationId: events[i].causationId,
                    correlationId: events[i].correlationId,
                    userId: events[i].userId,
                    version: '1.0.0'
                }
            };

            processedEvents.push(event);
        }

        // Append events to stream
        stream.events.push(...processedEvents);
        stream.version += processedEvents.length;
        stream.lastEventAt = new Date();

        // Trim stream if it's getting too large
        if (stream.events.length > this.maxEventsPerStream) {
            await this.trimStream(streamId);
        }

        // Emit events for projections and handlers
        for (const event of processedEvents) {
            this.emit('event:appended', event);
            await this.processEvent(event);
        }

        // Create snapshot if threshold reached
        if (this.enableSnapshots && 
            stream.events.length > 0 && 
            stream.events.length % this.snapshotThreshold === 0) {
            await this.createSnapshot(streamId);
        }

        this.emit('events:appended', {
            streamId,
            eventCount: processedEvents.length,
            newVersion: stream.version,
            timestamp: new Date()
        });

        return {
            streamId,
            eventIds: processedEvents.map(e => e.eventId),
            version: stream.version,
            eventCount: processedEvents.length
        };
    }

    async getEvents(streamId, fromEventNumber = 0, maxCount = null) {
        const stream = this.eventStore.get(streamId);
        if (!stream) {
            return {
                streamId,
                events: [],
                version: -1,
                isEndOfStream: true
            };
        }

        let events = stream.events.filter(event => event.eventNumber >= fromEventNumber);
        
        if (maxCount && events.length > maxCount) {
            events = events.slice(0, maxCount);
        }

        return {
            streamId,
            events,
            version: stream.version,
            isEndOfStream: events.length < (maxCount || Infinity),
            nextEventNumber: events.length > 0 ? events[events.length - 1].eventNumber + 1 : fromEventNumber
        };
    }

    async getAllEvents(fromPosition = 0, maxCount = 1000) {
        const allEvents = [];
        let position = 0;

        for (const [streamId, stream] of this.eventStore) {
            for (const event of stream.events) {
                if (position >= fromPosition) {
                    allEvents.push({
                        ...event,
                        globalPosition: position
                    });
                }
                position++;
                
                if (allEvents.length >= maxCount) {
                    break;
                }
            }
            
            if (allEvents.length >= maxCount) {
                break;
            }
        }

        return {
            events: allEvents,
            fromPosition,
            nextPosition: position,
            hasMoreEvents: position < this.getTotalEventCount()
        };
    }

    async processEvent(event) {
        // Process event handlers
        const handlers = this.eventHandlers.get(event.eventType) || [];
        for (const handler of handlers) {
            try {
                await handler(event);
            } catch (error) {
                this.emit('handler:error', {
                    eventId: event.eventId,
                    eventType: event.eventType,
                    handlerName: handler.name,
                    error: error.message
                });
            }
        }

        // Update projections
        if (this.enableProjections) {
            await this.updateProjections(event);
        }

        // Process sagas
        await this.processSagas(event);
    }

    registerEventHandler(eventType, handler) {
        if (!this.eventHandlers.has(eventType)) {
            this.eventHandlers.set(eventType, []);
        }
        
        this.eventHandlers.get(eventType).push(handler);
        this.emit('handler:registered', { eventType, handlerName: handler.name });
    }

    unregisterEventHandler(eventType, handler) {
        const handlers = this.eventHandlers.get(eventType);
        if (handlers) {
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
                if (handlers.length === 0) {
                    this.eventHandlers.delete(eventType);
                }
            }
        }
    }

    createProjection(projectionId, config) {
        const projection = {
            id: projectionId,
            name: config.name || projectionId,
            eventTypes: config.eventTypes || [],
            initialState: config.initialState || {},
            reducer: config.reducer,
            state: config.initialState || {},
            version: 0,
            lastProcessedEvent: -1,
            enabled: config.enabled !== false,
            createdAt: new Date(),
            metadata: config.metadata || {}
        };

        this.projections.set(projectionId, projection);
        this.emit('projection:created', projection);

        // Replay events if requested
        if (config.replayEvents) {
            this.replayProjection(projectionId);
        }

        return projection;
    }

    async updateProjections(event) {
        for (const [projectionId, projection] of this.projections) {
            if (!projection.enabled) continue;

            // Check if this projection handles this event type
            if (projection.eventTypes.length === 0 || 
                projection.eventTypes.includes(event.eventType)) {
                
                try {
                    const newState = await projection.reducer(projection.state, event);
                    if (newState !== projection.state) {
                        projection.state = newState;
                        projection.version++;
                        projection.lastProcessedEvent = event.eventNumber;
                        projection.lastUpdatedAt = new Date();

                        this.emit('projection:updated', {
                            projectionId,
                            event,
                            newState
                        });
                    }
                } catch (error) {
                    this.emit('projection:error', {
                        projectionId,
                        event,
                        error: error.message
                    });
                }
            }
        }
    }

    async replayProjection(projectionId, fromEventNumber = 0) {
        const projection = this.projections.get(projectionId);
        if (!projection) {
            throw new Error(`Projection not found: ${projectionId}`);
        }

        // Reset projection state
        projection.state = { ...projection.initialState };
        projection.version = 0;
        projection.lastProcessedEvent = -1;

        const replayInfo = {
            projectionId,
            startTime: new Date(),
            eventsProcessed: 0,
            errors: []
        };

        this.emit('projection:replay-started', replayInfo);

        try {
            // Replay all relevant events
            for (const [streamId, stream] of this.eventStore) {
                for (const event of stream.events) {
                    if (event.eventNumber >= fromEventNumber &&
                        (projection.eventTypes.length === 0 || 
                         projection.eventTypes.includes(event.eventType))) {
                        
                        try {
                            const newState = await projection.reducer(projection.state, event);
                            projection.state = newState;
                            projection.version++;
                            projection.lastProcessedEvent = event.eventNumber;
                            replayInfo.eventsProcessed++;
                        } catch (error) {
                            replayInfo.errors.push({
                                eventId: event.eventId,
                                error: error.message
                            });
                        }
                    }
                }
            }

            replayInfo.endTime = new Date();
            replayInfo.duration = replayInfo.endTime - replayInfo.startTime;
            replayInfo.success = true;

            this.emit('projection:replay-completed', replayInfo);
            return replayInfo;

        } catch (error) {
            replayInfo.error = error.message;
            replayInfo.success = false;
            this.emit('projection:replay-failed', replayInfo);
            throw error;
        }
    }

    getProjectionState(projectionId) {
        const projection = this.projections.get(projectionId);
        return projection ? {
            id: projection.id,
            name: projection.name,
            state: projection.state,
            version: projection.version,
            lastProcessedEvent: projection.lastProcessedEvent,
            lastUpdatedAt: projection.lastUpdatedAt
        } : null;
    }

    async createSnapshot(streamId) {
        const stream = this.eventStore.get(streamId);
        if (!stream) {
            throw new Error(`Stream not found: ${streamId}`);
        }

        // Build aggregate state from events (simplified)
        const aggregateState = this.buildAggregateState(streamId);
        
        const snapshot = {
            snapshotId: crypto.randomUUID(),
            streamId,
            version: stream.version,
            data: aggregateState,
            timestamp: new Date(),
            eventCount: stream.events.length,
            metadata: {
                createdBy: 'EventSourcing',
                reason: 'threshold_reached'
            }
        };

        this.snapshots.set(streamId, snapshot);
        this.emit('snapshot:created', snapshot);
        
        return snapshot;
    }

    buildAggregateState(streamId) {
        // This is a simplified aggregate state builder
        // In a real implementation, this would use proper aggregate logic
        const stream = this.eventStore.get(streamId);
        if (!stream) return {};

        const state = {
            id: streamId,
            version: stream.version,
            events: stream.events.length,
            lastEventType: stream.events.length > 0 ? 
                stream.events[stream.events.length - 1].eventType : null,
            createdAt: stream.createdAt,
            lastEventAt: stream.lastEventAt
        };

        // Apply basic event-based state changes
        for (const event of stream.events) {
            switch (event.eventType) {
                case 'EntityCreated':
                    state.created = true;
                    state.data = event.data;
                    break;
                case 'EntityUpdated':
                    state.data = { ...state.data, ...event.data };
                    break;
                case 'EntityDeleted':
                    state.deleted = true;
                    break;
            }
        }

        return state;
    }

    getSnapshot(streamId) {
        return this.snapshots.get(streamId);
    }

    async loadAggregate(aggregateId, fromSnapshot = true) {
        let aggregate = this.aggregates.get(aggregateId);
        
        if (!aggregate) {
            aggregate = {
                id: aggregateId,
                version: -1,
                state: {},
                uncommittedEvents: [],
                loadedAt: new Date()
            };
            this.aggregates.set(aggregateId, aggregate);
        }

        // Load from snapshot first if available
        let fromEventNumber = 0;
        if (fromSnapshot && this.snapshots.has(aggregateId)) {
            const snapshot = this.snapshots.get(aggregateId);
            aggregate.state = { ...snapshot.data };
            aggregate.version = snapshot.version;
            fromEventNumber = snapshot.version + 1;
        }

        // Load events since snapshot
        const eventResult = await this.getEvents(aggregateId, fromEventNumber);
        for (const event of eventResult.events) {
            this.applyEventToAggregate(aggregate, event);
        }

        return aggregate;
    }

    applyEventToAggregate(aggregate, event) {
        // Apply event to aggregate state
        // This is simplified - in practice, you'd have specific aggregate logic
        switch (event.eventType) {
            case 'EntityCreated':
                aggregate.state = { ...aggregate.state, ...event.data, created: true };
                break;
            case 'EntityUpdated':
                aggregate.state = { ...aggregate.state, ...event.data };
                break;
            case 'EntityDeleted':
                aggregate.state = { ...aggregate.state, deleted: true };
                break;
        }
        
        aggregate.version = event.eventNumber;
    }

    registerCommandHandler(commandType, handler) {
        this.commandHandlers.set(commandType, handler);
        this.emit('command-handler:registered', { commandType, handlerName: handler.name });
    }

    async handleCommand(command) {
        const handler = this.commandHandlers.get(command.type);
        if (!handler) {
            throw new Error(`No handler registered for command type: ${command.type}`);
        }

        const commandInfo = {
            commandId: command.commandId || crypto.randomUUID(),
            commandType: command.type,
            aggregateId: command.aggregateId,
            timestamp: new Date(),
            userId: command.userId,
            metadata: command.metadata || {}
        };

        this.emit('command:received', commandInfo);

        try {
            // Load aggregate
            const aggregate = await this.loadAggregate(command.aggregateId);
            
            // Execute command
            const events = await handler(aggregate.state, command);
            
            if (events && events.length > 0) {
                // Add command metadata to events
                const enrichedEvents = events.map(event => ({
                    ...event,
                    causationId: commandInfo.commandId,
                    correlationId: command.correlationId || commandInfo.commandId,
                    userId: command.userId,
                    metadata: {
                        ...event.metadata,
                        commandType: command.type,
                        handledAt: new Date()
                    }
                }));

                // Append events
                const result = await this.appendEvents(
                    command.aggregateId,
                    enrichedEvents,
                    aggregate.version
                );

                commandInfo.success = true;
                commandInfo.eventIds = result.eventIds;
                commandInfo.newVersion = result.version;
                
                this.emit('command:completed', commandInfo);
                return result;
            } else {
                commandInfo.success = true;
                commandInfo.eventIds = [];
                this.emit('command:completed', commandInfo);
                return { eventIds: [], version: aggregate.version };
            }

        } catch (error) {
            commandInfo.success = false;
            commandInfo.error = error.message;
            this.emit('command:failed', commandInfo);
            throw error;
        }
    }

    createSaga(sagaId, config) {
        const saga = {
            id: sagaId,
            name: config.name || sagaId,
            correlationProperty: config.correlationProperty,
            startingEventTypes: config.startingEventTypes || [],
            eventTypes: config.eventTypes || [],
            handler: config.handler,
            state: config.initialState || {},
            version: 0,
            isCompleted: false,
            completedAt: null,
            createdAt: new Date(),
            instances: new Map(), // correlationId -> saga instance
            metadata: config.metadata || {}
        };

        this.sagas.set(sagaId, saga);
        this.emit('saga:created', saga);
        return saga;
    }

    async processSagas(event) {
        for (const [sagaId, saga] of this.sagas) {
            if (saga.isCompleted) continue;

            // Check if this saga handles this event type
            if (!saga.eventTypes.includes(event.eventType)) {
                continue;
            }

            try {
                const correlationId = this.extractCorrelationId(event, saga.correlationProperty);
                
                // Get or create saga instance
                let instance = saga.instances.get(correlationId);
                if (!instance) {
                    // Check if this is a starting event
                    if (!saga.startingEventTypes.includes(event.eventType)) {
                        continue;
                    }
                    
                    instance = {
                        correlationId,
                        sagaId,
                        state: { ...saga.state },
                        version: 0,
                        startedAt: new Date(),
                        isCompleted: false
                    };
                    saga.instances.set(correlationId, instance);
                    
                    this.emit('saga:instance-started', {
                        sagaId,
                        correlationId,
                        event
                    });
                }

                // Execute saga handler
                const result = await saga.handler(instance.state, event, {
                    correlationId,
                    sagaId,
                    appendEvents: (streamId, events) => this.appendEvents(streamId, events),
                    handleCommand: (command) => this.handleCommand(command)
                });

                if (result) {
                    instance.state = result.newState || instance.state;
                    instance.version++;
                    
                    if (result.isCompleted) {
                        instance.isCompleted = true;
                        instance.completedAt = new Date();
                        
                        this.emit('saga:instance-completed', {
                            sagaId,
                            correlationId,
                            finalState: instance.state
                        });
                    }
                }

            } catch (error) {
                this.emit('saga:error', {
                    sagaId,
                    event,
                    error: error.message
                });
            }
        }
    }

    extractCorrelationId(event, correlationProperty) {
        if (!correlationProperty) {
            return event.correlationId || event.eventId;
        }

        // Extract from event data using dot notation
        const path = correlationProperty.split('.');
        let value = event;
        for (const prop of path) {
            value = value[prop];
            if (value === undefined) break;
        }

        return value || event.correlationId || event.eventId;
    }

    async trimStream(streamId) {
        const stream = this.eventStore.get(streamId);
        if (!stream) return;

        // Keep only the most recent events
        const keepCount = Math.floor(this.maxEventsPerStream * 0.8);
        const removedCount = stream.events.length - keepCount;
        
        if (removedCount > 0) {
            stream.events = stream.events.slice(removedCount);
            
            this.emit('stream:trimmed', {
                streamId,
                removedEvents: removedCount,
                remainingEvents: stream.events.length
            });
        }
    }

    async queryEvents(criteria = {}) {
        const results = [];

        for (const [streamId, stream] of this.eventStore) {
            for (const event of stream.events) {
                let matches = true;

                // Filter by stream ID
                if (criteria.streamId && event.streamId !== criteria.streamId) {
                    matches = false;
                }

                // Filter by event type
                if (criteria.eventType && event.eventType !== criteria.eventType) {
                    matches = false;
                }

                // Filter by event types
                if (criteria.eventTypes && !criteria.eventTypes.includes(event.eventType)) {
                    matches = false;
                }

                // Filter by date range
                if (criteria.fromDate && event.metadata.timestamp < new Date(criteria.fromDate)) {
                    matches = false;
                }

                if (criteria.toDate && event.metadata.timestamp > new Date(criteria.toDate)) {
                    matches = false;
                }

                // Filter by user
                if (criteria.userId && event.metadata.userId !== criteria.userId) {
                    matches = false;
                }

                // Filter by correlation ID
                if (criteria.correlationId && event.metadata.correlationId !== criteria.correlationId) {
                    matches = false;
                }

                if (matches) {
                    results.push(event);
                }
            }
        }

        // Sort results
        results.sort((a, b) => {
            if (criteria.sortBy === 'eventNumber') {
                return a.eventNumber - b.eventNumber;
            }
            return a.metadata.timestamp - b.metadata.timestamp;
        });

        // Apply limit
        if (criteria.limit) {
            return results.slice(0, criteria.limit);
        }

        return results;
    }

    getTotalEventCount() {
        let total = 0;
        for (const [streamId, stream] of this.eventStore) {
            total += stream.events.length;
        }
        return total;
    }

    getStreamStats(streamId) {
        const stream = this.eventStore.get(streamId);
        if (!stream) {
            return null;
        }

        const eventTypes = {};
        let totalDataSize = 0;

        for (const event of stream.events) {
            eventTypes[event.eventType] = (eventTypes[event.eventType] || 0) + 1;
            totalDataSize += JSON.stringify(event).length;
        }

        return {
            streamId,
            version: stream.version,
            eventCount: stream.events.length,
            eventTypes,
            totalDataSize,
            averageEventSize: stream.events.length > 0 ? totalDataSize / stream.events.length : 0,
            createdAt: stream.createdAt,
            lastEventAt: stream.lastEventAt,
            hasSnapshot: this.snapshots.has(streamId)
        };
    }

    getAllStreams() {
        const streams = [];
        for (const [streamId, stream] of this.eventStore) {
            streams.push({
                streamId,
                version: stream.version,
                eventCount: stream.events.length,
                createdAt: stream.createdAt,
                lastEventAt: stream.lastEventAt
            });
        }
        return streams;
    }

    setupEventHandlers() {
        this.on('event:appended', (event) => {
            console.log(`Event appended: ${event.eventType} to stream ${event.streamId}`);
        });

        this.on('projection:updated', (info) => {
            console.log(`Projection updated: ${info.projectionId} for event ${info.event.eventType}`);
        });

        this.on('command:completed', (info) => {
            console.log(`Command completed: ${info.commandType} generated ${info.eventIds.length} events`);
        });

        // Cleanup old events periodically
        setInterval(() => {
            this.cleanup();
        }, 3600000); // Every hour
    }

    cleanup() {
        const cutoff = new Date(Date.now() - this.retentionPeriod);
        let cleanedStreams = 0;
        let cleanedEvents = 0;

        for (const [streamId, stream] of this.eventStore) {
            const originalCount = stream.events.length;
            stream.events = stream.events.filter(event => 
                event.metadata.timestamp > cutoff
            );
            
            const removedCount = originalCount - stream.events.length;
            if (removedCount > 0) {
                cleanedEvents += removedCount;
                
                if (stream.events.length === 0) {
                    this.eventStore.delete(streamId);
                    cleanedStreams++;
                } else {
                    // Update stream version
                    stream.version = stream.events.length > 0 ? 
                        stream.events[stream.events.length - 1].eventNumber : -1;
                }
            }
        }

        // Clean old snapshots
        let cleanedSnapshots = 0;
        for (const [streamId, snapshot] of this.snapshots) {
            if (snapshot.timestamp < cutoff) {
                this.snapshots.delete(streamId);
                cleanedSnapshots++;
            }
        }

        if (cleanedEvents > 0 || cleanedSnapshots > 0) {
            this.emit('cleanup:completed', {
                cleanedStreams,
                cleanedEvents,
                cleanedSnapshots,
                timestamp: new Date()
            });
        }

        return {
            cleanedStreams,
            cleanedEvents,
            cleanedSnapshots
        };
    }

    getStats() {
        return {
            streams: this.eventStore.size,
            totalEvents: this.getTotalEventCount(),
            snapshots: this.snapshots.size,
            projections: this.projections.size,
            eventHandlers: this.eventHandlers.size,
            commandHandlers: this.commandHandlers.size,
            sagas: this.sagas.size,
            aggregates: this.aggregates.size
        };
    }

    reset() {
        this.eventStore.clear();
        this.snapshots.clear();
        this.projections.clear();
        this.eventHandlers.clear();
        this.aggregates.clear();
        this.commandHandlers.clear();
        this.sagas.clear();
        this.emit('reset');
    }
}

module.exports = EventSourcing;