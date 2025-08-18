# 📧 Bulk Email Automation System

A professional bulk email automation system with background execution, real-time analytics, and comprehensive deduplication.

## 🌟 Features

- **📧 Bulk Email Sending** - Send personalized emails to thousands of recipients
- **🔄 Background Execution** - Campaigns run independently of the web interface
- **📊 Real-Time Analytics** - Live dashboard with auto-refresh every 30 seconds
- **🚫 Smart Deduplication** - Guaranteed no duplicate emails sent
- **📅 Scheduling System** - Daily limits, custom schedules, and automatic resumption
- **🗄️ MongoDB Storage** - Professional database with file storage for leads and templates
- **📱 Modern UI** - Beautiful Streamlit interface with responsive design
- **🔒 Gmail Integration** - Secure app password authentication
- **📈 Progress Tracking** - Real-time campaign progress and performance metrics

## 🚀 Quick Setup

### 1. Install MongoDB

#### On macOS (using Homebrew):
```bash
# Install Homebrew if you haven't already
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install MongoDB
brew tap mongodb/brew
brew install mongodb-community

# Start MongoDB service
brew services start mongodb-community
```

#### On Ubuntu/Debian:
```bash
# Import MongoDB public GPG key
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -

# Create list file for MongoDB
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# Update package database
sudo apt-get update

# Install MongoDB
sudo apt-get install -y mongodb-org

# Start MongoDB service
sudo systemctl start mongod
sudo systemctl enable mongod
```

#### On Windows:
Download and install MongoDB Community Server from [MongoDB Download Center](https://www.mongodb.com/try/download/community)

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
The `.env` file has been created with the default MongoDB URI:
```
MONGODB_URI=mongodb://localhost:27017/bulk_email_automation
```

You can modify this URI if you need to connect to a different MongoDB instance.

### 4. Start the Application
```bash
streamlit run main.py
```

The system will automatically:
- Connect to MongoDB
- Initialize the background campaign runner
- Load existing campaigns and data
- Start the web interface

## 🔄 Data Migration

The system automatically handles data migration from JSON files to MongoDB. If you have existing data:

1. **Senders** → `senders` collection
2. **Campaigns** → `campaigns` collection  
3. **History** → `history` collection
4. **Email Logs** → `email_logs` collection
5. **Configuration** → `config` collection

**Note:** Migration happens automatically when you first run the application. Old JSON files can be safely removed after successful migration.

## 🚀 Background Execution

The system includes a background campaign runner that ensures campaigns continue running even when you close the web interface:

### **Development Mode:**
```bash
streamlit run main.py
# Background runner starts automatically
```

### **Production Mode:**
```bash
# Deploy as system service
sudo ./deploy.sh

# Or manually start the service
sudo systemctl enable campaign_runner
sudo systemctl start campaign_runner
```

### **Service Management:**
```bash
# Check status
sudo systemctl status campaign_runner

# View logs
sudo journalctl -u campaign_runner -f

# Stop service
sudo systemctl stop campaign_runner
```

## 🚫 Smart Deduplication

The system guarantees **100% duplicate-free email delivery** through multi-level protection:

### **Level 1: CSV Upload Deduplication**
- Automatically detects and removes duplicate emails during upload
- Normalizes emails (lowercase, trim whitespace)
- Provides immediate feedback on duplicates found

### **Level 2: Campaign Execution Protection**
- Runtime protection during campaign execution
- Historical tracking of all processed emails
- Comprehensive logging of deduplication actions

### **Level 3: Email Sending Protection**
- Real-time checks before each email send
- Processing state tracking to prevent concurrent processing
- Failure handling to track failed emails

## 📊 Real-Time Analytics

The system provides comprehensive analytics with live updates:

### **Dashboard Features:**
- **Auto-refresh every 30 seconds** - Always current data
- **Live campaign progress** - Real-time status for all campaigns
- **Comprehensive metrics** - Sent, failed, pending, success rates
- **Deduplication statistics** - Efficiency metrics and duplicate prevention

### **Campaign Analytics:**
- **Progress visualization** - Progress bars and percentages
- **Performance metrics** - Success rates and failure analysis
- **Recent activity** - Last 10 sent and failed emails
- **Daily tracking** - Today's progress vs daily limits

## 🗄️ Database Structure

### Collections:

#### `senders`
- `email`: Sender email address (unique)
- `password`: Gmail app password

#### `campaigns`
- `id`: Campaign unique identifier
- `name`: Campaign name
- `description`: Campaign description
- `status`: Campaign status (draft, running, paused, completed)
- `selected_senders`: Array of sender emails
- `leads_file`: Path to leads CSV file
- `template_file`: Path to email template
- `subject_line`: Email subject line
- `daily_limit`: Daily email limit per account
- `delay`: Delay between emails in seconds
- `schedule_enabled`: Whether daily scheduling is enabled
- `schedule_time`: Daily schedule time
- `scheduled_date`: Specific scheduled date
- `stats`: Campaign statistics
- `created_at`: Creation timestamp

#### `history`
- `campaign_id`: Reference to campaign
- `sent`: Array of sent email addresses
- `failed`: Array of failed email addresses
- `processing`: Array of currently processing emails
- `processing_timestamps`: Timestamps for processing emails
- `daily_sent_tracking`: Daily email count tracking

#### `email_logs`
- `timestamp`: Log entry timestamp
- `sender`: Sender email address
- `recipient`: Recipient email address
- `subject`: Email subject
- `success`: Whether email was sent successfully
- `error`: Error message if failed

#### `config`
- General application configuration

## 🔧 Troubleshooting

### MongoDB Connection Issues
1. **Check if MongoDB is running:**
   ```bash
   # macOS
   brew services list | grep mongodb
   
   # Ubuntu/Debian
   sudo systemctl status mongod
   ```

2. **Check MongoDB logs:**
   ```bash
   # macOS
   tail -f /usr/local/var/log/mongodb/mongo.log
   
   # Ubuntu/Debian
   sudo tail -f /var/log/mongodb/mongod.log
   ```

3. **Test connection manually:**
   ```bash
   mongosh mongodb://localhost:27017
   ```

### Permission Issues
If you encounter permission issues:
```bash
# macOS - ensure proper ownership
sudo chown -R $(whoami) /usr/local/var/mongodb
sudo chown -R $(whoami) /usr/local/var/log/mongodb

# Ubuntu/Debian - check MongoDB user
sudo chown -R mongodb:mongodb /var/lib/mongodb
sudo chown -R mongodb:mongodb /var/log/mongodb
```

## 📊 Performance Optimization

The database includes several indexes for better performance:
- Unique index on sender emails
- Index on campaign IDs and status
- Indexes on history campaign_id and timestamp
- Indexes on email logs timestamp, sender, and recipient

## 🔒 Security Notes

- MongoDB runs on localhost by default (no external access)
- No authentication is required for local development
- For production, consider enabling authentication and SSL
- Update `.env` file with appropriate credentials for production

## 🚀 Running the Application

After setup, run the application as usual:
```bash
streamlit run main.py
```

The application will automatically connect to MongoDB and use the new database instead of JSON files.

## 📝 Backward Compatibility

The system maintains backward compatibility through wrapper functions in `database.py`. All existing code continues to work without modification.

## 🆘 Support

If you encounter issues:
1. Check MongoDB connection using `setup_mongodb.py`
2. Verify all dependencies are installed
3. Check the console for error messages
4. Ensure MongoDB service is running

Happy emailing! 📧
