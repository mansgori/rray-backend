"""
YUNO Email Service - SendGrid Integration
Handles booking confirmations, reminders, and cancellations
"""

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from datetime import datetime

class EmailService:
    def __init__(self):
        self.api_key = os.environ.get('SENDGRID_API_KEY', '')
        self.from_email = os.environ.get('FROM_EMAIL', 'YUNO <no-reply@yuno.app>')
        self.provider = os.environ.get('NOTIFY_PROVIDER', 'email')
        self.base_url = os.environ.get('BASE_URL', 'http://localhost:3000')
        
        if self.provider == 'email' and self.api_key:
            self.client = SendGridAPIClient(self.api_key)
        else:
            self.client = None
    
    def send_booking_confirmation(self, user_email: str, booking_data: dict):
        """Send booking confirmation email"""
        if not self.client:
            print(f"[MOCK EMAIL] Booking confirmation to {user_email}")
            return
        
        subject = f"You're booked for {booking_data['listing_title']} - {booking_data['session_date']}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%); 
                           color: white; padding: 30px; text-align: center; border-radius: 8px; }}
                .content {{ padding: 30px; background: #f8fafc; border-radius: 8px; margin: 20px 0; }}
                .detail-row {{ padding: 12px 0; border-bottom: 1px solid #e2e8f0; }}
                .label {{ font-weight: bold; color: #475569; }}
                .value {{ color: #1e293b; }}
                .button {{ background: #06b6d4; color: white; padding: 12px 24px; text-decoration: none;
                          border-radius: 6px; display: inline-block; margin: 10px 0; }}
                .footer {{ text-align: center; color: #64748b; font-size: 14px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>You're In! ✨</h1>
                <p>Your booking is confirmed</p>
            </div>
            
            <div class="content">
                <div class="detail-row">
                    <span class="label">Booking ID:</span>
                    <span class="value">{booking_data['booking_id']}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Class:</span>
                    <span class="value">{booking_data['listing_title']}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Child:</span>
                    <span class="value">{booking_data['child_name']} (Age {booking_data['child_age']})</span>
                </div>
                <div class="detail-row">
                    <span class="label">Date & Time:</span>
                    <span class="value">{booking_data['session_date']} at {booking_data['session_time']}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Duration:</span>
                    <span class="value">{booking_data['duration']} minutes</span>
                </div>
                <div class="detail-row">
                    <span class="label">Location:</span>
                    <span class="value">{booking_data.get('venue', 'Online')}</span>
                </div>
                
                <div style="margin-top: 20px; padding: 15px; background: #fffbeb; border-radius: 6px;">
                    <strong>Cancellation Policy:</strong><br>
                    Full refund until 6h before start. 50% refund 2-6h before. No refund after.
                </div>
                
                <div style="text-align: center; margin-top: 20px;">
                    <a href="{booking_data.get('calendar_link', '#')}" class="button">Add to Calendar</a>
                </div>
            </div>
            
            <div class="footer">
                <p>Need help? Email support@yuno.app</p>
                <p style="font-size: 12px; color: #94a3b8;">© 2025 YUNO. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=user_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            print(f"Email sent to {user_email}: {response.status_code}")
            return response.status_code == 202
        
        except Exception as e:
            print(f"Email error: {str(e)}")
            return False
    
    def send_reminder_24h(self, user_email: str, booking_data: dict):
        """Send 24-hour reminder"""
        if not self.client:
            print(f"[MOCK EMAIL] 24h reminder to {user_email}")
            return
        
        subject = f"Tomorrow: {booking_data['listing_title']} for {booking_data['child_name']}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .reminder {{ background: #dbeafe; padding: 20px; border-radius: 8px; text-align: center; }}
                .time {{ font-size: 32px; font-weight: bold; color: #1e40af; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="reminder">
                <h2>🔔 Reminder: Class Tomorrow!</h2>
                <div class="time">{booking_data['session_time']}</div>
                <p><strong>{booking_data['listing_title']}</strong></p>
                <p>For {booking_data['child_name']}</p>
                
                {f"<p>📍 {booking_data.get('venue', 'Online')}</p>" if booking_data.get('venue') else ''}
                
                {f"<p><strong>Bring:</strong> {booking_data.get('equipment', 'Nothing special')}</p>" if booking_data.get('equipment') else ''}
            </div>
            
            <p style="text-align: center; margin-top: 20px; color: #64748b;">
                See you tomorrow! 🎉
            </p>
        </body>
        </html>
        """
        
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=user_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            return response.status_code == 202
        
        except Exception as e:
            print(f"Email error: {str(e)}")
            return False
    
    def send_reminder_2h(self, user_email: str, booking_data: dict):
        """Send 2-hour reminder"""
        if not self.client:
            print(f"[MOCK EMAIL] 2h reminder to {user_email}")
            return
        
        subject = f"Starts in 2 hours: {booking_data['listing_title']}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .urgent {{ background: linear-gradient(135deg, #fef3c7 0%, #fbbf24 100%); 
                          padding: 20px; border-radius: 8px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="urgent">
                <h2>⏰ Starting Soon!</h2>
                <p style="font-size: 18px;"><strong>{booking_data['listing_title']}</strong></p>
                <p>Starts at <strong>{booking_data['session_time']}</strong></p>
                
                {f"<p>📍 <a href='{booking_data.get('map_link', '#')}'>{booking_data.get('venue', 'Online')}</a></p>" if booking_data.get('venue') else ''}
                
                <p style="font-size: 14px; color: #78350f; margin-top: 10px;">
                    Running late? You can cancel for 50% refund until 2h before start.
                </p>
            </div>
        </body>
        </html>
        """
        
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=user_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            return response.status_code == 202
        
        except Exception as e:
            print(f"Email error: {str(e)}")
            return False
    
    def send_cancellation_notice(self, user_email: str, booking_data: dict):
        """Send cancellation confirmation"""
        if not self.client:
            print(f"[MOCK EMAIL] Cancellation notice to {user_email}")
            return
        
        subject = f"Booking canceled - {booking_data['listing_title']}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .notice {{ background: #fef2f2; padding: 20px; border-radius: 8px; border: 2px solid #fca5a5; }}
            </style>
        </head>
        <body>
            <div class="notice">
                <h2>Booking Canceled</h2>
                <p>Your booking for <strong>{booking_data['listing_title']}</strong> has been canceled.</p>
                
                <p><strong>Refund Details:</strong></p>
                <ul>
                    <li>Amount: {f"₹{booking_data.get('refund_amount', 0)}" if booking_data.get('refund_amount', 0) > 0 else f"{booking_data.get('refund_credits', 0)} credits"}</li>
                    <li>Processing time: 5-7 business days</li>
                </ul>
                
                <p style="margin-top: 20px;">
                    We're sorry to see you go! Browse more classes at <a href="https://yuno.app">yuno.app</a>
                </p>
            </div>
        </body>
        </html>
        """
        
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=user_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            return response.status_code == 202
        
        except Exception as e:
            print(f"Email error: {str(e)}")
            return False
    
    def send_partner_approval(self, partner_email: str, partner_data: dict):
        """Send partner approval email"""
        if not self.client:
            print(f"[MOCK EMAIL] Partner approval to {partner_email}")
            return
        
        subject = f"🎉 Welcome to rayy - Your Partner Account is Approved!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                           color: white; padding: 30px; text-align: center; border-radius: 8px; }}
                .content {{ padding: 30px; background: #f8fafc; border-radius: 8px; margin: 20px 0; }}
                .button {{ background: #10b981; color: white; padding: 12px 24px; text-decoration: none;
                          border-radius: 6px; display: inline-block; margin: 10px 0; }}
                .checklist {{ background: white; padding: 20px; border-radius: 6px; margin: 15px 0; }}
                .check-item {{ padding: 8px 0; color: #1e293b; }}
                .footer {{ text-align: center; color: #64748b; font-size: 14px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎉 Congratulations!</h1>
                <p>Your rayy Partner Account is Now Active</p>
            </div>
            
            <div class="content">
                <p>Hi {partner_data['brand_name']},</p>
                
                <p>Great news! Your partner application has been approved. You can now start listing your classes and reaching thousands of parents looking for quality activities for their children.</p>
                
                <div class="checklist">
                    <h3>Next Steps to Get Started:</h3>
                    <div class="check-item">✓ Create your first listing</div>
                    <div class="check-item">✓ Schedule sessions for the upcoming weeks</div>
                    <div class="check-item">✓ Set your pricing and availability</div>
                    <div class="check-item">✓ Add photos and detailed descriptions</div>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="{self.base_url}/partner/dashboard" class="button">Go to Partner Dashboard</a>
                </div>
                
                <div style="margin-top: 30px; padding: 15px; background: #dbeafe; border-radius: 6px;">
                    <strong>💡 Pro Tip:</strong> Partners with high-quality photos and detailed descriptions get 3x more bookings!
                </div>
            </div>
            
            <div class="footer">
                <p>Need help getting started? Email partner-support@rrray.app</p>
                <p style="font-size: 12px; color: #94a3b8;">© 2025 rayy. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=partner_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            print(f"Partner approval email sent to {partner_email}: {response.status_code}")
            return response.status_code == 202
        
        except Exception as e:
            print(f"Email error: {str(e)}")
            return False
    
    def send_partner_rejection(self, partner_email: str, partner_data: dict, reason: str):
        """Send partner rejection email with reason and resubmission instructions"""
        if not self.client:
            print(f"[MOCK EMAIL] Partner rejection to {partner_email}")
            return
        
        subject = "rayy Partner Application Update - Action Required"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); 
                           color: white; padding: 30px; text-align: center; border-radius: 8px; }}
                .content {{ padding: 30px; background: #f8fafc; border-radius: 8px; margin: 20px 0; }}
                .reason-box {{ background: #fef2f2; border-left: 4px solid #ef4444; padding: 15px; 
                              border-radius: 4px; margin: 20px 0; color: #1e293b; }}
                .button {{ background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none;
                          border-radius: 6px; display: inline-block; margin: 10px 0; }}
                .footer {{ text-align: center; color: #64748b; font-size: 14px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Application Status Update</h1>
                <p>Your rayy Partner Application Needs Attention</p>
            </div>
            
            <div class="content">
                <p>Hi {partner_data['brand_name']},</p>
                
                <p>Thank you for your interest in becoming a rayy partner. After reviewing your application, we've identified some issues that need to be addressed before we can approve your account.</p>
                
                <div class="reason-box">
                    <strong>Reason for Rejection:</strong><br>
                    {reason}
                </div>
                
                <h3>What You Can Do:</h3>
                <p>The good news is that you can resubmit your application after addressing the issues mentioned above. Simply:</p>
                <ol>
                    <li>Log in to your partner account</li>
                    <li>Update your KYC documents and information</li>
                    <li>Ensure all address details are accurate (we use Google Maps for verification)</li>
                    <li>Resubmit for review</li>
                </ol>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="{self.base_url}/partner/onboarding" class="button">Update & Resubmit Application</a>
                </div>
                
                <div style="margin-top: 30px; padding: 15px; background: #dbeafe; border-radius: 6px;">
                    <strong>📞 Need Help?</strong><br>
                    If you have questions about the rejection reason or need assistance with your application, our team is here to help at partner-support@rrray.app
                </div>
            </div>
            
            <div class="footer">
                <p>We look forward to welcoming you to the rayy partner community!</p>
                <p style="font-size: 12px; color: #94a3b8;">© 2025 rayy. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=partner_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            print(f"Partner rejection email sent to {partner_email}: {response.status_code}")
            return response.status_code == 202
        
        except Exception as e:
            print(f"Email error: {str(e)}")
            return False



    
    # ==================== PARTNER EMAIL NOTIFICATIONS ====================
    
    def send_partner_registration_confirmation(self, partner_email: str, partner_data: dict):
        """Send confirmation email when partner registers"""
        if not self.client:
            print(f"[MOCK EMAIL] Partner registration confirmation to {partner_email}")
            return True
        
        subject = "Welcome to rayy! Your Partner Account is Pending Approval"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%); 
                           color: white; padding: 40px; text-align: center; border-radius: 12px; }}
                .content {{ padding: 30px; background: #f8fafc; border-radius: 12px; margin: 20px 0; }}
                .info-box {{ background: #f0f9ff; border-left: 4px solid #06b6d4; padding: 16px; margin: 16px 0; border-radius: 4px; }}
                .button {{ background: #06b6d4; color: white; padding: 14px 28px; text-decoration: none;
                          border-radius: 8px; display: inline-block; margin: 16px 0; font-weight: 600; }}
                .footer {{ text-align: center; color: #64748b; font-size: 14px; margin-top: 30px; }}
                .checklist {{ list-style: none; padding-left: 0; }}
                .checklist li {{ padding: 8px 0; }}
                .checklist li:before {{ content: "✓ "; color: #10b981; font-weight: bold; margin-right: 8px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎉 Welcome to rayy!</h1>
                <p style="font-size: 18px; margin-top: 12px;">Thank you for joining our partner community</p>
            </div>
            
            <div class="content">
                <h2 style="color: #0f172a;">Hi {partner_data.get('name', 'Partner')},</h2>
                
                <p style="color: #475569; line-height: 1.6;">
                    Thank you for registering <strong>{partner_data.get('organizationName', 'your organization')}</strong> 
                    as a partner on rayy! We're excited to have you join our growing community of educational service providers.
                </p>
                
                <div class="info-box">
                    <h3 style="color: #0891b2; margin-top: 0;">📋 What Happens Next?</h3>
                    <p style="color: #475569; margin-bottom: 0;">
                        Our team will review your application within <strong>24-48 hours</strong>. Once approved, 
                        you'll be able to start creating listings and receiving bookings.
                    </p>
                </div>
                
                <h3 style="color: #0f172a; margin-top: 24px;">✨ What to Expect:</h3>
                <ul class="checklist">
                    <li><strong>0% Commission for 30 Days</strong> - Start earning with zero platform fees!</li>
                    <li><strong>Dashboard Access</strong> - Manage listings, bookings, and earnings</li>
                    <li><strong>Payment Support</strong> - Bi-weekly payouts to your bank account</li>
                    <li><strong>Marketing Boost</strong> - Featured placement for trial classes</li>
                    <li><strong>Support Team</strong> - Dedicated support to help you succeed</li>
                </ul>
                
                <div style="background: #fffbeb; padding: 16px; border-radius: 8px; margin: 20px 0;">
                    <h4 style="color: #d97706; margin-top: 0;">⏳ During Review Period:</h4>
                    <p style="color: #78350f; margin-bottom: 0; font-size: 14px;">
                        You'll receive an email notification once your account is approved. 
                        Make sure to check your spam folder just in case!
                    </p>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="{self.base_url}/partner/dashboard" class="button">View Partner Dashboard</a>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>Need help?</strong> Contact us at partners@rrray.com</p>
                <p>📱 WhatsApp: +91 XXX-XXX-XXXX</p>
                <p style="font-size: 12px; color: #94a3b8; margin-top: 16px;">
                    © 2024 rayy. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """
        
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=partner_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            print(f"Partner registration email sent to {partner_email}: {response.status_code}")
            return response.status_code == 202
        
        except Exception as e:
            print(f"Partner email error: {str(e)}")
            return False
    
    def send_partner_approval_notification(self, partner_email: str, partner_data: dict):
        """Send notification when partner is approved"""
        if not self.client:
            print(f"[MOCK EMAIL] Partner approval to {partner_email}")
            return True
        
        subject = "🎉 Your rayy Partner Account is Approved!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
                           color: white; padding: 40px; text-align: center; border-radius: 12px; }}
                .content {{ padding: 30px; background: #f8fafc; border-radius: 12px; margin: 20px 0; }}
                .success-box {{ background: #d1fae5; border-left: 4px solid #10b981; padding: 16px; margin: 16px 0; border-radius: 4px; }}
                .button {{ background: #10b981; color: white; padding: 14px 28px; text-decoration: none;
                          border-radius: 8px; display: inline-block; margin: 16px 0; font-weight: 600; }}
                .promo-highlight {{ background: linear-gradient(135deg, #fef3c7 0%, #fcd34d 100%); 
                                   padding: 20px; border-radius: 12px; margin: 20px 0; text-align: center; }}
                .footer {{ text-align: center; color: #64748b; font-size: 14px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎉 Congratulations!</h1>
                <p style="font-size: 20px; margin-top: 12px;">Your partner account is now <strong>ACTIVE</strong></p>
            </div>
            
            <div class="content">
                <h2 style="color: #0f172a;">Great News, {partner_data.get('name', 'Partner')}!</h2>
                
                <p style="color: #475569; line-height: 1.6;">
                    Your partner application has been approved! You can now start creating listings, 
                    managing bookings, and growing your business on rayy.
                </p>
                
                <div class="promo-highlight">
                    <h3 style="color: #d97706; margin-top: 0;">🎁 Special Welcome Offer</h3>
                    <p style="font-size: 24px; font-weight: 800; color: #78350f; margin: 12px 0;">
                        0% COMMISSION FOR 30 DAYS
                    </p>
                    <p style="color: #92400e; font-size: 14px; margin-bottom: 0;">
                        Keep 100% of your earnings for the first month!
                    </p>
                </div>
                
                <h3 style="color: #0f172a; margin-top: 24px;">🚀 Get Started:</h3>
                <ol style="color: #475569; line-height: 1.8;">
                    <li><strong>Create Your First Listing</strong> - Add classes, workshops, or activities</li>
                    <li><strong>Set Your Schedule</strong> - Define available session times</li>
                    <li><strong>Upload Photos</strong> - Showcase your venue and activities</li>
                    <li><strong>Offer Trial Classes</strong> - Attract new customers with trial sessions</li>
                    <li><strong>Start Receiving Bookings</strong> - Get notified instantly!</li>
                </ol>
                
                <div class="success-box">
                    <h4 style="color: #059669; margin-top: 0;">✓ Account Status</h4>
                    <p style="color: #064e3b; margin-bottom: 8px;"><strong>Status:</strong> Active & Approved</p>
                    <p style="color: #064e3b; margin-bottom: 8px;"><strong>Commission:</strong> 0% (Next 30 days)</p>
                    <p style="color: #064e3b; margin-bottom: 0;"><strong>Payout Cycle:</strong> Bi-weekly</p>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="{self.base_url}/partner/dashboard" class="button">Go to Dashboard →</a>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>Questions?</strong> Our support team is here to help!</p>
                <p>Email: partners@rrray.com | Phone: +91 XXX-XXX-XXXX</p>
                <p style="font-size: 12px; color: #94a3b8; margin-top: 16px;">
                    © 2024 rayy. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """
        
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=partner_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            print(f"Partner approval email sent to {partner_email}: {response.status_code}")
            return response.status_code == 202
        
        except Exception as e:
            print(f"Partner email error: {str(e)}")
            return False
    
    def send_partner_rejection_notification(self, partner_email: str, partner_data: dict, reason: str = ""):
        """Send notification when partner is rejected"""
        if not self.client:
            print(f"[MOCK EMAIL] Partner rejection to {partner_email}")
            return True
        
        subject = "rayy Partner Application Update"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #64748b 0%, #475569 100%); 
                           color: white; padding: 40px; text-align: center; border-radius: 12px; }}
                .content {{ padding: 30px; background: #f8fafc; border-radius: 12px; margin: 20px 0; }}
                .info-box {{ background: #fef2f2; border-left: 4px solid #ef4444; padding: 16px; margin: 16px 0; border-radius: 4px; }}
                .button {{ background: #06b6d4; color: white; padding: 14px 28px; text-decoration: none;
                          border-radius: 8px; display: inline-block; margin: 16px 0; font-weight: 600; }}
                .footer {{ text-align: center; color: #64748b; font-size: 14px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Application Status Update</h1>
            </div>
            
            <div class="content">
                <h2 style="color: #0f172a;">Hi {partner_data.get('name', 'Partner')},</h2>
                
                <p style="color: #475569; line-height: 1.6;">
                    Thank you for your interest in partnering with rayy. After careful review, 
                    we're unable to approve your application at this time.
                </p>
                
                {f'''
                <div class="info-box">
                    <h4 style="color: #dc2626; margin-top: 0;">Reason:</h4>
                    <p style="color: #7f1d1d; margin-bottom: 0;">{reason}</p>
                </div>
                ''' if reason else ''}
                
                <h3 style="color: #0f172a; margin-top: 24px;">What You Can Do:</h3>
                <ul style="color: #475569; line-height: 1.8;">
                    <li>Review and update your information</li>
                    <li>Ensure all required documents are provided</li>
                    <li>Reapply after addressing the feedback</li>
                    <li>Contact our support team for clarification</li>
                </ul>
                
                <p style="color: #475569; line-height: 1.6; margin-top: 20px;">
                    We appreciate your interest in rayy and encourage you to reapply once 
                    you've addressed any concerns. Our team is here to help!
                </p>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="{self.base_url}/contact" class="button">Contact Support</a>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>Need clarification?</strong> Reach out to us!</p>
                <p>Email: partners@rrray.com | Phone: +91 XXX-XXX-XXXX</p>
                <p style="font-size: 12px; color: #94a3b8; margin-top: 16px;">
                    © 2024 rayy. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """
        
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=partner_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            print(f"Partner rejection email sent to {partner_email}: {response.status_code}")
            return response.status_code == 202
        
        except Exception as e:
            print(f"Partner email error: {str(e)}")

    
    def send_partner_admin_invitation(self, partner_email: str, partner_data: dict):
        """Send invitation email when admin creates a partner account"""
        if not self.client:
            print(f"[MOCK EMAIL] Admin partner invitation to {partner_email}")
            return True
        
        subject = "Welcome to rayy! Your Partner Account Has Been Created"
        
        password = partner_data.get('password', '[Contact Admin]')
        status = partner_data.get('status', 'pending')
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); 
                           color: white; padding: 40px; text-align: center; border-radius: 12px; }}
                .content {{ padding: 30px; background: #f8fafc; border-radius: 12px; margin: 20px 0; }}
                .credentials-box {{ background: #f0f9ff; border: 2px solid #06b6d4; padding: 20px; margin: 20px 0; border-radius: 8px; }}
                .button {{ background: #06b6d4; color: white; padding: 14px 28px; text-decoration: none;
                          border-radius: 8px; display: inline-block; margin: 16px 0; font-weight: 600; }}
                .warning {{ background: #fef2f2; border-left: 4px solid #ef4444; padding: 12px; margin: 16px 0; border-radius: 4px; }}
                .footer {{ text-align: center; color: #64748b; font-size: 14px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎉 Welcome to rayy!</h1>
                <p style="font-size: 18px; margin-top: 12px;">Your partner account has been created</p>
            </div>
            
            <div class="content">
                <h2 style="color: #0f172a;">Hi {partner_data.get('name', 'Partner')},</h2>
                
                <p style="color: #475569; line-height: 1.6;">
                    Great news! Your partner account for <strong>{partner_data.get('organizationName', 'your organization')}</strong> 
                    has been created by our admin team. You can now access your partner dashboard and start managing your listings.
                </p>
                
                <div class="credentials-box">
                    <h3 style="color: #0891b2; margin-top: 0;">🔐 Your Login Credentials</h3>
                    <p style="margin: 8px 0;"><strong>Email:</strong> {partner_email}</p>
                    <p style="margin: 8px 0;"><strong>Password:</strong> <code style="background: white; padding: 4px 8px; border-radius: 4px;">{password}</code></p>
                    <p style="color: #0891b2; font-size: 14px; margin-top: 12px;">
                        💡 Please change your password after first login for security
                    </p>
                </div>
                
                {f'''
                <div class="warning">
                    <p style="color: #7f1d1d; margin: 0; font-size: 14px;">
                        ⏳ <strong>Account Status: Pending Approval</strong><br/>
                        Your account needs admin approval before you can start receiving bookings. 
                        You'll be notified once approved (typically within 24-48 hours).
                    </p>
                </div>
                ''' if status == 'pending' else '''
                <div style="background: #d1fae5; border-left: 4px solid #10b981; padding: 12px; margin: 16px 0; border-radius: 4px;">
                    <p style="color: #064e3b; margin: 0; font-size: 14px;">
                        ✅ <strong>Account Status: Active</strong><br/>
                        Your account is approved! You can start creating listings immediately.
                    </p>
                </div>
                '''}
                
                <h3 style="color: #0f172a; margin-top: 24px;">🚀 Next Steps:</h3>
                <ol style="color: #475569; line-height: 1.8;">
                    <li>Login to your partner dashboard</li>
                    <li>Complete your profile information</li>
                    <li>Create your first listing</li>
                    <li>Set up your schedule and pricing</li>
                    <li>Start receiving bookings!</li>
                </ol>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="{self.base_url}/partner/dashboard" class="button">Access Partner Dashboard →</a>
                </div>
            </div>
            
            <div class="footer">
                <p><strong>Need help getting started?</strong></p>
                <p>Contact: partners@rrray.com | Phone: +91 XXX-XXX-XXXX</p>
                <p style="font-size: 12px; color: #94a3b8; margin-top: 16px;">
                    © 2024 rayy. All rights reserved.
                </p>
            </div>
        </body>
        </html>
        """
        
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=partner_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            print(f"Admin invitation email sent to {partner_email}: {response.status_code}")
            return response.status_code == 202
        
        except Exception as e:
            print(f"Admin invitation email error: {str(e)}")
            return False


            return False
    
    def send_admin_new_partner_notification(self, admin_email: str, partner_data: dict):
        """Notify admin of new pending partner"""
        if not self.client:
            print(f"[MOCK EMAIL] Admin notification about new partner")
            return True
        
        subject = f"🔔 New Partner Registration: {partner_data.get('organizationName', 'Unknown')}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); 
                           color: white; padding: 30px; text-align: center; border-radius: 12px; }}
                .content {{ padding: 30px; background: #f8fafc; border-radius: 12px; margin: 20px 0; }}
                .detail-row {{ padding: 12px 0; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; }}
                .label {{ font-weight: 600; color: #475569; }}
                .value {{ color: #1e293b; }}
                .button {{ background: #8b5cf6; color: white; padding: 14px 28px; text-decoration: none;
                          border-radius: 8px; display: inline-block; margin: 16px 0; font-weight: 600; }}
                .footer {{ text-align: center; color: #64748b; font-size: 14px; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔔 New Partner Registration</h1>
                <p>Action required: Review and approve</p>
            </div>
            
            <div class="content">
                <h3 style="color: #0f172a;">Partner Details:</h3>
                
                <div class="detail-row">
                    <span class="label">Organization Name:</span>
                    <span class="value">{partner_data.get('organizationName', 'N/A')}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Contact Person:</span>
                    <span class="value">{partner_data.get('name', 'N/A')}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Email:</span>
                    <span class="value">{partner_data.get('email', 'N/A')}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Phone:</span>
                    <span class="value">{partner_data.get('phone', 'N/A')}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Location:</span>
                    <span class="value">{partner_data.get('city', 'N/A')}, {partner_data.get('state', 'N/A')}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Categories:</span>
                    <span class="value">{', '.join(partner_data.get('categories', []))}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Registration Date:</span>
                    <span class="value">{partner_data.get('created_at', 'N/A')}</span>
                </div>
                
                <div style="background: #fffbeb; padding: 16px; border-radius: 8px; margin: 20px 0;">
                    <p style="color: #78350f; margin: 0; font-size: 14px;">
                        ⏱️ <strong>SLA Reminder:</strong> Please review and respond within 24-48 hours
                    </p>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="{self.base_url}/admin/partners" class="button">Review in Admin Panel →</a>
                </div>
            </div>
            
            <div class="footer">
                <p style="font-size: 12px; color: #94a3b8;">
                    © 2024 rayy Admin Notification System
                </p>
            </div>
        </body>
        </html>
        """
        
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=admin_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.client.send(message)
            print(f"Admin notification email sent to {admin_email}: {response.status_code}")
            return response.status_code == 202
        
        except Exception as e:
            print(f"Admin email error: {str(e)}")
            return False


