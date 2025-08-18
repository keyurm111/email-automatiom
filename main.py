import streamlit as st
import pandas as pd
import time
import os
import datetime
import threading
import uuid
from email_sender import send_email, check_sender_health, validate_app_password
from database import db, load_json, save_json
from campaign_runner import start_campaign_runner

SENDER_FILE = "senders.json"
HISTORY_FILE = "sent_log.json"
CONFIG_FILE = "config.json"
CAMPAIGNS_FILE = "campaigns.json"

st.set_page_config(page_title="Bulk Email Automation", layout="wide")
st.title("📧 Bulk Email Automation System")

# Initialize session state
if 'campaign_running' not in st.session_state:
    st.session_state.campaign_running = False
if 'current_campaign_id' not in st.session_state:
    st.session_state.current_campaign_id = None
if 'show_campaign_details' not in st.session_state:
    st.session_state.show_campaign_details = None

# Initialize background campaign runner
try:
    # Only start campaign runner if not already running
    if 'campaign_runner_ready' not in st.session_state:
        campaign_runner = start_campaign_runner()
        st.session_state.campaign_runner_ready = True
        st.session_state.campaign_runner = campaign_runner
except Exception as e:
    st.error(f"Failed to start campaign runner: {e}")
    st.session_state.campaign_runner_ready = False
    st.session_state.campaign_runner = None

# Sidebar for navigation
st.sidebar.title("🎯 Navigation")
page = st.sidebar.selectbox(
    "Choose a section:",
    ["🏠 Dashboard", "📧 Manage Senders", "📋 Manage Campaigns", "🎯 Active Campaign", "📊 Analytics"]
)

# Load data
senders = load_json(SENDER_FILE, [])
campaigns = load_json(CAMPAIGNS_FILE, {})

# Clean up invalid session state references
if st.session_state.get('show_campaign_details') and st.session_state.show_campaign_details not in campaigns:
    st.session_state.show_campaign_details = None

if st.session_state.get('current_campaign_id') and st.session_state.current_campaign_id not in campaigns:
    st.session_state.current_campaign_id = None
    st.session_state.campaign_running = False

# Dashboard Page
if page == "🏠 Dashboard":
    st.header("🏠 Dashboard")
    
    # App password information
    with st.expander("💡 Important: App Password Information", expanded=False):
        st.markdown("""
        **Gmail App Passwords:**
        - ✅ **Spaces are allowed** in app passwords and will be preserved
        - ✅ Use Gmail app passwords (not your regular Gmail password)
        - ✅ Enable 2-factor authentication first to generate app passwords
        - ✅ App passwords are typically 16 characters long
        - ❌ Don't use your regular Gmail password
        
        **How to get an App Password:**
        1. Go to your Google Account settings
        2. Enable 2-factor authentication
        3. Go to Security → App passwords
        4. Generate a new app password for "Mail"
        5. Copy the 16-character password (spaces included)
        """)
    
    # Campaign Runner Status
    if st.session_state.get('campaign_runner_ready'):
        campaign_runner = st.session_state.get('campaign_runner')
        if campaign_runner:
            runner_status = campaign_runner.get_status()
            
            with st.expander("🔄 Background Campaign Runner Status", expanded=False):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Service Status", "🟢 Running" if runner_status['scheduler_running'] else "🔴 Stopped")
                
                with col2:
                    st.metric("Running Campaigns", runner_status['running_campaigns'])
                
                with col3:
                    st.metric("Scheduled Jobs", runner_status['scheduled_jobs'])
                
                with col4:
                    if runner_status['running_campaigns'] > 0:
                        st.metric("Active Campaigns", runner_status['running_campaigns'])
                    else:
                        st.metric("Active Campaigns", 0)
                
                # Show running campaign details
                if runner_status['campaigns']:
                    st.write("**Currently Running Campaigns:**")
                    for campaign_info in runner_status['campaigns']:
                        st.write(f"• Campaign ID: {campaign_info['id'][:8]}... | Started: {campaign_info['started_at']}")
                
                # Manual controls
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Refresh Status"):
                        st.rerun()
                
                with col2:
                    if st.button("📊 View Logs"):
                        st.session_state.show_runner_logs = True
        else:
            st.warning("⚠️ Campaign Runner not available")
    else:
        st.error("❌ Campaign Runner failed to start")
    
    # Quick stats with real-time updates
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Senders", len(senders))
    
    with col2:
        st.metric("Total Campaigns", len(campaigns))
    
    with col3:
        active_campaigns = sum(1 for c in campaigns.values() if c['status'] == 'running')
        st.metric("Active Campaigns", active_campaigns)
    
    with col4:
        # Calculate real-time total sent from history
        total_sent = 0
        total_failed = 0
        total_pending = 0
        
        for campaign_id, campaign in campaigns.items():
            history = load_json(HISTORY_FILE, {})
            campaign_history = history.get(campaign_id, {})
            
            sent_count = len(campaign_history.get("sent", []))
            failed_count = len(campaign_history.get("failed", []))
            leads_count = campaign['stats']['total_leads']
            
            total_sent += sent_count
            total_failed += failed_count
            total_pending += max(0, leads_count - sent_count - failed_count)
        
        st.metric("Total Emails Sent", total_sent)
    
    # Additional real-time stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Failed", total_failed)
    
    with col2:
        st.metric("Pending Emails", total_pending)
    
    with col3:
        total_leads = sum(c['stats']['total_leads'] for c in campaigns.values())
        success_rate = (total_sent / total_leads * 100) if total_leads > 0 else 0
        st.metric("Success Rate", f"{success_rate:.1f}%")
    
    with col4:
        completion_rate = ((total_sent + total_failed) / total_leads * 100) if total_leads > 0 else 0
        st.metric("Completion Rate", f"{completion_rate:.1f}%")
    
    # Quick actions
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Add New Sender", use_container_width=True):
            st.session_state.show_add_sender = True
            st.rerun()
    
    with col2:
        if st.button("📋 Create New Campaign", use_container_width=True):
            st.session_state.show_create_campaign = True
            st.rerun()
    
    with col3:
        if st.button("📤 Send Test Email", use_container_width=True):
            st.session_state.show_test_email = True
            st.rerun()
    
    # Recent activity
    st.subheader("📈 Recent Activity")
    
    if campaigns:
        for campaign_id, campaign in list(campaigns.items())[-3:]:  # Show last 3 campaigns
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(f"**{campaign['name']}**")
                    st.write(f"Status: {campaign['status'].title()}")
                    if campaign['stats']['total_leads'] > 0:
                        progress = campaign['stats']['total_sent'] / campaign['stats']['total_leads']
                        st.progress(progress)
                        st.write(f"Progress: {campaign['stats']['total_sent']}/{campaign['stats']['total_leads']} sent")
                
                with col2:
                    if st.button("▶️ Start", key=f"quick_start_{campaign_id}"):
                        if len(campaign['selected_senders']) == 0:
                            st.error("No senders selected!")
                        elif not campaign.get('leads_file_id'):
                            st.error("No leads uploaded!")
                        elif not campaign.get('template_file_id'):
                            st.error("No template uploaded!")
                        else:
                            # Start campaign using background runner
                            if st.session_state.get('campaign_runner_ready'):
                                campaign_runner = st.session_state.get('campaign_runner')
                                if campaign_runner and campaign_runner.start_campaign(campaign_id):
                                    campaigns[campaign_id]['status'] = 'running'
                                    save_json(CAMPAIGNS_FILE, campaigns)
                                    st.success(f"✅ Campaign '{campaign['name']}' started in background")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to start campaign in background")
                            else:
                                st.error("❌ Background campaign runner not available")
                
                with col3:
                    if st.button("⚙️ Manage", key=f"quick_manage_{campaign_id}"):
                        st.session_state.show_campaign_details = campaign_id
                        st.rerun()
    else:
        st.info("No campaigns yet. Create your first campaign!")
    
    # Real-time campaign progress
    if campaigns:
        st.subheader("📊 Live Campaign Progress")
        
        # Create progress cards for each campaign
        for campaign_id, campaign in campaigns.items():
            history = load_json(HISTORY_FILE, {})
            campaign_history = history.get(campaign_id, {})
            
            sent_count = len(campaign_history.get("sent", []))
            failed_count = len(campaign_history.get("failed", []))
            leads_count = campaign['stats']['total_leads']
            pending_count = max(0, leads_count - sent_count - failed_count)
            
            # Calculate progress
            progress = ((sent_count + failed_count) / leads_count) if leads_count > 0 else 0
            success_rate = (sent_count / leads_count * 100) if leads_count > 0 else 0
            
            # Get daily progress
            today = datetime.date.today().isoformat()
            daily_sent = campaign_history.get("daily_sent_tracking", {}).get(today, 0)
            daily_limit = campaign.get('daily_limit', 120)
            
            with st.container():
                st.markdown("---")
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.write(f"**{campaign['name']}**")
                    st.write(f"Status: {campaign['status'].title()}")
                    
                    # Progress bar
                    st.progress(progress)
                    st.write(f"Progress: {progress:.1%}")
                
                with col2:
                    st.write("**📊 Metrics**")
                    st.write(f"Sent: {sent_count}")
                    st.write(f"Failed: {failed_count}")
                    st.write(f"Pending: {pending_count}")
                
                with col3:
                    st.write("**📈 Performance**")
                    st.write(f"Success Rate: {success_rate:.1f}%")
                    st.write(f"Today: {daily_sent}/{daily_limit}")
                    
                    # Daily progress bar
                    daily_progress = daily_sent / daily_limit if daily_limit > 0 else 0
                    st.progress(daily_progress)
                
                with col4:
                    if campaign['status'] == 'running':
                        st.success("🟢 Running")
                    elif campaign['status'] == 'paused':
                        st.warning("🟡 Paused")
                    elif campaign['status'] == 'completed':
                        st.info("🔵 Completed")
                    else:
                        st.info("⚪ Ready")
                    
                    if st.button("📋 Details", key=f"details_{campaign_id}"):
                        st.session_state.show_campaign_details = campaign_id
                        st.rerun()

# Manage Senders Page
elif page == "📧 Manage Senders":
    st.header("📧 Manage Sender Emails")
    
    # Add new sender
    with st.expander("➕ Add New Sender", expanded=False):
        with st.form("add_sender_form"):
            sender_email = st.text_input("Sender Email")
            sender_pass = st.text_input("App Password", type="password", help="Enter your Gmail app password. Spaces are allowed and will be preserved.")
            st.info("💡 **App Password Tips:**\n- Use Gmail app passwords (not your regular password)\n- Spaces in app passwords are allowed and should be preserved\n- Enable 2-factor authentication first to generate app passwords")
            
            if st.form_submit_button("Add Sender"):
                if sender_email and sender_pass:
                    # Validate app password
                    is_valid, validation_msg = validate_app_password(sender_pass)
                    if not is_valid:
                        st.error(f"❌ {validation_msg}")
                        st.stop()
                    
                    if any(sender['email'] == sender_email for sender in senders):
                        st.error(f"Email {sender_email} already exists!")
                    else:
                        senders.append({"email": sender_email, "password": sender_pass})
                        save_json(SENDER_FILE, senders)
                        st.success(f"✅ Added {sender_email}")
                        st.rerun()
                else:
                    st.error("Please enter both email and password")
    
    # Display senders
    if senders:
        st.subheader("📧 Your Sender Emails")
        
        for i, sender in enumerate(senders):
            with st.container():
                st.markdown("---")
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    # Show password info (spaces indicator)
                    password_info = ""
                    if ' ' in sender['password']:
                        password_info = " (contains spaces)"
                    st.write(f"**{sender['email']}**{password_info}")
                
                with col2:
                    if st.button("🔍 Test", key=f"test_{i}"):
                        if check_sender_health(sender['email'], sender['password']):
                            st.success("✅ Healthy")
                        else:
                            st.error("❌ Issues")
                
                with col3:
                    if st.button("✏️ Edit", key=f"edit_{i}"):
                        st.session_state.editing_sender = i
                        st.rerun()
                
                with col4:
                    if st.button("🗑️ Delete", key=f"delete_{i}"):
                        senders.pop(i)
                        save_json(SENDER_FILE, senders)
                        st.success(f"✅ Deleted {sender['email']}")
                        st.rerun()
                
                # Edit mode
                if st.session_state.get('editing_sender') == i:
                    with st.form(key=f"edit_sender_{i}"):
                        new_email = st.text_input("Email", value=sender['email'])
                        new_password = st.text_input("App Password", type="password", value=sender['password'], help="Enter your Gmail app password. Spaces are allowed and will be preserved.")
                        st.info("💡 **App Password Tips:**\n- Use Gmail app passwords (not your regular password)\n- Spaces in app passwords are allowed and should be preserved\n- Enable 2-factor authentication first to generate app passwords")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Save"):
                                # Validate app password
                                is_valid, validation_msg = validate_app_password(new_password)
                                if not is_valid:
                                    st.error(f"❌ {validation_msg}")
                                    st.stop()
                                
                                senders[i]['email'] = new_email
                                senders[i]['password'] = new_password
                                save_json(SENDER_FILE, senders)
                                st.success(f"✅ Updated {new_email}")
                                st.session_state.editing_sender = None
                                st.rerun()
                        
                        with col2:
                            if st.form_submit_button("❌ Cancel"):
                                st.session_state.editing_sender = None
                                st.rerun()
    else:
        st.info("No senders added yet. Add your first sender email above.")

# Manage Campaigns Page
elif page == "📋 Manage Campaigns":
    st.header("📋 Manage Campaigns")
    
    # Create new campaign
    with st.expander("➕ Create New Campaign", expanded=False):
        with st.form("create_campaign_form"):
            campaign_name = st.text_input("Campaign Name", placeholder="e.g., Q4 Newsletter")
            campaign_description = st.text_area("Description", placeholder="Describe your campaign...")
            
            if st.form_submit_button("Create Campaign"):
                if campaign_name:
                    campaign_id = str(uuid.uuid4())
                    campaign_data = {
                        "id": campaign_id,
                        "name": campaign_name,
                        "description": campaign_description,
                        "created_at": datetime.datetime.now().isoformat(),
                        "status": "draft",
                        "selected_senders": [],
                        "leads_file": None,
                        "template_file": None,
                        "subject_line": "",
                        "daily_limit": 120,
                        "delay": 30,
                        "schedule_enabled": False,
                        "schedule_time": "10:00",
                        "scheduled_date": None,
                        "stats": {"total_sent": 0, "total_failed": 0, "total_leads": 0}
                    }
                    campaigns[campaign_id] = campaign_data
                    save_json(CAMPAIGNS_FILE, campaigns)
                    st.success(f"✅ Campaign '{campaign_name}' created!")
                    st.rerun()
                else:
                    st.error("Please enter campaign name")
    
    # Display campaigns
    if campaigns:
        st.subheader("📋 Your Campaigns")
        
        for campaign_id, campaign in campaigns.items():
            with st.container():
                st.markdown("---")
                
                # Campaign header
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.write(f"**{campaign['name']}**")
                    if campaign.get('description'):
                        st.write(f"*{campaign['description']}*")
                    
                    # Status and progress
                    status_color = {"draft": "⚪", "running": "🟢", "paused": "🟡", "completed": "🔵"}
                    st.write(f"{status_color.get(campaign['status'], '⚪')} {campaign['status'].title()}")
                    
                    # Show scheduling info
                    if campaign.get('schedule_enabled'):
                        st.write(f"📅 Daily: {campaign['schedule_time']}")
                    elif campaign.get('scheduled_date'):
                        scheduled_datetime = datetime.datetime.strptime(f"{campaign['scheduled_date']} {campaign['schedule_time']}", "%Y-%m-%d %H:%M")
                        st.write(f"📅 Scheduled: {scheduled_datetime.strftime('%b %d, %I:%M %p')}")
                    else:
                        st.write("🚀 Ready to start")
                    
                    if campaign['stats']['total_leads'] > 0:
                        progress = campaign['stats']['total_sent'] / campaign['stats']['total_leads']
                        st.progress(progress)
                        st.write(f"📊 {campaign['stats']['total_sent']}/{campaign['stats']['total_leads']} sent")
                
                with col2:
                    if st.button("⚙️ Setup", key=f"setup_{campaign_id}"):
                        st.session_state.show_campaign_details = campaign_id
                        st.rerun()
                
                with col3:
                    if st.button("▶️ Start", key=f"start_{campaign_id}"):
                        if len(campaign['selected_senders']) == 0:
                            st.error("No senders selected!")
                        elif not campaign.get('leads_file_id'):
                            st.error("No leads uploaded!")
                        elif not campaign.get('template_file_id'):
                            st.error("No template uploaded!")
                        else:
                            # Start campaign using background runner
                            if st.session_state.get('campaign_runner_ready'):
                                campaign_runner = st.session_state.get('campaign_runner')
                                if campaign_runner and campaign_runner.start_campaign(campaign_id):
                                    campaigns[campaign_id]['status'] = 'running'
                                    save_json(CAMPAIGNS_FILE, campaigns)
                                    st.success(f"✅ Campaign '{campaign['name']}' started in background")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to start campaign in background")
                            else:
                                st.error("❌ Background campaign runner not available")
                
                with col4:
                    if st.button("🗑️ Delete", key=f"delete_{campaign_id}"):
                        del campaigns[campaign_id]
                        save_json(CAMPAIGNS_FILE, campaigns)
                        st.success(f"✅ Campaign '{campaign['name']}' deleted")
                        st.rerun()
    else:
        st.info("No campaigns yet. Create your first campaign above!")

# Campaign Setup/Management
if st.session_state.get('show_campaign_details'):
    campaign_id = st.session_state.show_campaign_details
    
    # Check if campaign exists
    if campaign_id not in campaigns:
        st.error(f"❌ Campaign not found. It may have been deleted.")
        st.session_state.show_campaign_details = None
        st.rerun()
    
    campaign = campaigns[campaign_id]
    
    st.header(f"⚙️ Setup Campaign: {campaign['name']}")
    
    # Setup progress indicator
    setup_steps = [
        ("📧 Select Senders", len(campaign['selected_senders']) > 0),
        ("📊 Upload Leads", campaign.get('leads_file_id') is not None),
        ("📝 Upload Template", campaign.get('template_file_id') is not None),
        ("⚙️ Configure Settings", campaign.get('subject_line') != "")
    ]
    
    st.write("**Setup Progress:**")
    for step, completed in setup_steps:
        status = "✅" if completed else "⭕"
        st.write(f"{status} {step}")
    
    # Setup sections
    tab1, tab2, tab3, tab4 = st.tabs(["📧 Senders", "📊 Leads", "📝 Template", "⚙️ Settings"])
    
    with tab1:
        st.write("**Select Sender Emails for this Campaign:**")
        
        # Available senders
        available_senders = [s for s in senders if s['email'] not in campaign['selected_senders']]
        selected_senders = [s for s in senders if s['email'] in campaign['selected_senders']]
        
        if available_senders:
            st.write("**Available Senders:**")
            for sender in available_senders:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"📧 {sender['email']}")
                with col2:
                    if st.button("➕ Add", key=f"add_{sender['email']}"):
                        campaign['selected_senders'].append(sender['email'])
                        save_json(CAMPAIGNS_FILE, campaigns)
                        st.success(f"✅ Added {sender['email']}")
                        st.rerun()
        
        if selected_senders:
            st.write("**Selected Senders:**")
            for sender in selected_senders:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"✅ {sender['email']}")
                with col2:
                    if st.button("➖ Remove", key=f"remove_{sender['email']}"):
                        campaign['selected_senders'].remove(sender['email'])
                        save_json(CAMPAIGNS_FILE, campaigns)
                        st.success(f"✅ Removed {sender['email']}")
                        st.rerun()
        
        if not selected_senders:
            st.info("No senders selected yet. Add senders from the available list above.")
    
    with tab2:
        st.write("**Upload Leads for this Campaign:**")
        
        if not campaign.get('leads_file_id'):
            leads_file = st.file_uploader("Upload CSV file with email addresses", type=["csv"])
            
            if leads_file:
                # Read CSV data once and store in MongoDB
                csv_content = leads_file.getbuffer()
                file_id = db.store_csv_leads(campaign_id, csv_content, leads_file.name)
                
                if file_id:
                    # Read CSV data for display (before getbuffer() consumed it)
                    leads_file.seek(0)  # Reset file pointer to beginning
                    df_leads = pd.read_csv(leads_file)
                    
                    campaign['leads_file_id'] = file_id
                    campaign['leads_filename'] = leads_file.name
                    campaign['stats']['total_leads'] = len(df_leads)
                    save_json(CAMPAIGNS_FILE, campaigns)
                    
                    st.success(f"✅ Uploaded {campaign['stats']['total_leads']} leads to MongoDB")
                    st.dataframe(df_leads.head())
                else:
                    st.error("❌ Failed to store leads in database")
        else:
            # Load leads from MongoDB
            df_leads = db.get_csv_as_dataframe(campaign_id)
            if df_leads is not None:
                st.success(f"✅ {len(df_leads)} leads loaded from MongoDB")
                st.dataframe(df_leads.head())
                
                if st.button("🗑️ Remove Leads"):
                    # Delete from MongoDB
                    if db.delete_file(campaign['leads_file_id']):
                        campaign['leads_file_id'] = None
                        campaign['leads_filename'] = None
                        campaign['stats']['total_leads'] = 0
                        save_json(CAMPAIGNS_FILE, campaigns)
                        st.success("✅ Leads removed from database")
                        st.rerun()
                    else:
                        st.error("❌ Failed to remove leads")
            else:
                st.error("❌ Failed to load leads from database")
                # Clear invalid reference
                campaign['leads_file_id'] = None
                campaign['leads_filename'] = None
                save_json(CAMPAIGNS_FILE, campaigns)
    
    with tab3:
        st.write("**Upload Email Template for this Campaign:**")
        
        if not campaign.get('template_file_id'):
            template_file = st.file_uploader("Upload HTML template", type=["html"])
            
            if template_file:
                # Read and store HTML template in MongoDB
                html_content = template_file.getbuffer()
                file_id = db.store_email_template(campaign_id, html_content, template_file.name)
                
                if file_id:
                    campaign['template_file_id'] = file_id
                    campaign['template_filename'] = template_file.name
                    save_json(CAMPAIGNS_FILE, campaigns)
                    st.success("✅ Template uploaded to MongoDB")
                else:
                    st.error("❌ Failed to store template in database")
        else:
            # Load template from MongoDB
            template_content = db.get_email_template(campaign_id)
            if template_content:
                st.success("✅ Template loaded from MongoDB")
                st.code(template_content[:500] + "..." if len(template_content) > 500 else template_content, language="html")
                
                if st.button("🗑️ Remove Template"):
                    # Delete from MongoDB
                    if db.delete_file(campaign['template_file_id']):
                        campaign['template_file_id'] = None
                        campaign['template_filename'] = None
                        save_json(CAMPAIGNS_FILE, campaigns)
                        st.success("✅ Template removed from database")
                        st.rerun()
                    else:
                        st.error("❌ Failed to remove template")
            else:
                st.error("❌ Failed to load template from database")
                # Clear invalid reference
                campaign['template_file_id'] = None
                campaign['template_filename'] = None
                save_json(CAMPAIGNS_FILE, campaigns)
    
    with tab4:
        st.write("**Campaign Settings:**")
        
        # Campaign start options (outside form for immediate response)
        st.write("**Campaign Start Options:**")
        start_option = st.radio(
            "Choose when to start:",
            ["Start Immediately", "Start Immediately + Daily Schedule", "Schedule for Specific Date", "Daily Schedule"],
            index=0 if not campaign.get('schedule_enabled') and not campaign.get('scheduled_date') and not campaign.get('start_immediate_daily') else (1 if campaign.get('start_immediate_daily') else (2 if campaign.get('scheduled_date') else 3)),
            key=f"start_option_{campaign_id}"
        )
        
        # Show scheduling inputs based on selection
        if start_option == "Start Immediately":
            campaign['schedule_enabled'] = False
            campaign['scheduled_date'] = None
            campaign['start_immediate_daily'] = False
            campaign['schedule_time'] = "10:00"
            st.info("🚀 Campaign will start immediately when launched")
        
        elif start_option == "Start Immediately + Daily Schedule":
            campaign['schedule_enabled'] = False
            campaign['scheduled_date'] = None
            campaign['start_immediate_daily'] = True
            daily_time = st.time_input(
                "Daily start time (for upcoming days)",
                value=datetime.datetime.strptime(campaign.get('schedule_time', '10:00'), "%H:%M").time(),
                key=f"immediate_daily_time_{campaign_id}"
            )
            campaign['schedule_time'] = daily_time.strftime("%H:%M")
            st.info(f"🚀 Campaign will start immediately today, then run daily at {daily_time.strftime('%I:%M %p')} starting tomorrow")
        
        elif start_option == "Schedule for Specific Date":
            campaign['schedule_enabled'] = False
            campaign['start_immediate_daily'] = False
            selected_date = st.date_input(
                "Select start date",
                value=datetime.datetime.strptime(campaign.get('scheduled_date', datetime.date.today().isoformat()), "%Y-%m-%d").date() if campaign.get('scheduled_date') else datetime.date.today(),
                key=f"date_{campaign_id}"
            )
            selected_time = st.time_input(
                "Select start time",
                value=datetime.datetime.strptime(campaign.get('schedule_time', '10:00'), "%H:%M").time(),
                key=f"time_{campaign_id}"
            )
            campaign['scheduled_date'] = selected_date.isoformat()
            campaign['schedule_time'] = selected_time.strftime("%H:%M")
            st.info(f"📅 Campaign scheduled for {selected_date.strftime('%B %d, %Y')} at {selected_time.strftime('%I:%M %p')}")
        
        elif start_option == "Daily Schedule":
            campaign['schedule_enabled'] = True
            campaign['scheduled_date'] = None
            campaign['start_immediate_daily'] = False
            daily_time = st.time_input(
                "Daily start time",
                value=datetime.datetime.strptime(campaign.get('schedule_time', '10:00'), "%H:%M").time(),
                key=f"daily_time_{campaign_id}"
            )
            campaign['schedule_time'] = daily_time.strftime("%H:%M")
            st.info(f"📅 Campaign will run daily at {daily_time.strftime('%I:%M %p')}")
        
        # Other settings in form
        with st.form("campaign_settings"):
            campaign['subject_line'] = st.text_input("Email Subject Line", value=campaign.get('subject_line', ''))
            campaign['daily_limit'] = st.number_input("Daily Limit (emails per account)", value=campaign.get('daily_limit', 120), min_value=1, max_value=500)
            campaign['delay'] = st.selectbox("Delay between emails (seconds)", [15, 30, 60, 120], index=[15, 30, 60, 120].index(campaign.get('delay', 30)))
            
            if st.form_submit_button("💾 Save Settings"):
                save_json(CAMPAIGNS_FILE, campaigns)
                st.success("✅ Settings saved!")
    
    # Close setup
    if st.button("❌ Close Setup"):
        st.session_state.show_campaign_details = None
        st.rerun()

# Active Campaign Page
elif page == "🎯 Active Campaign":
    st.header("🎯 Active Campaign")
    
    if st.session_state.get('current_campaign_id') and st.session_state.get('campaign_running', False):
        current_campaign_id = st.session_state.current_campaign_id
        
        # Check if campaign exists
        if current_campaign_id not in campaigns:
            st.error(f"❌ Active campaign not found. It may have been deleted.")
            st.session_state.current_campaign_id = None
            st.session_state.campaign_running = False
            st.rerun()
        
        current_campaign = campaigns[current_campaign_id]
        
        # Campaign info
        st.info(f"**Active Campaign:** {current_campaign.get('name', 'Unknown Campaign')}")
        subject_line = current_campaign.get('subject_line', 'No subject set')
        st.write(f"📧 Subject: {subject_line}")
        
        selected_senders = current_campaign.get('selected_senders', [])
        if selected_senders:
            st.write(f"📧 Senders: {', '.join(selected_senders)}")
        else:
            st.write("📧 Senders: No senders selected")
        
        delay = current_campaign.get('delay', 30)
        daily_limit = current_campaign.get('daily_limit', 120)
        st.write(f"⏱️ Delay: {delay}s | 📊 Daily Limit: {daily_limit}")
        
        # Show scheduling info
        schedule_time = current_campaign.get('schedule_time', '10:00')
        if current_campaign.get('schedule_enabled'):
            st.write(f"📅 Daily Schedule: {schedule_time}")
        elif current_campaign.get('start_immediate_daily'):
            st.write(f"🚀 Started immediately + Daily at {schedule_time}")
        elif current_campaign.get('scheduled_date'):
            try:
                scheduled_datetime = datetime.datetime.strptime(f"{current_campaign['scheduled_date']} {schedule_time}", "%Y-%m-%d %H:%M")
                st.write(f"📅 Scheduled for: {scheduled_datetime.strftime('%B %d, %Y at %I:%M %p')}")
            except (ValueError, KeyError):
                st.write("📅 Scheduled: Invalid date format")
        else:
            st.write("🚀 Ready to start immediately")
        
        # Controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("⏸️ Pause Campaign", use_container_width=True):
                # Stop campaign using background runner
                if st.session_state.get('campaign_runner_ready'):
                    campaign_runner = st.session_state.get('campaign_runner')
                    if campaign_runner and campaign_runner.stop_campaign(current_campaign_id):
                        st.success("⏸️ Campaign paused")
                        st.rerun()
                    else:
                        st.error("❌ Failed to pause campaign")
                else:
                    st.error("❌ Background campaign runner not available")
        
        with col2:
            if st.button("🔄 Reset Campaign", use_container_width=True):
                history = load_json(HISTORY_FILE, {})
                if current_campaign_id not in history:
                    history[current_campaign_id] = {}
                history[current_campaign_id]["sent"] = []
                history[current_campaign_id]["failed"] = []
                history[current_campaign_id]["processing"] = []
                history[current_campaign_id]["processing_timestamps"] = {}
                history[current_campaign_id]["daily_sent_tracking"] = {}
                save_json(HISTORY_FILE, history)
                
                campaigns[current_campaign_id]['stats']['total_sent'] = 0
                campaigns[current_campaign_id]['stats']['total_failed'] = 0
                save_json(CAMPAIGNS_FILE, campaigns)
                st.success("🔄 Campaign reset - all emails marked as unsent")
                st.rerun()
        
        with col3:
            if st.button("📊 View Analytics", use_container_width=True):
                st.session_state.show_analytics = True
                st.rerun()
        
        # Campaign execution
        if current_campaign.get('leads_file_id') and current_campaign.get('template_file_id'):
            st.subheader("📊 Campaign Progress")
            
            # Load campaign data
            history = load_json(HISTORY_FILE, {})
            if current_campaign_id not in history:
                history[current_campaign_id] = {}
            campaign_history = history[current_campaign_id]
            
            # Load leads from MongoDB
            df = db.get_csv_as_dataframe(current_campaign_id)
            if df is None:
                st.error("❌ Failed to load leads from database")
                st.stop()
            
            # Enhanced deduplication system with comprehensive tracking
            sent_emails = set(campaign_history.get("sent", []))
            failed_emails = set(campaign_history.get("failed", []))
            processing_emails = set(campaign_history.get("processing", []))
            
            # Remove any emails from processing that are older than 1 hour
            if "processing_timestamps" in campaign_history:
                current_time = datetime.datetime.now()
                valid_processing = {}
                for email, timestamp_str in campaign_history["processing_timestamps"].items():
                    try:
                        timestamp = datetime.datetime.fromisoformat(timestamp_str)
                        if (current_time - timestamp).total_seconds() < 3600:
                            valid_processing[email] = timestamp_str
                        else:
                            if email in processing_emails:
                                processing_emails.remove(email)
                    except:
                        pass
                campaign_history["processing_timestamps"] = valid_processing
            
            # Create comprehensive blacklist to prevent duplicates
            blacklisted_emails = sent_emails | failed_emails | processing_emails
            
            # Additional deduplication: Check for duplicate emails in leads
            unique_leads = []
            seen_emails = set()
            
            for _, row in df.iterrows():
                email = row.get('email', '').strip().lower()  # Normalize email
                if email and email not in seen_emails and email not in blacklisted_emails:
                    unique_leads.append(row)
                    seen_emails.add(email)
                elif email in seen_emails:
                    print(f"⚠️ Duplicate email in leads: {email}")
                elif email in blacklisted_emails:
                    print(f"⚠️ Email already processed: {email}")
            
            # Update DataFrame with unique leads only
            df = pd.DataFrame(unique_leads)
            print(f"📊 Deduplication: {len(df)} unique leads out of {len(df) + len(blacklisted_emails)} total")
            
            # Load template from MongoDB
            html_template = db.get_email_template(current_campaign_id)
            if html_template is None:
                st.error("❌ Failed to load template from database")
                st.stop()
            
            limit = current_campaign.get("daily_limit", 120)
            delay_sec = int(current_campaign.get("delay", 30))
            subject_line = current_campaign.get("subject_line", "Your Subject Here")
            
            # Calculate progress with proper daily tracking
            total_leads = len(df)
            sent_count = len(sent_emails)
            failed_count = len(failed_emails)
            processing_count = len(processing_emails)
            remaining = total_leads - len(blacklisted_emails)
            
            # Display deduplication info
            st.info(f"🔄 **Deduplication Active**: {len(blacklisted_emails)} emails already processed, {remaining} unique emails remaining")
            
            # Calculate daily sent based on today's date
            today = datetime.date.today().isoformat()
            if "daily_sent_tracking" not in campaign_history:
                campaign_history["daily_sent_tracking"] = {}
            
            # Reset daily count if it's a new day
            if today not in campaign_history["daily_sent_tracking"]:
                campaign_history["daily_sent_tracking"][today] = 0
            
            daily_sent = campaign_history["daily_sent_tracking"][today]
            
            # Progress display
            col1, col2 = st.columns(2)
            
            with col1:
                progress = min(sent_count / total_leads, 1.0) if total_leads > 0 else 0
                st.progress(progress)
                st.write(f"📊 Progress: {sent_count}/{total_leads} emails sent ({progress:.1%})")
                st.write(f"📅 Today's sent: {daily_sent}/{limit}")
            
            with col2:
                st.write(f"📋 Remaining: {remaining} emails")
                st.write(f"❌ Failed: {failed_count} | ⏳ Processing: {processing_count}")
            
            # Campaign execution logic based on scheduling
            should_send = False
            current_datetime = datetime.datetime.now()
            
            # Check if campaign should run based on scheduling
            if current_campaign.get('schedule_enabled'):
                # Daily schedule
                current_time = current_datetime.time()
                try:
                    schedule_time = datetime.datetime.strptime(current_campaign.get('schedule_time', '10:00'), "%H:%M").time()
                except ValueError:
                    schedule_time = datetime.datetime.strptime('10:00', "%H:%M").time()
                
                if current_time >= schedule_time:
                    if daily_sent < limit:
                        should_send = True
                        st.info(f"⏰ Daily schedule triggered - starting batch...")
                    else:
                        st.info(f"📊 Daily limit already reached ({daily_sent}/{limit}). Waiting for tomorrow.")
                else:
                    next_run = datetime.datetime.combine(datetime.date.today(), schedule_time)
                    time_until = next_run - current_datetime
                    st.info(f"⏰ Next daily run: {next_run.strftime('%I:%M %p, %B %d')}")
                    if daily_sent >= limit:
                        st.info(f"📊 Daily limit reached ({daily_sent}/{limit}). Will continue tomorrow.")
            
            elif current_campaign.get('start_immediate_daily'):
                # Start immediately + daily schedule
                current_time = current_datetime.time()
                try:
                    schedule_time = datetime.datetime.strptime(current_campaign.get('schedule_time', '10:00'), "%H:%M").time()
                except ValueError:
                    schedule_time = datetime.datetime.strptime('10:00', "%H:%M").time()
                
                # Check if this is the first run today (no emails sent yet)
                if daily_sent == 0:
                    should_send = True
                    st.info("🚀 Starting campaign immediately (first run today)...")
                elif current_time >= schedule_time:
                    if daily_sent < limit:
                        should_send = True
                        st.info(f"⏰ Daily schedule triggered - starting batch...")
                    else:
                        st.info(f"📊 Daily limit already reached ({daily_sent}/{limit}). Waiting for tomorrow.")
                else:
                    next_run = datetime.datetime.combine(datetime.date.today(), schedule_time)
                    time_until = next_run - current_datetime
                    st.info(f"⏰ Next daily run: {next_run.strftime('%I:%M %p, %B %d')}")
                    if daily_sent >= limit:
                        st.info(f"📊 Daily limit reached ({daily_sent}/{limit}). Will continue tomorrow.")
            
            elif current_campaign.get('scheduled_date'):
                # Specific date schedule
                try:
                    scheduled_datetime = datetime.datetime.strptime(f"{current_campaign['scheduled_date']} {current_campaign.get('schedule_time', '10:00')}", "%Y-%m-%d %H:%M")
                except ValueError:
                    st.error("Invalid scheduled date format")
                    should_send = False
                
                if current_datetime >= scheduled_datetime:
                    should_send = True
                    st.info(f"⏰ Scheduled time reached - starting campaign...")
                    # Clear scheduled date after first run
                    campaigns[current_campaign_id]['scheduled_date'] = None
                    save_json(CAMPAIGNS_FILE, campaigns)
                else:
                    time_until = scheduled_datetime - current_datetime
                    st.info(f"⏰ Scheduled for: {scheduled_datetime.strftime('%B %d, %Y at %I:%M %p')}")
                    st.info(f"⏰ Time remaining: {time_until.days}d {time_until.seconds//3600}h {(time_until.seconds%3600)//60}m")
            
            else:
                # Start immediately
                should_send = True
                st.info("🚀 Starting campaign immediately...")
            
            # Execute campaign if conditions are met
            if should_send:
                campaign_senders = current_campaign.get('selected_senders', [])
                selected_senders = [s for s in senders if s['email'] in campaign_senders]
                batch_sent = 0
                
                # Find the next email to send (skip already sent/failed emails)
                for idx, row in df.iterrows():
                    email = row['Emails']
                    
                    # Skip if already sent, failed, or processing
                    if email in blacklisted_emails:
                        continue
                    
                    # Check daily limit
                    if daily_sent + batch_sent >= limit:
                        st.info(f"📊 Daily limit reached ({limit} emails). Stopping for today.")
                        break
                    
                    # Mark as processing
                    processing_emails.add(email)
                    if "processing_timestamps" not in campaign_history:
                        campaign_history["processing_timestamps"] = {}
                    campaign_history["processing_timestamps"][email] = datetime.datetime.now().isoformat()
                    save_json(HISTORY_FILE, history)
                    
                    # Rotate through selected senders
                    sender_index = (sent_count + batch_sent) % len(selected_senders)
                    sender = selected_senders[sender_index]
                    st.write(f"Sending to {email} via {sender['email']}")
                    
                    # Personalize template
                    personalized_template = html_template
                    for column in row.index:
                        placeholder = f"{{{{{column}}}}}"
                        if placeholder in personalized_template:
                            personalized_template = personalized_template.replace(placeholder, str(row[column]))
                    
                    success = send_email(sender['email'], sender['password'], email, subject_line, personalized_template)
                    
                    # Update status
                    processing_emails.remove(email)
                    if "processing_timestamps" in campaign_history and email in campaign_history["processing_timestamps"]:
                        del campaign_history["processing_timestamps"][email]
                    
                    if success:
                        sent_emails.add(email)
                        batch_sent += 1
                        # Update daily tracking
                        campaign_history["daily_sent_tracking"][today] += 1
                        st.success(f"✅ Sent to {email}")
                    else:
                        failed_emails.add(email)
                        st.error(f"❌ Failed to send to {email}")
                    
                    # Update history
                    campaign_history.update({
                        "sent": list(sent_emails),
                        "failed": list(failed_emails),
                        "processing": list(processing_emails)
                    })
                    save_json(HISTORY_FILE, history)
                    
                    # Update campaign stats
                    campaigns[current_campaign_id]['stats']['total_sent'] = len(sent_emails)
                    campaigns[current_campaign_id]['stats']['total_failed'] = len(failed_emails)
                    save_json(CAMPAIGNS_FILE, campaigns)
                    
                    time.sleep(delay_sec)
                
                if batch_sent > 0:
                    st.success(f"🎉 Batch complete. Sent {batch_sent} emails today.")
                    st.info(f"📊 Daily progress: {daily_sent + batch_sent}/{limit} emails sent today")
                else:
                    st.info("📊 No new emails sent (daily limit reached or all emails processed)")
    else:
        st.info("📋 No active campaign. Go to 'Manage Campaigns' to start a campaign.")

# Campaign Runner Logs Page
elif page == "📊 Analytics":
    st.header("📊 Analytics")
    
    # Auto-refresh every 30 seconds
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    # Check if it's time to refresh
    current_time = time.time()
    if current_time - st.session_state.last_refresh > 30:  # Refresh every 30 seconds
        st.session_state.last_refresh = current_time
        st.rerun()
    
    # Show campaign runner logs if requested
    if st.session_state.get('show_runner_logs'):
        st.subheader("🔄 Campaign Runner Logs")
        
        try:
            with open('campaign_runner.log', 'r') as f:
                logs = f.readlines()
            
            # Show last 50 lines
            recent_logs = logs[-50:] if len(logs) > 50 else logs
            
            st.code(''.join(recent_logs), language='text')
            
            if st.button("❌ Close Logs"):
                st.session_state.show_runner_logs = False
                st.rerun()
                
        except FileNotFoundError:
            st.info("No log file found yet. Logs will appear here once campaigns start running.")
            if st.button("❌ Close"):
                st.session_state.show_runner_logs = False
                st.rerun()
    
    if campaigns:
        # Overall stats with real-time updates
        st.subheader("📈 Overall Statistics")
        
        # Calculate comprehensive stats
        total_sent = 0
        total_failed = 0
        total_leads = 0
        total_pending = 0
        running_campaigns = 0
        completed_campaigns = 0
        
        for campaign_id, campaign in campaigns.items():
            history = load_json(HISTORY_FILE, {})
            campaign_history = history.get(campaign_id, {})
            
            sent_count = len(campaign_history.get("sent", []))
            failed_count = len(campaign_history.get("failed", []))
            leads_count = campaign['stats']['total_leads']
            
            total_sent += sent_count
            total_failed += failed_count
            total_leads += leads_count
            total_pending += max(0, leads_count - sent_count - failed_count)
            
            if campaign['status'] == 'running':
                running_campaigns += 1
            elif campaign['status'] == 'completed':
                completed_campaigns += 1
        
        success_rate = (total_sent / total_leads * 100) if total_leads > 0 else 0
        completion_rate = (total_sent + total_failed) / total_leads * 100 if total_leads > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Sent", total_sent, delta=f"{total_sent - (st.session_state.get('last_total_sent', 0))}")
            st.session_state.last_total_sent = total_sent
        
        with col2:
            st.metric("Total Failed", total_failed, delta=f"{total_failed - (st.session_state.get('last_total_failed', 0))}")
            st.session_state.last_total_failed = total_failed
        
        with col3:
            st.metric("Success Rate", f"{success_rate:.1f}%", delta=f"{success_rate - (st.session_state.get('last_success_rate', 0)):.1f}%")
            st.session_state.last_success_rate = success_rate
        
        with col4:
            st.metric("Total Campaigns", len(campaigns))
        
        # Additional stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Pending Emails", total_pending)
        
        with col2:
            st.metric("Running Campaigns", running_campaigns)
        
        with col3:
            st.metric("Completed Campaigns", completed_campaigns)
        
        with col4:
            st.metric("Completion Rate", f"{completion_rate:.1f}%")
        
        # Campaign-specific analytics with detailed progress
        st.subheader("📊 Campaign Progress Dashboard")
        
        # Create a comprehensive campaign table
        campaign_data = []
        for campaign_id, campaign in campaigns.items():
            history = load_json(HISTORY_FILE, {})
            campaign_history = history.get(campaign_id, {})
            
            sent_count = len(campaign_history.get("sent", []))
            failed_count = len(campaign_history.get("failed", []))
            leads_count = campaign['stats']['total_leads']
            pending_count = max(0, leads_count - sent_count - failed_count)
            
            # Calculate progress percentage
            progress = ((sent_count + failed_count) / leads_count * 100) if leads_count > 0 else 0
            success_rate = (sent_count / leads_count * 100) if leads_count > 0 else 0
            
            # Get daily progress
            today = datetime.date.today().isoformat()
            daily_sent = campaign_history.get("daily_sent_tracking", {}).get(today, 0)
            daily_limit = campaign.get('daily_limit', 120)
            
            campaign_data.append({
                'ID': campaign_id[:8] + '...',
                'Name': campaign['name'],
                'Status': campaign['status'].title(),
                'Total Leads': leads_count,
                'Sent': sent_count,
                'Failed': failed_count,
                'Pending': pending_count,
                'Progress': f"{progress:.1f}%",
                'Success Rate': f"{success_rate:.1f}%",
                'Today Sent': f"{daily_sent}/{daily_limit}",
                'Daily Limit': daily_limit
            })
        
        # Display campaign table
        if campaign_data:
            df_campaigns = pd.DataFrame(campaign_data)
            st.dataframe(df_campaigns, use_container_width=True)
        
        # Detailed campaign analysis
        st.subheader("🔍 Detailed Campaign Analysis")
        
        for campaign_id, campaign in campaigns.items():
            with st.expander(f"📋 {campaign['name']} - {campaign['status'].title()}", expanded=False):
                history = load_json(HISTORY_FILE, {})
                campaign_history = history.get(campaign_id, {})
                
                sent_count = len(campaign_history.get("sent", []))
                failed_count = len(campaign_history.get("failed", []))
                leads_count = campaign['stats']['total_leads']
                pending_count = max(0, leads_count - sent_count - failed_count)
                
                # Progress visualization
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**📊 Progress Overview**")
                    
                    # Progress bar
                    progress = ((sent_count + failed_count) / leads_count) if leads_count > 0 else 0
                    st.progress(progress)
                    st.write(f"Overall Progress: {progress:.1%}")
                    
                    # Metrics
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Sent", sent_count)
                    with col_b:
                        st.metric("Failed", failed_count)
                    with col_c:
                        st.metric("Pending", pending_count)
                
                with col2:
                    st.write("**📈 Performance Metrics**")
                    
                    success_rate = (sent_count / leads_count * 100) if leads_count > 0 else 0
                    failure_rate = (failed_count / leads_count * 100) if leads_count > 0 else 0
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Success Rate", f"{success_rate:.1f}%")
                    with col_b:
                        st.metric("Failure Rate", f"{failure_rate:.1f}%")
                    
                    # Daily progress
                    today = datetime.date.today().isoformat()
                    daily_sent = campaign_history.get("daily_sent_tracking", {}).get(today, 0)
                    daily_limit = campaign.get('daily_limit', 120)
                    
                    st.write(f"**📅 Today's Progress: {daily_sent}/{daily_limit}**")
                    daily_progress = daily_sent / daily_limit if daily_limit > 0 else 0
                    st.progress(daily_progress)
                
                # Recent activity
                st.write("**📧 Recent Activity**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if campaign_history.get("sent"):
                        st.write("**✅ Recently Sent:**")
                        for email in campaign_history["sent"][-10:]:
                            st.write(f"  • {email}")
                    else:
                        st.write("**✅ Sent:** No emails sent yet")
                
                with col2:
                    if campaign_history.get("failed"):
                        st.write("**❌ Recently Failed:**")
                        for email in campaign_history["failed"][-10:]:
                            st.write(f"  • {email}")
                    else:
                        st.write("**❌ Failed:** No failed emails")
                
                # Campaign settings
                st.write("**⚙️ Campaign Settings**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Daily Limit:** {campaign.get('daily_limit', 120)}")
                    st.write(f"**Delay:** {campaign.get('delay', 30)}s")
                
                with col2:
                    st.write(f"**Schedule:** {'Enabled' if campaign.get('schedule_enabled') else 'Disabled'}")
                    if campaign.get('schedule_time'):
                        st.write(f"**Time:** {campaign.get('schedule_time')}")
                
                with col3:
                    st.write(f"**Created:** {campaign.get('created_at', 'Unknown')[:10]}")
                    st.write(f"**Status:** {campaign['status'].title()}")
        
        # Deduplication Statistics
        st.subheader("🔄 Deduplication Statistics")
        
        total_duplicates_prevented = 0
        total_processed_emails = 0
        
        for campaign_id, campaign in campaigns.items():
            history = load_json(HISTORY_FILE, {})
            campaign_history = history.get(campaign_id, {})
            
            sent_count = len(campaign_history.get("sent", []))
            failed_count = len(campaign_history.get("failed", []))
            leads_count = campaign['stats']['total_leads']
            
            total_processed_emails += sent_count + failed_count
            total_duplicates_prevented += max(0, leads_count - sent_count - failed_count)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Processed", total_processed_emails)
        
        with col2:
            st.metric("Duplicates Prevented", total_duplicates_prevented)
        
        with col3:
            efficiency = (total_processed_emails / (total_processed_emails + total_duplicates_prevented) * 100) if (total_processed_emails + total_duplicates_prevented) > 0 else 0
            st.metric("Deduplication Efficiency", f"{efficiency:.1f}%")
        
        # Real-time updates info
        st.info("🔄 **Auto-refresh:** This dashboard updates automatically every 30 seconds. Click 'Refresh' to update manually.")
        
        # Manual refresh button
        if st.button("🔄 Refresh Dashboard"):
            st.rerun()
            
    else:
        st.info("No campaigns yet. Create campaigns to see analytics.")

# Test Email Section (if triggered from dashboard)
if st.session_state.get('show_test_email'):
    st.subheader("📤 Send Test Email")
    
    if not senders:
        st.error("❌ Please add sender emails first!")
    else:
        # Find a campaign with leads and template
        test_campaign = None
        for campaign_id, campaign in campaigns.items():
            if campaign.get('leads_file_id') and campaign.get('template_file_id'):
                test_campaign = campaign
                break
        
        if not test_campaign:
            st.error("❌ Please create a campaign with leads and template first!")
        else:
            st.info(f"📤 Testing with campaign: {test_campaign['name']}")
            
            if st.button("📤 Send Test Batch (5 emails)"):
                # Test email sending logic
                history = load_json(HISTORY_FILE, {})
                if test_campaign['id'] not in history:
                    history[test_campaign['id']] = {}
                campaign_history = history[test_campaign['id']]
                
                # Load leads from MongoDB
                df = db.get_csv_as_dataframe(test_campaign['id'])
                if df is None:
                    st.error("❌ Failed to load leads from database")
                    st.stop()
                sent_emails = set(campaign_history.get("sent", []))
                failed_emails = set(campaign_history.get("failed", []))
                processing_emails = set(campaign_history.get("processing", []))
                blacklisted_emails = sent_emails | failed_emails | processing_emails
                
                # Initialize daily tracking for test
                today = datetime.date.today().isoformat()
                if "daily_sent_tracking" not in campaign_history:
                    campaign_history["daily_sent_tracking"] = {}
                if today not in campaign_history["daily_sent_tracking"]:
                    campaign_history["daily_sent_tracking"][today] = 0
                
                # Load template from MongoDB
                html_template = db.get_email_template(test_campaign['id'])
                if html_template is None:
                    st.error("❌ Failed to load template from database")
                    st.stop()
                selected_senders = [s for s in senders if s['email'] in test_campaign['selected_senders']]
                if not selected_senders:
                    selected_senders = senders
                
                i = 0
                total_sent = 0
                limit = 5
                
                for idx, row in df.iterrows():
                    email = row['Emails']
                    
                    # Skip if already sent, failed, or processing
                    if email in blacklisted_emails:
                        continue
                    if total_sent >= limit:
                        break
                    
                    # Mark as processing
                    processing_emails.add(email)
                    if "processing_timestamps" not in campaign_history:
                        campaign_history["processing_timestamps"] = {}
                    campaign_history["processing_timestamps"][email] = datetime.datetime.now().isoformat()
                    save_json(HISTORY_FILE, history)
                    
                    # Rotate through selected senders
                    sender_index = (len(sent_emails) + total_sent) % len(selected_senders)
                    sender = selected_senders[sender_index]
                    st.write(f"Sending to {email} via {sender['email']}")
                    
                    # Personalize template
                    personalized_template = html_template
                    for column in row.index:
                        placeholder = f"{{{{{column}}}}}"
                        if placeholder in personalized_template:
                            personalized_template = personalized_template.replace(placeholder, str(row[column]))
                    
                    success = send_email(sender['email'], sender['password'], email, "Test Email", personalized_template)
                    
                    # Update status
                    processing_emails.remove(email)
                    if "processing_timestamps" in campaign_history and email in campaign_history["processing_timestamps"]:
                        del campaign_history["processing_timestamps"][email]
                    
                    if success:
                        sent_emails.add(email)
                        total_sent += 1
                        st.success(f"✅ Sent to {email}")
                    else:
                        failed_emails.add(email)
                        st.error(f"❌ Failed to send to {email}")
                    
                    # Update history
                    campaign_history.update({
                        "sent": list(sent_emails),
                        "failed": list(failed_emails),
                        "processing": list(processing_emails)
                    })
                    save_json(HISTORY_FILE, history)
                    
                    time.sleep(15)
                
                st.success(f"🎉 Test complete. Sent {total_sent} emails.")
    
    if st.button("❌ Close Test"):
        st.session_state.show_test_email = False
        st.rerun()

# Add New Sender Section (if triggered from dashboard)
if st.session_state.get('show_add_sender'):
    st.subheader("➕ Add New Sender")
    
    with st.form("quick_add_sender_form"):
        sender_email = st.text_input("Sender Email")
        sender_pass = st.text_input("App Password", type="password", help="Enter your Gmail app password. Spaces are allowed and will be preserved.")
        st.info("💡 **App Password Tips:**\n- Use Gmail app passwords (not your regular password)\n- Spaces in app passwords are allowed and should be preserved\n- Enable 2-factor authentication first to generate app passwords")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Add Sender"):
                if sender_email and sender_pass:
                    # Validate app password
                    is_valid, validation_msg = validate_app_password(sender_pass)
                    if not is_valid:
                        st.error(f"❌ {validation_msg}")
                        st.stop()
                    
                    if any(sender['email'] == sender_email for sender in senders):
                        st.error(f"Email {sender_email} already exists!")
                    else:
                        senders.append({"email": sender_email, "password": sender_pass})
                        save_json(SENDER_FILE, senders)
                        st.success(f"✅ Added {sender_email}")
                        st.session_state.show_add_sender = False
                        st.rerun()
                else:
                    st.error("Please enter both email and password")
        
        with col2:
            if st.form_submit_button("❌ Cancel"):
                st.session_state.show_add_sender = False
                st.rerun()

# Create New Campaign Section (if triggered from dashboard)
if st.session_state.get('show_create_campaign'):
    st.subheader("📋 Create New Campaign")
    
    with st.form("quick_create_campaign_form"):
        campaign_name = st.text_input("Campaign Name", placeholder="e.g., Q4 Newsletter")
        campaign_description = st.text_area("Description", placeholder="Describe your campaign...")
        
        # Sender selection
        if senders:
            selected_senders = st.multiselect(
                "Select Sender Emails",
                [sender['email'] for sender in senders],
                default=[sender['email'] for sender in senders]
            )
        else:
            st.error("❌ Please add sender emails first!")
            selected_senders = []
        
        # File uploads
        leads_file = st.file_uploader("Upload Leads CSV", type=['csv'])
        template_file = st.file_uploader("Upload Email Template", type=['html'])
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 Create Campaign"):
                if campaign_name and selected_senders:
                    if leads_file and template_file:
                        # Create campaign ID
                        campaign_id = str(uuid.uuid4())
                        
                        # Store files in MongoDB
                        csv_content = leads_file.getbuffer()
                        html_content = template_file.getbuffer()
                        
                        csv_file_id = db.store_csv_leads(campaign_id, csv_content, leads_file.name)
                        template_file_id = db.store_email_template(campaign_id, html_content, template_file.name)
                        
                        if csv_file_id and template_file_id:
                            # Read CSV data for stats (before getbuffer() consumed it)
                            leads_file.seek(0)  # Reset file pointer to beginning
                            df_leads = pd.read_csv(leads_file)
                            
                            # Create campaign
                            campaigns[campaign_id] = {
                                'id': campaign_id,
                                'name': campaign_name,
                                'description': campaign_description,
                                'selected_senders': selected_senders,
                                'leads_file_id': csv_file_id,
                                'leads_filename': leads_file.name,
                                'template_file_id': template_file_id,
                                'template_filename': template_file.name,
                                'status': 'created',
                                'created_at': datetime.datetime.now().isoformat(),
                                'schedule_enabled': False,
                                'start_immediate_daily': False,
                                'scheduled_date': None,
                                'schedule_time': '10:00',
                                'stats': {
                                    'total_leads': len(df_leads),
                                    'total_sent': 0,
                                    'total_failed': 0
                                }
                            }
                        
                        save_json(CAMPAIGNS_FILE, campaigns)
                        st.success(f"✅ Campaign '{campaign_name}' created successfully!")
                        st.session_state.show_create_campaign = False
                        st.rerun()
                    else:
                        st.error("Please upload both leads CSV and email template!")
                else:
                    st.error("Please enter campaign name and select senders!")
        
        with col2:
            if st.form_submit_button("❌ Cancel"):
                st.session_state.show_create_campaign = False
                st.rerun()
