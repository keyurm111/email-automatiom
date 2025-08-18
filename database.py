import os
from pymongo import MongoClient
from dotenv import load_dotenv
import datetime
from typing import Dict, List, Any, Optional
import io
import base64

# Load environment variables
load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/bulk_email_automation')
        self.client = MongoClient(self.mongodb_uri)
        self.db = self.client.bulk_email_automation
        
        # Initialize collections
        self.senders = self.db.senders
        self.campaigns = self.db.campaigns
        self.history = self.db.history
        self.email_logs = self.db.email_logs
        self.config = self.db.config
        self.files = self.db.files  # New collection for file storage
        
        # Create indexes for better performance
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for better performance"""
        try:
            # Senders collection indexes
            try:
                self.senders.create_index("email", unique=True)
            except Exception as e:
                if "IndexKeySpecsConflict" not in str(e):
                    print(f"Warning: Could not create senders email index: {e}")
            
            # Campaigns collection indexes
            try:
                self.campaigns.create_index("id", unique=True)
                self.campaigns.create_index("status")
            except Exception as e:
                if "IndexKeySpecsConflict" not in str(e):
                    print(f"Warning: Could not create campaigns indexes: {e}")
            
            # History collection indexes
            try:
                self.history.create_index("campaign_id")
                self.history.create_index("timestamp")
            except Exception as e:
                if "IndexKeySpecsConflict" not in str(e):
                    print(f"Warning: Could not create history indexes: {e}")
            
            # Email logs indexes
            try:
                self.email_logs.create_index("timestamp")
                self.email_logs.create_index("sender")
                self.email_logs.create_index("recipient")
            except Exception as e:
                if "IndexKeySpecsConflict" not in str(e):
                    print(f"Warning: Could not create email logs indexes: {e}")
            
            # Files collection indexes
            try:
                self.files.create_index("file_id", unique=True)
                self.files.create_index("campaign_id")
                self.files.create_index("file_type")
            except Exception as e:
                if "IndexKeySpecsConflict" not in str(e):
                    print(f"Warning: Could not create files indexes: {e}")
            
        except Exception as e:
            print(f"Warning: Could not create indexes: {e}")
    
    # File storage methods
    def store_file(self, file_id: str, campaign_id: str, file_type: str, file_content, filename: str) -> bool:
        """Store a file (CSV or HTML) in MongoDB"""
        try:
            # Convert various input types to bytes
            if hasattr(file_content, 'tobytes'):
                # Handle memoryview objects
                content_bytes = file_content.tobytes()
            elif hasattr(file_content, 'read'):
                # Handle file-like objects
                content_bytes = file_content.read()
            elif isinstance(file_content, bytes):
                # Already bytes
                content_bytes = file_content
            elif isinstance(file_content, str):
                # String content
                content_bytes = file_content.encode('utf-8')
            else:
                # Try to convert to bytes
                content_bytes = bytes(file_content)
            
            file_doc = {
                "file_id": file_id,
                "campaign_id": campaign_id,
                "file_type": file_type,  # 'csv' or 'html'
                "filename": filename,
                "content": content_bytes,
                "size": len(content_bytes),
                "uploaded_at": datetime.datetime.now().isoformat()
            }
            
            self.files.replace_one(
                {"file_id": file_id},
                file_doc,
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error storing file: {e}")
            return False
    
    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a file from MongoDB"""
        try:
            file_doc = self.files.find_one({"file_id": file_id})
            if file_doc:
                file_doc.pop('_id', None)
                return file_doc
            return None
        except Exception as e:
            print(f"Error retrieving file: {e}")
            return None
    
    def delete_file(self, file_id: str) -> bool:
        """Delete a file from MongoDB"""
        try:
            result = self.files.delete_one({"file_id": file_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False
    
    def get_campaign_files(self, campaign_id: str) -> List[Dict[str, Any]]:
        """Get all files for a specific campaign"""
        try:
            files = list(self.files.find({"campaign_id": campaign_id}, {'_id': 0, 'content': 0}))
            return files
        except Exception as e:
            print(f"Error getting campaign files: {e}")
            return []
    
    def store_csv_leads(self, campaign_id: str, csv_content, filename: str = "leads.csv") -> str:
        """Store CSV leads file in MongoDB and return file_id"""
        file_id = f"leads_{campaign_id}"
        if self.store_file(file_id, campaign_id, "csv", csv_content, filename):
            return file_id
        return None
    
    def store_email_template(self, campaign_id: str, html_content, filename: str = "template.html") -> str:
        """Store email template in MongoDB and return file_id"""
        file_id = f"template_{campaign_id}"
        if self.store_file(file_id, campaign_id, "html", html_content, filename):
            return file_id
        return None
    
    def get_csv_leads(self, campaign_id: str) -> Optional[bytes]:
        """Get CSV leads content for a campaign"""
        file_id = f"leads_{campaign_id}"
        file_doc = self.get_file(file_id)
        if file_doc and file_doc.get('file_type') == 'csv':
            return file_doc.get('content')
        return None
    
    def get_email_template(self, campaign_id: str) -> Optional[str]:
        """Get email template content for a campaign"""
        file_id = f"template_{campaign_id}"
        file_doc = self.get_file(file_id)
        if file_doc and file_doc.get('file_type') == 'html':
            return file_doc.get('content').decode('utf-8')
        return None
    
    def get_csv_as_dataframe(self, campaign_id: str):
        """Get CSV leads as pandas DataFrame"""
        try:
            import pandas as pd
            csv_content = self.get_csv_leads(campaign_id)
            if csv_content:
                csv_string = csv_content.decode('utf-8')
                return pd.read_csv(io.StringIO(csv_string))
            return None
        except Exception as e:
            print(f"Error converting CSV to DataFrame: {e}")
            return None
    
    # Existing methods remain the same
    def load_senders(self) -> List[Dict[str, str]]:
        """Load all senders from MongoDB"""
        try:
            senders = list(self.senders.find({}, {'_id': 0}))
            return senders
        except Exception as e:
            print(f"Error loading senders: {e}")
            return []
    
    def save_senders(self, senders: List[Dict[str, str]]) -> bool:
        """Save senders to MongoDB"""
        try:
            # Clear existing senders and insert new ones
            self.senders.delete_many({})
            if senders:
                self.senders.insert_many(senders)
            return True
        except Exception as e:
            print(f"Error saving senders: {e}")
            return False
    
    def add_sender(self, sender: Dict[str, str]) -> bool:
        """Add a single sender to MongoDB"""
        try:
            self.senders.insert_one(sender)
            return True
        except Exception as e:
            print(f"Error adding sender: {e}")
            return False
    
    def update_sender(self, email: str, updated_sender: Dict[str, str]) -> bool:
        """Update a sender in MongoDB"""
        try:
            result = self.senders.update_one(
                {"email": email},
                {"$set": updated_sender}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating sender: {e}")
            return False
    
    def delete_sender(self, email: str) -> bool:
        """Delete a sender from MongoDB"""
        try:
            result = self.senders.delete_one({"email": email})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting sender: {e}")
            return False
    
    def load_campaigns(self) -> Dict[str, Any]:
        """Load all campaigns from MongoDB"""
        try:
            campaigns = {}
            for campaign in self.campaigns.find({}, {'_id': 0}):
                campaigns[campaign['id']] = campaign
            return campaigns
        except Exception as e:
            print(f"Error loading campaigns: {e}")
            return {}
    
    def save_campaigns(self, campaigns: Dict[str, Any]) -> bool:
        """Save campaigns to MongoDB"""
        try:
            # Clear existing campaigns and insert new ones
            self.campaigns.delete_many({})
            if campaigns:
                self.campaigns.insert_many(campaigns.values())
            return True
        except Exception as e:
            print(f"Error saving campaigns: {e}")
            return False
    
    def save_campaign(self, campaign: Dict[str, Any]) -> bool:
        """Save a single campaign to MongoDB"""
        try:
            self.campaigns.replace_one(
                {"id": campaign['id']},
                campaign,
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving campaign: {e}")
            return False
    
    def delete_campaign(self, campaign_id: str) -> bool:
        """Delete a campaign from MongoDB"""
        try:
            result = self.campaigns.delete_one({"id": campaign_id})
            return result.deleted_count > 0
        except Exception as e:
            print(f"Error deleting campaign: {e}")
            return False
    
    def load_history(self, campaign_id: str) -> Dict[str, Any]:
        """Load campaign history from MongoDB"""
        try:
            history = self.history.find_one({"campaign_id": campaign_id})
            if history:
                history.pop('_id', None)
                return history
            return {}
        except Exception as e:
            print(f"Error loading history: {e}")
            return {}
    
    def save_history(self, campaign_id: str, history: Dict[str, Any]) -> bool:
        """Save campaign history to MongoDB"""
        try:
            history['campaign_id'] = campaign_id
            self.history.replace_one(
                {"campaign_id": campaign_id},
                history,
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error saving history: {e}")
            return False
    
    def load_email_logs(self) -> List[Dict[str, Any]]:
        """Load email logs from MongoDB"""
        try:
            logs = list(self.email_logs.find({}, {'_id': 0}).sort("timestamp", -1).limit(1000))
            return logs
        except Exception as e:
            print(f"Error loading email logs: {e}")
            return []
    
    def save_email_log(self, log_entry: Dict[str, Any]) -> bool:
        """Save email log entry to MongoDB"""
        try:
            self.email_logs.insert_one(log_entry)
            
            # Keep only last 1000 entries
            total_logs = self.email_logs.count_documents({})
            if total_logs > 1000:
                # Find the 1000th most recent log
                cursor = self.email_logs.find({}, {'_id': 1}).sort("timestamp", -1).skip(999).limit(1)
                if cursor:
                    oldest_id = cursor[0]['_id']
                    # Delete older logs
                    self.email_logs.delete_many({"_id": {"$lt": oldest_id}})
            
            return True
        except Exception as e:
            print(f"Error saving email log: {e}")
            return False
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from MongoDB"""
        try:
            config = self.config.find_one({}, {'_id': 0})
            return config if config else {}
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to MongoDB"""
        try:
            self.config.replace_one({}, config, upsert=True)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def close_connection(self):
        """Close MongoDB connection"""
        try:
            self.client.close()
        except Exception as e:
            print(f"Error closing connection: {e}")

# Global database instance
db = DatabaseManager()

# Convenience functions for backward compatibility
def load_json(filepath: str, default=None):
    """Backward compatibility function - maps to appropriate MongoDB collection"""
    if filepath == "senders.json":
        return db.load_senders()
    elif filepath == "campaigns.json":
        return db.load_campaigns()
    elif filepath == "sent_log.json":
        return db.load_history("global")  # Global history
    elif filepath == "email_logs.json":
        return db.load_email_logs()
    elif filepath == "config.json":
        return db.load_config()
    else:
        return default

def save_json(filepath: str, data):
    """Backward compatibility function - maps to appropriate MongoDB collection"""
    if filepath == "senders.json":
        return db.save_senders(data)
    elif filepath == "campaigns.json":
        return db.save_campaigns(data)
    elif filepath == "sent_log.json":
        return db.save_history("global", data)  # Global history
    elif filepath == "config.json":
        return db.save_config(data)
    else:
        return False
