import smtplib, time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import db
import datetime

def send_email(sender_email, sender_pass, recipient_email, subject, html_template):
    """
    Send an email with enhanced error handling and logging
    """
    # Validate inputs
    if not sender_email or not sender_pass:
        error_msg = "Missing email or password"
        log_email_send(sender_email, recipient_email, subject, False, error_msg)
        return False
    
    # Ensure password is not empty or just whitespace
    if not sender_pass.strip():
        error_msg = "Password cannot be empty or just spaces"
        log_email_send(sender_email, recipient_email, subject, False, error_msg)
        return False
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    msg.attach(MIMEText(html_template, 'html'))

    try:
        # Connect to Gmail SMTP
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        
        # Login with the password as-is (preserving spaces)
        server.login(sender_email, sender_pass)
        
        # Send email
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        
        # Log successful send
        log_email_send(sender_email, recipient_email, subject, True, None)
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"Authentication failed for {sender_email}: {str(e)}"
        log_email_send(sender_email, recipient_email, subject, False, error_msg)
        return False
        
    except smtplib.SMTPRecipientsRefused as e:
        error_msg = f"Recipient refused: {recipient_email} - {str(e)}"
        log_email_send(sender_email, recipient_email, subject, False, error_msg)
        return False
        
    except smtplib.SMTPServerDisconnected as e:
        error_msg = f"Server disconnected: {str(e)}"
        log_email_send(sender_email, recipient_email, subject, False, error_msg)
        return False
        
    except smtplib.SMTPException as e:
        error_msg = f"SMTP error: {str(e)}"
        log_email_send(sender_email, recipient_email, subject, False, error_msg)
        return False
        
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        log_email_send(sender_email, recipient_email, subject, False, error_msg)
        return False

def log_email_send(sender_email, recipient_email, subject, success, error_msg):
    """
    Log email sending attempts for debugging and analytics
    """
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "sender": sender_email,
        "recipient": recipient_email,
        "subject": subject,
        "success": success,
        "error": error_msg
    }
    
    # Save log entry to MongoDB
    db.save_email_log(log_entry)

def validate_app_password(password):
    """
    Validate app password format and provide helpful feedback
    """
    if not password:
        return False, "Password cannot be empty"
    
    if not password.strip():
        return False, "Password cannot be just spaces"
    
    # Check the trimmed length (ignoring leading/trailing spaces)
    trimmed_length = len(password.strip())
    
    # Gmail app passwords are typically 16 characters
    if trimmed_length < 10:
        return False, "App password seems too short (should be 16 characters)"
    
    if trimmed_length > 20:
        return False, "App password seems too long (should be 16 characters)"
    
    # Check if there are leading/trailing spaces and warn
    if password != password.strip():
        return True, "Password format looks good (note: leading/trailing spaces will be preserved)"
    
    return True, "Password format looks good"

def check_sender_health(sender_email, sender_pass):
    """
    Check if a sender account is healthy and can send emails
    """
    # Validate inputs
    if not sender_email or not sender_pass:
        return False
    
    # Ensure password is not empty or just whitespace
    if not sender_pass.strip():
        return False
    
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        # Login with the password as-is (preserving spaces)
        server.login(sender_email, sender_pass)
        server.quit()
        return True
    except Exception as e:
        return False
