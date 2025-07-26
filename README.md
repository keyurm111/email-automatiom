# 📧 Bulk Email Automation System

A comprehensive email automation platform with advanced campaign management, scheduling, and analytics capabilities.

## 🚀 Features

### Campaign Management
- **Multiple Campaigns**: Create and manage multiple email campaigns simultaneously
- **Campaign Naming**: Give each campaign a descriptive name and description
- **Campaign Status**: Track campaign status (draft, running, paused, completed)
- **Individual Settings**: Each campaign has its own settings (daily limits, delays, scheduling)

### Sender Management
- **Multiple Senders**: Add multiple Gmail accounts for email rotation
- **Health Checks**: Verify sender account health before campaigns
- **Sender Statistics**: Track performance per sender account
- **Secure Storage**: Passwords stored securely in JSON format
- **App Password Support**: Full support for Gmail app passwords with spaces

### Lead Management
- **CSV Upload**: Upload leads in CSV format
- **Deduplication**: Automatic duplicate email prevention
- **Personalization**: Dynamic template personalization with lead data
- **Progress Tracking**: Real-time progress monitoring

### Email Templates
- **HTML Support**: Rich HTML email templates
- **Personalization**: Use `{{ColumnName}}` placeholders for dynamic content
- **Template Preview**: Preview templates before sending

### Scheduling & Automation
- **Daily Scheduling**: Set up daily automated campaigns
- **Time-based Execution**: Execute campaigns at specific times
- **Batch Processing**: Process emails in configurable batches
- **Rate Limiting**: Respect Gmail sending limits

### Analytics & Monitoring
- **Real-time Progress**: Live progress bars and statistics
- **Success Rates**: Track delivery success rates
- **Error Logging**: Detailed error logging and debugging
- **Campaign Analytics**: Comprehensive campaign performance metrics

### Safety Features
- **Duplicate Prevention**: Multiple layers of duplicate protection
- **Processing Recovery**: Resume interrupted campaigns
- **Error Handling**: Graceful error handling and recovery
- **Rate Limiting**: Built-in delays to prevent account suspension

## 📋 Requirements

- Python 3.7+
- Streamlit
- pandas
- smtplib (built-in)

## 🛠️ Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd bulk_email_automation
```

2. Install dependencies:
```bash
pip install streamlit pandas
```

3. Set up Gmail accounts:
   - Enable 2-factor authentication
   - Generate app passwords (spaces are allowed and preserved)
   - Add accounts to `senders.json`

## 🚀 Usage

### 1. Start the Application
```bash
streamlit run main.py
```

### 2. Add Sender Accounts
1. Go to "📧 Manage Senders"
2. Click "Add New Sender"
3. Enter Gmail address and app password (spaces are allowed)
4. Test account health with "Test" button

### 3. Upload Leads
1. Go to "📋 Manage Campaigns" and create a campaign
2. Upload CSV file with email addresses
3. Ensure one column is named "Emails"

### 4. Create Email Template
1. Go to "📋 Manage Campaigns" and select your campaign
2. Upload HTML template file
3. Use `{{ColumnName}}` for personalization

### 5. Create Campaign
1. Go to "📋 Manage Campaigns"
2. Click "Create New Campaign"
3. Configure:
   - Campaign name and description
   - Email subject line
   - Daily limits and delays
   - Scheduling options

### 6. Run Campaign
1. Go to "🎯 Active Campaign"
2. Select campaign from list
3. Click "Start" to begin
4. Monitor progress in real-time

## 📊 File Structure

```
bulk_email_automation/
├── main.py              # Main Streamlit application
├── email_sender.py      # Email sending functionality
├── utils.py             # Utility functions
├── senders.json         # Sender account credentials
├── campaigns.json       # Campaign configurations
├── sent_log.json        # Email sending history
├── config.json          # Global settings
├── email_logs.json      # Detailed email logs
├── templates/
│   └── user_template.html  # Email templates
└── uploads/
    └── leads.csv        # Lead data
```

## 🔧 Configuration

### Sender Accounts (`senders.json`)
```json
[
    {
        "email": "your-email@gmail.com",
        "password": "your-app-password"
    }
]
```

### Campaign Settings
Each campaign includes:
- **Daily Limit**: Maximum emails per day per account
- **Delay**: Seconds between emails
- **Scheduling**: Daily execution time
- **Subject Line**: Email subject
- **Status**: Campaign state tracking

## 📈 Analytics

### Campaign Metrics
- Total emails sent
- Success/failure rates
- Remaining emails
- Daily progress

### Sender Performance
- Per-sender statistics
- Health status
- Error tracking

## 🛡️ Safety Features

### Rate Limiting
- Configurable delays between emails
- Daily sending limits
- Account rotation

### Duplicate Prevention
- Multiple deduplication layers
- Processing state tracking
- Recovery from interruptions

### Error Handling
- Detailed error logging
- Graceful failure recovery
- Account health monitoring

## 🔍 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Ensure 2FA is enabled
   - Use app passwords, not regular passwords
   - **App passwords with spaces are fully supported**
   - Check account health

2. **Sending Limits**
   - Gmail daily limit: ~500 emails
   - Reduce daily limits in campaign settings
   - Add more sender accounts

3. **Template Issues**
   - Ensure HTML is valid
   - Check placeholder syntax: `{{ColumnName}}`
   - Test with small batches first

### Debugging
- Check `email_logs.json` for detailed error information
- Use "Test Batch" feature for small-scale testing
- Monitor sender health regularly

## 📝 Best Practices

1. **Start Small**: Test with 5-10 emails first
2. **Monitor Health**: Regularly check sender account health
3. **Use Multiple Senders**: Distribute load across accounts
4. **Respect Limits**: Stay within Gmail sending limits
5. **Quality Content**: Use engaging, relevant email content
6. **Regular Monitoring**: Check campaign progress regularly

## ⚠️ Important Notes

- This tool is for legitimate email marketing only
- Respect recipient privacy and unsubscribe requests
- Follow email marketing best practices
- Monitor for any account restrictions
- Keep sender accounts secure

## 🔄 Updates

The system automatically:
- Tracks campaign progress
- Prevents duplicate sends
- Logs all activities
- Recovers from interruptions
- Updates statistics in real-time

---

**Happy Email Marketing! 📧✨** 