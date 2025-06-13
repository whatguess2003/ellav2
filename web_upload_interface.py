#!/usr/bin/env python3
"""
Web Upload Interface for Hotel Staff
Simple alternative to WhatsApp media uploads

Hotel Staff → Web Form → S3 → Database → Guest Access via WhatsApp
"""

import os
import json
import sqlite3
import time
import boto3
import base64
from typing import Dict
from flask import Flask, request, render_template_string, redirect, url_for, flash

# AI imports
from langchain_openai import ChatOpenAI

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
AWS_BUCKET_NAME = "ella-hotel-media"

# Initialize clients
s3_client = boto3.client('s3', region_name='ap-southeast-1')
llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model="gpt-4o", temperature=0.3) if OPENAI_API_KEY else None

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# HTML Template for upload form
UPLOAD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Hotel Photo Upload</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, select, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        button { background: #007bff; color: white; padding: 15px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        button:hover { background: #0056b3; }
        .success { color: green; padding: 10px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px; }
        .error { color: red; padding: 10px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 5px; }
        .preview { max-width: 300px; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>🏨 Hotel Photo Upload</h1>
    
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    
    <form method="POST" enctype="multipart/form-data">
        <div class="form-group">
            <label for="hotel">Hotel:</label>
            <select id="hotel" name="hotel" required>
                <option value="">Select Hotel</option>
                <option value="grand_hyatt_kuala_lumpur">Grand Hyatt Kuala Lumpur</option>
                <option value="sam_hotel_kl">Sam Hotel Kuala Lumpur</option>
                <option value="marina_court_resort_kk">Marina Court Resort Kota Kinabalu</option>
            </select>
        </div>
        
        <div class="form-group">
            <label for="category">Category:</label>
            <select id="category" name="category" required>
                <option value="">Select Category</option>
                <option value="hotel">Hotel (Lobby, Exterior, Entrance)</option>
                <option value="room">Room (Bedroom, Suite, Bathroom)</option>
                <option value="facility">Facility (Pool, Spa, Gym, Restaurant)</option>
            </select>
        </div>
        
        <div class="form-group">
            <label for="description">Description:</label>
            <textarea id="description" name="description" rows="3" placeholder="e.g., Deluxe king room with city view" required></textarea>
        </div>
        
        <div class="form-group">
            <label for="photo">Photo:</label>
            <input type="file" id="photo" name="photo" accept="image/*" required onchange="previewImage(this)">
            <img id="preview" class="preview" style="display:none;">
        </div>
        
        <button type="submit">📸 Upload Photo</button>
    </form>
    
    <script>
        function previewImage(input) {
            if (input.files && input.files[0]) {
                var reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('preview').src = e.target.result;
                    document.getElementById('preview').style.display = 'block';
                }
                reader.readAsDataURL(input.files[0]);
            }
        }
    </script>
</body>
</html>
"""

class WebUploadHandler:
    """Handle web-based photo uploads"""
    
    async def process_upload(self, form_data: Dict, file_data) -> Dict:
        """Process uploaded photo from web form"""
        
        try:
            # Extract form data
            hotel_id = form_data.get('hotel')
            category = form_data.get('category')
            description = form_data.get('description')
            
            # Map hotel IDs to names
            hotel_names = {
                'grand_hyatt_kuala_lumpur': 'Grand Hyatt Kuala Lumpur',
                'sam_hotel_kl': 'Sam Hotel Kuala Lumpur',
                'marina_court_resort_kk': 'Marina Court Resort Kota Kinabalu'
            }
            
            analysis = {
                'hotel_id': hotel_id,
                'hotel_name': hotel_names.get(hotel_id, 'Unknown Hotel'),
                'category': category,
                'features': description
            }
            
            print(f"📥 Processing web upload: {analysis}")
            
            # Save uploaded file temporarily
            temp_path = f"/tmp/upload_{int(time.time())}.jpg"
            file_data.save(temp_path)
            
            # Generate AI description if available
            ai_description = await self._generate_ai_description(temp_path, analysis)
            
            # Upload to S3
            s3_result = await self._upload_to_s3(temp_path, analysis, ai_description)
            
            # Update database
            if s3_result["success"]:
                db_result = await self._update_database(analysis, s3_result["s3_url"], ai_description)
                
                if db_result["success"]:
                    # Clean up temp file
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
                    
                    return {
                        "success": True,
                        "s3_url": s3_result["s3_url"],
                        "description": ai_description,
                        "hotel": analysis["hotel_name"],
                        "category": analysis["category"]
                    }
            
            return {"success": False, "error": "Upload or database update failed"}
            
        except Exception as e:
            print(f"❌ Web upload processing error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_ai_description(self, image_path: str, analysis: Dict) -> str:
        """Generate guest-friendly description"""
        
        try:
            if llm and os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode()
                
                prompt = f"Create an appealing 80-character description for hotel guests viewing this {analysis['category']} photo from {analysis['hotel_name']}. Focus on luxury and comfort."
                
                llm_vision = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model="gpt-4o-mini")
                response = llm_vision.invoke([{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                }])
                
                ai_description = response.content.strip()[:100]
                print(f"🤖 AI Description: {ai_description}")
                return ai_description
                
        except Exception as e:
            print(f"⚠️ AI description failed: {e}")
        
        return f"{analysis['hotel_name']} {analysis['category']} - {analysis['features']}"
    
    async def _upload_to_s3(self, file_path: str, analysis: Dict, description: str) -> Dict:
        """Upload to AWS S3"""
        
        try:
            timestamp = int(time.time())
            features_clean = analysis['features'].replace(' ', '_').lower()[:30]
            filename = f"{analysis['category']}_{features_clean}_{timestamp}.jpg"
            s3_key = f"hotels/{analysis['hotel_id']}/{filename}"
            
            print(f"📤 Uploading to S3: {s3_key}")
            
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
                        'uploaded_via': 'web_interface'
                    }
                }
            )
            
            s3_url = f"https://{AWS_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
            return {"success": True, "s3_url": s3_url}
            
        except Exception as e:
            print(f"❌ S3 upload failed: {e}")
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
            print(f"❌ Database update failed: {e}")
            return {"success": False, "error": str(e)}

# Initialize handler
upload_handler = WebUploadHandler()

@app.route('/', methods=['GET', 'POST'])
def upload_form():
    """Main upload form"""
    
    if request.method == 'POST':
        try:
            form_data = request.form.to_dict()
            file_data = request.files['photo']
            
            if file_data.filename == '':
                flash('No file selected', 'error')
                return redirect(url_for('upload_form'))
            
            # Process upload
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(upload_handler.process_upload(form_data, file_data))
            loop.close()
            
            if result["success"]:
                flash(f'✅ Photo uploaded successfully! Hotel: {result["hotel"]}, Category: {result["category"]}. Guests can now request this photo via chat assistant.', 'success')
            else:
                flash(f'❌ Upload failed: {result["error"]}', 'error')
                
        except Exception as e:
            flash(f'❌ Upload error: {str(e)}', 'error')
        
        return redirect(url_for('upload_form'))
    
    return render_template_string(UPLOAD_TEMPLATE)

@app.route('/health')
def health():
    return {"status": "healthy", "service": "web-upload-interface"}

if __name__ == "__main__":
    print("🌐 WEB UPLOAD INTERFACE FOR HOTEL PHOTOS")
    print("📸 Alternative to WhatsApp media uploads")
    print("🔗 Access: http://localhost:5000")
    print("🎯 Hotel staff can upload photos via web browser")
    print("💬 Guests still access photos via WhatsApp chat assistant")
    
    app.run(host='0.0.0.0', port=5000, debug=True) 