#!/usr/bin/env python3
"""
Claude API Chooser Demo
Demonstrates intelligent model selection and ML training
"""

import asyncio
import json
import time
import random
from claude_api_chooser import claude_chooser, choose_claude_model, record_claude_feedback

async def demo_claude_chooser():
    """Demonstrate Claude API Chooser functionality"""
    
    print("🤖 Claude API Chooser Demo")
    print("=" * 50)
    
    # Example tasks of different types and complexities
    test_tasks = [
        {
            'text': "Fix this Python bug: def calculate(x, y): return x + y + z",
            'context': {'type': 'debugging', 'urgency': 'high'},
            'expected_model': 'opus_41'  # High complexity debugging
        },
        {
            'text': "Write a simple hello world function in Python",
            'context': {'type': 'coding', 'complexity': 'simple'},
            'expected_model': 'haiku'  # Simple task
        },
        {
            'text': """Design a distributed microservice architecture for an e-commerce platform 
                     with high availability, scalability, and security considerations. Include 
                     API gateway, service mesh, database sharding, and monitoring strategies.""",
            'context': {'type': 'architecture', 'complexity': 'very_high'},
            'expected_model': 'opus'  # Complex architecture
        },
        {
            'text': "How's the weather today?",
            'context': {'type': 'conversation'},
            'expected_model': 'haiku'  # Simple conversation
        },
        {
            'text': """Analyze the performance bottlenecks in this SQL query and optimize it:
                     SELECT u.*, p.*, c.count FROM users u 
                     JOIN profiles p ON u.id = p.user_id 
                     JOIN (SELECT user_id, COUNT(*) as count FROM posts GROUP BY user_id) c 
                     ON u.id = c.user_id 
                     WHERE u.created_at > '2024-01-01'""",
            'context': {'type': 'optimization', 'technical': True},
            'expected_model': 'sonnet'  # Technical optimization
        },
        {
            'text': "Write a creative story about a robot who discovers emotions",
            'context': {'type': 'creative'},
            'expected_model': 'opus'  # Creative task
        }
    ]
    
    print("\n1. 🎯 Testing Model Selection")
    print("-" * 30)
    
    selection_results = []
    
    for i, task in enumerate(test_tasks, 1):
        print(f"\nTask {i}: {task['text'][:60]}...")
        
        # Analyze task
        features = claude_chooser.analyze_task(task['text'], task['context'])
        print(f"  📊 Analysis:")
        print(f"    Type: {features.task_type}")
        print(f"    Complexity: {features.complexity_score:.2f}")
        print(f"    Text Length: {features.text_length}")
        print(f"    Technical Keywords: {features.technical_keywords}")
        print(f"    Code Blocks: {features.code_blocks}")
        
        # Choose model
        chosen_model = await choose_claude_model(task['text'], task['context'])
        print(f"  🤖 Chosen Model: {chosen_model.value}")
        print(f"  🎯 Expected: {task['expected_model']}")
        
        # Check if selection makes sense
        is_good_choice = (
            (features.complexity_score > 0.7 and 'opus' in chosen_model.value.lower()) or
            (features.complexity_score < 0.3 and 'haiku' in chosen_model.value.lower()) or
            ('sonnet' in chosen_model.value.lower())
        )
        
        selection_results.append({
            'task_type': features.task_type,
            'complexity': features.complexity_score,
            'chosen_model': chosen_model.value,
            'good_choice': is_good_choice
        })
        
        print(f"  ✅ Selection Quality: {'Good' if is_good_choice else 'Questionable'}")
    
    print("\n2. 🧠 Simulating ML Training")
    print("-" * 30)
    
    # Simulate user feedback and training
    print("Generating training data from simulated user interactions...")
    
    training_count = 0
    for i in range(20):  # Simulate 20 interactions
        # Pick random task
        task = random.choice(test_tasks)
        
        # Simulate model choice and response
        chosen_model = await choose_claude_model(task['text'], task['context'])
        
        # Simulate response time (faster models respond quicker)
        if 'haiku' in chosen_model.value:
            response_time = random.uniform(0.5, 1.5)
        elif 'sonnet' in chosen_model.value:
            response_time = random.uniform(1.0, 2.5)
        else:  # opus variants
            response_time = random.uniform(2.0, 4.0)
        
        # Simulate user rating based on model appropriateness
        features = claude_chooser.analyze_task(task['text'], task['context'])
        
        # Good ratings for appropriate model choices
        if (features.complexity_score > 0.7 and 'opus' in chosen_model.value.lower()) or \
           (features.complexity_score < 0.3 and 'haiku' in chosen_model.value.lower()) or \
           (0.3 <= features.complexity_score <= 0.7 and 'sonnet' in chosen_model.value.lower()):
            user_rating = random.uniform(0.7, 1.0)  # Good rating
        else:
            user_rating = random.uniform(0.3, 0.7)  # Poor to mediocre rating
        
        # Record feedback
        request_id = f"demo_req_{i}_{int(time.time())}"
        record_claude_feedback(
            request_id, user_rating, task['text'], chosen_model.value, response_time, task['context']
        )
        
        training_count += 1
        
        if training_count % 5 == 0:
            print(f"  📝 Recorded {training_count} training examples...")
    
    print(f"✅ Generated {training_count} training examples")
    
    print("\n3. 📊 Performance Statistics")
    print("-" * 30)
    
    stats = claude_chooser.get_performance_stats()
    print(f"  🗂️  Total Notes: {stats['total_notes']}")
    print(f"  🎯 Training Queue: {stats['training_queue_size']}")
    print(f"  🧠 ML Model Trained: {'Yes' if stats['is_trained'] else 'No'}")
    print(f"  🔄 Training Active: {'Yes' if stats['training_active'] else 'No'}")
    
    if stats['model_performance']:
        print(f"\n  📈 Model Performance:")
        for model, perf in stats['model_performance'].items():
            print(f"    {model}:")
            print(f"      Requests: {perf['total_requests']}")
            print(f"      Avg Rating: {perf['avg_rating']:.2f}")
            print(f"      Avg Response Time: {perf['avg_response_time']:.2f}s")
            print(f"      Success Rate: {perf['success_rate']:.2%}")
    
    if 'best_model' in stats:
        print(f"  🏆 Best Model: {stats['best_model']['model']} (Score: {stats['best_model']['score']:.2f})")
    
    print("\n4. 🗑️  Space Management")
    print("-" * 30)
    
    # Demonstrate cleanup
    deleted_count = claude_chooser.cleanup_old_notes(days_to_keep=1)  # Very aggressive cleanup for demo
    print(f"  🧹 Cleaned up {deleted_count} old notes")
    
    # Show compact note format
    if claude_chooser.compact_notes:
        sample_note = claude_chooser.compact_notes[-1]
        print(f"  📝 Sample Compact Note: {json.dumps(sample_note, indent=2)}")
        
        # Calculate space efficiency
        original_size = len(json.dumps({
            'model': 'claude-3-opus-20240229',
            'task_type': 'debugging',
            'text_length': 150,
            'complexity_score': 0.8,
            'user_rating': 0.9,
            'response_time': 2.5,
            'token_efficiency': 100.0,
            'task_completion': 1.0,
            'user_feedback': 'excellent',
            'timestamp': time.time()
        }))
        
        compact_size = len(json.dumps(sample_note))
        space_saving = (1 - compact_size / original_size) * 100
        
        print(f"  💾 Space Saving: {space_saving:.1f}% ({original_size} → {compact_size} bytes)")
    
    print("\n5. 🔮 Future Model Selection")
    print("-" * 30)
    
    # Test model selection after training
    test_text = "Optimize this complex database query with millions of records"
    context = {'type': 'optimization', 'complexity': 'high'}
    
    print(f"Test Query: {test_text}")
    final_model = await choose_claude_model(test_text, context)
    print(f"Selected Model: {final_model.value}")
    
    # Analyze the choice
    features = claude_chooser.analyze_task(test_text, context)
    print(f"Task Analysis:")
    print(f"  Complexity: {features.complexity_score:.2f}")
    print(f"  Technical Keywords: {features.technical_keywords}")
    
    # Reasoning
    if features.complexity_score > 0.6:
        expected_reasoning = "High complexity optimization task should use Opus or Opus-4.1"
    else:
        expected_reasoning = "Moderate task could use Sonnet"
    
    print(f"Expected: {expected_reasoning}")
    
    print("\n🎉 Claude API Chooser Demo Complete!")
    print("=" * 50)
    
    return {
        'selection_results': selection_results,
        'training_examples': training_count,
        'final_stats': stats,
        'cleanup_count': deleted_count
    }

# Real-world usage example
async def real_world_example():
    """Example of how to use the chooser in a real application"""
    
    print("\n🌍 Real-World Usage Example")
    print("-" * 30)
    
    # Example: User submits different types of requests
    user_requests = [
        "Help me debug this React component that's not rendering",
        "What's the best way to learn Python?",
        "Design a scalable microservices architecture for my startup"
    ]
    
    for request_text in user_requests:
        print(f"\n📝 User Request: {request_text}")
        
        # 1. Choose model
        model = await choose_claude_model(request_text, {'user_type': 'developer'})
        print(f"🤖 Selected: {model.value}")
        
        # 2. Simulate API call (would be actual call in real usage)
        print(f"📡 Making API call to {model.value}...")
        
        # Simulate response
        response_time = random.uniform(1.0, 3.0)
        mock_response = {
            'success': True,
            'response': f"Mock response from {model.value} for: {request_text[:30]}...",
            'model_used': model.value,
            'response_time': response_time,
            'token_efficiency': random.uniform(50, 200)
        }
        
        print(f"✅ Response received in {response_time:.2f}s")
        
        # 3. User provides feedback (in real app, this would be from UI)
        user_satisfaction = random.uniform(0.6, 1.0)  # Simulate user rating
        
        record_claude_feedback(
            f"real_req_{int(time.time())}", 
            user_satisfaction, 
            request_text, 
            model.value, 
            response_time
        )
        
        print(f"📊 User feedback recorded: {user_satisfaction:.2f}/1.0")
    
    print("\n✅ Real-world example complete - ML learning from user interactions!")

if __name__ == "__main__":
    # Run the demo
    results = asyncio.run(demo_claude_chooser())
    
    # Run real-world example
    asyncio.run(real_world_example())
    
    print("\n📋 Demo Summary:")
    print(f"  • Tested {len(results['selection_results'])} model selections")
    print(f"  • Generated {results['training_examples']} training examples")
    print(f"  • Cleaned up {results['cleanup_count']} old notes")
    print(f"  • ML Model Status: {'Trained' if results['final_stats']['is_trained'] else 'Training'}")
    print("\n🚀 Claude API Chooser is ready for production use!")