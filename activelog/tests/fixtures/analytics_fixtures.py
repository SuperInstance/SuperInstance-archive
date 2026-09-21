"""
Analytics-related test fixtures and data generators
"""

import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from faker import Faker
import numpy as np

fake = Faker()


class AnalyticsFixtures:
    """Generate analytics test data and fixtures"""
    
    @staticmethod
    def create_user_analytics(
        user_id: Optional[str] = None,
        date_range_days: int = 30,
        **kwargs
    ) -> Dict[str, Any]:
        """Create user analytics fixture"""
        
        user_id = user_id or str(uuid.uuid4())
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=date_range_days)
        
        return {
            'user_id': user_id,
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': date_range_days
            },
            'activity_summary': {
                'total_sessions': random.randint(10, 200),
                'total_time_minutes': random.randint(300, 10000),
                'avg_session_duration_minutes': random.randint(5, 60),
                'total_actions': random.randint(100, 5000),
                'days_active': random.randint(5, date_range_days),
                'login_count': random.randint(10, 100)
            },
            'file_activity': {
                'files_uploaded': random.randint(0, 50),
                'files_downloaded': random.randint(0, 200),
                'files_viewed': random.randint(10, 500),
                'files_shared': random.randint(0, 30),
                'files_deleted': random.randint(0, 10),
                'total_upload_size_mb': round(random.uniform(0, 1000), 2),
                'total_download_size_mb': round(random.uniform(0, 2000), 2)
            },
            'search_activity': {
                'total_searches': random.randint(0, 200),
                'semantic_searches': random.randint(0, 50),
                'successful_searches': random.randint(0, 180),
                'avg_results_per_search': round(random.uniform(1, 20), 1),
                'most_searched_terms': fake.words(nb=5)
            },
            'ai_usage': {
                'ai_requests': random.randint(0, 100),
                'analysis_requests': random.randint(0, 50),
                'translation_requests': random.randint(0, 20),
                'summarization_requests': random.randint(0, 30),
                'tokens_consumed': random.randint(0, 100000),
                'ai_cost': round(random.uniform(0, 50), 2)
            },
            'device_info': {
                'primary_device': random.choice(['desktop', 'mobile', 'tablet']),
                'browsers_used': random.sample(['chrome', 'firefox', 'safari', 'edge'], random.randint(1, 3)),
                'operating_systems': random.sample(['windows', 'macos', 'linux', 'ios', 'android'], random.randint(1, 2)),
                'mobile_usage_percentage': round(random.uniform(0, 100), 1)
            },
            **kwargs
        }
    
    @staticmethod
    def create_system_analytics(
        date_range_days: int = 7,
        **kwargs
    ) -> Dict[str, Any]:
        """Create system-wide analytics fixture"""
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=date_range_days)
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': date_range_days
            },
            'user_metrics': {
                'total_users': random.randint(100, 10000),
                'active_users': random.randint(50, 8000),
                'new_users': random.randint(5, 500),
                'returning_users': random.randint(45, 7500),
                'user_retention_rate': round(random.uniform(0.6, 0.9), 3),
                'avg_users_per_day': round(random.uniform(50, 1000), 1)
            },
            'content_metrics': {
                'total_files': random.randint(1000, 100000),
                'files_uploaded': random.randint(100, 5000),
                'files_processed': random.randint(90, 4800),
                'total_storage_gb': round(random.uniform(100, 10000), 2),
                'storage_growth_gb': round(random.uniform(10, 500), 2),
                'avg_file_size_mb': round(random.uniform(0.5, 50), 2)
            },
            'performance_metrics': {
                'avg_response_time_ms': random.randint(100, 1000),
                'p95_response_time_ms': random.randint(500, 3000),
                'uptime_percentage': round(random.uniform(99.0, 99.99), 2),
                'error_rate': round(random.uniform(0.001, 0.05), 4),
                'throughput_requests_per_second': round(random.uniform(10, 1000), 1)
            },
            'ai_metrics': {
                'total_ai_requests': random.randint(1000, 100000),
                'successful_ai_requests': random.randint(950, 99000),
                'ai_processing_time_avg_ms': random.randint(500, 5000),
                'tokens_processed': random.randint(100000, 10000000),
                'ai_cost_total': round(random.uniform(100, 10000), 2),
                'most_used_models': ['gpt-4', 'gpt-3.5-turbo', 'text-embedding-ada-002']
            },
            'search_metrics': {
                'total_searches': random.randint(500, 50000),
                'semantic_searches': random.randint(100, 10000),
                'search_success_rate': round(random.uniform(0.8, 0.95), 3),
                'avg_search_time_ms': random.randint(50, 500),
                'zero_result_searches': random.randint(10, 1000)
            },
            **kwargs
        }
    
    @staticmethod
    def create_file_analytics(
        file_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create file-specific analytics fixture"""
        
        file_id = file_id or str(uuid.uuid4())
        created_date = fake.date_time_between(start_date='-1y', end_date='-30d')
        
        return {
            'file_id': file_id,
            'created_at': created_date,
            'analytics_period': {
                'start_date': created_date,
                'end_date': datetime.utcnow(),
                'days_since_creation': (datetime.utcnow() - created_date).days
            },
            'access_metrics': {
                'total_views': random.randint(0, 1000),
                'unique_viewers': random.randint(0, 100),
                'total_downloads': random.randint(0, 200),
                'unique_downloaders': random.randint(0, 50),
                'shares_created': random.randint(0, 20),
                'share_views': random.randint(0, 500),
                'last_accessed': fake.date_time_between(start_date='-7d', end_date='now')
            },
            'search_metrics': {
                'appeared_in_searches': random.randint(0, 100),
                'clicked_from_search': random.randint(0, 50),
                'search_click_rate': round(random.uniform(0, 1), 3),
                'avg_search_rank': round(random.uniform(1, 20), 1),
                'semantic_search_matches': random.randint(0, 30)
            },
            'ai_analysis': {
                'analyses_performed': random.randint(0, 10),
                'embedding_generated': fake.boolean(),
                'last_analysis_date': fake.date_time_between(start_date='-30d', end_date='now') if fake.boolean() else None,
                'analysis_types': random.sample([
                    'content_analysis', 'sentiment_analysis', 'entity_extraction',
                    'summarization', 'translation'
                ], random.randint(0, 3)),
                'ai_confidence_avg': round(random.uniform(0.6, 0.95), 3) if fake.boolean() else None
            },
            'collaboration_metrics': {
                'collaborators_count': random.randint(0, 20),
                'comments_count': random.randint(0, 50),
                'versions_count': random.randint(1, 10),
                'concurrent_edits': random.randint(0, 5),
                'sync_conflicts': random.randint(0, 3)
            },
            'performance_metrics': {
                'avg_load_time_ms': random.randint(100, 2000),
                'processing_time_ms': random.randint(500, 10000) if fake.boolean() else None,
                'cache_hit_rate': round(random.uniform(0.5, 0.95), 3),
                'bandwidth_usage_mb': round(random.uniform(0.1, 100), 2)
            },
            **kwargs
        }
    
    @staticmethod
    def create_time_series_data(
        metric_name: str,
        start_date: datetime,
        end_date: datetime,
        interval_minutes: int = 60,
        **kwargs
    ) -> Dict[str, Any]:
        """Create time series analytics data"""
        
        # Generate data points
        data_points = []
        current_date = start_date
        
        while current_date <= end_date:
            # Generate realistic value based on metric type
            if 'response_time' in metric_name:
                value = random.gauss(500, 100)  # Normal distribution around 500ms
            elif 'requests' in metric_name:
                value = random.poisson(50)  # Poisson distribution for request counts
            elif 'users' in metric_name:
                # Simulate daily pattern for user count
                hour = current_date.hour
                base_value = 100
                if 9 <= hour <= 17:  # Business hours
                    value = base_value + random.randint(50, 200)
                else:
                    value = base_value + random.randint(0, 50)
            elif 'error_rate' in metric_name:
                value = max(0, random.gauss(0.02, 0.01))  # Low error rate
            else:
                value = random.uniform(0, 100)
            
            data_points.append({
                'timestamp': current_date,
                'value': round(value, 3),
                'count': random.randint(1, 1000) if fake.boolean() else None
            })
            
            current_date += timedelta(minutes=interval_minutes)
        
        # Calculate statistics
        values = [dp['value'] for dp in data_points]
        
        return {
            'metric_name': metric_name,
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'interval_minutes': interval_minutes
            },
            'data_points': data_points,
            'statistics': {
                'count': len(data_points),
                'min': round(min(values), 3),
                'max': round(max(values), 3),
                'avg': round(np.mean(values), 3),
                'median': round(np.median(values), 3),
                'std_dev': round(np.std(values), 3),
                'percentile_95': round(np.percentile(values, 95), 3),
                'percentile_99': round(np.percentile(values, 99), 3)
            },
            'trends': {
                'is_increasing': np.polyfit(range(len(values)), values, 1)[0] > 0,
                'slope': round(np.polyfit(range(len(values)), values, 1)[0], 6),
                'correlation': round(np.corrcoef(range(len(values)), values)[0, 1], 3)
            },
            **kwargs
        }
    
    @staticmethod
    def create_dashboard_data(
        user_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create dashboard analytics data"""
        
        user_id = user_id or str(uuid.uuid4())
        
        return {
            'user_id': user_id,
            'generated_at': datetime.utcnow(),
            'widgets': {
                'overview_stats': {
                    'total_files': random.randint(50, 1000),
                    'total_size_gb': round(random.uniform(1, 100), 2),
                    'files_this_week': random.randint(0, 50),
                    'storage_used_percentage': round(random.uniform(10, 90), 1)
                },
                'recent_activity': [
                    {
                        'id': str(uuid.uuid4()),
                        'type': random.choice(['upload', 'download', 'share', 'delete', 'search']),
                        'description': fake.sentence(),
                        'timestamp': fake.date_time_between(start_date='-7d', end_date='now'),
                        'file_name': fake.file_name() if fake.boolean() else None
                    } for _ in range(random.randint(5, 20))
                ],
                'popular_files': [
                    {
                        'file_id': str(uuid.uuid4()),
                        'name': fake.file_name(),
                        'views': random.randint(10, 500),
                        'downloads': random.randint(1, 100),
                        'last_accessed': fake.date_time_between(start_date='-30d', end_date='now')
                    } for _ in range(random.randint(3, 10))
                ],
                'storage_breakdown': {
                    'documents': round(random.uniform(10, 40), 1),
                    'images': round(random.uniform(20, 50), 1),
                    'videos': round(random.uniform(5, 30), 1),
                    'audio': round(random.uniform(1, 10), 1),
                    'archives': round(random.uniform(1, 15), 1),
                    'other': round(random.uniform(1, 10), 1)
                },
                'search_trends': [
                    {
                        'term': fake.word(),
                        'count': random.randint(1, 50),
                        'trend': random.choice(['up', 'down', 'stable'])
                    } for _ in range(random.randint(5, 15))
                ],
                'ai_usage_summary': {
                    'requests_this_month': random.randint(0, 200),
                    'tokens_consumed': random.randint(0, 50000),
                    'cost_this_month': round(random.uniform(0, 25), 2),
                    'favorite_features': random.sample([
                        'semantic_search', 'summarization', 'translation',
                        'sentiment_analysis', 'entity_extraction'
                    ], random.randint(1, 3))
                }
            },
            'charts_data': {
                'daily_activity': AnalyticsFixtures.create_time_series_data(
                    'daily_activity',
                    datetime.utcnow() - timedelta(days=30),
                    datetime.utcnow(),
                    interval_minutes=1440  # Daily intervals
                ),
                'storage_growth': AnalyticsFixtures.create_time_series_data(
                    'storage_gb',
                    datetime.utcnow() - timedelta(days=90),
                    datetime.utcnow(),
                    interval_minutes=1440
                )
            },
            **kwargs
        }
    
    @staticmethod
    def create_report_data(
        report_type: str = "monthly",
        **kwargs
    ) -> Dict[str, Any]:
        """Create analytics report data"""
        
        if report_type == "monthly":
            start_date = datetime.utcnow().replace(day=1) - timedelta(days=1)
            start_date = start_date.replace(day=1)
            end_date = datetime.utcnow().replace(day=1) - timedelta(days=1)
        elif report_type == "weekly":
            start_date = datetime.utcnow() - timedelta(days=7)
            end_date = datetime.utcnow()
        else:  # daily
            start_date = datetime.utcnow() - timedelta(days=1)
            end_date = datetime.utcnow()
        
        return {
            'id': str(uuid.uuid4()),
            'report_type': report_type,
            'generated_at': datetime.utcnow(),
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'summary': {
                'total_users': random.randint(100, 10000),
                'active_users': random.randint(50, 8000),
                'new_signups': random.randint(10, 500),
                'files_processed': random.randint(1000, 50000),
                'ai_requests': random.randint(500, 25000),
                'storage_used_gb': round(random.uniform(1000, 50000), 2)
            },
            'highlights': [
                f"User engagement increased by {random.randint(5, 25)}%",
                f"AI usage grew by {random.randint(10, 40)}%",
                f"Storage efficiency improved by {random.randint(2, 15)}%",
                f"Search success rate: {random.randint(85, 98)}%"
            ],
            'detailed_metrics': {
                'user_engagement': {
                    'avg_session_duration': random.randint(10, 60),
                    'bounce_rate': round(random.uniform(0.1, 0.4), 3),
                    'pages_per_session': round(random.uniform(3, 15), 1),
                    'return_user_rate': round(random.uniform(0.6, 0.9), 3)
                },
                'content_performance': {
                    'upload_success_rate': round(random.uniform(0.95, 0.99), 3),
                    'processing_success_rate': round(random.uniform(0.9, 0.98), 3),
                    'avg_processing_time': random.randint(500, 5000),
                    'popular_file_types': {
                        'document': random.randint(100, 1000),
                        'image': random.randint(200, 2000),
                        'video': random.randint(10, 200)
                    }
                },
                'search_performance': {
                    'total_searches': random.randint(1000, 100000),
                    'semantic_search_ratio': round(random.uniform(0.2, 0.6), 3),
                    'avg_results_returned': round(random.uniform(5, 25), 1),
                    'zero_result_rate': round(random.uniform(0.05, 0.2), 3)
                }
            },
            'recommendations': [
                "Consider optimizing file processing pipeline",
                "Implement caching for frequently accessed files",
                "Add more AI model options for better accuracy",
                "Improve search result ranking algorithm"
            ],
            **kwargs
        }


class AnalyticsFactory:
    """Factory for creating complex analytics scenarios"""
    
    def __init__(self):
        self.user_analytics = []
        self.file_analytics = []
        self.time_series = []
    
    def create_multi_user_analytics(
        self,
        user_ids: List[str],
        date_range_days: int = 30
    ) -> Dict[str, Any]:
        """Create analytics for multiple users"""
        
        analytics_data = []
        
        for user_id in user_ids:
            user_data = AnalyticsFixtures.create_user_analytics(user_id, date_range_days)
            analytics_data.append(user_data)
            self.user_analytics.append(user_data)
        
        # Calculate aggregate statistics
        total_sessions = sum(ua['activity_summary']['total_sessions'] for ua in analytics_data)
        total_files_uploaded = sum(ua['file_activity']['files_uploaded'] for ua in analytics_data)
        total_searches = sum(ua['search_activity']['total_searches'] for ua in analytics_data)
        
        return {
            'user_count': len(user_ids),
            'individual_analytics': analytics_data,
            'aggregated_stats': {
                'total_sessions': total_sessions,
                'avg_sessions_per_user': round(total_sessions / len(user_ids), 1),
                'total_files_uploaded': total_files_uploaded,
                'total_searches': total_searches,
                'active_users': len([ua for ua in analytics_data if ua['activity_summary']['days_active'] > 0])
            },
            'insights': {
                'most_active_user': max(analytics_data, key=lambda x: x['activity_summary']['total_sessions'])['user_id'],
                'avg_session_duration': round(np.mean([ua['activity_summary']['avg_session_duration_minutes'] for ua in analytics_data]), 1),
                'power_users': [ua['user_id'] for ua in analytics_data if ua['activity_summary']['total_sessions'] > 50]
            }
        }
    
    def create_performance_monitoring_data(
        self,
        days: int = 7,
        interval_minutes: int = 15
    ) -> Dict[str, Any]:
        """Create comprehensive performance monitoring data"""
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        metrics = [
            'response_time_ms',
            'requests_per_second',
            'active_users',
            'error_rate',
            'cpu_usage_percent',
            'memory_usage_percent',
            'disk_usage_percent',
            'network_io_mbps'
        ]
        
        time_series_data = {}
        
        for metric in metrics:
            ts_data = AnalyticsFixtures.create_time_series_data(
                metric, start_date, end_date, interval_minutes
            )
            time_series_data[metric] = ts_data
            self.time_series.append(ts_data)
        
        # Generate alerts based on thresholds
        alerts = []
        for metric, data in time_series_data.items():
            max_value = data['statistics']['max']
            
            if metric == 'response_time_ms' and max_value > 2000:
                alerts.append({
                    'type': 'warning',
                    'metric': metric,
                    'message': f'High response time detected: {max_value}ms',
                    'timestamp': fake.date_time_between(start_date, end_date)
                })
            elif metric == 'error_rate' and max_value > 0.05:
                alerts.append({
                    'type': 'critical',
                    'metric': metric,
                    'message': f'High error rate: {max_value*100:.1f}%',
                    'timestamp': fake.date_time_between(start_date, end_date)
                })
        
        return {
            'monitoring_period': {
                'start_date': start_date,
                'end_date': end_date,
                'interval_minutes': interval_minutes
            },
            'metrics': time_series_data,
            'alerts': alerts,
            'health_score': round(random.uniform(0.8, 0.99), 3),
            'availability': round(random.uniform(0.99, 0.9999), 4)
        }