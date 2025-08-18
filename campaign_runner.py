#!/usr/bin/env python3
"""
Background Campaign Runner Service
This service runs independently of the Streamlit web interface and handles:
- Campaign execution based on schedules
- Daily limit management
- Automatic daily resumption
- Campaign state persistence
"""

import time
import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from database import db
from email_sender import send_email
import pandas as pd
import threading
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('campaign_runner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CampaignRunner:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.running_campaigns = {}
        self.stop_event = threading.Event()
        
        # Start the scheduler
        self.scheduler.start()
        logger.info("Campaign Runner Service started")
    

    
    def shutdown(self):
        """Shutdown the campaign runner service"""
        logger.info("Shutting down Campaign Runner Service...")
        self.stop_event.set()
        
        # Stop all running campaigns
        for campaign_id in list(self.running_campaigns.keys()):
            self.stop_campaign(campaign_id)
        
        # Shutdown scheduler
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        
        logger.info("Campaign Runner Service shutdown complete")
    
    def start_campaign(self, campaign_id: str):
        """Start a campaign execution"""
        try:
            campaign = db.load_campaigns().get(campaign_id)
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return False
            
            if campaign['status'] != 'running':
                logger.info(f"Campaign {campaign_id} is not in running status")
                return False
            
            # Check if campaign is already running
            if campaign_id in self.running_campaigns:
                logger.info(f"Campaign {campaign_id} is already running")
                return True
            
            # Start campaign execution thread
            campaign_thread = threading.Thread(
                target=self._execute_campaign,
                args=(campaign_id,),
                daemon=True
            )
            campaign_thread.start()
            
            self.running_campaigns[campaign_id] = {
                'thread': campaign_thread,
                'started_at': datetime.datetime.now(),
                'status': 'running'
            }
            
            logger.info(f"Campaign {campaign_id} started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting campaign {campaign_id}: {e}")
            return False
    
    def stop_campaign(self, campaign_id: str):
        """Stop a running campaign"""
        try:
            if campaign_id in self.running_campaigns:
                # Update campaign status in database
                campaigns = db.load_campaigns()
                if campaign_id in campaigns:
                    campaigns[campaign_id]['status'] = 'paused'
                    db.save_campaigns(campaigns)
                
                # Remove from running campaigns
                del self.running_campaigns[campaign_id]
                logger.info(f"Campaign {campaign_id} stopped")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error stopping campaign {campaign_id}: {e}")
            return False
    
    def _execute_campaign(self, campaign_id: str):
        """Execute a campaign in a separate thread"""
        try:
            campaign = db.load_campaigns().get(campaign_id)
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found during execution")
                return
            
            logger.info(f"Starting execution of campaign: {campaign['name']}")
            
            # Load campaign data
            history = db.load_history(campaign_id)
            if not history:
                history = {
                    "sent": [],
                    "failed": [],
                    "processing": [],
                    "processing_timestamps": {},
                    "daily_sent_tracking": {}
                }
            
            # Load leads and template
            df_leads = db.get_csv_as_dataframe(campaign_id)
            html_template = db.get_email_template(campaign_id)
            
            if df_leads is None or html_template is None:
                logger.error(f"Failed to load leads or template for campaign {campaign_id}")
                self.stop_campaign(campaign_id)
                return
            
            # Apply deduplication to prevent sending duplicate emails
            df_leads = self._deduplicate_leads(df_leads, history, campaign_id)
            
            if df_leads.empty:
                logger.info(f"No unique leads to send for campaign {campaign_id}")
                self.stop_campaign(campaign_id)
                return
            
            # Load senders
            senders = db.load_senders()
            campaign_senders = [s for s in senders if s['email'] in campaign.get('selected_senders', [])]
            
            if not campaign_senders:
                logger.error(f"No valid senders found for campaign {campaign_id}")
                self.stop_campaign(campaign_id)
                return
            
            # Campaign execution loop
            while not self.stop_event.is_set() and campaign_id in self.running_campaigns:
                try:
                    # Check if campaign should run based on scheduling
                    if not self._should_run_campaign(campaign, history):
                        time.sleep(60)  # Wait 1 minute before checking again
                        continue
                    
                    # Execute email batch
                    emails_sent = self._send_email_batch(
                        campaign, campaign_id, history, df_leads, 
                        html_template, campaign_senders
                    )
                    
                    if emails_sent == 0:
                        # No more emails to send or daily limit reached
                        logger.info(f"Campaign {campaign_id} completed or paused")
                        break
                    
                    # Wait for delay between batches
                    delay = campaign.get('delay', 30)
                    time.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"Error during campaign execution {campaign_id}: {e}")
                    time.sleep(60)  # Wait before retrying
            
            # Campaign execution finished
            if campaign_id in self.running_campaigns:
                self.stop_campaign(campaign_id)
            
            logger.info(f"Campaign {campaign_id} execution completed")
            
        except Exception as e:
            logger.error(f"Fatal error in campaign execution {campaign_id}: {e}")
            self.stop_campaign(campaign_id)
    
    def _deduplicate_leads(self, df_leads, history: dict, campaign_id: str):
        """Remove duplicate emails and already processed emails from leads"""
        try:
            import pandas as pd
            
            # Get already processed emails
            sent_emails = set(history.get("sent", []))
            failed_emails = set(history.get("failed", []))
            processing_emails = set(history.get("processing", []))
            
            # Create comprehensive blacklist
            blacklisted_emails = sent_emails | failed_emails | processing_emails
            
            # Normalize and deduplicate leads
            unique_leads = []
            seen_emails = set()
            
            for _, row in df_leads.iterrows():
                email = str(row.get('email', '')).strip().lower()
                if email and email not in seen_emails and email not in blacklisted_emails:
                    unique_leads.append(row)
                    seen_emails.add(email)
                elif email in seen_emails:
                    logger.info(f"⚠️ Duplicate email in leads for campaign {campaign_id}: {email}")
                elif email in blacklisted_emails:
                    logger.info(f"⚠️ Email already processed for campaign {campaign_id}: {email}")
            
            # Create new DataFrame with unique leads
            df_unique = pd.DataFrame(unique_leads)
            
            logger.info(f"📊 Campaign {campaign_id} deduplication: {len(df_unique)} unique leads out of {len(df_leads)} total")
            
            return df_unique
            
        except Exception as e:
            logger.error(f"Error during deduplication for campaign {campaign_id}: {e}")
            return df_leads  # Return original if deduplication fails
    
    def _should_run_campaign(self, campaign: dict, history: dict) -> bool:
        """Check if campaign should run based on scheduling and limits"""
        try:
            current_datetime = datetime.datetime.now()
            today = current_datetime.date().isoformat()
            
            # Get daily sent count
            daily_sent = history.get("daily_sent_tracking", {}).get(today, 0)
            daily_limit = campaign.get('daily_limit', 120)
            
            # Check daily limit
            if daily_sent >= daily_limit:
                logger.info(f"Daily limit reached for campaign {campaign['id']}: {daily_sent}/{daily_limit}")
                return False
            
            # Check scheduling
            if campaign.get('schedule_enabled'):
                # Daily schedule
                current_time = current_datetime.time()
                try:
                    schedule_time = datetime.datetime.strptime(
                        campaign.get('schedule_time', '10:00'), 
                        "%H:%M"
                    ).time()
                    
                    if current_time < schedule_time:
                        return False
                except ValueError:
                    logger.error(f"Invalid schedule time for campaign {campaign['id']}")
                    return False
            
            elif campaign.get('scheduled_date'):
                # Specific date schedule
                try:
                    scheduled_datetime = datetime.datetime.strptime(
                        f"{campaign['scheduled_date']} {campaign.get('schedule_time', '10:00')}", 
                        "%Y-%m-%d %H:%M"
                    )
                    
                    if current_datetime < scheduled_datetime:
                        return False
                    
                    # Clear scheduled date after first run
                    campaigns = db.load_campaigns()
                    if campaign['id'] in campaigns:
                        campaigns[campaign['id']]['scheduled_date'] = None
                        db.save_campaigns(campaigns)
                        
                except ValueError:
                    logger.error(f"Invalid scheduled date for campaign {campaign['id']}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking campaign run conditions: {e}")
            return False
    
    def _send_email_batch(self, campaign: dict, campaign_id: str, history: dict, 
                          df_leads: pd.DataFrame, html_template: str, 
                          campaign_senders: list) -> int:
        """Send a batch of emails for the campaign"""
        try:
            emails_sent = 0
            batch_size = min(10, campaign.get('daily_limit', 120) - 
                           history.get("daily_sent_tracking", {}).get(
                               datetime.date.today().isoformat(), 0
                           ))
            
            if batch_size <= 0:
                return 0
            
            # Get emails to send
            sent_emails = set(history.get("sent", []))
            failed_emails = set(history.get("failed", []))
            processing_emails = set(history.get("processing", []))
            blacklisted_emails = sent_emails | failed_emails | processing_emails
            
            # Find next emails to send
            for idx, row in df_leads.iterrows():
                if emails_sent >= batch_size:
                    break
                
                # Get email from the first column or 'email' column
                email = None
                if 'email' in row.index:
                    email = str(row['email']).strip().lower()
                elif 'Emails' in row.index:
                    email = str(row['Emails']).strip().lower()
                else:
                    # Try to find email in any column
                    for col in row.index:
                        if 'email' in col.lower():
                            email = str(row[col]).strip().lower()
                            break
                
                if not email or email in blacklisted_emails:
                    continue
                
                # Mark as processing
                processing_emails.add(email)
                if "processing_timestamps" not in history:
                    history["processing_timestamps"] = {}
                history["processing_timestamps"][email] = datetime.datetime.now().isoformat()
                
                # Select sender (round-robin)
                sender_index = (len(sent_emails) + emails_sent) % len(campaign_senders)
                sender = campaign_senders[sender_index]
                
                # Personalize template
                personalized_template = html_template
                for column in row.index:
                    placeholder = f"{{{{{column}}}}}"
                    if placeholder in personalized_template:
                        personalized_template = personalized_template.replace(
                            placeholder, str(row[column])
                        )
                
                # Send email
                subject = campaign.get('subject_line', 'Your Subject Here')
                success = send_email(
                    sender['email'], sender['password'], 
                    email, subject, personalized_template
                )
                
                # Update status
                processing_emails.remove(email)
                if email in history["processing_timestamps"]:
                    del history["processing_timestamps"][email]
                
                if success:
                    sent_emails.add(email)
                    emails_sent += 1
                    logger.info(f"Email sent successfully to {email} via {sender['email']}")
                else:
                    failed_emails.add(email)
                    logger.error(f"Failed to send email to {email}")
                
                # Update daily tracking
                today = datetime.date.today().isoformat()
                if "daily_sent_tracking" not in history:
                    history["daily_sent_tracking"] = {}
                if today not in history["daily_sent_tracking"]:
                    history["daily_sent_tracking"][today] = 0
                history["daily_sent_tracking"][today] += 1
                
                # Update history
                history.update({
                    "sent": list(sent_emails),
                    "failed": list(failed_emails),
                    "processing": list(processing_emails)
                })
                db.save_history(campaign_id, history)
                
                # Update campaign stats
                campaigns = db.load_campaigns()
                if campaign_id in campaigns:
                    campaigns[campaign_id]['stats']['total_sent'] = len(sent_emails)
                    campaigns[campaign_id]['stats']['total_failed'] = len(failed_emails)
                    db.save_campaigns(campaigns)
                
                # Small delay between emails
                time.sleep(1)
            
            return emails_sent
            
        except Exception as e:
            logger.error(f"Error sending email batch for campaign {campaign_id}: {e}")
            return 0
    
    def schedule_campaign(self, campaign_id: str):
        """Schedule a campaign to run based on its settings"""
        try:
            campaign = db.load_campaigns().get(campaign_id)
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found for scheduling")
                return False
            
            # Remove existing schedule if any
            try:
                self.scheduler.remove_job(f"campaign_{campaign_id}")
            except:
                pass
            
            if campaign.get('schedule_enabled'):
                # Daily schedule
                schedule_time = campaign.get('schedule_time', '10:00')
                hour, minute = map(int, schedule_time.split(':'))
                
                job = self.scheduler.add_job(
                    func=self.start_campaign,
                    trigger=CronTrigger(hour=hour, minute=minute),
                    args=[campaign_id],
                    id=f"campaign_{campaign_id}",
                    name=f"Daily Campaign {campaign['name']}",
                    replace_existing=True
                )
                
                logger.info(f"Campaign {campaign_id} scheduled daily at {schedule_time}")
                
            elif campaign.get('scheduled_date'):
                # Specific date schedule
                scheduled_datetime = datetime.datetime.strptime(
                    f"{campaign['scheduled_date']} {campaign.get('schedule_time', '10:00')}", 
                    "%Y-%m-%d %H:%M"
                )
                
                job = self.scheduler.add_job(
                    func=self.start_campaign,
                    trigger=DateTrigger(run_date=scheduled_datetime),
                    args=[campaign_id],
                    id=f"campaign_{campaign_id}",
                    name=f"Scheduled Campaign {campaign['name']}",
                    replace_existing=True
                )
                
                logger.info(f"Campaign {campaign_id} scheduled for {scheduled_datetime}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling campaign {campaign_id}: {e}")
            return False
    
    def load_and_schedule_campaigns(self):
        """Load all campaigns from database and schedule them"""
        try:
            campaigns = db.load_campaigns()
            for campaign_id, campaign in campaigns.items():
                if campaign['status'] == 'running':
                    # Start immediately if it's a running campaign
                    self.start_campaign(campaign_id)
                elif campaign.get('schedule_enabled') or campaign.get('scheduled_date'):
                    # Schedule future runs
                    self.schedule_campaign(campaign_id)
            
            logger.info(f"Loaded and scheduled {len(campaigns)} campaigns")
            
        except Exception as e:
            logger.error(f"Error loading and scheduling campaigns: {e}")
    
    def get_status(self) -> dict:
        """Get current status of the campaign runner"""
        return {
            'running_campaigns': len(self.running_campaigns),
            'scheduled_jobs': len(self.scheduler.get_jobs()),
            'scheduler_running': self.scheduler.running,
            'campaigns': [
                {
                    'id': campaign_id,
                    'status': info['status'],
                    'started_at': info['started_at'].isoformat() if info['started_at'] else None
                }
                for campaign_id, info in self.running_campaigns.items()
            ]
        }

# Global campaign runner instance
campaign_runner = None

def start_campaign_runner():
    """Start the global campaign runner service"""
    global campaign_runner
    if campaign_runner is None:
        campaign_runner = CampaignRunner()
        campaign_runner.load_and_schedule_campaigns()
    return campaign_runner

def get_campaign_runner():
    """Get the global campaign runner instance"""
    return campaign_runner

if __name__ == "__main__":
    # Run as standalone service
    runner = start_campaign_runner()
    
    try:
        # Keep the service running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nReceived interrupt, shutting down...")
        runner.shutdown()
