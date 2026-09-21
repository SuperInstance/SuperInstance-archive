# Research on Affirmation Recognition Techniques

## Executive Summary

This document provides comprehensive research on existing affirmation recognition techniques, sentiment analysis models, context-aware feedback systems, and real-time response correlation methods. This research forms the foundation for the Building Bots Network's ML-powered user affirmation recognition system.

## 🔬 Research Methodology

The research was conducted through comprehensive analysis of:
- Academic literature on sentiment analysis and emotion recognition
- Current state-of-the-art NLP models and techniques
- Industry implementations of feedback classification systems
- Context-aware computing and real-time response correlation
- Machine learning approaches for user satisfaction detection

## 📊 Current State of Affirmation Recognition (2025)

### Key Findings from Research

1. **Advanced NLP Integration**: Modern NLP systems utilize sentiment analysis to determine emotional tone (positive, negative, neutral), emotion detection to identify specific emotions (happiness, satisfaction, frustration), and opinion mining to analyze user feedback and reviews.

2. **Self-Supervised Learning**: SSL is particularly useful for NLP because it requires large amounts of labeled data. Self-supervised approaches are more time-effective and cost-effective as they replace manual annotation with automated data generation.

3. **Context-Aware Memory Systems**: 2025 marks a pivotal year where context-aware feedback systems are increasingly sophisticated but still face challenges in persistent memory and real-time correlation.

4. **Transformer Models**: The latest transformer-based models show significant improvements in understanding nuanced language patterns and contextual relationships.

## 🧠 Natural Language Processing Approaches

### 1. Traditional ML Approaches

#### Naive Bayes Classification
- **Strengths**: Fast training, good baseline performance
- **Use Case**: Initial text classification with bag-of-words features
- **Implementation**: Multinomial Naive Bayes for text classification
- **Accuracy**: 70-80% for basic sentiment classification

#### Support Vector Machines (SVM)
- **Strengths**: Good performance with high-dimensional text data
- **Use Case**: Feature-rich text classification
- **Implementation**: Linear SVM with TF-IDF features
- **Accuracy**: 75-85% with proper feature engineering

#### Random Forest
- **Strengths**: Handles mixed feature types well, provides feature importance
- **Use Case**: Ensemble approach combining text and contextual features
- **Implementation**: Multiple decision trees with different feature subsets
- **Accuracy**: 80-87% with comprehensive feature engineering

### 2. Deep Learning Approaches

#### Recurrent Neural Networks (RNNs)
- **Architecture**: LSTM/GRU with attention mechanisms
- **Strengths**: Captures sequential patterns in text
- **Use Case**: Understanding temporal context in conversations
- **Performance**: 85-90% accuracy with proper preprocessing

#### Transformer Models
- **Current State**: Pre-trained models like BERT, RoBERTa, DeBERTa
- **Advantages**: Bidirectional context understanding, transfer learning capabilities
- **Use Case**: Fine-tuning for affirmation-specific classification
- **Performance**: 90-95% accuracy on specialized tasks

#### Attention Mechanisms
- **Multi-head Attention**: Focuses on different aspects of input simultaneously
- **Self-Attention**: Allows model to weigh importance of different parts
- **Cross-Attention**: Links user requests to system responses
- **Implementation**: Transformer-based architectures with custom attention heads

### 3. Hybrid Approaches

#### Rule-Based + ML Ensemble
```python
# Example hybrid approach
def classify_affirmation(text):
    # Rule-based initial screening
    rule_confidence = rule_based_classifier(text)
    
    # ML-based classification
    ml_confidence = ml_classifier.predict_proba(text)
    
    # Ensemble combination
    final_confidence = 0.3 * rule_confidence + 0.7 * ml_confidence
    
    return final_confidence
```

#### Multi-Model Ensemble
- **Voting Systems**: Hard/soft voting across multiple models
- **Stacking**: Meta-learner combines predictions from base models
- **Bagging**: Bootstrap aggregating for variance reduction
- **Boosting**: Sequential learning to correct previous mistakes

## 💭 Sentiment Analysis Models

### 1. Lexicon-Based Approaches

#### VADER Sentiment Analysis
- **Strengths**: Domain-independent, handles informal text well
- **Features**: Punctuation awareness, capitalization sensitivity, degree modifiers
- **Output**: Compound score (-1 to 1), positive/negative/neutral scores
- **Use Case**: Real-time sentiment scoring for user feedback

#### TextBlob
- **Approach**: Pattern-based sentiment analysis
- **Output**: Polarity (-1 to 1) and subjectivity (0 to 1)
- **Strengths**: Simple API, good for basic sentiment detection
- **Limitations**: Limited context understanding

### 2. Machine Learning Models

#### Fine-tuned BERT Models
```python
# Example BERT fine-tuning for affirmation detection
model = AutoModelForSequenceClassification.from_pretrained(
    'cardiffnlp/twitter-roberta-base-sentiment-latest'
)

# Fine-tune on affirmation data
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=affirmation_dataset,
    eval_dataset=validation_dataset
)
```

#### RoBERTa for Sentiment Analysis
- **Model**: twitter-roberta-base-sentiment-latest
- **Training Data**: 58M tweets with sentiment labels
- **Performance**: 90%+ accuracy on Twitter sentiment
- **Adaptation**: Fine-tunable for affirmation-specific tasks

### 3. Emotion Recognition Models

#### GoEmotions Dataset Models
- **Emotions Detected**: 28 distinct emotions including admiration, approval, gratitude
- **Architecture**: BERT-based multi-label classification
- **Use Case**: Fine-grained emotion detection in user feedback
- **Performance**: F1 scores ranging from 0.3 to 0.7 depending on emotion

#### Emotion Intensity Prediction
- **Approach**: Regression models for emotion intensity scoring
- **Features**: Word embeddings, syntactic features, lexical features
- **Output**: Continuous intensity scores for different emotions
- **Applications**: Understanding strength of user satisfaction

## 🌐 Context-Aware Feedback Systems

### 1. Context Window Management

#### Sliding Window Approach
```python
class ContextWindow:
    def __init__(self, window_size=300):  # 5 minutes
        self.window_size = window_size
        self.messages = deque()
    
    def add_message(self, message):
        # Add message with timestamp
        current_time = time.time()
        self.messages.append((current_time, message))
        
        # Remove old messages outside window
        cutoff = current_time - self.window_size
        while self.messages and self.messages[0][0] < cutoff:
            self.messages.popleft()
```

#### Hierarchical Context
- **Session Level**: Long-term conversation context
- **Task Level**: Current task or goal context
- **Turn Level**: Immediate request-response pair
- **Implementation**: Multi-level attention mechanisms

### 2. Memory-Augmented Networks

#### Neural Turing Machines (NTM)
- **Architecture**: Controller network + external memory matrix
- **Strengths**: Can learn to store and retrieve context information
- **Use Case**: Maintaining conversation history and patterns
- **Challenges**: Training complexity, computational overhead

#### Memory Networks
- **Components**: Memory storage, attention mechanism, response generation
- **Advantages**: Explicit memory for long-term context
- **Applications**: Multi-turn conversation understanding
- **Performance**: Improved context retention over standard RNNs

### 3. Graph-Based Context Models

#### Conversation Graphs
```python
# Example conversation graph structure
class ConversationGraph:
    def __init__(self):
        self.nodes = {}  # message_id -> message_content
        self.edges = {}  # relationships between messages
    
    def add_interaction(self, user_message, system_response, user_feedback):
        # Create nodes for each message
        user_node = self.add_node(user_message, 'user_request')
        response_node = self.add_node(system_response, 'system_response')
        feedback_node = self.add_node(user_feedback, 'user_feedback')
        
        # Create edges to show relationships
        self.add_edge(user_node, response_node, 'triggers')
        self.add_edge(response_node, feedback_node, 'elicits')
```

#### Knowledge Graphs for Context
- **Entities**: Users, services, tasks, responses
- **Relationships**: request-response, user-satisfaction, task-completion
- **Applications**: Pattern discovery, recommendation systems
- **Tools**: Neo4j, NetworkX for graph operations

## ⚡ Real-Time Response Correlation Methods

### 1. Stream Processing Architectures

#### Apache Kafka + Stream Processing
```python
# Example Kafka consumer for real-time feedback processing
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'user-feedback',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

for message in consumer:
    feedback = message.value
    # Real-time affirmation detection
    result = affirmation_classifier.classify(feedback)
    
    if result.confidence > threshold:
        # Trigger learning pipeline
        learning_pipeline.add_example(feedback, result)
```

#### Event-Driven Architecture
- **Events**: User request, system response, user feedback
- **Processing**: Real-time correlation and pattern matching
- **Storage**: Event sourcing for complete interaction history
- **Benefits**: Scalability, fault tolerance, replay capability

### 2. Temporal Pattern Matching

#### Time-Series Analysis
```python
# Example temporal pattern detection
def detect_response_pattern(user_id, time_window=300):
    # Get user interactions in time window
    interactions = get_user_interactions(user_id, time_window)
    
    # Analyze temporal patterns
    response_times = [i.response_time for i in interactions]
    satisfaction_scores = [i.satisfaction_score for i in interactions]
    
    # Correlation analysis
    correlation = np.corrcoef(response_times, satisfaction_scores)[0,1]
    
    return {
        'correlation': correlation,
        'avg_response_time': np.mean(response_times),
        'avg_satisfaction': np.mean(satisfaction_scores)
    }
```

#### Sequence Pattern Mining
- **Algorithms**: PrefixSpan, SPADE, GSP for pattern discovery
- **Applications**: Finding common interaction sequences
- **Use Cases**: Identifying successful conversation patterns
- **Output**: Frequent patterns with support and confidence metrics

### 3. Correlation Algorithms

#### Pearson Correlation
- **Use Case**: Linear correlation between response time and satisfaction
- **Interpretation**: Values from -1 (negative) to 1 (positive correlation)
- **Application**: Understanding factors affecting user satisfaction

#### Spearman Rank Correlation
- **Use Case**: Non-linear monotonic relationships
- **Advantages**: Robust to outliers, works with ordinal data
- **Application**: Ranking-based satisfaction analysis

#### Cross-Correlation Analysis
```python
# Example cross-correlation for response timing
def cross_correlate_feedback(service_responses, user_feedback):
    # Align time series
    aligned_responses, aligned_feedback = align_time_series(
        service_responses, user_feedback
    )
    
    # Calculate cross-correlation
    correlation = np.correlate(aligned_responses, aligned_feedback, mode='full')
    
    # Find optimal lag
    optimal_lag = np.argmax(correlation) - len(aligned_feedback) + 1
    
    return {
        'max_correlation': np.max(correlation),
        'optimal_lag': optimal_lag
    }
```

## 🎯 Intent Recognition Techniques

### 1. Intent Classification Models

#### BERT-based Intent Detection
- **Architecture**: Fine-tuned BERT with classification head
- **Training Data**: Intent-labeled conversation datasets
- **Performance**: 95%+ accuracy on well-defined intent categories
- **Use Case**: Understanding user intentions behind feedback

#### Joint Intent and Slot Filling
```python
# Example joint model for intent and entity extraction
class JointModel(nn.Module):
    def __init__(self, intent_classes, slot_classes):
        super().__init__()
        self.bert = AutoModel.from_pretrained('bert-base-uncased')
        self.intent_classifier = nn.Linear(768, len(intent_classes))
        self.slot_tagger = nn.Linear(768, len(slot_classes))
    
    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids, attention_mask)
        
        # Intent classification from [CLS] token
        intent_logits = self.intent_classifier(outputs.pooler_output)
        
        # Slot tagging from sequence output
        slot_logits = self.slot_tagger(outputs.last_hidden_state)
        
        return intent_logits, slot_logits
```

### 2. Multi-Intent Recognition

#### Hierarchical Intent Classification
- **Structure**: Tree-based intent hierarchy
- **Levels**: Domain → Intent → Sub-intent
- **Example**: Feedback → Positive → Strong Affirmation
- **Benefits**: Better handling of complex user intentions

#### Multi-Label Intent Detection
- **Approach**: Users can have multiple simultaneous intents
- **Architecture**: Sigmoid outputs instead of softmax
- **Use Case**: Complex feedback with multiple aspects
- **Evaluation**: F1 scores per intent class

## 🔄 Continuous Learning Systems

### 1. Online Learning Approaches

#### Incremental Learning
```python
# Example incremental learning for affirmation detection
class IncrementalClassifier:
    def __init__(self):
        self.model = SGDClassifier(loss='log_loss')
        self.vectorizer = HashingVectorizer()
        self.is_fitted = False
    
    def partial_fit(self, X, y):
        X_vectorized = self.vectorizer.transform(X)
        
        if not self.is_fitted:
            self.model.partial_fit(X_vectorized, y, classes=[0, 1])
            self.is_fitted = True
        else:
            self.model.partial_fit(X_vectorized, y)
```

#### Active Learning
- **Strategy**: Query most informative samples for labeling
- **Uncertainty Sampling**: Select examples with highest prediction uncertainty
- **Diversity Sampling**: Ensure diverse training examples
- **Application**: Efficient use of human feedback for model improvement

### 2. Federated Learning

#### FedAvg Algorithm
```python
# Example federated averaging
def federated_averaging(local_models, num_samples):
    # Calculate weighted average
    total_samples = sum(num_samples)
    
    # Initialize global model
    global_model = copy.deepcopy(local_models[0])
    
    # Weighted averaging of parameters
    for name, param in global_model.named_parameters():
        param.data.zero_()
        
        for i, model in enumerate(local_models):
            weight = num_samples[i] / total_samples
            param.data += weight * model.state_dict()[name]
    
    return global_model
```

#### Privacy-Preserving Learning
- **Differential Privacy**: Add noise to protect individual privacy
- **Secure Aggregation**: Compute aggregates without revealing individual data
- **Homomorphic Encryption**: Perform computations on encrypted data
- **Application**: Learning from user feedback while protecting privacy

## 📈 Performance Optimization

### 1. Model Efficiency

#### Knowledge Distillation
```python
# Example knowledge distillation for model compression
class DistillationLoss(nn.Module):
    def __init__(self, temperature=3.0, alpha=0.5):
        super().__init__()
        self.temperature = temperature
        self.alpha = alpha
        self.kl_div = nn.KLDivLoss(reduction='batchmean')
        self.ce_loss = nn.CrossEntropyLoss()
    
    def forward(self, student_logits, teacher_logits, labels):
        # Soft targets from teacher
        soft_targets = F.softmax(teacher_logits / self.temperature, dim=1)
        soft_prob = F.log_softmax(student_logits / self.temperature, dim=1)
        
        # Distillation loss
        distill_loss = self.kl_div(soft_prob, soft_targets) * (self.temperature ** 2)
        
        # Classification loss
        student_loss = self.ce_loss(student_logits, labels)
        
        return self.alpha * distill_loss + (1 - self.alpha) * student_loss
```

#### Quantization and Pruning
- **Post-Training Quantization**: Reduce model precision (FP32 → INT8)
- **Quantization-Aware Training**: Train with quantization in mind
- **Weight Pruning**: Remove less important connections
- **Structured Pruning**: Remove entire neurons/channels

### 2. Inference Optimization

#### Model Caching
```python
# Example LRU cache for model predictions
from functools import lru_cache

class CachedClassifier:
    def __init__(self, model, cache_size=1000):
        self.model = model
        self.cache_size = cache_size
    
    @lru_cache(maxsize=1000)
    def predict_cached(self, text_hash):
        # Hash-based caching for duplicate texts
        return self.model.predict(text_hash)
    
    def predict(self, text):
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return self.predict_cached(text_hash)
```

#### Batch Processing
- **Dynamic Batching**: Group requests for efficient GPU utilization
- **Async Processing**: Non-blocking prediction requests
- **Queue Management**: Handle request spikes with queuing
- **Load Balancing**: Distribute requests across multiple model instances

## 🔍 Evaluation Metrics

### 1. Classification Metrics

#### Standard Metrics
```python
# Example comprehensive evaluation
def evaluate_affirmation_classifier(y_true, y_pred, y_proba):
    metrics = {
        'accuracy': accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, average='weighted'),
        'recall': recall_score(y_true, y_pred, average='weighted'),
        'f1_score': f1_score(y_true, y_pred, average='weighted'),
        'auc_roc': roc_auc_score(y_true, y_proba[:, 1]),
        'confusion_matrix': confusion_matrix(y_true, y_pred)
    }
    
    return metrics
```

#### Domain-Specific Metrics
- **Affirmation Detection Rate**: Percentage of true affirmations detected
- **False Positive Rate**: Rate of incorrectly classified neutral/negative feedback
- **Confidence Calibration**: How well confidence scores match actual accuracy
- **Temporal Consistency**: Stability of predictions over time

### 2. Context-Aware Metrics

#### Context Relevance Score
```python
def calculate_context_relevance(predicted_affirmation, context_window):
    # Check if affirmation relates to recent system response
    recent_responses = get_recent_responses(context_window, max_age=300)
    
    if not recent_responses:
        return 0.0
    
    # Calculate semantic similarity
    similarity_scores = [
        semantic_similarity(predicted_affirmation.content, response)
        for response in recent_responses
    ]
    
    return max(similarity_scores)
```

#### Temporal Accuracy
- **Response Window**: Accuracy within expected response timeframes
- **Decay Function**: Relevance decreases with time
- **Pattern Matching**: Consistency with historical patterns
- **Drift Detection**: Identification of concept drift over time

## 🚀 Future Research Directions

### 1. Emerging Techniques

#### Large Language Models (LLMs)
- **GPT-4/Claude Integration**: Using LLMs for few-shot affirmation detection
- **Prompt Engineering**: Crafting optimal prompts for affirmation classification
- **Chain-of-Thought**: Step-by-step reasoning for complex feedback analysis
- **In-Context Learning**: Learning from examples within the prompt

#### Multimodal Learning
- **Text + Audio**: Combining textual feedback with voice characteristics
- **Visual Cues**: Incorporating user interface interactions
- **Physiological Signals**: Heart rate, eye tracking for satisfaction measurement
- **Cross-Modal Attention**: Attention mechanisms across different modalities

### 2. Advanced Applications

#### Personalized Affirmation Models
```python
# Example personalized model architecture
class PersonalizedAffirmationModel:
    def __init__(self, base_model):
        self.base_model = base_model
        self.user_adapters = {}
    
    def get_user_adapter(self, user_id):
        if user_id not in self.user_adapters:
            # Create user-specific adapter
            self.user_adapters[user_id] = UserAdapter(
                input_dim=768,
                hidden_dim=128,
                output_dim=768
            )
        return self.user_adapters[user_id]
    
    def predict(self, text, user_id):
        # Base prediction
        base_features = self.base_model.encode(text)
        
        # User adaptation
        adapter = self.get_user_adapter(user_id)
        adapted_features = adapter(base_features)
        
        # Final prediction
        return self.base_model.classify(adapted_features)
```

#### Real-Time Learning Systems
- **Stream Learning**: Continuous adaptation from live feedback
- **Concept Drift Detection**: Identifying when patterns change
- **Model Refresh Strategies**: When and how to update models
- **A/B Testing Frameworks**: Systematic comparison of model versions

## 📊 Benchmarking and Datasets

### 1. Public Datasets

#### Sentiment Analysis Datasets
- **Stanford Sentiment Treebank (SST)**: 11,855 sentences with fine-grained labels
- **IMDB Movie Reviews**: 50,000 movie reviews for binary classification
- **Twitter Sentiment**: Large-scale Twitter datasets with sentiment labels
- **Amazon Product Reviews**: Multi-domain product review sentiment

#### Emotion Recognition Datasets
- **GoEmotions**: 58K Reddit comments labeled with 28 emotion categories
- **SemEval Emotion Tasks**: Annual competitions with emotion detection datasets
- **EmoContext**: Datasets for emotion detection in conversations
- **ISEAR**: International Survey on Emotion Antecedents and Reactions

### 2. Evaluation Protocols

#### Cross-Domain Evaluation
```python
# Example cross-domain evaluation
def cross_domain_evaluation(models, datasets):
    results = {}
    
    for source_domain, source_data in datasets.items():
        for target_domain, target_data in datasets.items():
            if source_domain != target_domain:
                # Train on source domain
                model = models[source_domain]
                model.fit(source_data['X_train'], source_data['y_train'])
                
                # Test on target domain
                y_pred = model.predict(target_data['X_test'])
                accuracy = accuracy_score(target_data['y_test'], y_pred)
                
                results[f"{source_domain}→{target_domain}"] = accuracy
    
    return results
```

#### Temporal Evaluation
- **Time-Split Validation**: Train on historical data, test on recent data
- **Temporal Consistency**: Measure prediction stability over time
- **Drift Detection**: Quantify how much patterns change
- **Adaptation Speed**: How quickly models adapt to new patterns

## 🔧 Implementation Considerations

### 1. Production Deployment

#### Scalability Patterns
```python
# Example microservice architecture for scalable deployment
class AffirmationService:
    def __init__(self):
        self.model_cache = ModelCache(max_size=5)
        self.request_queue = asyncio.Queue(maxsize=1000)
        self.batch_processor = BatchProcessor(batch_size=32)
    
    async def process_request(self, request):
        # Add to queue
        await self.request_queue.put(request)
        
        # Batch processing for efficiency
        batch = await self.batch_processor.get_batch(self.request_queue)
        results = await self.model_cache.predict_batch(batch)
        
        return results[request.id]
```

#### Monitoring and Alerting
- **Performance Metrics**: Response time, throughput, error rates
- **Model Metrics**: Accuracy, confidence distribution, drift detection
- **Business Metrics**: User satisfaction, pattern adoption rates
- **Alert Thresholds**: Automated alerts for degraded performance

### 2. Data Management

#### Data Pipeline
```python
# Example data pipeline for continuous learning
class DataPipeline:
    def __init__(self):
        self.collectors = [
            FeedbackCollector(),
            InteractionLogger(),
            ContextExtractor()
        ]
        self.processors = [
            DataCleaner(),
            FeatureExtractor(),
            LabelGenerator()
        ]
        self.storage = TrainingDataStorage()
    
    async def process_interaction(self, interaction):
        # Collect data from multiple sources
        raw_data = {}
        for collector in self.collectors:
            raw_data.update(await collector.collect(interaction))
        
        # Process and clean data
        processed_data = raw_data
        for processor in self.processors:
            processed_data = await processor.process(processed_data)
        
        # Store for training
        await self.storage.store(processed_data)
```

#### Privacy and Security
- **Data Anonymization**: Remove personally identifiable information
- **Encryption**: Encrypt data at rest and in transit
- **Access Control**: Role-based access to training data
- **Audit Logging**: Track data access and model updates

## 📚 Conclusion

The research reveals a rich ecosystem of techniques for affirmation recognition and user satisfaction detection. Key insights include:

1. **Hybrid Approaches Work Best**: Combining rule-based, traditional ML, and deep learning methods provides optimal performance
2. **Context is Crucial**: Systems that maintain and utilize conversation context significantly outperform context-free approaches
3. **Real-Time Processing is Essential**: Users expect immediate feedback and system adaptation
4. **Continuous Learning is Necessary**: Static models quickly become outdated in dynamic environments
5. **Privacy-Preserving Methods are Important**: Federated learning and differential privacy enable learning while protecting user data

The Building Bots Network's affirmation recognition system incorporates these research findings into a comprehensive solution that balances accuracy, efficiency, privacy, and scalability.

## 📖 References

1. Devlin, J., et al. (2018). BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding. arXiv preprint arXiv:1810.04805.

2. Liu, Y., et al. (2019). RoBERTa: A Robustly Optimized BERT Pretraining Approach. arXiv preprint arXiv:1907.11692.

3. Hutto, C., & Gilbert, E. (2014). VADER: A Parsimonious Rule-Based Model for Sentiment Analysis of Social Media Text. AAAI Conference on Web and Social Media.

4. Demszky, D., et al. (2020). GoEmotions: A Dataset of Fine-Grained Emotions. Association for Computational Linguistics.

5. McMahan, B., et al. (2017). Communication-Efficient Learning of Deep Networks from Decentralized Data. Artificial Intelligence and Statistics.

6. Hinton, G., Vinyals, O., & Dean, J. (2015). Distilling the Knowledge in a Neural Network. arXiv preprint arXiv:1503.02531.

7. Vaswani, A., et al. (2017). Attention is All You Need. Advances in Neural Information Processing Systems.

8. Brown, T., et al. (2020). Language Models are Few-Shot Learners. Advances in Neural Information Processing Systems.

---

*This research document was compiled in August 2025 to support the development of the Building Bots Network's Affirmation Recognition System.*