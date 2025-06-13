#!/usr/bin/env python3
"""
Email-based Photo Upload System
Hotel Staff → Email with Photo → S3 → Database → Guest Access

Simple alternative: hotel staff emails photos to a dedicated email address
"""

import os
import json
import sqlite3
import time
import boto3
import email
import imaplib
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List
import tempfile
import asyncio

# AI imports
from langchain_openai import ChatOpenAI

# Configuration
EMAIL_SERVER = os.getenv('EMAIL_SERVER', 'imap.gmail.com')
EMAIL_USERNAME = os.getenv('EMAIL_USERNAME')  # photos@yourhotel.com
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')  # App password
***REMOVED*** = os.getenv('***REMOVED***')
AWS_BUCKET_NAME = "ella-hotel-media"

# Initialize clients
s3_client = boto3.client('s3', region_name='ap-southeast-1')
llm = ChatOpenAI(openai_api_key=***REMOVED***, model="gpt-4o", temperature=0.3) if ***REMOVED*** else None

class EmailUploadProcessor:
    """Process photo uploads via email"""
    
    def __init__(self):
        self.processed_emails = set()  # Track processed emails
    
    async def check_for_new_photos(self):
        """Check email inbox for new photo uploads"""
        
        try:
            print("📧 Checking for new photo emails...")
            
            # Connect to email server
            mail = imaplib.IMAP4_SSL(EMAIL_SERVER)
            mail.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            mail.select('inbox')
            
            # Search for unread emails
            status, messages = mail.search(None, 'UNSEEN')
            
            if status == 'OK':
                message_ids = messages[0].split()
                print(f"📬 Found {len(message_ids)} unread emails")
                
                for msg_id in message_ids:
                    await self._process_email_message(mail, msg_id)
            
            mail.close()
            mail.logout()
            
        except Exception as e:
            print(f"❌ Email check failed: {e}")
    
    async def _process_email_message(self, mail, msg_id):
        """Process individual email message"""
        
        try:
            # Fetch email message
            status, msg_data = mail.fetch(msg_id, '(RFC822)')
            
            if status == 'OK':
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Extract email details
                sender = email_message['From']
                subject = email_message['Subject'] or ""
                
                print(f"📨 Processing email from {sender}")
                print(f"📝 Subject: {subject}")
                
                # Check if email has attachments
                attachments = self._extract_attachments(email_message)
                
                if attachments:
                    for attachment in attachments:
                        await self._process_photo_attachment(attachment, subject, sender)
                else:
                    print("⚠️ No photo attachments found in email")
                
                # Mark as read
                mail.store(msg_id, '+FLAGS', '\\Seen')
                
        except Exception as e:
            print(f"❌ Email processing error: {e}")
    
    def _extract_attachments(self, email_message) -> List[Dict]:
        """Extract photo attachments from email"""
        
        attachments = []
        
        for part in email_message.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                
                if filename and any(ext in filename.lower() for ext in ['.jpg', '.jpeg', '.png']):
                    attachment_data = part.get_payload(decode=True)
                    
                    attachments.append({
                        'filename': filename,
                        'data': attachment_data,
                        'content_type': part.get_content_type()
                    })
                    
                    print(f"📎 Found photo attachment: {filename}")
        
        return attachments
    
    async def _process_photo_attachment(self, attachment: Dict, subject: str, sender: str):
        """Process individual photo attachment"""
        
        try:
            print(f"📸 Processing photo: {attachment['filename']}")
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.jpg',
                prefix=f"email_upload_{int(time.time())}_"
            )
            
            with temp_file as f:
                f.write(attachment['data'])
            
            # Analyze email content
            analysis = await self._analyze_email_content(subject, sender, attachment['filename'])
            
            # Generate guest description
            description = await self._generate_guest_description(temp_file.name, analysis)
            
            # Upload to S3
            s3_result = await self._upload_to_s3(temp_file.name, analysis, description)
            
            # Update database
            if s3_result["success"]:
                db_result = await self._update_database(analysis, s3_result["s3_url"], description)
                
                if db_result["success"]:
                    # Send confirmation email
                    await self._send_confirmation_email(sender, {
                        "success": True,
                        "filename": attachment['filename'],
                        "s3_url": s3_result["s3_url"],
                        "description": description,
                        "hotel": analysis["hotel_name"],
                        "category": analysis["category"]
                    })
            
            # Clean up temp file
            try:
                os.unlink(temp_file.name)
            except:
                pass
                
        except Exception as e:
            print(f"❌ Photo processing error: {e}")
    
    async def _analyze_email_content(self, subject: str, sender: str, filename: str) -> Dict:
        """Analyze email content to determine hotel and category"""
        
        if llm:
            try:
                analysis_prompt = f"""
                Analyze this email photo upload from hotel staff:
                
                EMAIL SUBJECT: {subject}
                SENDER: {sender}
                FILENAME: {filename}
                
                Determine hotel and categorize:
                
                HOTELS:
                - Grand Hyatt → "grand_hyatt_kuala_lumpur"
                - Sam Hotel → "sam_hotel_kl"
                - Marina Court → "marina_court_resort_kk"
                
                CATEGORIES:
                - "hotel": lobby, exterior, entrance
                - "room": bedrooms, suites, bathrooms
                - "facility": pool, spa, gym, restaurant
                
                Return JSON:
                {{
                    "hotel_id": "grand_hyatt_kuala_lumpur",
                    "hotel_name": "Grand Hyatt Kuala Lumpur",
                    "category": "room",
                    "features": "deluxe king room"
                }}
                """
                
                response = llm.invoke([{"role": "user", "content": analysis_prompt}])
                analysis_text = response.content.strip()
                
                if "```json" in analysis_text:
                    analysis_text = analysis_text.split("```json")[1].split("```")[0]
                
                analysis = json.loads(analysis_text)
                print(f"🧠 Email Analysis: {analysis}")
                return analysis
                
            except Exception as e:
                print(f"⚠️ AI analysis failed: {e}")
        
        # Fallback analysis based on subject/filename
        subject_lower = subject.lower()
        filename_lower = filename.lower()
        
        # Determine category
        if any(word in subject_lower or word in filename_lower for word in ['pool', 'spa', 'gym', 'restaurant']):
            category = "facility"
        elif any(word in subject_lower or word in filename_lower for word in ['room', 'bedroom', 'suite']):
            category = "room"
        else:
            category = "hotel"
        
        return {
            "hotel_id": "grand_hyatt_kuala_lumpur",
            "hotel_name": "Grand Hyatt Kuala Lumpur",
            "category": category,
            "features": subject[:50] if subject else "hotel feature"
        }
    
    async def _generate_guest_description(self, image_path: str, analysis: Dict) -> str:
        """Generate guest-friendly description"""
        
        try:
            if llm and os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode()
                
                prompt = f"Create appealing 80-char description for {analysis['category']} photo from {analysis['hotel_name']}"
                
                llm_vision = ChatOpenAI(openai_api_key=***REMOVED***, model="gpt-4o-mini")
                response = llm_vision.invoke([{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                }])
                
                return response.content.strip()[:100]
                
        except Exception as e:
            print(f"⚠️ Description generation failed: {e}")
        
        return f"{analysis['hotel_name']} {analysis['category']} - {analysis['features']}"
    
    async def _upload_to_s3(self, file_path: str, analysis: Dict, description: str) -> Dict:
        """Upload to AWS S3"""
        
        try:
            timestamp = int(time.time())
            features_clean = analysis['features'].replace(' ', '_').lower()[:30]
            filename = f"{analysis['category']}_{features_clean}_{timestamp}.jpg"
            s3_key = f"hotels/{analysis['hotel_id']}/{filename}"
            
            s3_client.upload_file(
                file_path,
                AWS_BUCKET_NAME,
                s3_key,
                ExtraArgs={
                    'ContentType': 'image/jpeg',
                    'ACL': 'public-read',
                    'Metadata': {
                        'hotel': analysis['hotel_name'],
                        'category': analysis['category'],
                        'description': description,
                        'uploaded_via': 'email'
                    }
                }
            )
            
            s3_url = f"https://{AWS_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
            return {"success": True, "s3_url": s3_url}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _update_database(self, analysis: Dict, s3_url: str, description: str) -> Dict:
        """Update database with photo URL"""
        
        try:
            with sqlite3.connect("ella.db") as conn:
                cursor = conn.cursor()
                photo_entry = {"url": s3_url, "description": description}
                
                if analysis["category"] == "room":
                    cursor.execute("""
                        SELECT property_id, photo_urls FROM room_types rt
                        JOIN hotels h ON rt.property_id = h.property_id
                        WHERE LOWER(h.hotel_name) LIKE LOWER(?) LIMIT 1
                    """, [f"%{analysis['hotel_name']}%"])
                    
                    result = cursor.fetchone()
                    if result:
                        property_id, existing = result
                        photos = json.loads(existing) if existing else {"room_photos": []}
                        if "room_photos" not in photos:
                            photos["room_photos"] = []
                        photos["room_photos"].append(photo_entry)
                        
                        cursor.execute("UPDATE room_types SET photo_urls = ? WHERE property_id = ?",
                                     [json.dumps(photos), property_id])
                else:
                    cursor.execute("SELECT photo_urls FROM hotels WHERE LOWER(hotel_name) LIKE LOWER(?)",
                                 [f"%{analysis['hotel_name']}%"])
                    
                    result = cursor.fetchone()
                    if result:
                        existing = result[0]
                        photos = json.loads(existing) if existing else {"hotel_photos": [], "facility_photos": []}
                        
                        if analysis["category"] == "facility":
                            if "facility_photos" not in photos:
                                photos["facility_photos"] = []
                            photos["facility_photos"].append(photo_entry)
                        else:
                            if "hotel_photos" not in photos:
                                photos["hotel_photos"] = []
                            photos["hotel_photos"].append(photo_entry)
                        
                        cursor.execute("UPDATE hotels SET photo_urls = ? WHERE LOWER(hotel_name) LIKE LOWER(?)",
                                     [json.dumps(photos), f"%{analysis['hotel_name']}%"])
                
                conn.commit()
                return {"success": True}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _send_confirmation_email(self, recipient: str, result: Dict):
        """Send confirmation email to hotel staff"""
        
        try:
            import smtplib
            
            msg = MIMEMultipart()
            msg['From'] = EMAIL_USERNAME
            msg['To'] = recipient
            msg['Subject'] = "✅ Photo Upload Successful"
            
            body = f"""Hotel Photo Upload Confirmation

✅ Photo uploaded successfully!

📁 File: {result['filename']}
🏨 Hotel: {result['hotel']}
📂 Category: {result['category'].title()}
🤖 Description: {result['description']}

📋 Guests can now request this photo via chat assistant!

Example requests:
• "Show me {result['category']} photos"
• "I want to see hotel images"

🌐 Cloud URL: {result['s3_url']}

Thank you for using our photo upload system!
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email (configure SMTP settings)
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            text = msg.as_string()
            server.sendmail(EMAIL_USERNAME, recipient, text)
            server.quit()
            
            print(f"✅ Confirmation email sent to {recipient}")
            
        except Exception as e:
            print(f"❌ Confirmation email failed: {e}")

async def main():
    """Main email processing loop"""
    
    processor = EmailUploadProcessor()
    
    print("📧 EMAIL PHOTO UPLOAD PROCESSOR")
    print("="*40)
    print(f"📬 Monitoring: {EMAIL_USERNAME}")
    print("📸 Hotel staff can email photos to this address")
    print("🤖 AI will categorize and make available for guest requests")
    print("="*40)
    
    while True:
        try:
            await processor.check_for_new_photos()
            print("⏱️ Waiting 60 seconds before next check...")
            await asyncio.sleep(60)  # Check every minute
            
        except KeyboardInterrupt:
            print("\n🛑 Stopping email processor...")
            break
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    print("🚀 Starting Email Photo Upload Processor")
    asyncio.run(main()) 