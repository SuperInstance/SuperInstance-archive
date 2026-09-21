"""
AI Processor Lambda Function
Handles AI processing tasks for ActiveLog using OpenAI API
"""

import json
import os
import boto3
import logging
from typing import Dict, Any, List
import openai
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
secrets_client = boto3.client('secretsmanager')

# Initialize OpenAI client
openai.api_key = os.environ.get('OPENAI_API_KEY')

def process_ai_request(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process AI analysis requests
    """
    try:
        # Parse SQS messages
        records = event.get('Records', [])
        results = []
        
        for record in records:
            try:
                # Parse message body
                message_body = json.loads(record['body'])
                task_type = message_body.get('task_type')
                object_key = message_body.get('object_key')
                bucket_name = message_body.get('bucket_name')
                
                logger.info(f"Processing AI task: {task_type} for {object_key}")
                
                # Route to appropriate AI processing function
                if task_type == 'ai_analysis':
                    result = await process_ai_analysis(bucket_name, object_key)
                elif task_type == 'generate_summary':
                    result = await generate_summary(bucket_name, object_key)
                elif task_type == 'extract_tags':
                    result = await extract_tags(bucket_name, object_key)
                elif task_type == 'generate_embeddings':
                    result = await generate_embeddings(bucket_name, object_key)
                else:
                    logger.warning(f"Unknown AI task type: {task_type}")
                    continue
                
                results.append({
                    'object_key': object_key,
                    'task_type': task_type,
                    'result': result,
                    'status': 'completed'
                })
                
            except Exception as e:
                logger.error(f"Error processing AI task for record: {e}")
                results.append({
                    'object_key': object_key if 'object_key' in locals() else 'unknown',
                    'task_type': task_type if 'task_type' in locals() else 'unknown',
                    'error': str(e),
                    'status': 'failed'
                })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Processed {len(records)} AI task(s)',
                'results': results
            })
        }
        
    except Exception as e:
        logger.error(f"Error in AI processor: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to process AI tasks'
            })
        }


async def process_ai_analysis(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """
    Comprehensive AI analysis of file content
    """
    try:
        # Get file content
        file_content = await get_file_content(bucket_name, object_key)
        
        if not file_content:
            return {'error': 'Could not extract text content'}
        
        # Truncate content if too long (OpenAI token limits)
        if len(file_content) > 8000:  # Conservative limit
            file_content = file_content[:8000] + "..."
        
        # Generate analysis using OpenAI
        analysis_prompt = f"""
        Please analyze the following document and provide:
        1. A concise summary (2-3 sentences)
        2. Key topics and themes
        3. Important entities (people, organizations, dates, etc.)
        4. Relevant tags for categorization
        5. Sentiment analysis
        
        Document content:
        {file_content}
        
        Please format your response as JSON with the following structure:
        {{
            "summary": "...",
            "topics": ["topic1", "topic2", ...],
            "entities": ["entity1", "entity2", ...],
            "tags": ["tag1", "tag2", ...],
            "sentiment": "positive/negative/neutral",
            "confidence": 0.0-1.0
        }}
        """
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert document analyzer. Provide accurate, concise analysis in the requested JSON format."},
                {"role": "user", "content": analysis_prompt}
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        analysis_text = response.choices[0].message.content
        
        try:
            analysis_result = json.loads(analysis_text)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            analysis_result = {
                "summary": analysis_text[:200] + "..." if len(analysis_text) > 200 else analysis_text,
                "topics": [],
                "entities": [],
                "tags": [],
                "sentiment": "neutral",
                "confidence": 0.5
            }
        
        # Store analysis results
        await store_analysis_results(object_key, analysis_result)
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"Error in AI analysis for {object_key}: {e}")
        return {'error': str(e)}


async def generate_summary(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """
    Generate summary for document content
    """
    try:
        file_content = await get_file_content(bucket_name, object_key)
        
        if not file_content:
            return {'error': 'Could not extract text content'}
        
        # Truncate if too long
        if len(file_content) > 6000:
            file_content = file_content[:6000] + "..."
        
        summary_prompt = f"""
        Please provide a concise summary of the following document in 2-3 sentences:
        
        {file_content}
        """
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional summarizer. Create clear, concise summaries."},
                {"role": "user", "content": summary_prompt}
            ],
            max_tokens=200,
            temperature=0.3
        )
        
        summary = response.choices[0].message.content
        
        return {
            'summary': summary,
            'word_count': len(file_content.split()),
            'generated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating summary for {object_key}: {e}")
        return {'error': str(e)}


async def extract_tags(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """
    Extract relevant tags from document content
    """
    try:
        file_content = await get_file_content(bucket_name, object_key)
        
        if not file_content:
            return {'error': 'Could not extract text content'}
        
        # Truncate if too long
        if len(file_content) > 4000:
            file_content = file_content[:4000] + "..."
        
        tags_prompt = f"""
        Based on the following document content, provide 5-10 relevant tags for categorization.
        Focus on key topics, industries, concepts, and themes.
        Return only the tags as a comma-separated list.
        
        Document content:
        {file_content}
        """
        
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert tagger. Provide relevant, specific tags for document categorization."},
                {"role": "user", "content": tags_prompt}
            ],
            max_tokens=100,
            temperature=0.3
        )
        
        tags_text = response.choices[0].message.content
        tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()]
        
        return {
            'tags': tags,
            'generated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error extracting tags for {object_key}: {e}")
        return {'error': str(e)}


async def generate_embeddings(bucket_name: str, object_key: str) -> Dict[str, Any]:
    """
    Generate vector embeddings for semantic search
    """
    try:
        file_content = await get_file_content(bucket_name, object_key)
        
        if not file_content:
            return {'error': 'Could not extract text content'}
        
        # Split content into chunks for embedding
        chunks = split_text_into_chunks(file_content, max_chunk_size=1000)
        embeddings_data = []
        
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 50:  # Skip very short chunks
                continue
            
            # Generate embedding
            response = await openai.Embedding.acreate(
                model="text-embedding-ada-002",
                input=chunk
            )
            
            embedding = response.data[0].embedding
            
            embeddings_data.append({
                'chunk_index': i,
                'chunk_text': chunk,
                'embedding': embedding,
                'chunk_size': len(chunk)
            })
        
        # Store embeddings in database
        await store_embeddings(object_key, embeddings_data)
        
        return {
            'chunks_processed': len(embeddings_data),
            'total_chunks': len(chunks),
            'generated_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating embeddings for {object_key}: {e}")
        return {'error': str(e)}


async def get_file_content(bucket_name: str, object_key: str) -> str:
    """
    Retrieve and extract text content from S3 file
    """
    try:
        # Check if we already have extracted text
        metadata_key = f"metadata/{object_key}.json"
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=metadata_key)
            metadata = json.loads(response['Body'].read())
            if 'extracted_text' in metadata:
                return metadata['extracted_text']
        except:
            pass  # Metadata doesn't exist yet
        
        # Extract text from original file
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        content_type = response.get('ContentType', '')
        file_content = response['Body'].read()
        
        # Extract text based on file type
        if content_type.startswith('text/'):
            return file_content.decode('utf-8', errors='ignore')
        else:
            # For other file types, would need appropriate libraries
            # For now, return empty string
            logger.warning(f"Text extraction not implemented for {content_type}")
            return ""
    
    except Exception as e:
        logger.error(f"Error getting file content for {object_key}: {e}")
        return ""


def split_text_into_chunks(text: str, max_chunk_size: int = 1000) -> List[str]:
    """
    Split text into chunks for embedding generation
    """
    chunks = []
    words = text.split()
    current_chunk = []
    current_size = 0
    
    for word in words:
        word_size = len(word) + 1  # +1 for space
        
        if current_size + word_size > max_chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_size = word_size
        else:
            current_chunk.append(word)
            current_size += word_size
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks


async def store_analysis_results(object_key: str, analysis: Dict[str, Any]):
    """
    Store AI analysis results in database
    """
    try:
        # This would connect to PostgreSQL and store the results
        # For now, we'll log the results
        logger.info(f"Storing analysis results for {object_key}: {analysis}")
        
        # In a real implementation, you would:
        # 1. Connect to PostgreSQL using the database credentials
        # 2. Insert/update the file_metadata table with analysis results
        # 3. Handle any database errors appropriately
        
    except Exception as e:
        logger.error(f"Error storing analysis results: {e}")


async def store_embeddings(object_key: str, embeddings_data: List[Dict[str, Any]]):
    """
    Store vector embeddings in database
    """
    try:
        # This would connect to PostgreSQL and store the embeddings
        # For now, we'll log the operation
        logger.info(f"Storing {len(embeddings_data)} embeddings for {object_key}")
        
        # In a real implementation, you would:
        # 1. Connect to PostgreSQL using the database credentials
        # 2. Insert into the file_embeddings table
        # 3. Use the pgvector extension for efficient vector storage
        # 4. Handle any database errors appropriately
        
    except Exception as e:
        logger.error(f"Error storing embeddings: {e}")