"""
Comprehensive data generators for testing scenarios
"""

import uuid
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from faker import Faker
import json
import base64
import hashlib

fake = Faker()


class DataGenerators:
    """Centralized data generation utilities"""
    
    @staticmethod
    def generate_realistic_content(content_type: str = "document", length: int = 1000) -> str:
        """Generate realistic content based on type"""
        
        if content_type == "document":
            return DataGenerators._generate_document_content(length)
        elif content_type == "email":
            return DataGenerators._generate_email_content()
        elif content_type == "code":
            return DataGenerators._generate_code_content()
        elif content_type == "legal":
            return DataGenerators._generate_legal_content(length)
        elif content_type == "technical":
            return DataGenerators._generate_technical_content(length)
        elif content_type == "marketing":
            return DataGenerators._generate_marketing_content(length)
        else:
            return fake.text(max_nb_chars=length)
    
    @staticmethod
    def _generate_document_content(length: int) -> str:
        """Generate realistic document content"""
        
        # Create structured document with headers, paragraphs, etc.
        content = []
        
        # Title
        content.append(f"# {fake.catch_phrase().title()}\n\n")
        
        # Abstract/Introduction
        content.append(f"## Introduction\n\n{fake.paragraph(nb_sentences=5)}\n\n")
        
        # Main sections
        num_sections = random.randint(3, 6)
        for i in range(num_sections):
            section_title = fake.bs().title()
            content.append(f"## {section_title}\n\n")
            
            # Paragraphs in section
            num_paragraphs = random.randint(2, 4)
            for _ in range(num_paragraphs):
                content.append(f"{fake.paragraph(nb_sentences=random.randint(3, 8))}\n\n")
            
            # Sometimes add bullet points
            if random.random() > 0.6:
                content.append("Key points:\n")
                for _ in range(random.randint(3, 6)):
                    content.append(f"- {fake.sentence()}\n")
                content.append("\n")
        
        # Conclusion
        content.append(f"## Conclusion\n\n{fake.paragraph(nb_sentences=4)}\n\n")
        
        full_content = "".join(content)
        
        # Trim to desired length
        if len(full_content) > length:
            full_content = full_content[:length].rsplit(' ', 1)[0] + "..."
        
        return full_content
    
    @staticmethod
    def _generate_email_content() -> str:
        """Generate realistic email content"""
        
        subject = fake.sentence(nb_words=6).rstrip('.')
        sender = fake.email()
        recipient = fake.email()
        date = fake.date_time_between(start_date='-30d', end_date='now')
        
        # Email body
        greeting = random.choice([
            f"Dear {fake.first_name()},",
            f"Hi {fake.first_name()},",
            "Hello,",
            f"Good morning {fake.first_name()},"
        ])
        
        body_paragraphs = []
        for _ in range(random.randint(1, 4)):
            body_paragraphs.append(fake.paragraph(nb_sentences=random.randint(2, 6)))
        
        closing = random.choice([
            "Best regards,",
            "Sincerely,",
            "Thank you,",
            "Best,",
            "Kind regards,"
        ])
        
        signature = fake.name()
        
        email_content = f"""From: {sender}
To: {recipient}
Date: {date}
Subject: {subject}

{greeting}

{' '.join(body_paragraphs)}

{closing}
{signature}"""
        
        return email_content
    
    @staticmethod
    def _generate_code_content() -> str:
        """Generate realistic code content"""
        
        languages = ['python', 'javascript', 'java', 'cpp']
        language = random.choice(languages)
        
        if language == 'python':
            return DataGenerators._generate_python_code()
        elif language == 'javascript':
            return DataGenerators._generate_javascript_code()
        elif language == 'java':
            return DataGenerators._generate_java_code()
        else:
            return DataGenerators._generate_cpp_code()
    
    @staticmethod
    def _generate_python_code() -> str:
        """Generate Python code"""
        
        functions = []
        for _ in range(random.randint(2, 5)):
            func_name = fake.pystr(min_chars=5, max_chars=15).lower()
            params = ', '.join([fake.pystr(min_chars=3, max_chars=8).lower() for _ in range(random.randint(1, 4))])
            
            function_code = f'''def {func_name}({params}):
    """
    {fake.sentence()}
    """
    # {fake.sentence()}
    result = []
    for item in {params.split(',')[0].strip()}:
        if item.is_valid():
            result.append(item.process())
    return result
'''
            functions.append(function_code)
        
        main_code = '''
if __name__ == "__main__":
    # Main execution
    data = load_data()
    processed = process_data(data)
    save_results(processed)
'''
        
        return f'''#!/usr/bin/env python3
"""
{fake.catch_phrase()}
{fake.paragraph(nb_sentences=2)}
"""

import os
import sys
import json
from typing import List, Dict, Any

{chr(10).join(functions)}
{main_code}'''
    
    @staticmethod
    def _generate_javascript_code() -> str:
        """Generate JavaScript code"""
        
        return f'''/**
 * {fake.catch_phrase()}
 * {fake.sentence()}
 */

class {fake.pystr(min_chars=5, max_chars=12).title()} {{
    constructor(options = {{}}) {{
        this.options = {{
            timeout: 5000,
            retries: 3,
            ...options
        }};
        this.data = [];
    }}

    async processData(input) {{
        try {{
            const result = await this.validateInput(input);
            return this.transformData(result);
        }} catch (error) {{
            console.error('Processing failed:', error);
            throw error;
        }}
    }}

    validateInput(input) {{
        if (!input || typeof input !== 'object') {{
            throw new Error('Invalid input provided');
        }}
        return input;
    }}

    transformData(data) {{
        return data.map(item => ({{
            ...item,
            processed: true,
            timestamp: Date.now()
        }}));
    }}
}}

// Usage example
const processor = new {fake.pystr(min_chars=5, max_chars=12).title()}();
processor.processData(inputData)
    .then(result => console.log('Success:', result))
    .catch(error => console.error('Error:', error));'''
    
    @staticmethod
    def _generate_java_code() -> str:
        """Generate Java code"""
        
        class_name = fake.pystr(min_chars=5, max_chars=12).title()
        
        return f'''package com.example.{fake.pystr(min_chars=5, max_chars=10).lower()};

import java.util.*;
import java.time.LocalDateTime;
import java.io.IOException;

/**
 * {fake.catch_phrase()}
 * 
 * @author {fake.name()}
 * @version 1.0
 * @since {fake.date_between(start_date='-2y', end_date='now').year}
 */
public class {class_name} {{
    
    private final List<String> data;
    private final Map<String, Object> config;
    
    public {class_name}() {{
        this.data = new ArrayList<>();
        this.config = new HashMap<>();
        initializeConfig();
    }}
    
    private void initializeConfig() {{
        config.put("timeout", 30000);
        config.put("maxRetries", 3);
        config.put("enableLogging", true);
    }}
    
    /**
     * {fake.sentence()}
     * @param input the input data to process
     * @return processed result
     * @throws IllegalArgumentException if input is invalid
     */
    public List<String> processData(List<String> input) throws IllegalArgumentException {{
        if (input == null || input.isEmpty()) {{
            throw new IllegalArgumentException("Input cannot be null or empty");
        }}
        
        List<String> result = new ArrayList<>();
        for (String item : input) {{
            if (isValidItem(item)) {{
                result.add(transformItem(item));
            }}
        }}
        
        return result;
    }}
    
    private boolean isValidItem(String item) {{
        return item != null && !item.trim().isEmpty();
    }}
    
    private String transformItem(String item) {{
        return item.trim().toLowerCase() + "_processed_" + System.currentTimeMillis();
    }}
}}'''
    
    @staticmethod
    def _generate_cpp_code() -> str:
        """Generate C++ code"""
        
        class_name = fake.pystr(min_chars=5, max_chars=12).title()
        
        return f'''#include <iostream>
#include <vector>
#include <string>
#include <memory>
#include <algorithm>

/**
 * {fake.catch_phrase()}
 */
class {class_name} {{
private:
    std::vector<std::string> data_;
    int max_size_;
    
public:
    explicit {class_name}(int max_size = 1000) : max_size_(max_size) {{
        data_.reserve(max_size_);
    }}
    
    ~{class_name}() = default;
    
    // Copy constructor
    {class_name}(const {class_name}& other) = default;
    
    // Move constructor
    {class_name}({class_name}&& other) noexcept = default;
    
    /**
     * {fake.sentence()}
     */
    bool addItem(const std::string& item) {{
        if (data_.size() >= max_size_) {{
            return false;
        }}
        
        if (isValidItem(item)) {{
            data_.push_back(item);
            return true;
        }}
        
        return false;
    }}
    
    /**
     * {fake.sentence()}
     */
    std::vector<std::string> processItems() const {{
        std::vector<std::string> result;
        result.reserve(data_.size());
        
        std::transform(data_.begin(), data_.end(),
                      std::back_inserter(result),
                      [](const std::string& item) {{
                          return "processed_" + item;
                      }});
        
        return result;
    }}
    
private:
    bool isValidItem(const std::string& item) const {{
        return !item.empty() && item.length() <= 255;
    }}
}};

int main() {{
    {class_name} processor(500);
    
    // Add some test data
    std::vector<std::string> test_data = {{"item1", "item2", "item3"}};
    
    for (const auto& item : test_data) {{
        if (!processor.addItem(item)) {{
            std::cerr << "Failed to add item: " << item << std::endl;
        }}
    }}
    
    auto results = processor.processItems();
    
    std::cout << "Processed " << results.size() << " items." << std::endl;
    
    return 0;
}}'''
    
    @staticmethod
    def _generate_legal_content(length: int) -> str:
        """Generate legal document content"""
        
        content = f"""AGREEMENT

This Agreement is entered into as of {fake.date_between(start_date='-1y', end_date='now')} (the "Effective Date") 
by and between {fake.company()} ("Company") and {fake.name()} ("Client").

WHEREAS, Company provides {fake.bs()};

WHEREAS, Client desires to {fake.bs()};

NOW, THEREFORE, in consideration of the mutual covenants contained herein, the parties agree as follows:

1. SERVICES
   Company agrees to provide the following services: {fake.paragraph(nb_sentences=3)}

2. COMPENSATION
   Client agrees to pay Company ${random.randint(1000, 100000)} for the services described herein.
   Payment shall be due within {random.randint(15, 60)} days of invoice date.

3. TERM
   This Agreement shall commence on the Effective Date and continue for a period of 
   {random.randint(6, 36)} months unless earlier terminated.

4. TERMINATION
   Either party may terminate this Agreement with {random.randint(15, 90)} days written notice.

5. CONFIDENTIALITY
   Both parties acknowledge that they may have access to confidential information.
   {fake.paragraph(nb_sentences=2)}

6. GOVERNING LAW
   This Agreement shall be governed by the laws of {fake.state()}.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the Effective Date.

Company: _________________________

Client: ___________________________

Date: ____________________________"""
        
        if len(content) > length:
            content = content[:length].rsplit(' ', 1)[0] + "..."
        
        return content
    
    @staticmethod
    def _generate_technical_content(length: int) -> str:
        """Generate technical documentation content"""
        
        system_name = fake.catch_phrase().title()
        
        content = f"""# {system_name} Technical Documentation

## Overview
{fake.paragraph(nb_sentences=4)}

## System Architecture

### Components
The {system_name} consists of the following key components:

1. **API Gateway**: {fake.sentence()}
   - Port: {random.randint(8000, 9000)}
   - Protocol: HTTPS
   - Rate Limiting: {random.randint(100, 1000)} requests/minute

2. **Database Layer**: {fake.sentence()}
   - Type: PostgreSQL {fake.bothify('#.##')}
   - Max Connections: {random.randint(100, 500)}
   - Backup Schedule: {random.choice(['Daily', 'Hourly', 'Weekly'])}

3. **Processing Engine**: {fake.sentence()}
   - Workers: {random.randint(4, 32)}
   - Queue Size: {random.randint(1000, 10000)}
   - Timeout: {random.randint(30, 300)} seconds

## API Endpoints

### Authentication
```
POST /auth/login
Content-Type: application/json

{{
    "username": "string",
    "password": "string",
    "remember_me": boolean
}}
```

### File Operations
```
GET /files
Authorization: Bearer <token>
Query Parameters:
- limit: integer (default: 50)
- offset: integer (default: 0)
- type: string (optional)
```

## Configuration

Environment variables required:
- DATABASE_URL: Connection string for the database
- REDIS_URL: Connection string for Redis cache
- SECRET_KEY: Encryption key for JWT tokens
- DEBUG: Boolean flag for debug mode

## Deployment

### Requirements
- Node.js {fake.bothify('1#.##')} or higher
- PostgreSQL {fake.bothify('1#.#')} or higher
- Redis {fake.bothify('#.#')} or higher
- Minimum RAM: {random.randint(2, 8)}GB
- Minimum Storage: {random.randint(10, 100)}GB

### Installation Steps
1. Clone the repository
2. Install dependencies: `npm install`
3. Configure environment variables
4. Run database migrations: `npm run migrate`
5. Start the application: `npm start`

## Monitoring

### Health Check
The system provides a health check endpoint at `/health` that returns:
- System status
- Database connectivity
- Cache status
- Disk usage
- Memory usage

### Logging
Logs are structured in JSON format and include:
- Timestamp
- Log level
- Component
- Message
- Request ID (for request logs)

### Metrics
Key metrics monitored:
- Request latency (p50, p95, p99)
- Error rate
- Throughput (requests/second)
- Database query time
- Cache hit ratio

## Troubleshooting

Common issues and solutions:
1. **High Memory Usage**: {fake.paragraph(nb_sentences=2)}
2. **Slow Database Queries**: {fake.paragraph(nb_sentences=2)}
3. **Authentication Failures**: {fake.paragraph(nb_sentences=2)}"""
        
        if len(content) > length:
            content = content[:length].rsplit(' ', 1)[0] + "..."
        
        return content
    
    @staticmethod
    def _generate_marketing_content(length: int) -> str:
        """Generate marketing content"""
        
        product_name = fake.catch_phrase().title()
        
        content = f"""🚀 Introducing {product_name} - The Future is Here!

Are you tired of {fake.bs()}? Looking for a solution that can {fake.bs()}? 
Look no further! {product_name} is revolutionizing the way businesses {fake.bs()}.

✨ KEY BENEFITS:
• {fake.sentence()}
• {fake.sentence()}  
• {fake.sentence()}
• {fake.sentence()}

🎯 PERFECT FOR:
- {fake.job()} professionals
- {fake.job()} teams
- Companies looking to {fake.bs()}
- Anyone who wants to {fake.bs()}

💡 HOW IT WORKS:
{fake.paragraph(nb_sentences=4)}

📊 PROVEN RESULTS:
Our customers report:
- {random.randint(25, 95)}% increase in productivity
- ${random.randint(10, 500)}K+ saved annually
- {random.randint(50, 90)}% reduction in manual work
- {random.randint(95, 99)}% customer satisfaction rate

🌟 CUSTOMER TESTIMONIALS:

"{fake.paragraph(nb_sentences=2)}"
— {fake.name()}, {fake.job()} at {fake.company()}

"{fake.paragraph(nb_sentences=2)}"
— {fake.name()}, {fake.job()} at {fake.company()}

💰 SPECIAL LAUNCH OFFER:
Get {random.randint(20, 50)}% OFF for the first {random.randint(100, 1000)} customers!
Use code: EARLY{random.randint(2024, 2025)}

🔥 LIMITED TIME: Only {random.randint(5, 30)} days left!

Ready to transform your business? 
👉 Sign up now at {fake.domain_name()}
📞 Call us: {fake.phone_number()}
📧 Email: hello@{fake.domain_name()}

Don't let your competitors get ahead. Join thousands of satisfied customers who have already made the switch to {product_name}!

#Innovation #Business #Technology #Productivity"""
        
        if len(content) > length:
            content = content[:length].rsplit(' ', 1)[0] + "..."
        
        return content
    
    @staticmethod
    def generate_test_files_batch(
        count: int = 100,
        user_ids: List[str] = None,
        file_types: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate a batch of test files efficiently"""
        
        from .file_fixtures import FileFixtures
        
        if not user_ids:
            user_ids = [str(uuid.uuid4()) for _ in range(10)]
        
        if not file_types:
            file_types = list(FileFixtures.FILE_TYPES.keys())
        
        files = []
        for _ in range(count):
            user_id = random.choice(user_ids)
            file_type = random.choice(file_types)
            
            file_data = FileFixtures.create_file(
                user_id=user_id,
                file_type=file_type
            )
            
            # Add realistic content
            content_length = random.randint(100, 5000)
            file_data['content'] = DataGenerators.generate_realistic_content(
                file_type.replace('spreadsheet', 'document'), 
                content_length
            )
            
            files.append(file_data)
        
        return files
    
    @staticmethod
    def generate_test_scenario_data(scenario_type: str) -> Dict[str, Any]:
        """Generate data for specific test scenarios"""
        
        if scenario_type == "new_user_onboarding":
            return DataGenerators._generate_onboarding_scenario()
        elif scenario_type == "heavy_user_workflow":
            return DataGenerators._generate_heavy_user_scenario()
        elif scenario_type == "team_collaboration":
            return DataGenerators._generate_collaboration_scenario()
        elif scenario_type == "system_stress_test":
            return DataGenerators._generate_stress_test_scenario()
        elif scenario_type == "ai_processing_pipeline":
            return DataGenerators._generate_ai_pipeline_scenario()
        else:
            raise ValueError(f"Unknown scenario type: {scenario_type}")
    
    @staticmethod
    def _generate_onboarding_scenario() -> Dict[str, Any]:
        """Generate new user onboarding scenario"""
        from .user_fixtures import UserFixtures
        from .file_fixtures import FileFixtures
        
        # Create new user
        user = UserFixtures.create_user()
        
        # Initial files (small set)
        files = []
        for i in range(random.randint(3, 8)):
            file_data = FileFixtures.create_file(user_id=user['id'])
            file_data['content'] = DataGenerators.generate_realistic_content(
                file_data['file_type'], random.randint(100, 1000)
            )
            files.append(file_data)
        
        # Initial searches
        searches = [
            "getting started",
            "tutorial",
            "help",
            "documentation"
        ]
        
        return {
            'scenario': 'new_user_onboarding',
            'user': user,
            'files': files,
            'initial_searches': searches,
            'expected_actions': [
                'profile_setup',
                'first_file_upload',
                'first_search',
                'explore_features'
            ]
        }
    
    @staticmethod
    def _generate_heavy_user_scenario() -> Dict[str, Any]:
        """Generate heavy user scenario"""
        from .user_fixtures import UserFixtures
        from .file_fixtures import FileFixtures
        from .ai_fixtures import AIFixtures
        
        # Create power user
        user = UserFixtures.create_user(
            permissions=['read', 'write', 'admin', 'share']
        )
        
        # Large number of files
        files = []
        for _ in range(random.randint(200, 500)):
            file_data = FileFixtures.create_file(user_id=user['id'])
            files.append(file_data)
        
        # Heavy AI usage
        ai_analyses = []
        for file_data in random.sample(files, min(50, len(files))):
            for analysis_type in ['content_analysis', 'summarization', 'entity_extraction']:
                analysis = AIFixtures.create_ai_analysis(file_data['id'], analysis_type)
                ai_analyses.append(analysis)
        
        return {
            'scenario': 'heavy_user_workflow',
            'user': user,
            'files': files,
            'ai_analyses': ai_analyses,
            'usage_patterns': {
                'daily_uploads': random.randint(20, 100),
                'daily_searches': random.randint(50, 200),
                'ai_requests_per_day': random.randint(30, 150),
                'concurrent_sessions': random.randint(3, 10)
            }
        }
    
    @staticmethod
    def _generate_collaboration_scenario() -> Dict[str, Any]:
        """Generate team collaboration scenario"""
        from .user_fixtures import UserFixtures, UserFactory
        from .file_fixtures import FileFixtures, FileFactory
        
        # Create team
        user_factory = UserFactory()
        team_data = user_factory.create_organization_with_users(
            user_count=random.randint(5, 15),
            team_count=2
        )
        
        # Create shared projects
        file_factory = FileFactory()
        projects = []
        for _ in range(random.randint(2, 4)):
            project = file_factory.create_shared_project(
                team_data['owner']['id'],
                [u['id'] for u in random.sample(team_data['users'], 3)]
            )
            projects.append(project)
        
        return {
            'scenario': 'team_collaboration',
            'organization': team_data['organization'],
            'users': team_data['all_users'],
            'teams': team_data['teams'],
            'projects': projects,
            'collaboration_patterns': {
                'shared_folders': random.randint(10, 30),
                'concurrent_editors': random.randint(2, 8),
                'daily_interactions': random.randint(50, 200),
                'file_versions_per_project': random.randint(5, 20)
            }
        }
    
    @staticmethod
    def _generate_stress_test_scenario() -> Dict[str, Any]:
        """Generate system stress test scenario"""
        
        # High-volume data
        user_count = random.randint(1000, 5000)
        file_count = random.randint(10000, 50000)
        concurrent_operations = random.randint(100, 1000)
        
        return {
            'scenario': 'system_stress_test',
            'parameters': {
                'user_count': user_count,
                'file_count': file_count,
                'concurrent_operations': concurrent_operations,
                'test_duration_minutes': random.randint(30, 120),
                'operation_types': [
                    'file_upload',
                    'file_download', 
                    'search',
                    'semantic_search',
                    'ai_analysis',
                    'user_login',
                    'file_sharing'
                ]
            },
            'expected_metrics': {
                'max_response_time_ms': 5000,
                'max_error_rate': 0.05,
                'min_throughput_rps': 50,
                'max_memory_usage_gb': 16,
                'max_cpu_usage_percent': 80
            }
        }
    
    @staticmethod
    def _generate_ai_pipeline_scenario() -> Dict[str, Any]:
        """Generate AI processing pipeline scenario"""
        from .file_fixtures import FileFixtures
        from .ai_fixtures import AIFixtures
        
        # Files for AI processing
        files = []
        for _ in range(random.randint(20, 100)):
            file_data = FileFixtures.create_file()
            file_data['content'] = DataGenerators.generate_realistic_content(
                file_data['file_type'],
                random.randint(500, 5000)
            )
            files.append(file_data)
        
        # AI processing pipeline
        pipeline_stages = [
            'content_extraction',
            'preprocessing',
            'embedding_generation',
            'analysis',
            'indexing',
            'quality_check'
        ]
        
        return {
            'scenario': 'ai_processing_pipeline',
            'files': files,
            'pipeline_stages': pipeline_stages,
            'processing_config': {
                'batch_size': random.randint(10, 50),
                'max_concurrent_jobs': random.randint(5, 20),
                'retry_attempts': random.randint(2, 5),
                'timeout_seconds': random.randint(300, 1800),
                'quality_threshold': random.uniform(0.7, 0.95)
            },
            'expected_outputs': {
                'embeddings_generated': len(files),
                'analyses_completed': len(files) * random.randint(2, 5),
                'success_rate_min': 0.95,
                'avg_processing_time_max': 30000  # milliseconds
            }
        }
    
    @staticmethod
    def generate_performance_test_data(
        operation_type: str,
        scale: str = "medium"
    ) -> Dict[str, Any]:
        """Generate data for performance testing"""
        
        scales = {
            "small": {"multiplier": 1, "concurrent_users": 10},
            "medium": {"multiplier": 10, "concurrent_users": 50}, 
            "large": {"multiplier": 100, "concurrent_users": 200},
            "xlarge": {"multiplier": 1000, "concurrent_users": 1000}
        }
        
        scale_config = scales.get(scale, scales["medium"])
        
        if operation_type == "file_upload":
            return {
                'operation': 'file_upload',
                'scale': scale,
                'test_files': [
                    {
                        'size_mb': random.randint(1, 100),
                        'type': random.choice(['document', 'image', 'video']),
                        'count': random.randint(1, 10) * scale_config['multiplier']
                    }
                    for _ in range(random.randint(5, 20))
                ],
                'concurrent_users': scale_config['concurrent_users'],
                'duration_minutes': random.randint(5, 30),
                'expected_throughput_ops_per_second': 10 * scale_config['multiplier']
            }
        
        elif operation_type == "search":
            return {
                'operation': 'search',
                'scale': scale,
                'search_queries': [
                    fake.sentence(nb_words=random.randint(2, 8))
                    for _ in range(100 * scale_config['multiplier'])
                ],
                'concurrent_users': scale_config['concurrent_users'],
                'queries_per_user': random.randint(10, 100),
                'expected_response_time_ms': 500
            }
        
        elif operation_type == "ai_processing":
            return {
                'operation': 'ai_processing',
                'scale': scale,
                'documents_to_process': random.randint(10, 100) * scale_config['multiplier'],
                'processing_types': ['embedding', 'analysis', 'summarization'],
                'batch_size': random.randint(5, 50),
                'expected_processing_time_per_doc_ms': 5000
            }
        
        else:
            raise ValueError(f"Unknown operation type: {operation_type}")
    
    @staticmethod
    def generate_security_test_data() -> Dict[str, Any]:
        """Generate data for security testing (defensive only)"""
        
        return {
            'test_type': 'security_validation',
            'valid_inputs': [
                {'email': fake.email(), 'password': fake.password(length=12)},
                {'filename': fake.file_name(), 'content_type': 'application/pdf'},
                {'search_query': fake.sentence(), 'limit': 50}
            ],
            'boundary_test_cases': [
                {'long_email': 'a' * 254 + '@example.com'},  # Max email length
                {'large_file': {'size_mb': 100, 'name': 'large_test_file.pdf'}},
                {'complex_search': fake.text(max_nb_chars=500)}
            ],
            'validation_rules': {
                'email_format': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                'file_size_limit_mb': 100,
                'search_query_max_length': 500,
                'password_min_length': 8
            }
        }
    
    @staticmethod
    def generate_edge_case_data() -> Dict[str, Any]:
        """Generate edge case test data"""
        
        return {
            'empty_values': {
                'empty_string': '',
                'empty_list': [],
                'empty_dict': {},
                'none_value': None,
                'whitespace_string': '   ',
                'zero_value': 0
            },
            'boundary_values': {
                'max_int': 2147483647,
                'min_int': -2147483648,
                'very_long_string': 'a' * 10000,
                'unicode_string': 'Hello 🌍 Ωorld 中文 العربية',
                'special_chars': '!@#$%^&*()_+-=[]{}|;:,.<>?'
            },
            'malformed_data': {
                'invalid_email': 'not-an-email',
                'invalid_date': '2024-13-32',
                'invalid_json': '{"invalid": json}',
                'invalid_url': 'not-a-url',
                'invalid_uuid': 'not-a-uuid'
            },
            'timing_edge_cases': {
                'leap_year_date': '2024-02-29',
                'year_boundary': '2023-12-31T23:59:59Z',
                'timezone_edge': '2024-03-10T02:30:00-05:00'  # DST transition
            }
        }