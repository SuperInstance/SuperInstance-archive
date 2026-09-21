#!/usr/bin/env python3
"""
Social Media Import Plugin for ActiveLog
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import requests
import tweepy
from textblob import TextBlob
import pandas as pd

from activelog_plugin_sdk import (
    Plugin, PluginContext, TriggerEvent, TriggerResult,
    api_endpoint, trigger_handler, validate_params
)


@dataclass
class SocialPost:
    platform: str
    post_id: str
    author: str
    content: str
    timestamp: datetime
    likes: int = 0
    shares: int = 0
    comments: int = 0
    hashtags: List[str] = None
    mentions: List[str] = None
    media_urls: List[str] = None
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class ImportResult:
    platform: str
    posts_imported: int
    posts_failed: int
    start_time: datetime
    end_time: datetime
    errors: List[str] = None


class SocialMediaImportPlugin(Plugin):
    """
    Social Media Import Plugin
    
    Imports posts from various social media platforms with sentiment analysis,
    hashtag extraction, and engagement tracking.
    """
    
    def get_manifest(self) -> Dict[str, Any]:
        with open('manifest.json', 'r') as f:
            return json.load(f)
    
    async def on_load(self, context: PluginContext) -> None:
        await super().on_load(context)
        self.log('info', 'Social Media Import plugin loaded')
        
        # Initialize platform clients
        self.clients = {}
        await self._initialize_clients()
    
    async def on_activate(self, context: PluginContext) -> None:
        await super().on_activate(context)
        self.log('info', 'Social Media Import plugin activated')
        
        # Create database tables if they don't exist
        await self._create_tables()
    
    @trigger_handler('schedule', 'Handle scheduled social media imports')
    async def on_trigger(self, event: TriggerEvent, context: PluginContext) -> TriggerResult:
        """Handle trigger events for importing social media data"""
        
        try:
            if event.type == 'schedule':
                return await self._handle_scheduled_import()
            elif event.type == 'user-action':
                return await self._handle_manual_import(event.data)
            elif event.type == 'webhook':
                return await self._handle_webhook_import(event.data)
            else:
                return TriggerResult(success=False, error='Unsupported trigger type')
                
        except Exception as e:
            self.log('error', f'Import failed: {str(e)}', e)
            return TriggerResult(success=False, error=str(e))
    
    @api_endpoint('/import/:platform', 'POST', 'Trigger import for specific platform')
    @validate_params(platform={'type': 'string', 'required': True})
    async def import_platform(self, platform: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Import data from a specific social media platform"""
        
        try:
            if platform not in ['twitter', 'facebook', 'instagram', 'linkedin']:
                return {'success': False, 'error': 'Unsupported platform'}
            
            # Check if platform is enabled
            config = self.get_config()
            platform_config = config.get('platforms', {}).get(platform, {})
            
            if not platform_config.get('enabled', False):
                return {'success': False, 'error': f'{platform} is not enabled'}
            
            result = await self._import_from_platform(platform, options or {})
            
            return {
                'success': True,
                'platform': platform,
                'posts_imported': result.posts_imported,
                'posts_failed': result.posts_failed,
                'duration_seconds': (result.end_time - result.start_time).total_seconds(),
                'errors': result.errors
            }
            
        except Exception as e:
            self.log('error', f'Platform import failed for {platform}', e)
            return {'success': False, 'error': str(e)}
    
    @api_endpoint('/posts', 'GET', 'Get imported social media posts')
    async def get_posts(
        self, 
        platform: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve imported social media posts with filtering"""
        
        try:
            # Build query
            where_conditions = []
            params = []
            
            if platform:
                where_conditions.append('platform = ?')
                params.append(platform)
            
            if start_date:
                where_conditions.append('timestamp >= ?')
                params.append(start_date)
            
            if end_date:
                where_conditions.append('timestamp <= ?')
                params.append(end_date)
            
            where_clause = ' WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
            
            # Get total count
            count_sql = f'SELECT COUNT(*) FROM social_posts{where_clause}'
            count_result = await self.db_query(count_sql, params)
            total_count = count_result.rows[0]['COUNT(*)'] if count_result.rows else 0
            
            # Get posts
            posts_sql = f'''
                SELECT * FROM social_posts{where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            '''
            params.extend([limit, offset])
            
            result = await self.db_query(posts_sql, params)
            
            posts = []
            for row in result.rows:
                post = dict(row)
                # Parse JSON fields
                if post.get('hashtags'):
                    post['hashtags'] = json.loads(post['hashtags'])
                if post.get('mentions'):
                    post['mentions'] = json.loads(post['mentions'])
                if post.get('media_urls'):
                    post['media_urls'] = json.loads(post['media_urls'])
                posts.append(post)
            
            return {
                'success': True,
                'total_count': total_count,
                'posts': posts,
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + len(posts) < total_count
                }
            }
            
        except Exception as e:
            self.log('error', 'Failed to get posts', e)
            return {'success': False, 'error': str(e)}
    
    @api_endpoint('/analytics/:platform', 'GET', 'Get analytics data for platform')
    async def get_platform_analytics(self, platform: str, days: int = 30) -> Dict[str, Any]:
        """Get analytics data for a specific platform"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get basic stats
            stats_sql = '''
                SELECT 
                    COUNT(*) as total_posts,
                    AVG(likes) as avg_likes,
                    AVG(shares) as avg_shares,
                    AVG(comments) as avg_comments,
                    AVG(sentiment_score) as avg_sentiment
                FROM social_posts 
                WHERE platform = ? AND timestamp >= ?
            '''
            
            stats_result = await self.db_query(stats_sql, [platform, start_date.isoformat()])
            stats = dict(stats_result.rows[0]) if stats_result.rows else {}
            
            # Get top hashtags
            hashtags_sql = '''
                SELECT hashtags FROM social_posts 
                WHERE platform = ? AND timestamp >= ? AND hashtags IS NOT NULL
            '''
            
            hashtags_result = await self.db_query(hashtags_sql, [platform, start_date.isoformat()])
            
            hashtag_counts = {}
            for row in hashtags_result.rows:
                if row['hashtags']:
                    hashtags = json.loads(row['hashtags'])
                    for tag in hashtags:
                        hashtag_counts[tag] = hashtag_counts.get(tag, 0) + 1
            
            top_hashtags = sorted(hashtag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Get engagement over time
            engagement_sql = '''
                SELECT 
                    DATE(timestamp) as date,
                    SUM(likes + shares + comments) as total_engagement,
                    COUNT(*) as post_count
                FROM social_posts 
                WHERE platform = ? AND timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date
            '''
            
            engagement_result = await self.db_query(engagement_sql, [platform, start_date.isoformat()])
            engagement_timeline = [dict(row) for row in engagement_result.rows]
            
            return {
                'success': True,
                'platform': platform,
                'period_days': days,
                'stats': stats,
                'top_hashtags': top_hashtags,
                'engagement_timeline': engagement_timeline
            }
            
        except Exception as e:
            self.log('error', f'Failed to get analytics for {platform}', e)
            return {'success': False, 'error': str(e)}
    
    @api_endpoint('/sentiment/:post_id', 'GET', 'Get sentiment analysis for a post')
    async def get_post_sentiment(self, post_id: str) -> Dict[str, Any]:
        """Get detailed sentiment analysis for a specific post"""
        
        try:
            sql = '''
                SELECT content, sentiment_score, sentiment_label 
                FROM social_posts 
                WHERE post_id = ?
            '''
            
            result = await self.db_query(sql, [post_id])
            
            if not result.rows:
                return {'success': False, 'error': 'Post not found'}
            
            post_data = dict(result.rows[0])
            
            # Perform detailed sentiment analysis if not already done
            if not post_data['sentiment_score']:
                sentiment_data = await self._analyze_sentiment(post_data['content'])
                
                # Update database
                update_sql = '''
                    UPDATE social_posts 
                    SET sentiment_score = ?, sentiment_label = ?
                    WHERE post_id = ?
                '''
                
                await self.db_query(update_sql, [
                    sentiment_data['score'],
                    sentiment_data['label'],
                    post_id
                ])
                
                post_data.update(sentiment_data)
            
            return {
                'success': True,
                'post_id': post_id,
                'content': post_data['content'],
                'sentiment_score': post_data['sentiment_score'],
                'sentiment_label': post_data['sentiment_label']
            }
            
        except Exception as e:
            self.log('error', f'Failed to get sentiment for post {post_id}', e)
            return {'success': False, 'error': str(e)}
    
    @api_endpoint('/accounts', 'GET', 'List connected social media accounts')
    async def get_connected_accounts(self) -> Dict[str, Any]:
        """List all connected social media accounts"""
        
        config = self.get_config()
        platforms = config.get('platforms', {})
        
        accounts = []
        for platform, platform_config in platforms.items():
            if platform_config.get('enabled', False):
                account_info = await self._get_account_info(platform)
                accounts.append({
                    'platform': platform,
                    'enabled': True,
                    'account_info': account_info
                })
        
        return {
            'success': True,
            'accounts': accounts
        }
    
    # Private methods
    
    async def _initialize_clients(self):
        """Initialize API clients for enabled platforms"""
        
        config = self.get_config()
        platforms = config.get('platforms', {})
        
        for platform, platform_config in platforms.items():
            if platform_config.get('enabled', False):
                try:
                    if platform == 'twitter':
                        self.clients['twitter'] = await self._init_twitter_client(platform_config)
                    elif platform == 'facebook':
                        self.clients['facebook'] = await self._init_facebook_client(platform_config)
                    elif platform == 'instagram':
                        self.clients['instagram'] = await self._init_instagram_client(platform_config)
                    elif platform == 'linkedin':
                        self.clients['linkedin'] = await self._init_linkedin_client(platform_config)
                        
                    self.log('info', f'{platform} client initialized')
                    
                except Exception as e:
                    self.log('error', f'Failed to initialize {platform} client', e)
    
    async def _init_twitter_client(self, config: Dict[str, Any]):
        """Initialize Twitter API client"""
        
        auth = tweepy.OAuth1UserHandler(
            config['api_key'],
            config['api_secret'],
            config['access_token'],
            config['access_token_secret']
        )
        
        return tweepy.API(auth)
    
    async def _init_facebook_client(self, config: Dict[str, Any]):
        """Initialize Facebook API client"""
        # Simplified implementation
        return {
            'app_id': config['app_id'],
            'app_secret': config['app_secret'],
            'access_token': config['access_token']
        }
    
    async def _init_instagram_client(self, config: Dict[str, Any]):
        """Initialize Instagram API client"""
        # Simplified implementation
        return {
            'access_token': config['access_token']
        }
    
    async def _init_linkedin_client(self, config: Dict[str, Any]):
        """Initialize LinkedIn API client"""
        # Simplified implementation
        return {
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'access_token': config['access_token']
        }
    
    async def _create_tables(self):
        """Create database tables for storing social media data"""
        
        # Social posts table
        posts_table_sql = '''
            CREATE TABLE IF NOT EXISTS social_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                post_id TEXT NOT NULL,
                author TEXT,
                content TEXT,
                timestamp DATETIME,
                likes INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                hashtags TEXT,
                mentions TEXT,
                media_urls TEXT,
                sentiment_score REAL,
                sentiment_label TEXT,
                raw_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(platform, post_id)
            )
        '''
        
        await self.db_query(posts_table_sql)
        
        # Analytics data table
        analytics_table_sql = '''
            CREATE TABLE IF NOT EXISTS analytics_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                date DATE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        '''
        
        await self.db_query(analytics_table_sql)
        
        self.log('info', 'Database tables created/verified')
    
    async def _handle_scheduled_import(self) -> TriggerResult:
        """Handle scheduled import from all enabled platforms"""
        
        config = self.get_config()
        platforms = config.get('platforms', {})
        
        results = []
        total_imported = 0
        total_failed = 0
        
        for platform, platform_config in platforms.items():
            if platform_config.get('enabled', False):
                try:
                    result = await self._import_from_platform(platform)
                    results.append({
                        'platform': platform,
                        'success': True,
                        'posts_imported': result.posts_imported,
                        'posts_failed': result.posts_failed
                    })
                    total_imported += result.posts_imported
                    total_failed += result.posts_failed
                    
                except Exception as e:
                    self.log('error', f'Import failed for {platform}', e)
                    results.append({
                        'platform': platform,
                        'success': False,
                        'error': str(e)
                    })
        
        # Send email report if configured
        await self._send_import_report(results, total_imported, total_failed)
        
        return TriggerResult(
            success=True,
            data={
                'total_imported': total_imported,
                'total_failed': total_failed,
                'platform_results': results
            }
        )
    
    async def _handle_manual_import(self, data: Dict[str, Any]) -> TriggerResult:
        """Handle manual import triggered by user"""
        
        platform = data.get('platform')
        if not platform:
            return TriggerResult(success=False, error='Platform not specified')
        
        try:
            result = await self._import_from_platform(platform, data.get('options', {}))
            
            return TriggerResult(
                success=True,
                data={
                    'platform': platform,
                    'posts_imported': result.posts_imported,
                    'posts_failed': result.posts_failed,
                    'duration': (result.end_time - result.start_time).total_seconds()
                }
            )
            
        except Exception as e:
            return TriggerResult(success=False, error=str(e))
    
    async def _handle_webhook_import(self, data: Dict[str, Any]) -> TriggerResult:
        """Handle webhook-triggered import"""
        
        platform = data.get('platform')
        if not platform:
            return TriggerResult(success=False, error='Platform not specified in webhook')
        
        try:
            # Process webhook data (e.g., real-time post notification)
            if 'post_data' in data:
                post = await self._process_webhook_post(platform, data['post_data'])
                await self._store_post(post)
                
                return TriggerResult(
                    success=True,
                    data={
                        'platform': platform,
                        'post_id': post.post_id,
                        'processed': True
                    }
                )
            else:
                # Regular import
                result = await self._import_from_platform(platform)
                return TriggerResult(
                    success=True,
                    data={
                        'platform': platform,
                        'posts_imported': result.posts_imported
                    }
                )
                
        except Exception as e:
            return TriggerResult(success=False, error=str(e))
    
    async def _import_from_platform(self, platform: str, options: Dict[str, Any] = None) -> ImportResult:
        """Import posts from a specific platform"""
        
        start_time = datetime.utcnow()
        posts_imported = 0
        posts_failed = 0
        errors = []
        
        try:
            if platform == 'twitter':
                posts = await self._import_twitter_posts(options)
            elif platform == 'facebook':
                posts = await self._import_facebook_posts(options)
            elif platform == 'instagram':
                posts = await self._import_instagram_posts(options)
            elif platform == 'linkedin':
                posts = await self._import_linkedin_posts(options)
            else:
                raise ValueError(f'Unsupported platform: {platform}')
            
            # Process and store posts
            for post in posts:
                try:
                    # Analyze sentiment if enabled
                    config = self.get_config()
                    if config.get('import_settings', {}).get('analyze_sentiment', True):
                        sentiment = await self._analyze_sentiment(post.content)
                        post.sentiment_score = sentiment['score']
                        post.sentiment_label = sentiment['label']
                    
                    # Store post
                    await self._store_post(post)
                    posts_imported += 1
                    
                except Exception as e:
                    self.log('error', f'Failed to process post {post.post_id}', e)
                    errors.append(f'Post {post.post_id}: {str(e)}')
                    posts_failed += 1
            
            # Track analytics
            await self.track_event('social_media_import', {
                'platform': platform,
                'posts_imported': posts_imported,
                'posts_failed': posts_failed,
                'duration_seconds': (datetime.utcnow() - start_time).total_seconds()
            })
            
        except Exception as e:
            self.log('error', f'Platform import failed for {platform}', e)
            errors.append(str(e))
        
        end_time = datetime.utcnow()
        
        return ImportResult(
            platform=platform,
            posts_imported=posts_imported,
            posts_failed=posts_failed,
            start_time=start_time,
            end_time=end_time,
            errors=errors
        )
    
    async def _import_twitter_posts(self, options: Dict[str, Any] = None) -> List[SocialPost]:
        """Import posts from Twitter"""
        
        if 'twitter' not in self.clients:
            raise ValueError('Twitter client not initialized')
        
        client = self.clients['twitter']
        config = self.get_config()
        import_settings = config.get('import_settings', {})
        filters = config.get('filters', {})
        
        max_posts = options.get('limit', import_settings.get('max_posts_per_run', 100))
        
        posts = []
        
        try:
            # Get timeline posts
            tweets = tweepy.Cursor(
                client.home_timeline,
                tweet_mode='extended',
                include_rts=False
            ).items(max_posts)
            
            for tweet in tweets:
                # Apply filters
                if filters.get('keywords'):
                    if not any(keyword.lower() in tweet.full_text.lower() 
                             for keyword in filters['keywords']):
                        continue
                
                # Extract data
                post = SocialPost(
                    platform='twitter',
                    post_id=str(tweet.id),
                    author=tweet.author.screen_name,
                    content=tweet.full_text,
                    timestamp=tweet.created_at,
                    likes=tweet.favorite_count,
                    shares=tweet.retweet_count,
                    comments=tweet.reply_count if hasattr(tweet, 'reply_count') else 0,
                    hashtags=self._extract_hashtags(tweet.full_text),
                    mentions=self._extract_mentions(tweet.full_text),
                    media_urls=self._extract_media_urls(tweet),
                    raw_data=tweet._json
                )
                
                posts.append(post)
            
        except Exception as e:
            self.log('error', 'Twitter import failed', e)
            raise
        
        return posts
    
    async def _import_facebook_posts(self, options: Dict[str, Any] = None) -> List[SocialPost]:
        """Import posts from Facebook"""
        
        # Simplified implementation - would need actual Facebook Graph API integration
        posts = []
        
        self.log('info', 'Facebook import - simplified implementation')
        
        return posts
    
    async def _import_instagram_posts(self, options: Dict[str, Any] = None) -> List[SocialPost]:
        """Import posts from Instagram"""
        
        # Simplified implementation - would need actual Instagram Basic Display API integration
        posts = []
        
        self.log('info', 'Instagram import - simplified implementation')
        
        return posts
    
    async def _import_linkedin_posts(self, options: Dict[str, Any] = None) -> List[SocialPost]:
        """Import posts from LinkedIn"""
        
        # Simplified implementation - would need actual LinkedIn API integration
        posts = []
        
        self.log('info', 'LinkedIn import - simplified implementation')
        
        return posts
    
    async def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text using TextBlob"""
        
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # -1 to 1
            
            # Convert to label
            if polarity > 0.1:
                label = 'positive'
            elif polarity < -0.1:
                label = 'negative'
            else:
                label = 'neutral'
            
            return {
                'score': polarity,
                'label': label
            }
            
        except Exception as e:
            self.log('error', 'Sentiment analysis failed', e)
            return {'score': 0.0, 'label': 'neutral'}
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text"""
        return re.findall(r'#\w+', text)
    
    def _extract_mentions(self, text: str) -> List[str]:
        """Extract mentions from text"""
        return re.findall(r'@\w+', text)
    
    def _extract_media_urls(self, tweet) -> List[str]:
        """Extract media URLs from tweet"""
        urls = []
        
        if hasattr(tweet, 'entities') and 'media' in tweet.entities:
            for media in tweet.entities['media']:
                urls.append(media['media_url_https'])
        
        return urls
    
    async def _store_post(self, post: SocialPost):
        """Store social media post in database"""
        
        sql = '''
            INSERT OR REPLACE INTO social_posts 
            (platform, post_id, author, content, timestamp, likes, shares, comments,
             hashtags, mentions, media_urls, sentiment_score, sentiment_label, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = [
            post.platform,
            post.post_id,
            post.author,
            post.content,
            post.timestamp.isoformat(),
            post.likes,
            post.shares,
            post.comments,
            json.dumps(post.hashtags) if post.hashtags else None,
            json.dumps(post.mentions) if post.mentions else None,
            json.dumps(post.media_urls) if post.media_urls else None,
            post.sentiment_score,
            post.sentiment_label,
            json.dumps(post.raw_data) if post.raw_data else None
        ]
        
        await self.db_query(sql, params)
    
    async def _process_webhook_post(self, platform: str, post_data: Dict[str, Any]) -> SocialPost:
        """Process post data received via webhook"""
        
        # This would depend on the specific webhook format for each platform
        # Simplified implementation
        
        return SocialPost(
            platform=platform,
            post_id=post_data.get('id', ''),
            author=post_data.get('author', ''),
            content=post_data.get('text', ''),
            timestamp=datetime.utcnow(),
            likes=post_data.get('likes', 0),
            shares=post_data.get('shares', 0),
            comments=post_data.get('comments', 0),
            raw_data=post_data
        )
    
    async def _get_account_info(self, platform: str) -> Dict[str, Any]:
        """Get account information for a platform"""
        
        # Simplified implementation - would get actual account info from APIs
        return {
            'platform': platform,
            'status': 'connected',
            'last_import': datetime.utcnow().isoformat()
        }
    
    async def _send_import_report(self, results: List[Dict], total_imported: int, total_failed: int):
        """Send email report after import"""
        
        config = self.get_config()
        if not config.get('notifications', {}).get('email_reports', False):
            return
        
        user = self.get_current_user()
        
        # Generate report
        report = f"""
Social Media Import Report

Total Posts Imported: {total_imported}
Total Posts Failed: {total_failed}

Platform Results:
"""
        
        for result in results:
            status = "Success" if result.get('success') else "Failed"
            report += f"- {result['platform']}: {status}"
            if result.get('posts_imported'):
                report += f" ({result['posts_imported']} posts)"
            if result.get('error'):
                report += f" - Error: {result['error']}"
            report += "\n"
        
        report += f"\nGenerated at: {datetime.utcnow().isoformat()}"
        
        try:
            await self.send_notification(
                'email',
                user.email,
                'Social Media Import Report',
                report,
                {
                    'total_imported': total_imported,
                    'total_failed': total_failed,
                    'platforms': len(results)
                }
            )
            
            self.log('info', 'Import report sent via email')
            
        except Exception as e:
            self.log('error', 'Failed to send import report', e)


# Export plugin class
plugin_class = SocialMediaImportPlugin