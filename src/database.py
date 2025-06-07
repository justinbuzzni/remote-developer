"""
MongoDB database connection and models
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError
from dotenv import load_dotenv
import json
from bson import ObjectId

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for MongoDB ObjectId"""
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)


class MongoDB:
    """MongoDB connection and operations manager"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.tasks_collection = None
        self.logs_collection = None
        self._connected = False
        self._use_fallback = False
        
    def connect(self):
        """Connect to MongoDB"""
        try:
            # Get connection parameters from environment
            mongodb_host = os.getenv('MONGODB_HOST')
            mongodb_user = os.getenv('MONGODB_USER')
            mongodb_password = os.getenv('MONGODB_PASSWORD')
            mongodb_database = os.getenv('MONGODB_DATABASE', 'remote_developer')
            
            # Build connection string
            if mongodb_host and mongodb_user and mongodb_password:
                # Use host-based connection string
                mongodb_url = f"mongodb://{mongodb_user}:{mongodb_password}@{mongodb_host}"
            else:
                # Fall back to MONGODB_URL
                mongodb_url = os.getenv('MONGODB_URL', 'mongodb://localhost:27017/')
                if mongodb_user and mongodb_password:
                    # If URL already contains credentials, don't add them again
                    if '@' not in mongodb_url:
                        # Parse URL to insert credentials
                        if mongodb_url.startswith('mongodb://'):
                            mongodb_url = f"mongodb://{mongodb_user}:{mongodb_password}@{mongodb_url[10:]}"
                        elif mongodb_url.startswith('mongodb+srv://'):
                            mongodb_url = f"mongodb+srv://{mongodb_user}:{mongodb_password}@{mongodb_url[14:]}"
            
            # Connection options
            options = {
                'maxPoolSize': int(os.getenv('MONGODB_MAX_POOL_SIZE', 50)),
                'minPoolSize': int(os.getenv('MONGODB_MIN_POOL_SIZE', 10)),
                'serverSelectionTimeoutMS': int(os.getenv('MONGODB_TIMEOUT_MS', 5000))
            }
            
            # Create client
            self.client = MongoClient(mongodb_url, **options)
            
            # Test connection
            self.client.admin.command('ping')
            
            # Get database
            self.db = self.client[mongodb_database]
            
            # Get collections
            self.tasks_collection = self.db['tasks']
            self.logs_collection = self.db['task_logs']
            
            # Create indexes
            self._create_indexes()
            
            self._connected = True
            logger.info(f"Connected to MongoDB database: {mongodb_database}")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"Failed to connect to MongoDB: {e}")
            logger.warning("MongoDB is not accessible. Tasks will be stored locally only.")
            self._connected = False
            self._use_fallback = True
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            self._connected = False
            self._use_fallback = True
    
    def _create_indexes(self):
        """Create database indexes for better performance"""
        try:
            # Task indexes
            self.tasks_collection.create_index([('task_id', ASCENDING)], unique=True)
            self.tasks_collection.create_index([('github_repo', ASCENDING)])
            self.tasks_collection.create_index([('status', ASCENDING)])
            self.tasks_collection.create_index([('created_at', DESCENDING)])
            self.tasks_collection.create_index([('devpod_name', ASCENDING)])
            
            # Compound index for repository grouping
            self.tasks_collection.create_index([
                ('github_repo', ASCENDING),
                ('created_at', DESCENDING)
            ])
            
            # Log indexes
            self.logs_collection.create_index([('task_id', ASCENDING)])
            self.logs_collection.create_index([('timestamp', ASCENDING)])
            
            # Compound index for efficient log retrieval
            self.logs_collection.create_index([
                ('task_id', ASCENDING),
                ('timestamp', ASCENDING)
            ])
            
            logger.info("MongoDB indexes created successfully")
            
        except OperationFailure as e:
            logger.error(f"Failed to create indexes: {e}")
    
    def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("Disconnected from MongoDB")
    
    def save_task(self, task_id: str, task_data: Dict[str, Any]) -> bool:
        """Save or update a task"""
        try:
            task_data['task_id'] = task_id
            task_data['last_updated'] = datetime.now()
            
            # Use upsert to insert or update
            result = self.tasks_collection.update_one(
                {'task_id': task_id},
                {'$set': task_data},
                upsert=True
            )
            
            return result.acknowledged
            
        except Exception as e:
            logger.error(f"Failed to save task {task_id}: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID"""
        try:
            task = self.tasks_collection.find_one({'task_id': task_id})
            if task:
                task['_id'] = str(task['_id'])  # Convert ObjectId to string
            return task
            
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None
    
    def get_all_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all tasks with optional limit"""
        try:
            tasks = list(self.tasks_collection.find().sort('created_at', DESCENDING).limit(limit))
            for task in tasks:
                task['_id'] = str(task['_id'])
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to get all tasks: {e}")
            return []
    
    def get_tasks_by_repo(self, github_repo: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get tasks for a specific repository"""
        try:
            tasks = list(self.tasks_collection.find(
                {'github_repo': github_repo}
            ).sort('created_at', DESCENDING).limit(limit))
            
            for task in tasks:
                task['_id'] = str(task['_id'])
            return tasks
            
        except Exception as e:
            logger.error(f"Failed to get tasks for repo {github_repo}: {e}")
            return []
    
    def get_tasks_grouped_by_repo(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all tasks grouped by repository"""
        try:
            pipeline = [
                {
                    '$sort': {'created_at': -1}
                },
                {
                    '$group': {
                        '_id': '$github_repo',
                        'tasks': {
                            '$push': {
                                'task_id': '$task_id',
                                'status': '$status',
                                'created_at': '$created_at',
                                'task_description': '$task_description',
                                'devpod_name': '$devpod_name',
                                'progress': '$progress',
                                'has_changes': '$has_changes',
                                'is_committed': '$is_committed'
                            }
                        },
                        'total_tasks': {'$sum': 1},
                        'completed_tasks': {
                            '$sum': {'$cond': [{'$eq': ['$status', 'completed']}, 1, 0]}
                        },
                        'failed_tasks': {
                            '$sum': {'$cond': [{'$eq': ['$status', 'failed']}, 1, 0]}
                        },
                        'running_tasks': {
                            '$sum': {
                                '$cond': [
                                    {'$not': {'$in': ['$status', ['completed', 'failed', 'interrupted']]}},
                                    1, 0
                                ]
                            }
                        }
                    }
                },
                {
                    '$project': {
                        'repo': '$_id',
                        'tasks': {'$slice': ['$tasks', 10]},  # Limit to 10 most recent tasks per repo
                        'stats': {
                            'total': '$total_tasks',
                            'completed': '$completed_tasks',
                            'failed': '$failed_tasks',
                            'running': '$running_tasks'
                        }
                    }
                },
                {
                    '$sort': {'stats.total': -1}  # Sort by most active repos
                }
            ]
            
            result = list(self.tasks_collection.aggregate(pipeline))
            
            # Convert to dictionary format
            grouped = {}
            for item in result:
                grouped[item['repo']] = {
                    'tasks': item['tasks'],
                    'stats': item['stats']
                }
            
            return grouped
            
        except Exception as e:
            logger.error(f"Failed to get grouped tasks: {e}")
            return {}
    
    def add_log(self, task_id: str, log_message: str) -> bool:
        """Add a log entry for a task"""
        try:
            log_entry = {
                'task_id': task_id,
                'message': log_message,
                'timestamp': datetime.now()
            }
            
            result = self.logs_collection.insert_one(log_entry)
            return result.acknowledged
            
        except Exception as e:
            logger.error(f"Failed to add log for task {task_id}: {e}")
            return False
    
    def get_logs(self, task_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get logs for a specific task"""
        try:
            logs = list(self.logs_collection.find(
                {'task_id': task_id}
            ).sort('timestamp', ASCENDING).limit(limit))
            
            for log in logs:
                log['_id'] = str(log['_id'])
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get logs for task {task_id}: {e}")
            return []
    
    def get_recent_logs(self, task_id: str, after_timestamp: datetime, limit: int = 100) -> List[Dict[str, Any]]:
        """Get logs after a specific timestamp"""
        try:
            logs = list(self.logs_collection.find({
                'task_id': task_id,
                'timestamp': {'$gt': after_timestamp}
            }).sort('timestamp', ASCENDING).limit(limit))
            
            for log in logs:
                log['_id'] = str(log['_id'])
            return logs
            
        except Exception as e:
            logger.error(f"Failed to get recent logs for task {task_id}: {e}")
            return []
    
    def delete_old_tasks(self, days: int = 30) -> int:
        """Delete tasks older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Find old tasks
            old_tasks = self.tasks_collection.find(
                {'created_at': {'$lt': cutoff_date}},
                {'task_id': 1}
            )
            
            task_ids = [task['task_id'] for task in old_tasks]
            
            # Delete logs first
            logs_result = self.logs_collection.delete_many({
                'task_id': {'$in': task_ids}
            })
            
            # Delete tasks
            tasks_result = self.tasks_collection.delete_many({
                'task_id': {'$in': task_ids}
            })
            
            logger.info(f"Deleted {tasks_result.deleted_count} old tasks and {logs_result.deleted_count} log entries")
            return tasks_result.deleted_count
            
        except Exception as e:
            logger.error(f"Failed to delete old tasks: {e}")
            return 0
    
    def get_repository_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all repositories"""
        try:
            pipeline = [
                {
                    '$group': {
                        '_id': '$github_repo',
                        'total_tasks': {'$sum': 1},
                        'completed_tasks': {
                            '$sum': {'$cond': [{'$eq': ['$status', 'completed']}, 1, 0]}
                        },
                        'failed_tasks': {
                            '$sum': {'$cond': [{'$eq': ['$status', 'failed']}, 1, 0]}
                        },
                        'total_commits': {
                            '$sum': {'$cond': [{'$eq': ['$is_committed', True]}, 1, 0]}
                        },
                        'last_activity': {'$max': '$last_updated'},
                        'first_activity': {'$min': '$created_at'}
                    }
                },
                {
                    '$project': {
                        'repository': '$_id',
                        'total_tasks': 1,
                        'completed_tasks': 1,
                        'failed_tasks': 1,
                        'total_commits': 1,
                        'success_rate': {
                            '$cond': [
                                {'$gt': ['$total_tasks', 0]},
                                {'$multiply': [
                                    {'$divide': ['$completed_tasks', '$total_tasks']},
                                    100
                                ]},
                                0
                            ]
                        },
                        'last_activity': 1,
                        'first_activity': 1
                    }
                },
                {
                    '$sort': {'last_activity': -1}
                }
            ]
            
            stats = list(self.tasks_collection.aggregate(pipeline))
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get repository stats: {e}")
            return []


# Global database instance
db = MongoDB()


# Helper functions for backward compatibility
def save_task_to_db(task_id: str, task_data: Dict[str, Any]) -> bool:
    """Save task to MongoDB"""
    if not db._connected and not db._use_fallback:
        db.connect()
    if db._connected:
        return db.save_task(task_id, task_data)
    return True  # Return True if using fallback (local storage)


def get_task_from_db(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task from MongoDB"""
    if not db._connected and not db._use_fallback:
        db.connect()
    if db._connected:
        return db.get_task(task_id)
    return None  # Return None if using fallback


def add_log_to_db(task_id: str, log_message: str) -> bool:
    """Add log to MongoDB"""
    if not db._connected and not db._use_fallback:
        db.connect()
    if db._connected:
        return db.add_log(task_id, log_message)
    return True  # Return True if using fallback (local storage)