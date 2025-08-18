#!/bin/bash

# Bulk Email Automation - Deployment Script
# This script sets up the background campaign runner service

echo "🚀 Deploying Bulk Email Automation System..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

# Get project directory
PROJECT_DIR=$(pwd)
echo "📁 Project directory: $PROJECT_DIR"

# Get current user (non-root user)
ACTUAL_USER=$(logname || who am i | awk '{print $1}' | head -n1)
echo "👤 User: $ACTUAL_USER"

# Install dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Create systemd service file
echo "🔧 Creating systemd service..."
cat > /etc/systemd/system/campaign-runner.service << EOF
[Unit]
Description=Bulk Email Campaign Runner Service
After=network.target mongod.service
Wants=mongod.service

[Service]
Type=simple
User=$ACTUAL_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin:/usr/local/bin:/usr/bin
ExecStart=/usr/bin/python3 $PROJECT_DIR/campaign_runner.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$PROJECT_DIR

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo "🔄 Reloading systemd..."
systemctl daemon-reload

# Enable and start service
echo "🚀 Starting campaign runner service..."
systemctl enable campaign-runner.service
systemctl start campaign-runner.service

# Check status
echo "📊 Service status:"
systemctl status campaign-runner.service --no-pager -l

echo ""
echo "✅ Deployment completed!"
echo ""
echo "📋 Useful commands:"
echo "   Check status: sudo systemctl status campaign-runner.service"
echo "   View logs: sudo journalctl -u campaign-runner.service -f"
echo "   Stop service: sudo systemctl stop campaign-runner.service"
echo "   Start service: sudo systemctl start campaign-runner.service"
echo "   Restart service: sudo systemctl restart campaign-runner.service"
echo ""
echo "🌐 Your Streamlit app will now work with background campaign execution!"
echo "   Campaigns will continue running even when you close the browser."
