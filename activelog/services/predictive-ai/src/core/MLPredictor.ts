import * as tf from '@tensorflow/tfjs-node';
import { UserAction, Prediction } from '../types';
import { v4 as uuidv4 } from 'uuid';

export class MLPredictor {
  private model: tf.Sequential | null = null;
  private featureSize = 20;
  private sequenceLength = 10;
  private actionTypes = ['file_access', 'folder_create', 'search', 'tag_add', 'move', 'delete', 'share'];
  private vocabSize = 1000;
  private tokenizer: Map<string, number> = new Map();
  private reverseTokenizer: Map<number, string> = new Map();
  private nextTokenId = 1;

  async initialize(): Promise<void> {
    this.model = this.createModel();
    this.initializeTokenizer();
  }

  private createModel(): tf.Sequential {
    const model = tf.sequential({
      layers: [
        tf.layers.embedding({
          inputDim: this.vocabSize,
          outputDim: 128,
          inputLength: this.sequenceLength
        }),
        tf.layers.lstm({
          units: 64,
          returnSequences: true,
          dropout: 0.2
        }),
        tf.layers.lstm({
          units: 64,
          dropout: 0.2
        }),
        tf.layers.dense({
          units: 32,
          activation: 'relu'
        }),
        tf.layers.dropout({ rate: 0.3 }),
        tf.layers.dense({
          units: this.actionTypes.length,
          activation: 'softmax'
        })
      ]
    });

    model.compile({
      optimizer: tf.train.adam(0.001),
      loss: 'categoricalCrossentropy',
      metrics: ['accuracy']
    });

    return model;
  }

  private initializeTokenizer(): void {
    for (const actionType of this.actionTypes) {
      this.tokenizer.set(actionType, this.nextTokenId);
      this.reverseTokenizer.set(this.nextTokenId, actionType);
      this.nextTokenId++;
    }
    
    this.tokenizer.set('<PAD>', 0);
    this.reverseTokenizer.set(0, '<PAD>');
  }

  async trainOnAction(action: UserAction): Promise<void> {
    if (!this.model) {
      throw new Error('Model not initialized');
    }

    const features = this.extractFeatures(action);
    const actionTypeIndex = this.actionTypes.indexOf(action.actionType);
    
    if (actionTypeIndex === -1) return;

    const xs = tf.tensor3d([features], [1, this.sequenceLength, 1]);
    const ys = tf.tensor2d([[...Array(this.actionTypes.length).keys()].map(i => i === actionTypeIndex ? 1 : 0)], [1, this.actionTypes.length]);

    await this.model.fit(xs, ys, {
      epochs: 1,
      verbose: 0,
      batchSize: 1
    });

    xs.dispose();
    ys.dispose();
  }

  async predict(userId: string, context: any, recentActions: UserAction[]): Promise<Prediction[]> {
    if (!this.model) {
      throw new Error('Model not initialized');
    }

    if (recentActions.length === 0) {
      return [];
    }

    const sequenceFeatures = this.prepareSequenceFeatures(recentActions);
    const xs = tf.tensor3d([sequenceFeatures], [1, this.sequenceLength, 1]);

    const predictions = this.model.predict(xs) as tf.Tensor;
    const probabilities = await predictions.data();
    
    xs.dispose();
    predictions.dispose();

    const results: Prediction[] = [];
    const now = new Date();

    for (let i = 0; i < this.actionTypes.length; i++) {
      const confidence = probabilities[i];
      
      if (confidence > 0.3) {
        results.push({
          id: uuidv4(),
          userId,
          predictionType: 'file_access',
          confidence,
          timestamp: now,
          expiresAt: new Date(now.getTime() + 2 * 60 * 60 * 1000), // 2 hours
          payload: {
            predictedActionType: this.actionTypes[i],
            mlConfidence: confidence,
            reasoning: 'Neural network prediction based on recent activity patterns'
          },
          context
        });
      }
    }

    return results.sort((a, b) => b.confidence - a.confidence);
  }

  async predictFileAccess(userId: string, filePath: string, context: any): Promise<number> {
    if (!this.model || !filePath) return 0;

    const pathTokens = this.tokenizePath(filePath);
    const contextFeatures = this.extractContextFeatures(context);
    
    const combinedFeatures = [...pathTokens, ...contextFeatures];
    const paddedFeatures = this.padSequence(combinedFeatures, this.sequenceLength);
    
    const xs = tf.tensor3d([paddedFeatures.map(f => [f])], [1, this.sequenceLength, 1]);
    
    const prediction = this.model.predict(xs) as tf.Tensor;
    const probabilities = await prediction.data();
    
    xs.dispose();
    prediction.dispose();

    const fileAccessIndex = this.actionTypes.indexOf('file_access');
    return fileAccessIndex >= 0 ? probabilities[fileAccessIndex] : 0;
  }

  async batchPredict(actions: UserAction[]): Promise<{ action: UserAction; confidence: number }[]> {
    if (!this.model || actions.length === 0) return [];

    const batchSize = Math.min(actions.length, 32);
    const results: { action: UserAction; confidence: number }[] = [];

    for (let i = 0; i < actions.length; i += batchSize) {
      const batch = actions.slice(i, i + batchSize);
      const batchFeatures = batch.map(action => this.extractFeatures(action));
      
      const xs = tf.tensor3d(batchFeatures.map(features => features.map(f => [f])), 
        [batch.length, this.sequenceLength, 1]);

      const predictions = this.model.predict(xs) as tf.Tensor;
      const probabilities = await predictions.data();
      
      for (let j = 0; j < batch.length; j++) {
        const actionTypeIndex = this.actionTypes.indexOf(batch[j].actionType);
        const confidence = actionTypeIndex >= 0 ? 
          probabilities[j * this.actionTypes.length + actionTypeIndex] : 0;
        
        results.push({ action: batch[j], confidence });
      }

      xs.dispose();
      predictions.dispose();
    }

    return results;
  }

  private extractFeatures(action: UserAction): number[] {
    const features: number[] = [];
    
    features.push(this.actionTypes.indexOf(action.actionType) + 1);
    
    const pathHash = this.simpleHash(action.resourcePath) % 100;
    features.push(pathHash);
    
    const timestamp = new Date(action.timestamp);
    features.push(timestamp.getHours());
    features.push(timestamp.getDay());
    features.push(timestamp.getMonth());
    
    if (action.context) {
      features.push(action.context.timeOfDay || 0);
      features.push(action.context.dayOfWeek || 0);
      features.push(action.context.month || 0);
    } else {
      features.push(0, 0, 0);
    }
    
    const metadataSize = Object.keys(action.metadata || {}).length;
    features.push(metadataSize);
    
    features.push(action.resourcePath.split('/').length);
    
    while (features.length < this.sequenceLength) {
      features.push(0);
    }
    
    return features.slice(0, this.sequenceLength);
  }

  private prepareSequenceFeatures(actions: UserAction[]): number[] {
    const recentActions = actions.slice(-this.sequenceLength);
    const features: number[] = [];
    
    for (const action of recentActions) {
      const actionFeatures = this.extractFeatures(action);
      features.push(actionFeatures[0]); // Just use the action type for sequence
    }
    
    while (features.length < this.sequenceLength) {
      features.unshift(0); // Pad at the beginning
    }
    
    return features.slice(0, this.sequenceLength);
  }

  private tokenizePath(path: string): number[] {
    const parts = path.toLowerCase().split(/[\/\\\-_\s.]+/).filter(p => p.length > 0);
    const tokens: number[] = [];
    
    for (const part of parts.slice(0, 5)) { // Limit to 5 parts
      if (!this.tokenizer.has(part)) {
        if (this.nextTokenId < this.vocabSize) {
          this.tokenizer.set(part, this.nextTokenId);
          this.reverseTokenizer.set(this.nextTokenId, part);
          this.nextTokenId++;
        }
      }
      
      const tokenId = this.tokenizer.get(part) || 0;
      tokens.push(tokenId);
    }
    
    return tokens;
  }

  private extractContextFeatures(context: any): number[] {
    const features: number[] = [];
    
    if (context) {
      features.push(context.timeOfDay || 0);
      features.push(context.dayOfWeek || 0);
      features.push(context.month || 0);
      
      const deviceTypeHash = context.deviceType ? 
        this.simpleHash(context.deviceType) % 10 : 0;
      features.push(deviceTypeHash);
      
      const locationHash = context.location ? 
        this.simpleHash(context.location) % 10 : 0;
      features.push(locationHash);
    } else {
      features.push(0, 0, 0, 0, 0);
    }
    
    return features;
  }

  private padSequence(sequence: number[], length: number): number[] {
    const result = [...sequence];
    while (result.length < length) {
      result.unshift(0);
    }
    return result.slice(0, length);
  }

  private simpleHash(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash);
  }

  async saveModel(path: string): Promise<void> {
    if (!this.model) {
      throw new Error('Model not initialized');
    }
    
    await this.model.save(`file://${path}`);
  }

  async loadModel(path: string): Promise<void> {
    try {
      this.model = await tf.loadLayersModel(`file://${path}`) as tf.Sequential;
    } catch (error) {
      console.warn('Could not load existing model, creating new one');
      this.model = this.createModel();
    }
  }
}