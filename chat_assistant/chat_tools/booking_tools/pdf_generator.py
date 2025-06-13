#!/usr/bin/env python3
"""
PDF Document Generator for Ella Hotel Assistant
Creates professional PDFs for bookings, invoices, payment receipts, and other guest documents.
Enhanced to support multiple document types and booking agent integration.
"""

import os
import qrcode
import tempfile
import atexit
from datetime import datetime
from typing import Dict, Optional, Literal
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from langchain_core.tools import tool
import io
import base64

# Global list to track temporary files for cleanup
_temp_files = []

def cleanup_temp_files():
    """Clean up all temporary PDF files"""
    global _temp_files
    for file_path in _temp_files[:]:
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                print(f"Cleaned up temporary PDF: {file_path}")
            _temp_files.remove(file_path)
        except Exception as e:
            print(f"Failed to cleanup {file_path}: {e}")

# Register cleanup function to run on exit
atexit.register(cleanup_temp_files)

class EllaPDFGenerator:
    """Enhanced PDF generator for multiple document types"""
    
    def __init__(self, output_dir: str = "generated_documents", use_temp_files: bool = False):
        self.output_dir = output_dir
        self.use_temp_files = use_temp_files
        
        # Create output directory structure if not using temp files
        if not use_temp_files:
            os.makedirs(output_dir, exist_ok=True)
            # Create subdirectories for each document type
            subdirs = ['booking_confirmations', 'invoices', 'payment_receipts', 'cancellations']
            for subdir in subdirs:
                os.makedirs(os.path.join(output_dir, subdir), exist_ok=True)
        
        # Define colors
        self.colors = {
            'primary': colors.HexColor('#128C7E'),      # Ella green
            'secondary': colors.HexColor('#075E54'),     # Dark green
            'accent': colors.HexColor('#25D366'),        # WhatsApp green
            'text': colors.HexColor('#2D2D2D'),         # Dark gray
            'light_gray': colors.HexColor('#F5F5F5'),   # Light background
            'border': colors.HexColor('#E0E0E0'),       # Light border
            'warning': colors.HexColor('#FF9800'),      # Orange
            'success': colors.HexColor('#4CAF50'),      # Green
            'error': colors.HexColor('#F44336'),        # Red
            'info': colors.HexColor('#2196F3')         # Blue
        }
        
        # Setup styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        
        # Main title style
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=self.colors['primary'],
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=self.colors['secondary'],
            spaceAfter=15,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=self.colors['primary'],
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        ))
        
        # Document reference style
        self.styles.add(ParagraphStyle(
            name='DocumentRef',
            parent=self.styles['Normal'],
            fontSize=18,
            textColor=self.colors['secondary'],
            spaceAfter=10,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            backColor=self.colors['light_gray'],
            borderColor=self.colors['border'],
            borderWidth=1,
            borderPadding=10
        ))
        
        # Important notice style
        self.styles.add(ParagraphStyle(
            name='ImportantNotice',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.colors['warning'],
            spaceAfter=10,
            spaceBefore=10,
            fontName='Helvetica-Bold',
            backColor=colors.HexColor('#FFF3E0'),
            borderColor=self.colors['warning'],
            borderWidth=1,
            borderPadding=8
        ))
        
        # Success notice style
        self.styles.add(ParagraphStyle(
            name='SuccessNotice',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=self.colors['success'],
            spaceAfter=10,
            spaceBefore=10,
            fontName='Helvetica-Bold',
            backColor=colors.HexColor('#E8F5E8'),
            borderColor=self.colors['success'],
            borderWidth=1,
            borderPadding=8
        ))
        
        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#777777'),
            alignment=TA_CENTER,
            spaceBefore=20
        ))
    
    def _generate_qr_code(self, booking_reference: str, booking_data: Dict) -> io.BytesIO:
        """Generate QR code with booking details"""
        qr_data = f"""Booking Reference: {booking_reference}
Guest: {booking_data.get('guest_name', '')}
Hotel: {booking_data.get('hotel_name', '')}
Check-in: {booking_data.get('check_in_date', '')}
Check-out: {booking_data.get('check_out_date', '')}
Rooms: {booking_data.get('rooms_booked', 1)}
Total: RM{booking_data.get('total_price', 0):.2f}
Generated by Ella Hotel Assistant"""
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to BytesIO
        img_buffer = io.BytesIO()
        qr_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return img_buffer
    
    def _add_header(self, story, booking_data: Dict):
        """Add PDF header with logo and title"""
        
        # Main title
        story.append(Paragraph("🏨 BOOKING CONFIRMATION", self.styles['MainTitle']))
        story.append(Paragraph("Ella Hotel Assistant", self.styles['Subtitle']))
        story.append(Spacer(1, 20))
        
        # Booking reference box
        ref_text = f"Booking Reference: <b>{booking_data.get('booking_reference', 'N/A')}</b>"
        story.append(Paragraph(ref_text, self.styles['DocumentRef']))
        story.append(Spacer(1, 20))
        
        # Confirmation message
        confirmation_msg = f"""
        <para align="center" fontSize="12" textColor="{self.colors['success']}">
        ✅ <b>Your booking has been confirmed!</b><br/>
        Confirmation sent on {datetime.now().strftime('%d %B %Y at %I:%M %p')}
        </para>
        """
        story.append(Paragraph(confirmation_msg, self.styles['Normal']))
        story.append(Spacer(1, 30))
    
    def _add_guest_details(self, story, booking_data: Dict):
        """Add guest information section"""
        
        story.append(Paragraph("👤 Guest Information", self.styles['SectionHeader']))
        
        guest_data = [
            ['Guest Name:', booking_data.get('guest_name', 'N/A')],
            ['Email:', booking_data.get('guest_email', 'N/A')],
            ['Phone:', booking_data.get('guest_phone', 'N/A')],
        ]
        
        guest_table = Table(guest_data, colWidths=[2*inch, 4*inch])
        guest_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), self.colors['text']),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        story.append(guest_table)
        story.append(Spacer(1, 20))
    
    def _add_hotel_details(self, story, booking_data: Dict):
        """Add hotel information section"""
        
        story.append(Paragraph("🏨 Hotel Information", self.styles['SectionHeader']))
        
        hotel_data = [
            ['Hotel Name:', booking_data.get('hotel_name', 'N/A')],
            ['Location:', booking_data.get('hotel_location', booking_data.get('city_name', 'N/A'))],
            ['Address:', booking_data.get('hotel_address', 'N/A')],
            ['Phone:', booking_data.get('hotel_phone', 'N/A')],
        ]
        
        hotel_table = Table(hotel_data, colWidths=[2*inch, 4*inch])
        hotel_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), self.colors['text']),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        story.append(hotel_table)
        story.append(Spacer(1, 20))
    
    def _add_booking_details(self, story, booking_data: Dict):
        """Add booking details section"""
        
        story.append(Paragraph("📅 Booking Details", self.styles['SectionHeader']))
        
        # Format dates nicely
        try:
            checkin = datetime.strptime(booking_data.get('check_in_date', ''), '%Y-%m-%d')
            checkout = datetime.strptime(booking_data.get('check_out_date', ''), '%Y-%m-%d')
            checkin_formatted = checkin.strftime('%A, %d %B %Y')
            checkout_formatted = checkout.strftime('%A, %d %B %Y')
        except:
            checkin_formatted = booking_data.get('check_in_date', 'N/A')
            checkout_formatted = booking_data.get('check_out_date', 'N/A')
        
        booking_details = [
            ['Room Type:', booking_data.get('room_name', 'N/A')],
            ['Check-in Date:', checkin_formatted],
            ['Check-out Date:', checkout_formatted],
            ['Number of Nights:', str(booking_data.get('nights', 'N/A'))],
            ['Number of Rooms:', str(booking_data.get('rooms_booked', 'N/A'))],
            ['Total Amount:', f"RM{booking_data.get('total_price', 0):.2f}"],
        ]
        
        booking_table = Table(booking_details, colWidths=[2*inch, 4*inch])
        booking_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), self.colors['text']),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            # Highlight total amount
            ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 5), (-1, 5), 12),
            ('TEXTCOLOR', (1, 5), (1, 5), self.colors['primary']),
        ]))
        
        story.append(booking_table)
        story.append(Spacer(1, 20))
        
        # Special requests if any
        if booking_data.get('special_requests'):
            story.append(Paragraph("📝 Special Requests", self.styles['SectionHeader']))
            story.append(Paragraph(booking_data['special_requests'], self.styles['Normal']))
            story.append(Spacer(1, 20))
    
    def _add_qr_code_and_important_info(self, story, booking_data: Dict):
        """Add QR code and important information"""
        
        # Create a table with QR code and important info side by side
        qr_buffer = self._generate_qr_code(booking_data.get('booking_reference', ''), booking_data)
        qr_image = Image(qr_buffer, width=1.5*inch, height=1.5*inch)
        
        important_info = """
        <b>Important Information:</b><br/>
        • Please bring a valid ID for check-in<br/>
        • Check-in time: 3:00 PM<br/>
        • Check-out time: 12:00 PM<br/>
        • Contact hotel directly for early check-in<br/>
        • Show this confirmation or QR code at hotel
        """
        
        qr_info_data = [
            [qr_image, Paragraph(important_info, self.styles['Normal'])]
        ]
        
        qr_info_table = Table(qr_info_data, colWidths=[2*inch, 4*inch])
        qr_info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        story.append(Paragraph("📱 QR Code & Important Information", self.styles['SectionHeader']))
        story.append(qr_info_table)
        story.append(Spacer(1, 20))
    
    def _add_cancellation_policy(self, story):
        """Add cancellation policy"""
        
        story.append(Paragraph("❌ Cancellation Policy", self.styles['SectionHeader']))
        
        policy_text = """
        <para fontSize="10" spaceBefore="5" spaceAfter="5">
        • <b>Free cancellation</b> up to 24 hours before check-in<br/>
        • Cancellations within 24 hours are subject to one night's charge<br/>
        • No-shows will be charged the full stay amount<br/>
        • To cancel or modify your booking, contact us with your booking reference<br/>
        • Modifications subject to availability and rate changes
        </para>
        """
        
        story.append(Paragraph(policy_text, self.styles['Normal']))
        story.append(Spacer(1, 20))
    
    def _add_footer(self, story, booking_data: Dict, document_type: str):
        """Add footer with contact information"""
        
        footer_text = f"""
        Generated by Ella Hotel Assistant on {datetime.now().strftime('%d %B %Y at %I:%M %p')}<br/>
        For support, contact: support@ella-assistant.com | +60 3-1234 5678<br/>
        Booking Reference: {booking_data.get('booking_reference', 'N/A')} | Thank you for choosing us! 🙏
        """
        
        story.append(Spacer(1, 30))
        story.append(Paragraph(footer_text, self.styles['Footer']))
    
    def generate_booking_confirmation(self, booking_data: Dict) -> str:
        """Generate booking confirmation PDF"""
        return self._generate_document(booking_data, "booking_confirmation")
    
    def generate_invoice(self, booking_data: Dict) -> str:
        """Generate invoice PDF"""
        return self._generate_document(booking_data, "invoice")
    
    def generate_payment_receipt(self, payment_data: Dict) -> str:
        """Generate payment receipt PDF"""
        return self._generate_document(payment_data, "payment_receipt")
    
    def generate_cancellation_confirmation(self, cancellation_data: Dict) -> str:
        """Generate cancellation confirmation PDF"""
        return self._generate_document(cancellation_data, "cancellation_confirmation")
    
    def _generate_document(self, data: Dict, document_type: str) -> str:
        """Generate PDF document based on type"""
        
        reference = data.get('booking_reference', data.get('reference', 'unknown'))
        
        # Create self-explanatory filenames with actual booking reference
        filename_map = {
            'booking_confirmation': f"booking_confirmation_{reference}.pdf",
            'invoice': f"invoice_{reference}.pdf",
            'payment_receipt': f"payment_receipt_{reference}.pdf",
            'cancellation_confirmation': f"cancellation_{reference}.pdf"
        }
        
        filename = filename_map.get(document_type, f"{document_type}_{reference}.pdf")
        
        if self.use_temp_files:
            # Create temporary file
            temp_fd, filepath = tempfile.mkstemp(suffix='.pdf', prefix=f'{document_type}_{reference}_')
            os.close(temp_fd)  # Close the file descriptor, we'll use the path
            
            # Track for cleanup
            global _temp_files
            _temp_files.append(filepath)
            print(f"Generated temporary PDF: {filepath}")
        else:
            # Use permanent file in appropriate subdirectory with self-explanatory name
            subdir_map = {
                'booking_confirmation': 'booking_confirmations',
                'invoice': 'invoices', 
                'payment_receipt': 'payment_receipts',
                'cancellation_confirmation': 'cancellations'
            }
            subdir = subdir_map.get(document_type, 'booking_confirmations')
            filepath = os.path.join(self.output_dir, subdir, filename)
            print(f"Generating PDF: {filepath}")
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        # Build the story based on document type
        story = []
        
        if document_type == "booking_confirmation":
            self._build_booking_confirmation(story, data)
        elif document_type == "invoice":
            self._build_invoice(story, data)
        elif document_type == "payment_receipt":
            self._build_payment_receipt(story, data)
        elif document_type == "cancellation_confirmation":
            self._build_cancellation_confirmation(story, data)
        
        # Build the PDF
        doc.build(story)
        
        print(f"✅ PDF generated successfully: {filepath}")
        return filepath
    
    def _build_booking_confirmation(self, story, booking_data: Dict):
        """Build booking confirmation document"""
        # Header
        story.append(Paragraph("🏨 BOOKING CONFIRMATION", self.styles['MainTitle']))
        story.append(Paragraph("Ella Hotel Assistant", self.styles['Subtitle']))
        story.append(Spacer(1, 20))
        
        # Booking reference
        ref_text = f"Booking Reference: <b>{booking_data.get('booking_reference', 'N/A')}</b>"
        story.append(Paragraph(ref_text, self.styles['DocumentRef']))
        story.append(Spacer(1, 20))
        
        # Confirmation message
        confirmation_msg = f"""
        <para align="center" fontSize="12" textColor="{self.colors['success']}">
        ✅ <b>Your booking has been confirmed!</b><br/>
        Confirmation sent on {datetime.now().strftime('%d %B %Y at %I:%M %p')}
        </para>
        """
        story.append(Paragraph(confirmation_msg, self.styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Add all sections
        self._add_guest_details(story, booking_data)
        self._add_hotel_details(story, booking_data)
        self._add_booking_details(story, booking_data)
        self._add_qr_code_and_important_info(story, booking_data)
        self._add_cancellation_policy(story)
        self._add_footer(story, booking_data, "booking_confirmation")
    
    def _build_invoice(self, story, booking_data: Dict):
        """Build invoice document"""
        # Header
        story.append(Paragraph("🧾 INVOICE", self.styles['MainTitle']))
        story.append(Paragraph("Ella Hotel Assistant", self.styles['Subtitle']))
        story.append(Spacer(1, 20))
        
        # Invoice reference
        ref_text = f"Invoice #: <b>INV-{booking_data.get('booking_reference', 'N/A')}</b>"
        story.append(Paragraph(ref_text, self.styles['DocumentRef']))
        story.append(Spacer(1, 20))
        
        # Invoice date
        invoice_msg = f"""
        <para align="center" fontSize="12" textColor="{self.colors['info']}">
        📅 <b>Invoice Date:</b> {datetime.now().strftime('%d %B %Y')}<br/>
        💳 <b>Payment Status:</b> {booking_data.get('payment_status', 'PENDING')}
        </para>
        """
        story.append(Paragraph(invoice_msg, self.styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Add invoice-specific sections
        self._add_guest_details(story, booking_data)
        self._add_hotel_details(story, booking_data)
        self._add_invoice_details(story, booking_data)
        self._add_payment_instructions(story, booking_data)
        self._add_footer(story, booking_data, "invoice")
    
    def _build_payment_receipt(self, story, payment_data: Dict):
        """Build payment receipt document"""
        # Header
        story.append(Paragraph("🧾 PAYMENT RECEIPT", self.styles['MainTitle']))
        story.append(Paragraph("Ella Hotel Assistant", self.styles['Subtitle']))
        story.append(Spacer(1, 20))
        
        # Receipt reference
        ref_text = f"Receipt #: <b>RCP-{payment_data.get('booking_reference', 'N/A')}</b>"
        story.append(Paragraph(ref_text, self.styles['DocumentRef']))
        story.append(Spacer(1, 20))
        
        # Payment confirmation
        payment_msg = f"""
        <para align="center" fontSize="12" textColor="{self.colors['success']}">
        ✅ <b>Payment Received Successfully!</b><br/>
        Payment processed on {datetime.now().strftime('%d %B %Y at %I:%M %p')}
        </para>
        """
        story.append(Paragraph(payment_msg, self.styles['SuccessNotice']))
        story.append(Spacer(1, 30))
        
        # Add payment-specific sections
        self._add_payment_details(story, payment_data)
        self._add_booking_summary(story, payment_data)
        self._add_footer(story, payment_data, "payment_receipt")
    
    def _build_cancellation_confirmation(self, story, cancellation_data: Dict):
        """Build cancellation confirmation document"""
        # Header
        story.append(Paragraph("❌ CANCELLATION CONFIRMATION", self.styles['MainTitle']))
        story.append(Paragraph("Ella Hotel Assistant", self.styles['Subtitle']))
        story.append(Spacer(1, 20))
        
        # Cancellation reference
        ref_text = f"Cancellation #: <b>CXL-{cancellation_data.get('booking_reference', 'N/A')}</b>"
        story.append(Paragraph(ref_text, self.styles['DocumentRef']))
        story.append(Spacer(1, 20))
        
        # Cancellation message
        cancel_msg = f"""
        <para align="center" fontSize="12" textColor="{self.colors['error']}">
        ❌ <b>Booking Cancelled Successfully</b><br/>
        Cancelled on {datetime.now().strftime('%d %B %Y at %I:%M %p')}
        </para>
        """
        story.append(Paragraph(cancel_msg, self.styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Add cancellation-specific sections
        self._add_cancellation_details(story, cancellation_data)
        self._add_refund_information(story, cancellation_data)
        self._add_footer(story, cancellation_data, "cancellation_confirmation")

    def _add_invoice_details(self, story, booking_data: Dict):
        """Add invoice-specific pricing breakdown"""
        
        story.append(Paragraph("💰 Invoice Details", self.styles['SectionHeader']))
        
        # Detailed pricing breakdown
        invoice_details = [
            ['Description', 'Quantity', 'Unit Price', 'Total'],
            [booking_data.get('room_name', 'Room'), 
             f"{booking_data.get('nights', 1)} nights × {booking_data.get('rooms_booked', 1)} rooms",
             f"RM{booking_data.get('room_rate', 0):.2f}",
             f"RM{booking_data.get('room_total', 0):.2f}"],
        ]
        
        # Add services if any
        if booking_data.get('breakfast_total', 0) > 0:
            invoice_details.append([
                'Breakfast', 
                f"{booking_data.get('nights', 1)} nights × {booking_data.get('adults', 1)} guests",
                f"RM{booking_data.get('breakfast_rate', 0):.2f}",
                f"RM{booking_data.get('breakfast_total', 0):.2f}"
            ])
        
        # Add taxes and charges
        if booking_data.get('service_charge', 0) > 0:
            invoice_details.append([
                'Service Charge (10%)', '', '', 
                f"RM{booking_data.get('service_charge', 0):.2f}"
            ])
        
        if booking_data.get('government_tax', 0) > 0:
            invoice_details.append([
                'Government Tax (6%)', '', '', 
                f"RM{booking_data.get('government_tax', 0):.2f}"
            ])
        
        # Total
        invoice_details.append([
            '', '', 'TOTAL AMOUNT:', 
            f"RM{booking_data.get('total_price', 0):.2f}"
        ])
        
        invoice_table = Table(invoice_details, colWidths=[3*inch, 1.5*inch, 1*inch, 1*inch])
        invoice_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['light_gray']),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.colors['text']),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('GRID', (0, 0), (-1, -2), 1, self.colors['border']),
            # Highlight total
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('BACKGROUND', (0, -1), (-1, -1), self.colors['primary']),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ]))
        
        story.append(invoice_table)
        story.append(Spacer(1, 20))
    
    def _add_payment_instructions(self, story, booking_data: Dict):
        """Add payment instructions for invoice"""
        
        story.append(Paragraph("💳 Payment Instructions", self.styles['SectionHeader']))
        
        payment_window = booking_data.get('payment_window', 'Prior to check-in')
        payment_methods = booking_data.get('payment_methods', 'Credit Card, Online Banking, PayPal')
        
        instructions = f"""
        <para fontSize="10" spaceBefore="5" spaceAfter="5">
        <b>Payment Due:</b> {payment_window}<br/>
        <b>Accepted Methods:</b> {payment_methods}<br/>
        <b>Booking Reference:</b> {booking_data.get('booking_reference', 'N/A')}<br/>
        <b>Amount Due:</b> RM{booking_data.get('total_price', 0):.2f}<br/><br/>
        
        Please ensure payment is completed within the specified timeframe to secure your reservation.
        For payment assistance, contact our support team.
        </para>
        """
        
        story.append(Paragraph(instructions, self.styles['ImportantNotice']))
        story.append(Spacer(1, 20))
    
    def _add_payment_details(self, story, payment_data: Dict):
        """Add payment transaction details"""
        
        story.append(Paragraph("💳 Payment Details", self.styles['SectionHeader']))
        
        payment_details = [
            ['Transaction ID:', payment_data.get('transaction_id', 'N/A')],
            ['Payment Method:', payment_data.get('payment_method', 'N/A')],
            ['Amount Paid:', f"RM{payment_data.get('amount_paid', 0):.2f}"],
            ['Payment Date:', payment_data.get('payment_date', datetime.now().strftime('%d %B %Y'))],
            ['Payment Status:', payment_data.get('payment_status', 'COMPLETED')],
        ]
        
        payment_table = Table(payment_details, colWidths=[2*inch, 4*inch])
        payment_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), self.colors['text']),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            # Highlight amount
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 2), (-1, 2), 12),
            ('TEXTCOLOR', (1, 2), (1, 2), self.colors['success']),
        ]))
        
        story.append(payment_table)
        story.append(Spacer(1, 20))
    
    def _add_booking_summary(self, story, booking_data: Dict):
        """Add booking summary for payment receipt"""
        
        story.append(Paragraph("📋 Booking Summary", self.styles['SectionHeader']))
        
        summary_details = [
            ['Booking Reference:', booking_data.get('booking_reference', 'N/A')],
            ['Hotel:', booking_data.get('hotel_name', 'N/A')],
            ['Room Type:', booking_data.get('room_name', 'N/A')],
            ['Guest Name:', booking_data.get('guest_name', 'N/A')],
            ['Check-in:', booking_data.get('check_in_date', 'N/A')],
            ['Check-out:', booking_data.get('check_out_date', 'N/A')],
            ['Nights:', str(booking_data.get('nights', 'N/A'))],
        ]
        
        summary_table = Table(summary_details, colWidths=[2*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), self.colors['text']),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
    
    def _add_cancellation_details(self, story, cancellation_data: Dict):
        """Add cancellation details"""
        
        story.append(Paragraph("❌ Cancellation Details", self.styles['SectionHeader']))
        
        cancellation_details = [
            ['Original Booking:', cancellation_data.get('booking_reference', 'N/A')],
            ['Hotel:', cancellation_data.get('hotel_name', 'N/A')],
            ['Guest Name:', cancellation_data.get('guest_name', 'N/A')],
            ['Original Check-in:', cancellation_data.get('check_in_date', 'N/A')],
            ['Original Check-out:', cancellation_data.get('check_out_date', 'N/A')],
            ['Cancellation Reason:', cancellation_data.get('cancellation_reason', 'Guest request')],
            ['Cancelled By:', cancellation_data.get('cancelled_by', 'Guest')],
        ]
        
        cancellation_table = Table(cancellation_details, colWidths=[2*inch, 4*inch])
        cancellation_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), self.colors['text']),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        story.append(cancellation_table)
        story.append(Spacer(1, 20))
    
    def _add_refund_information(self, story, cancellation_data: Dict):
        """Add refund information for cancellation"""
        
        story.append(Paragraph("💰 Refund Information", self.styles['SectionHeader']))
        
        refund_amount = cancellation_data.get('refund_amount', 0)
        refund_status = cancellation_data.get('refund_status', 'PROCESSING')
        refund_method = cancellation_data.get('refund_method', 'Original payment method')
        
        refund_info = f"""
        <para fontSize="10" spaceBefore="5" spaceAfter="5">
        <b>Refund Amount:</b> RM{refund_amount:.2f}<br/>
        <b>Refund Status:</b> {refund_status}<br/>
        <b>Refund Method:</b> {refund_method}<br/>
        <b>Processing Time:</b> 3-5 business days<br/><br/>
        
        Your refund will be processed according to our cancellation policy.
        You will receive a confirmation email once the refund is completed.
        </para>
        """
        
        story.append(Paragraph(refund_info, self.styles['SuccessNotice']))
        story.append(Spacer(1, 20))

    def get_pdf_url(self, reference: str, document_type: str = "booking_confirmation") -> str:
        """Get URL for accessing the PDF"""
        if self.use_temp_files:
            return f"/{document_type}/{reference}"
        else:
            subdir_map = {
                'booking_confirmation': 'booking_confirmations',
                'invoice': 'invoices', 
                'payment_receipt': 'payment_receipts',
                'cancellation_confirmation': 'cancellations'
            }
            subdir = subdir_map.get(document_type, 'booking_confirmations')
            return f"/generated_documents/{subdir}/{reference}"
    
    def get_local_file_path(self, reference: str, document_type: str = "booking_confirmation") -> str:
        """Get local file path for the PDF with self-explanatory naming"""
        if self.use_temp_files:
            return None
        
        subdir_map = {
            'booking_confirmation': 'booking_confirmations',
            'invoice': 'invoices', 
            'payment_receipt': 'payment_receipts',
            'cancellation_confirmation': 'cancellations'
        }
        subdir = subdir_map.get(document_type, 'booking_confirmations')
        subdir_path = os.path.join(self.output_dir, subdir)
        
        # Create self-explanatory filename
        filename_map = {
            'booking_confirmation': f"booking_confirmation_{reference}.pdf",
            'invoice': f"invoice_{reference}.pdf",
            'payment_receipt': f"payment_receipt_{reference}.pdf",
            'cancellation_confirmation': f"cancellation_{reference}.pdf"
        }
        
        expected_filename = filename_map.get(document_type, f"{document_type}_{reference}.pdf")
        expected_path = os.path.join(subdir_path, expected_filename)
        
        # Check if the exact file exists
        if os.path.exists(expected_path):
            return expected_path
        
        # Fallback: search for any file with this reference (for backward compatibility)
        if os.path.exists(subdir_path):
            files = [f for f in os.listdir(subdir_path) if reference in f and f.endswith('.pdf')]
            if files:
                # Sort by modification time (newest first) and return the most recent
                files_with_time = [(f, os.path.getmtime(os.path.join(subdir_path, f))) for f in files]
                files_with_time.sort(key=lambda x: x[1], reverse=True)
                return os.path.join(subdir_path, files_with_time[0][0])
        
        return None

# ==========================================
# BOOKING AGENT TOOL FUNCTIONS
# ==========================================

@tool
def generate_booking_confirmation_pdf(booking_reference: str, guest_id: str = "", use_local_storage: bool = True) -> str:
    """
    Generate booking confirmation PDF for a completed booking.
    
    Args:
        booking_reference: The booking reference number
        guest_id: Guest identifier (optional)
        use_local_storage: If True, save to local storage; if False, use temporary files
        
    Returns:
        Status message with PDF download link and local file path
    """
    try:
        # Get booking data
        from .booking_management import booking_manager
        booking_result = booking_manager.get_booking_status(booking_reference)
        
        if not booking_result['success']:
            return f"❌ Cannot generate PDF: Booking {booking_reference} not found"
        
        # Generate PDF
        generator = EllaPDFGenerator(use_temp_files=not use_local_storage)
        pdf_path = generator.generate_booking_confirmation(booking_result)
        
        # Get local file path if using local storage
        local_path = ""
        if use_local_storage:
            local_file = generator.get_local_file_path(booking_reference, "booking_confirmation")
            if local_file:
                filename = os.path.basename(local_file)
                local_path = f"\n📁 **Local File:** {filename}"
        
        return f"""
✅ Booking confirmation PDF generated successfully!

📋 **Booking Reference:** {booking_reference}
🏨 **Hotel:** {booking_result['hotel_name']}
👤 **Guest:** {booking_result['guest_name']}

📄 **Download Link:** `/booking-confirmation/{booking_reference}`{local_path}
📝 **File Name:** booking_confirmation_{booking_reference}.pdf

The PDF includes:
• Complete booking details and pricing
• QR code for easy check-in
• Hotel contact information
• Cancellation policy
• Important check-in instructions

PDF is ready for download and locally stored for easy retrieval.
"""
        
    except Exception as e:
        return f"❌ Error generating booking confirmation PDF: {str(e)}"

@tool
def generate_invoice_pdf(booking_reference: str, guest_id: str = "", use_local_storage: bool = True) -> str:
    """
    Generate invoice PDF for a booking requiring payment.
    
    Args:
        booking_reference: The booking reference number
        guest_id: Guest identifier (optional)
        use_local_storage: If True, save to local storage; if False, use temporary files
        
    Returns:
        Status message with PDF download link and local file path
    """
    try:
        # Get booking data
        from .booking_management import booking_manager
        booking_result = booking_manager.get_booking_status(booking_reference)
        
        if not booking_result['success']:
            return f"❌ Cannot generate invoice: Booking {booking_reference} not found"
        
        # Generate invoice PDF
        generator = EllaPDFGenerator(use_temp_files=not use_local_storage)
        pdf_path = generator.generate_invoice(booking_result)
        
        # Get local file path if using local storage
        local_path = ""
        if use_local_storage:
            local_file = generator.get_local_file_path(booking_reference, "invoice")
            if local_file:
                filename = os.path.basename(local_file)
                local_path = f"\n📁 **Local File:** {filename}"
        
        return f"""
🧾 Invoice PDF generated successfully!

📋 **Invoice #:** INV-{booking_reference}
🏨 **Hotel:** {booking_result['hotel_name']}
👤 **Guest:** {booking_result['guest_name']}
💰 **Amount Due:** RM{booking_result['total_price']:.2f}

📄 **Download Link:** `/invoice/{booking_reference}`{local_path}
📝 **File Name:** invoice_{booking_reference}.pdf

The invoice includes:
• Detailed pricing breakdown
• Payment instructions and methods
• Payment due date
• Booking terms and conditions

Please ensure payment is completed within the specified timeframe.
"""
        
    except Exception as e:
        return f"❌ Error generating invoice PDF: {str(e)}"

@tool
def generate_payment_receipt_pdf(booking_reference: str, transaction_id: str = "", amount_paid: float = 0.0, payment_method: str = "Credit Card", guest_id: str = "", use_local_storage: bool = True) -> str:
    """
    Generate payment receipt PDF after successful payment.
    
    Args:
        booking_reference: The booking reference number
        transaction_id: Payment transaction ID
        amount_paid: Amount that was paid
        payment_method: Method used for payment
        guest_id: Guest identifier (optional)
        use_local_storage: If True, save to local storage; if False, use temporary files
        
    Returns:
        Status message with PDF download link and local file path
    """
    try:
        # Get booking data
        from .booking_management import booking_manager
        booking_result = booking_manager.get_booking_status(booking_reference)
        
        if not booking_result['success']:
            return f"❌ Cannot generate receipt: Booking {booking_reference} not found"
        
        # Prepare payment data
        payment_data = {
            **booking_result,
            'transaction_id': transaction_id or f"TXN-{booking_reference}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'amount_paid': amount_paid or booking_result['total_price'],
            'payment_method': payment_method,
            'payment_date': datetime.now().strftime('%d %B %Y'),
            'payment_status': 'COMPLETED'
        }
        
        # Generate receipt PDF
        generator = EllaPDFGenerator(use_temp_files=not use_local_storage)
        pdf_path = generator.generate_payment_receipt(payment_data)
        
        # Get local file path if using local storage
        local_path = ""
        if use_local_storage:
            local_file = generator.get_local_file_path(booking_reference, "payment_receipt")
            if local_file:
                filename = os.path.basename(local_file)
                local_path = f"\n📁 **Local File:** {filename}"
        
        return f"""
🧾 Payment receipt PDF generated successfully!

📋 **Receipt #:** RCP-{booking_reference}
💳 **Transaction ID:** {payment_data['transaction_id']}
💰 **Amount Paid:** RM{payment_data['amount_paid']:.2f}
🏨 **Hotel:** {booking_result['hotel_name']}
👤 **Guest:** {booking_result['guest_name']}

📄 **Download Link:** `/payment-receipt/{booking_reference}`{local_path}
📝 **File Name:** payment_receipt_{booking_reference}.pdf

The receipt includes:
• Payment transaction details
• Booking summary
• Payment confirmation
• Contact information for support

Thank you for your payment! Your booking is now fully confirmed.
"""
        
    except Exception as e:
        return f"❌ Error generating payment receipt PDF: {str(e)}"

@tool
def generate_cancellation_pdf(booking_reference: str, cancellation_reason: str = "Guest request", refund_amount: float = 0.0, guest_id: str = "", use_local_storage: bool = True) -> str:
    """
    Generate cancellation confirmation PDF after booking cancellation.
    
    Args:
        booking_reference: The booking reference number
        cancellation_reason: Reason for cancellation
        refund_amount: Amount to be refunded
        guest_id: Guest identifier (optional)
        use_local_storage: If True, save to local storage; if False, use temporary files
        
    Returns:
        Status message with PDF download link and local file path
    """
    try:
        # Get booking data
        from .booking_management import booking_manager
        booking_result = booking_manager.get_booking_status(booking_reference)
        
        if not booking_result['success']:
            return f"❌ Cannot generate cancellation PDF: Booking {booking_reference} not found"
        
        # Prepare cancellation data
        cancellation_data = {
            **booking_result,
            'cancellation_reason': cancellation_reason,
            'cancelled_by': 'Guest',
            'refund_amount': refund_amount,
            'refund_status': 'PROCESSING' if refund_amount > 0 else 'NO REFUND',
            'refund_method': 'Original payment method'
        }
        
        # Generate cancellation PDF
        generator = EllaPDFGenerator(use_temp_files=not use_local_storage)
        pdf_path = generator.generate_cancellation_confirmation(cancellation_data)
        
        # Get local file path if using local storage
        local_path = ""
        if use_local_storage:
            local_file = generator.get_local_file_path(booking_reference, "cancellation_confirmation")
            if local_file:
                filename = os.path.basename(local_file)
                local_path = f"\n📁 **Local File:** {filename}"
        
        return f"""
❌ Cancellation confirmation PDF generated successfully!

📋 **Cancellation #:** CXL-{booking_reference}
🏨 **Hotel:** {booking_result['hotel_name']}
👤 **Guest:** {booking_result['guest_name']}
💰 **Refund Amount:** RM{refund_amount:.2f}

📄 **Download Link:** `/cancellation/{booking_reference}`{local_path}
📝 **File Name:** cancellation_{booking_reference}.pdf

The cancellation confirmation includes:
• Original booking details
• Cancellation reason and date
• Refund information and processing time
• Contact information for support

Your cancellation has been processed successfully.
"""
        
    except Exception as e:
        return f"❌ Error generating cancellation PDF: {str(e)}"

@tool
def list_available_documents(booking_reference: str, guest_id: str = "", include_local_paths: bool = True) -> str:
    """
    List all available PDF documents for a booking.
    
    Args:
        booking_reference: The booking reference number
        guest_id: Guest identifier (optional)
        include_local_paths: If True, include local file paths in the response
        
    Returns:
        List of available documents with download links and local paths
    """
    try:
        # Get booking data
        from .booking_management import booking_manager
        booking_result = booking_manager.get_booking_status(booking_reference)
        
        if not booking_result['success']:
            return f"❌ Booking {booking_reference} not found"
        
        booking_status = booking_result['booking_status']
        payment_status = booking_result['payment_status']
        
        documents = []
        generator = EllaPDFGenerator()
        
        # Booking confirmation (always available for confirmed bookings)
        if booking_status in ['CONFIRMED', 'CHECKED_IN', 'CHECKED_OUT']:
            doc_info = "📋 **Booking Confirmation** - `/booking-confirmation/{}`".format(booking_reference)
            if include_local_paths:
                local_file = generator.get_local_file_path(booking_reference, "booking_confirmation")
                if local_file:
                    doc_info += f"\n   📁 Local: {local_file}"
            documents.append(doc_info)
        
        # Invoice (for unpaid bookings)
        if payment_status in ['UNPAID', 'PARTIAL']:
            doc_info = "🧾 **Invoice** - `/invoice/{}`".format(booking_reference)
            if include_local_paths:
                local_file = generator.get_local_file_path(booking_reference, "invoice")
                if local_file:
                    doc_info += f"\n   📁 Local: {local_file}"
            documents.append(doc_info)
        
        # Payment receipt (for paid bookings)
        if payment_status == 'PAID':
            doc_info = "🧾 **Payment Receipt** - `/payment-receipt/{}`".format(booking_reference)
            if include_local_paths:
                local_file = generator.get_local_file_path(booking_reference, "payment_receipt")
                if local_file:
                    doc_info += f"\n   📁 Local: {local_file}"
            documents.append(doc_info)
        
        # Cancellation confirmation (for cancelled bookings)
        if booking_status == 'CANCELLED':
            doc_info = "❌ **Cancellation Confirmation** - `/cancellation/{}`".format(booking_reference)
            if include_local_paths:
                local_file = generator.get_local_file_path(booking_reference, "cancellation_confirmation")
                if local_file:
                    doc_info += f"\n   📁 Local: {local_file}"
            documents.append(doc_info)
        
        if not documents:
            return f"📄 No documents available for booking {booking_reference}"
        
        return f"""
📄 **Available Documents for {booking_reference}:**

{chr(10).join(documents)}

🏨 **Hotel:** {booking_result['hotel_name']}
👤 **Guest:** {booking_result['guest_name']}
📅 **Status:** {booking_status} | **Payment:** {payment_status}

All documents are stored locally and available for download on-demand.
"""
        
    except Exception as e:
        return f"❌ Error listing documents: {str(e)}"

@tool
def cleanup_old_pdfs(days_old: int = 30, guest_id: str = "") -> str:
    """
    Clean up PDF files older than specified days to manage storage.
    
    Args:
        days_old: Remove files older than this many days
        guest_id: Guest identifier (optional)
        
    Returns:
        Status message about cleanup operation
    """
    try:
        import time
        from pathlib import Path
        
        base_dir = Path("generated_documents")
        if not base_dir.exists():
            return "📁 No generated_documents directory found"
        
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        removed_count = 0
        total_size = 0
        
        for subdir in ['booking_confirmations', 'invoices', 'payment_receipts', 'cancellations']:
            subdir_path = base_dir / subdir
            if subdir_path.exists():
                for pdf_file in subdir_path.glob("*.pdf"):
                    if pdf_file.stat().st_mtime < cutoff_time:
                        file_size = pdf_file.stat().st_size
                        pdf_file.unlink()
                        removed_count += 1
                        total_size += file_size
        
        size_mb = total_size / (1024 * 1024)
        
        return f"""
🧹 PDF Cleanup completed!

📊 **Results:**
• Files removed: {removed_count}
• Space freed: {size_mb:.2f} MB
• Cutoff: Files older than {days_old} days

📁 **Directories cleaned:**
• Booking confirmations
• Invoices  
• Payment receipts
• Cancellation confirmations

Old PDFs have been removed to optimize storage space.
"""
        
    except Exception as e:
        return f"❌ Error during PDF cleanup: {str(e)}" 