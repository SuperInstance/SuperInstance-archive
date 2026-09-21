"""
Mock services for testing ActiveLog
Provides mock implementations of external services
"""

from .openai_mock import (
    MockOpenAIClient,
    MockOpenAIError,
    MockRateLimitError,
    MockAPIError,
    create_mock_openai_client,
    mock_openai_successful,
    mock_openai_rate_limited,
    mock_openai_error,
    get_mock_response,
    MOCK_RESPONSES
)

from .s3_mock import (
    MockS3Client,
    MockS3Error,
    MockS3NoSuchKeyError,
    MockS3BucketNotFoundError,
    MockS3AccessDeniedError,
    create_mock_s3_client,
    mock_s3_successful,
    mock_s3_access_denied,
    mock_s3_network_error,
    create_test_file_content,
    create_test_image_content,
    create_test_document_content
)

__all__ = [
    # OpenAI mocks
    "MockOpenAIClient",
    "MockOpenAIError", 
    "MockRateLimitError",
    "MockAPIError",
    "create_mock_openai_client",
    "mock_openai_successful",
    "mock_openai_rate_limited", 
    "mock_openai_error",
    "get_mock_response",
    "MOCK_RESPONSES",
    
    # S3 mocks
    "MockS3Client",
    "MockS3Error",
    "MockS3NoSuchKeyError",
    "MockS3BucketNotFoundError", 
    "MockS3AccessDeniedError",
    "create_mock_s3_client",
    "mock_s3_successful",
    "mock_s3_access_denied",
    "mock_s3_network_error",
    "create_test_file_content",
    "create_test_image_content",
    "create_test_document_content"
]