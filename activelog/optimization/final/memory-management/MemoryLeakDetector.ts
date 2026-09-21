/**
 * Advanced Memory Leak Detection and Prevention System
 * Comprehensive memory monitoring with automated leak detection and cleanup
 */

interface MemorySnapshot {
  timestamp: number;
  usedHeapSize: number;
  totalHeapSize: number;
  heapSizeLimit: number;
  components: ComponentMemoryInfo[];
  eventListeners: EventListenerInfo[];
  intervals: IntervalInfo[];
  timeouts: TimeoutInfo[];
  observers: ObserverInfo[];
}

interface ComponentMemoryInfo {
  name: string;
  instances: number;
  memoryUsage: number;
  leakRisk: 'low' | 'medium' | 'high';
  lastCleanup: number;
}

interface EventListenerInfo {
  element: string;
  event: string;
  handler: string;
  added: number;
  removed: boolean;
}

interface IntervalInfo {
  id: number;
  callback: string;
  delay: number;
  created: number;
  cleared: boolean;
}

interface TimeoutInfo {
  id: number;
  callback: string;
  delay: number;
  created: number;
  executed: boolean;
  cleared: boolean;
}

interface ObserverInfo {
  type: 'MutationObserver' | 'IntersectionObserver' | 'ResizeObserver' | 'PerformanceObserver';
  target: string;
  callback: string;
  created: number;
  disconnected: boolean;
}

interface MemoryLeak {
  type: 'component' | 'event-listener' | 'timer' | 'observer' | 'closure' | 'dom-reference';
  component?: string;
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  memoryImpact: number;
  detectedAt: number;
  recommendations: string[];
}

interface MemoryOptimization {
  action: 'cleanup' | 'optimize' | 'refactor';
  target: string;
  description: string;
  expectedSavings: number;
  automated: boolean;
}

class MemoryLeakDetector {
  private snapshots: MemorySnapshot[] = [];
  private detectedLeaks: MemoryLeak[] = [];
  private componentRegistry: Map<string, WeakRef<any>> = new Map();
  private eventListenerRegistry: Set<EventListenerInfo> = new Set();
  private intervalRegistry: Map<number, IntervalInfo> = new Map();
  private timeoutRegistry: Map<number, TimeoutInfo> = new Map();
  private observerRegistry: Set<ObserverInfo> = new Set();
  private cleanupTasks: Set<() => void> = new Set();
  private monitoringInterval: number | null = null;
  private isMonitoring = false;

  constructor(private options: {
    snapshotInterval: number;
    maxSnapshots: number;
    leakThreshold: number;
    autoCleanup: boolean;
  } = {
    snapshotInterval: 30000, // 30 seconds
    maxSnapshots: 100,
    leakThreshold: 50 * 1024 * 1024, // 50MB
    autoCleanup: true
  }) {
    this.instrumentNativeAPIs();
    this.setupUnloadHandlers();
  }

  /**
   * Start memory monitoring
   */
  startMonitoring(): void {
    if (this.isMonitoring) return;

    console.log('🔍 Starting memory leak monitoring...');
    this.isMonitoring = true;

    // Initial snapshot
    this.takeSnapshot();

    // Periodic monitoring
    this.monitoringInterval = window.setInterval(() => {
      this.takeSnapshot();
      this.analyzeMemoryPatterns();
      
      if (this.options.autoCleanup) {
        this.performAutomaticCleanup();
      }
    }, this.options.snapshotInterval);
  }

  /**
   * Stop memory monitoring
   */
  stopMonitoring(): void {
    if (!this.isMonitoring) return;

    console.log('⏹️ Stopping memory leak monitoring...');
    this.isMonitoring = false;

    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
      this.monitoringInterval = null;
    }
  }

  /**
   * Take memory snapshot
   */
  private takeSnapshot(): void {
    if (!('memory' in performance)) {
      console.warn('Performance.memory API not available');
      return;
    }

    const memory = (performance as any).memory;
    const timestamp = Date.now();

    const snapshot: MemorySnapshot = {
      timestamp,
      usedHeapSize: memory.usedJSHeapSize,
      totalHeapSize: memory.totalJSHeapSize,
      heapSizeLimit: memory.jsHeapSizeLimit,
      components: this.getComponentMemoryInfo(),
      eventListeners: Array.from(this.eventListenerRegistry),
      intervals: Array.from(this.intervalRegistry.values()),
      timeouts: Array.from(this.timeoutRegistry.values()),
      observers: Array.from(this.observerRegistry)
    };

    this.snapshots.push(snapshot);

    // Keep only recent snapshots
    if (this.snapshots.length > this.options.maxSnapshots) {
      this.snapshots = this.snapshots.slice(-this.options.maxSnapshots);
    }
  }

  /**
   * Analyze memory patterns for leaks
   */
  private analyzeMemoryPatterns(): void {
    if (this.snapshots.length < 3) return;

    const recent = this.snapshots.slice(-10);
    const memoryTrend = this.calculateMemoryTrend(recent);
    const componentLeaks = this.detectComponentLeaks(recent);
    const listenerLeaks = this.detectEventListenerLeaks(recent);
    const timerLeaks = this.detectTimerLeaks(recent);
    const observerLeaks = this.detectObserverLeaks(recent);

    // Analyze overall memory trend
    if (memoryTrend.slope > 1000000) { // Growing by >1MB per snapshot
      this.reportLeak({
        type: 'closure',
        description: `Memory usage increasing by ${this.formatBytes(memoryTrend.slope)} per monitoring interval`,
        severity: 'high',
        memoryImpact: memoryTrend.slope * 10, // Projected impact
        detectedAt: Date.now(),
        recommendations: [
          'Check for circular references in closures',
          'Review component cleanup logic',
          'Analyze event listener management'
        ]
      });
    }

    // Report detected leaks
    [...componentLeaks, ...listenerLeaks, ...timerLeaks, ...observerLeaks]
      .forEach(leak => this.reportLeak(leak));
  }

  /**
   * Calculate memory trend
   */
  private calculateMemoryTrend(snapshots: MemorySnapshot[]): { slope: number; correlation: number } {
    if (snapshots.length < 2) return { slope: 0, correlation: 0 };

    const n = snapshots.length;
    const times = snapshots.map(s => s.timestamp);
    const memories = snapshots.map(s => s.usedHeapSize);

    // Linear regression
    const meanTime = times.reduce((a, b) => a + b) / n;
    const meanMemory = memories.reduce((a, b) => a + b) / n;

    let numerator = 0;
    let denominatorTime = 0;
    let denominatorMemory = 0;

    for (let i = 0; i < n; i++) {
      const timeDiff = times[i] - meanTime;
      const memoryDiff = memories[i] - meanMemory;
      numerator += timeDiff * memoryDiff;
      denominatorTime += timeDiff * timeDiff;
      denominatorMemory += memoryDiff * memoryDiff;
    }

    const slope = denominatorTime === 0 ? 0 : numerator / denominatorTime;
    const correlation = Math.sqrt(denominatorTime * denominatorMemory) === 0 ? 0 : 
      numerator / Math.sqrt(denominatorTime * denominatorMemory);

    return { slope, correlation };
  }

  /**
   * Detect component-related memory leaks
   */
  private detectComponentLeaks(snapshots: MemorySnapshot[]): MemoryLeak[] {
    const leaks: MemoryLeak[] = [];
    const latest = snapshots[snapshots.length - 1];

    latest.components.forEach(component => {
      if (component.leakRisk === 'high' && component.memoryUsage > 5 * 1024 * 1024) { // >5MB
        leaks.push({
          type: 'component',
          component: component.name,
          description: `Component ${component.name} shows high memory usage with ${component.instances} instances`,
          severity: 'high',
          memoryImpact: component.memoryUsage,
          detectedAt: Date.now(),
          recommendations: [
            `Review ${component.name} component cleanup in useEffect/componentWillUnmount`,
            'Check for retained references in event handlers',
            'Verify proper cleanup of subscriptions and timers'
          ]
        });
      }
    });

    return leaks;
  }

  /**
   * Detect event listener leaks
   */
  private detectEventListenerLeaks(snapshots: MemorySnapshot[]): MemoryLeak[] {
    const leaks: MemoryLeak[] = [];
    const latest = snapshots[snapshots.length - 1];
    
    const unremovedListeners = latest.eventListeners.filter(listener => !listener.removed);
    const oldListeners = unremovedListeners.filter(listener => 
      Date.now() - listener.added > 300000 // >5 minutes old
    );

    if (oldListeners.length > 50) {
      leaks.push({
        type: 'event-listener',
        description: `${oldListeners.length} event listeners not properly removed`,
        severity: 'medium',
        memoryImpact: oldListeners.length * 1024, // Estimate 1KB per listener
        detectedAt: Date.now(),
        recommendations: [
          'Add cleanup code in component unmount handlers',
          'Use AbortController for easier listener management',
          'Review event delegation patterns'
        ]
      });
    }

    return leaks;
  }

  /**
   * Detect timer-related leaks
   */
  private detectTimerLeaks(snapshots: MemorySnapshot[]): MemoryLeak[] {
    const leaks: MemoryLeak[] = [];
    const latest = snapshots[snapshots.length - 1];
    
    const activeIntervals = latest.intervals.filter(interval => !interval.cleared);
    const activeTimeouts = latest.timeouts.filter(timeout => !timeout.executed && !timeout.cleared);
    
    if (activeIntervals.length > 20) {
      leaks.push({
        type: 'timer',
        description: `${activeIntervals.length} intervals not properly cleared`,
        severity: 'medium',
        memoryImpact: activeIntervals.length * 512, // Estimate
        detectedAt: Date.now(),
        recommendations: [
          'Clear intervals in cleanup functions',
          'Use React hooks (useEffect) for proper cleanup',
          'Consider using AbortController for timer management'
        ]
      });
    }

    if (activeTimeouts.length > 100) {
      leaks.push({
        type: 'timer',
        description: `${activeTimeouts.length} timeouts accumulating`,
        severity: 'low',
        memoryImpact: activeTimeouts.length * 256, // Estimate
        detectedAt: Date.now(),
        recommendations: [
          'Review timeout usage patterns',
          'Clear unnecessary timeouts',
          'Use debouncing for frequent timeout creation'
        ]
      });
    }

    return leaks;
  }

  /**
   * Detect observer-related leaks
   */
  private detectObserverLeaks(snapshots: MemorySnapshot[]): MemoryLeak[] {
    const leaks: MemoryLeak[] = [];
    const latest = snapshots[snapshots.length - 1];
    
    const activeObservers = latest.observers.filter(observer => !observer.disconnected);
    
    if (activeObservers.length > 10) {
      leaks.push({
        type: 'observer',
        description: `${activeObservers.length} observers not properly disconnected`,
        severity: 'medium',
        memoryImpact: activeObservers.length * 2048, // Estimate 2KB per observer
        detectedAt: Date.now(),
        recommendations: [
          'Disconnect observers in cleanup functions',
          'Use WeakRef for observer targets when possible',
          'Review observer lifecycle management'
        ]
      });
    }

    return leaks;
  }

  /**
   * Report detected leak
   */
  private reportLeak(leak: MemoryLeak): void {
    // Check if leak already reported recently
    const isDuplicate = this.detectedLeaks.some(existing => 
      existing.type === leak.type && 
      existing.description === leak.description &&
      Date.now() - existing.detectedAt < 300000 // Within 5 minutes
    );

    if (isDuplicate) return;

    this.detectedLeaks.push(leak);
    
    // Keep only recent leaks
    if (this.detectedLeaks.length > 100) {
      this.detectedLeaks = this.detectedLeaks.slice(-100);
    }

    // Log leak detection
    const severityEmoji = {
      critical: '🔴',
      high: '🟠',
      medium: '🟡',
      low: '🟢'
    };

    console.warn(
      `${severityEmoji[leak.severity]} Memory leak detected (${leak.severity}):`,
      leak.description,
      `Impact: ${this.formatBytes(leak.memoryImpact)}`
    );
  }

  /**
   * Perform automatic cleanup
   */
  private performAutomaticCleanup(): void {
    let cleanedItems = 0;

    // Clean up old timeouts
    this.timeoutRegistry.forEach((timeout, id) => {
      if (timeout.executed || Date.now() - timeout.created > 300000) {
        this.timeoutRegistry.delete(id);
        cleanedItems++;
      }
    });

    // Run registered cleanup tasks
    this.cleanupTasks.forEach(cleanup => {
      try {
        cleanup();
        cleanedItems++;
      } catch (error) {
        console.warn('Cleanup task failed:', error);
      }
    });
    this.cleanupTasks.clear();

    // Force garbage collection if available
    if ('gc' in window && typeof (window as any).gc === 'function') {
      try {
        (window as any).gc();
      } catch (error) {
        // GC not available
      }
    }

    if (cleanedItems > 0) {
      console.log(`🧹 Automatic cleanup: ${cleanedItems} items cleaned`);
    }
  }

  /**
   * Instrument native APIs for tracking
   */
  private instrumentNativeAPIs(): void {
    // Instrument setInterval
    const originalSetInterval = window.setInterval;
    window.setInterval = (handler: TimerHandler, timeout?: number, ...args: any[]): number => {
      const id = originalSetInterval(handler, timeout, ...args);
      
      this.intervalRegistry.set(id, {
        id,
        callback: handler.toString().substring(0, 100),
        delay: timeout || 0,
        created: Date.now(),
        cleared: false
      });
      
      return id;
    };

    // Instrument clearInterval
    const originalClearInterval = window.clearInterval;
    window.clearInterval = (id?: number): void => {
      if (id !== undefined) {
        const intervalInfo = this.intervalRegistry.get(id);
        if (intervalInfo) {
          intervalInfo.cleared = true;
        }
        originalClearInterval(id);
      }
    };

    // Instrument setTimeout
    const originalSetTimeout = window.setTimeout;
    window.setTimeout = (handler: TimerHandler, timeout?: number, ...args: any[]): number => {
      const id = originalSetTimeout(() => {
        const timeoutInfo = this.timeoutRegistry.get(id);
        if (timeoutInfo) {
          timeoutInfo.executed = true;
        }
        
        if (typeof handler === 'function') {
          handler();
        } else {
          eval(handler);
        }
      }, timeout, ...args);
      
      this.timeoutRegistry.set(id, {
        id,
        callback: handler.toString().substring(0, 100),
        delay: timeout || 0,
        created: Date.now(),
        executed: false,
        cleared: false
      });
      
      return id;
    };

    // Instrument clearTimeout
    const originalClearTimeout = window.clearTimeout;
    window.clearTimeout = (id?: number): void => {
      if (id !== undefined) {
        const timeoutInfo = this.timeoutRegistry.get(id);
        if (timeoutInfo) {
          timeoutInfo.cleared = true;
        }
        originalClearTimeout(id);
      }
    };

    // Instrument addEventListener
    const originalAddEventListener = EventTarget.prototype.addEventListener;
    EventTarget.prototype.addEventListener = function(type: string, listener: EventListenerOrEventListenerObject | null, options?: boolean | AddEventListenerOptions) {
      this.eventListenerRegistry = this.eventListenerRegistry || new Set();
      
      const listenerInfo: EventListenerInfo = {
        element: this.tagName || this.constructor.name,
        event: type,
        handler: (listener as Function)?.toString().substring(0, 100) || 'unknown',
        added: Date.now(),
        removed: false
      };
      
      (window as any).memoryLeakDetector?.eventListenerRegistry.add(listenerInfo);
      
      return originalAddEventListener.call(this, type, listener, options);
    };

    // Store detector instance globally for instrumentation access
    (window as any).memoryLeakDetector = this;
  }

  /**
   * Setup cleanup handlers for page unload
   */
  private setupUnloadHandlers(): void {
    const cleanup = () => {
      this.performFinalCleanup();
    };

    window.addEventListener('beforeunload', cleanup);
    window.addEventListener('unload', cleanup);
    window.addEventListener('pagehide', cleanup);

    // For SPAs
    if ('navigation' in window) {
      (window as any).navigation.addEventListener('navigate', cleanup);
    }
  }

  /**
   * Perform final cleanup before page unload
   */
  private performFinalCleanup(): void {
    console.log('🧹 Performing final memory cleanup...');

    // Clear all intervals
    this.intervalRegistry.forEach((interval, id) => {
      if (!interval.cleared) {
        clearInterval(id);
      }
    });

    // Clear all timeouts
    this.timeoutRegistry.forEach((timeout, id) => {
      if (!timeout.executed && !timeout.cleared) {
        clearTimeout(id);
      }
    });

    // Disconnect all observers
    this.observerRegistry.forEach(observer => {
      if (!observer.disconnected) {
        // This would need to be implemented per observer type
        console.log(`Should disconnect ${observer.type}`);
      }
    });

    // Run cleanup tasks
    this.cleanupTasks.forEach(cleanup => {
      try {
        cleanup();
      } catch (error) {
        console.warn('Final cleanup task failed:', error);
      }
    });

    this.stopMonitoring();
  }

  /**
   * Register component for memory tracking
   */
  registerComponent(name: string, instance: any): () => void {
    this.componentRegistry.set(name, new WeakRef(instance));
    
    // Return cleanup function
    return () => {
      this.componentRegistry.delete(name);
    };
  }

  /**
   * Add cleanup task
   */
  addCleanupTask(cleanup: () => void): void {
    this.cleanupTasks.add(cleanup);
  }

  /**
   * Get component memory information
   */
  private getComponentMemoryInfo(): ComponentMemoryInfo[] {
    const components: ComponentMemoryInfo[] = [];
    const componentCounts = new Map<string, number>();

    this.componentRegistry.forEach((weakRef, name) => {
      const instance = weakRef.deref();
      if (instance) {
        componentCounts.set(name, (componentCounts.get(name) || 0) + 1);
      } else {
        // Component was garbage collected
        this.componentRegistry.delete(name);
      }
    });

    componentCounts.forEach((count, name) => {
      components.push({
        name,
        instances: count,
        memoryUsage: count * 10240, // Rough estimate: 10KB per instance
        leakRisk: count > 100 ? 'high' : count > 50 ? 'medium' : 'low',
        lastCleanup: Date.now()
      });
    });

    return components;
  }

  /**
   * Generate memory report
   */
  generateReport(): {
    summary: {
      currentMemoryUsage: number;
      memoryTrend: 'increasing' | 'stable' | 'decreasing';
      totalLeaks: number;
      criticalLeaks: number;
    };
    leaks: MemoryLeak[];
    recommendations: MemoryOptimization[];
  } {
    const latest = this.snapshots[this.snapshots.length - 1];
    const trend = this.snapshots.length >= 2 
      ? this.calculateMemoryTrend(this.snapshots.slice(-10))
      : { slope: 0 };

    const memoryTrend = trend.slope > 100000 ? 'increasing' : 
                      trend.slope < -100000 ? 'decreasing' : 'stable';

    const criticalLeaks = this.detectedLeaks.filter(leak => 
      leak.severity === 'critical' || leak.severity === 'high'
    );

    const recommendations = this.generateOptimizationRecommendations();

    return {
      summary: {
        currentMemoryUsage: latest?.usedHeapSize || 0,
        memoryTrend,
        totalLeaks: this.detectedLeaks.length,
        criticalLeaks: criticalLeaks.length
      },
      leaks: this.detectedLeaks.slice(-20), // Recent leaks
      recommendations
    };
  }

  /**
   * Generate optimization recommendations
   */
  private generateOptimizationRecommendations(): MemoryOptimization[] {
    const recommendations: MemoryOptimization[] = [];

    // Based on detected leaks
    if (this.detectedLeaks.some(leak => leak.type === 'event-listener')) {
      recommendations.push({
        action: 'cleanup',
        target: 'Event Listeners',
        description: 'Implement proper event listener cleanup in component unmount',
        expectedSavings: 50 * 1024, // 50KB estimate
        automated: true
      });
    }

    if (this.detectedLeaks.some(leak => leak.type === 'timer')) {
      recommendations.push({
        action: 'cleanup',
        target: 'Timers',
        description: 'Clear intervals and timeouts in component cleanup',
        expectedSavings: 20 * 1024, // 20KB estimate
        automated: true
      });
    }

    if (this.detectedLeaks.some(leak => leak.type === 'component')) {
      recommendations.push({
        action: 'refactor',
        target: 'Components',
        description: 'Review component lifecycle and memory management',
        expectedSavings: 500 * 1024, // 500KB estimate
        automated: false
      });
    }

    return recommendations;
  }

  /**
   * Helper methods
   */
  private formatBytes(bytes: number): string {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  }

  /**
   * Get current memory usage
   */
  getCurrentMemoryUsage(): { used: number; total: number; percentage: number } {
    if (!('memory' in performance)) {
      return { used: 0, total: 0, percentage: 0 };
    }

    const memory = (performance as any).memory;
    return {
      used: memory.usedJSHeapSize,
      total: memory.totalJSHeapSize,
      percentage: (memory.usedJSHeapSize / memory.totalJSHeapSize) * 100
    };
  }

  /**
   * Get detected leaks
   */
  getDetectedLeaks(): MemoryLeak[] {
    return [...this.detectedLeaks];
  }

  /**
   * Clear leak history
   */
  clearLeakHistory(): void {
    this.detectedLeaks = [];
  }
}

// Singleton instance
export const memoryLeakDetector = new MemoryLeakDetector();

// React hook for memory monitoring
export const useMemoryMonitoring = () => {
  const [memoryInfo, setMemoryInfo] = React.useState({
    used: 0,
    total: 0,
    percentage: 0
  });

  const [leaks, setLeaks] = React.useState<MemoryLeak[]>([]);

  React.useEffect(() => {
    memoryLeakDetector.startMonitoring();

    const interval = setInterval(() => {
      setMemoryInfo(memoryLeakDetector.getCurrentMemoryUsage());
      setLeaks(memoryLeakDetector.getDetectedLeaks());
    }, 5000);

    return () => {
      clearInterval(interval);
      memoryLeakDetector.stopMonitoring();
    };
  }, []);

  return {
    memoryInfo,
    leaks,
    addCleanupTask: (cleanup: () => void) => memoryLeakDetector.addCleanupTask(cleanup),
    registerComponent: (name: string, instance: any) => 
      memoryLeakDetector.registerComponent(name, instance)
  };
};

export default MemoryLeakDetector;