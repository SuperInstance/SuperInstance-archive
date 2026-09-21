"""Insert default tools

Revision ID: 002
Revises: 001
Create Date: 2024-10-20 19:46:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Insert default tools
    op.execute("""
        INSERT INTO tools (
            id, name, description, tool_type, category, version, status,
            is_public, is_verified, config, parameters_schema, input_schema,
            output_schema, examples, timeout_seconds, max_retries, requires_auth,
            created_at, updated_at
        ) VALUES
        (
            gen_random_uuid(),
            'Text Generation',
            'Generate text using AI language models',
            'builtin',
            'ai_ml',
            '1.0.0',
            'active',
            true,
            true,
            '{"model": "gpt-3.5-turbo", "max_tokens": 1000, "temperature": 0.7}',
            '{"type": "object", "properties": {"prompt": {"type": "string", "description": "Text prompt for generation"}, "max_tokens": {"type": "integer", "default": 1000}}, "required": ["prompt"]}',
            {"type": "string"},
            {"type": "string"},
            [{"prompt": "Write a short story about a robot", "output": "Once upon a time, in a world not so different from ours..."}],
            30,
            3,
            false,
            now(),
            now()
        ),
        (
            gen_random_uuid(),
            'Code Generation',
            'Generate code in various programming languages',
            'builtin',
            'ai_ml',
            '1.0.0',
            'active',
            true,
            true,
            '{"model": "gpt-4", "max_tokens": 2000, "temperature": 0.1}',
            '{"type": "object", "properties": {"prompt": {"type": "string", "description": "Code generation prompt"}, "language": {"type": "string", "enum": ["python", "javascript", "java", "cpp", "go"]}, "max_tokens": {"type": "integer", "default": 2000}}, "required": ["prompt", "language"]}',
            {"type": "string"},
            {"type": "string"},
            [{"prompt": "Create a function that sorts an array", "language": "python", "output": "def sort_array(arr):\n    return sorted(arr)"}],
            45,
            3,
            false,
            now(),
            now()
        ),
        (
            gen_random_uuid(),
            'Data Analysis',
            'Analyze and process structured data',
            'builtin',
            'data_processing',
            '1.0.0',
            'active',
            true,
            true,
            '{"supported_formats": ["csv", "json", "excel"], "max_file_size_mb": 100}',
            '{"type": "object", "properties": {"data": {"type": "object", "description": "Data to analyze"}, "analysis_type": {"type": "string", "enum": ["summary", "statistics", "visualization"]}}, "required": ["data", "analysis_type"]}',
            {"type": "object"},
            {"type": "object"},
            [{"data": {"column1": [1,2,3], "column2": [4,5,6]}, "analysis_type": "summary", "output": {"rows": 3, "columns": 2, "summary_stats": {...}}}],
            60,
            2,
            false,
            now(),
            now()
        ),
        (
            gen_random_uuid(),
            'Web Search',
            'Search the web for information',
            'builtin',
            'integration',
            '1.0.0',
            'active',
            true,
            true,
            '{"search_engine": "google", "max_results": 10}',
            '{"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}, "max_results": {"type": "integer", "default": 10, "maximum": 50}}, "required": ["query"]}',
            {"type": "string"},
            {"type": "array", "items": {"type": "object"}},
            [{"query": "Python programming", "max_results": 5, "output": [{"title": "Python.org", "url": "https://python.org", "snippet": "Official Python website"}]}],
            30,
            3,
            true,
            now(),
            now()
        ),
        (
            gen_random_uuid(),
            'File Operations',
            'Read, write, and manipulate files',
            'builtin',
            'file_management',
            '1.0.0',
            'active',
            true,
            true,
            '{"allowed_extensions": [".txt", ".csv", ".json", ".md"], "max_file_size_mb": 50}',
            '{"type": "object", "properties": {"operation": {"type": "string", "enum": ["read", "write", "delete", "list"]}, "path": {"type": "string", "description": "File path"}, "content": {"type": "string", "description": "Content for write operations"}}, "required": ["operation", "path"]}',
            {"type": "object"},
            {"type": "object"},
            [{"operation": "read", "path": "/tmp/example.txt", "output": {"content": "File content here", "size": 100}}],
            15,
            3,
            false,
            now(),
            now()
        ),
        (
            gen_random_uuid(),
            'Email Sender',
            'Send emails via SMTP',
            'builtin',
            'communication',
            '1.0.0',
            'active',
            true,
            true,
            '{"smtp_host": "smtp.gmail.com", "smtp_port": 587, "use_tls": true}',
            '{"type": "object", "properties": {"to": {"type": "array", "items": {"type": "string"}, "description": "Recipient emails"}, "subject": {"type": "string", "description": "Email subject"}, "body": {"type": "string", "description": "Email body"}, "attachments": {"type": "array", "items": {"type": "string"}}}, "required": ["to", "subject", "body"]}',
            {"type": "object"},
            {"type": "object", "properties": {"message_id": {"type": "string"}, "status": {"type": "string"}}},
            [{"to": ["user@example.com"], "subject": "Test Email", "body": "This is a test email", "output": {"message_id": "12345", "status": "sent"}}],
            30,
            3,
            true,
            now(),
            now()
        ),
        (
            gen_random_uuid(),
            'API Caller',
            'Make HTTP requests to external APIs',
            'builtin',
            'integration',
            '1.0.0',
            'active',
            true,
            true,
            '{"timeout_seconds": 30, "max_response_size_mb": 10}',
            '{"type": "object", "properties": {"url": {"type": "string", "format": "uri", "description": "API URL"}, "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"], "default": "GET"}, "headers": {"type": "object"}, "body": {"type": "object"}, "params": {"type": "object"}}, "required": ["url"]}',
            {"type": "object"},
            {"type": "object", "properties": {"status_code": {"type": "integer"}, "headers": {"type": "object"}, "body": {"type": "object"}}},
            [{"url": "https://api.example.com/users", "method": "GET", "output": {"status_code": 200, "body": {"users": []}}}],
            30,
            3,
            false,
            now(),
            now()
        ),
        (
            gen_random_uuid(),
            'Database Query',
            'Execute SQL queries on databases',
            'builtin',
            'database',
            '1.0.0',
            'active',
            true,
            true,
            '{"supported_databases": ["postgresql", "mysql", "sqlite"], "query_timeout_seconds": 60}',
            '{"type": "object", "properties": {"query": {"type": "string", "description": "SQL query"}, "database_type": {"type": "string", "enum": ["postgresql", "mysql", "sqlite"]}, "connection_string": {"type": "string", "description": "Database connection string"}, "parameters": {"type": "array", "items": {"type": "object"}}}, "required": ["query", "database_type", "connection_string"]}',
            {"type": "object"},
            {"type": "object", "properties": {"rows": {"type": "array"}, "affected_rows": {"type": "integer"}}},
            [{"query": "SELECT * FROM users WHERE active = true", "database_type": "postgresql", "output": {"rows": [], "affected_rows": 0}}],
            60,
            2,
            true,
            now(),
            now()
        ),
        (
            gen_random_uuid(),
            'Image Processing',
            'Process and manipulate images',
            'builtin',
            'ai_ml',
            '1.0.0',
            'active',
            true,
            true,
            '{"supported_formats": ["jpg", "png", "gif", "webp"], "max_image_size_mb": 20}',
            '{"type": "object", "properties": {"operation": {"type": "string", "enum": ["resize", "crop", "rotate", "filter", "compress"]}, "image_path": {"type": "string", "description": "Path to image file"}, "parameters": {"type": "object", "description": "Operation-specific parameters"}}, "required": ["operation", "image_path"]}',
            {"type": "object"},
            {"type": "object", "properties": {"output_path": {"type": "string"}, "dimensions": {"type": "object"}, "file_size": {"type": "integer"}}},
            [{"operation": "resize", "image_path": "/tmp/image.jpg", "parameters": {"width": 800, "height": 600}, "output": {"output_path": "/tmp/resized_image.jpg", "dimensions": {"width": 800, "height": 600}}}],
            45,
            2,
            false,
            now(),
            now()
        ),
        (
            gen_random_uuid(),
            'Document Parser',
            'Extract text and metadata from documents',
            'builtin',
            'document_processing',
            '1.0.0',
            'active',
            true,
            true,
            '{"supported_formats": ["pdf", "docx", "txt", "md"], "max_document_size_mb": 50}',
            '{"type": "object", "properties": {"document_path": {"type": "string", "description": "Path to document file"}, "extract_type": {"type": "string", "enum": ["text", "metadata", "both"], "default": "both"}}, "required": ["document_path"]}',
            {"type": "object"},
            {"type": "object", "properties": {"text": {"type": "string"}, "metadata": {"type": "object"}, "page_count": {"type": "integer"}}},
            [{"document_path": "/tmp/document.pdf", "extract_type": "both", "output": {"text": "Extracted text content", "metadata": {"author": "John Doe", "title": "Sample Document"}, "page_count": 10}}],
            60,
            2,
            false,
            now(),
            now()
        );
    """)


def downgrade() -> None:
    """Downgrade database schema."""
    # Remove default tools
    op.execute("""
        DELETE FROM tools WHERE name IN (
            'Text Generation',
            'Code Generation',
            'Data Analysis',
            'Web Search',
            'File Operations',
            'Email Sender',
            'API Caller',
            'Database Query',
            'Image Processing',
            'Document Parser'
        );
    """)