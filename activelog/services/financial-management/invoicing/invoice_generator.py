#!/usr/bin/env python3
"""
Advanced Invoice Generation System for ActiveLog
Creates professional invoices with templates, automation, and multi-format output
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import asyncpg
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP
import yaml
import jinja2
import weasyprint
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import black, blue, red, grey
from reportlab.lib import colors
import qrcode
from io import BytesIO
import base64
from PIL import Image as PILImage, ImageDraw, ImageFont
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class InvoiceItem:
    """Invoice line item"""
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount_percent: Decimal = Decimal('0')
    tax_rate: Decimal = Decimal('0')
    
    @property
    def subtotal(self) -> Decimal:
        return self.quantity * self.unit_price
    
    @property
    def discount_amount(self) -> Decimal:
        return self.subtotal * (self.discount_percent / Decimal('100'))
    
    @property
    def net_amount(self) -> Decimal:
        return self.subtotal - self.discount_amount
    
    @property
    def tax_amount(self) -> Decimal:
        return self.net_amount * (self.tax_rate / Decimal('100'))
    
    @property
    def total(self) -> Decimal:
        return self.net_amount + self.tax_amount

@dataclass
class InvoiceAddress:
    """Address information"""
    name: str = ""
    company: str = ""
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = ""
    
    def to_display_format(self) -> List[str]:
        """Convert to display format"""
        lines = []
        if self.name:
            lines.append(self.name)
        if self.company:
            lines.append(self.company)
        if self.address_line1:
            lines.append(self.address_line1)
        if self.address_line2:
            lines.append(self.address_line2)
        
        city_line = []
        if self.city:
            city_line.append(self.city)
        if self.state:
            city_line.append(self.state)
        if self.postal_code:
            city_line.append(self.postal_code)
        if city_line:
            lines.append(', '.join(city_line))
        
        if self.country:
            lines.append(self.country)
        
        return lines

@dataclass
class Invoice:
    """Complete invoice data structure"""
    invoice_number: str
    issue_date: datetime
    due_date: datetime
    
    # Company information
    company_name: str
    company_logo: Optional[str] = None
    company_address: Optional[InvoiceAddress] = None
    company_phone: Optional[str] = None
    company_email: Optional[str] = None
    company_website: Optional[str] = None
    tax_id: Optional[str] = None
    
    # Customer information
    customer_name: str
    customer_address: Optional[InvoiceAddress] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_id: Optional[str] = None
    
    # Line items
    items: List[InvoiceItem] = None
    
    # Payment information
    payment_terms: str = "Net 30"
    payment_methods: List[str] = None
    bank_details: Optional[Dict[str, str]] = None
    
    # Totals
    currency: str = "USD"
    subtotal: Optional[Decimal] = None
    total_discount: Optional[Decimal] = None
    total_tax: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    
    # Additional information
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None
    purchase_order: Optional[str] = None
    project_reference: Optional[str] = None
    
    def __post_init__(self):
        if self.items is None:
            self.items = []
        if self.payment_methods is None:
            self.payment_methods = ["Check", "Bank Transfer", "Credit Card"]
        self.calculate_totals()
    
    def calculate_totals(self):
        """Calculate invoice totals"""
        if not self.items:
            self.subtotal = Decimal('0')
            self.total_discount = Decimal('0')
            self.total_tax = Decimal('0')
            self.total_amount = Decimal('0')
            return
        
        self.subtotal = sum(item.subtotal for item in self.items)
        self.total_discount = sum(item.discount_amount for item in self.items)
        self.total_tax = sum(item.tax_amount for item in self.items)
        self.total_amount = sum(item.total for item in self.items)
        
        # Round to 2 decimal places
        self.subtotal = self.subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.total_discount = self.total_discount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.total_tax = self.total_tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.total_amount = self.total_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

class InvoiceTemplateManager:
    """Manages invoice templates and rendering"""
    
    def __init__(self, templates_dir: str):
        self.templates_dir = templates_dir
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(templates_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        
        # Add custom filters
        self.jinja_env.filters['currency'] = self.format_currency
        self.jinja_env.filters['date'] = self.format_date
    
    def format_currency(self, amount: Decimal, currency: str = "USD") -> str:
        """Format currency amounts"""
        if currency == "USD":
            return f"${amount:,.2f}"
        elif currency == "EUR":
            return f"€{amount:,.2f}"
        elif currency == "GBP":
            return f"£{amount:,.2f}"
        else:
            return f"{currency} {amount:,.2f}"
    
    def format_date(self, date: datetime, format: str = "%B %d, %Y") -> str:
        """Format dates"""
        return date.strftime(format)
    
    def render_html(self, invoice: Invoice, template_name: str = "modern.html") -> str:
        """Render invoice as HTML"""
        template = self.jinja_env.get_template(template_name)
        
        return template.render(
            invoice=invoice,
            current_date=datetime.now()
        )
    
    def render_pdf_from_html(self, html_content: str, 
                           output_path: Optional[str] = None) -> bytes:
        """Convert HTML to PDF using WeasyPrint"""
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
        
        return pdf_bytes

class PDFInvoiceGenerator:
    """Generate invoices using ReportLab for more control"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.page_width = letter[0]
        self.page_height = letter[1]
        self.margin = 0.75 * inch
    
    def generate_pdf(self, invoice: Invoice, output_path: Optional[str] = None) -> bytes:
        """Generate PDF invoice"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )
        
        story = []
        
        # Header
        self._add_header(story, invoice)
        
        # Company and Customer Info
        self._add_addresses(story, invoice)
        
        # Invoice Details
        self._add_invoice_details(story, invoice)
        
        # Line Items Table
        self._add_line_items_table(story, invoice)
        
        # Totals
        self._add_totals(story, invoice)
        
        # Footer
        self._add_footer(story, invoice)
        
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
        
        return pdf_bytes
    
    def _add_header(self, story: List, invoice: Invoice):
        """Add invoice header"""
        # Logo and Company Name
        if invoice.company_logo and os.path.exists(invoice.company_logo):
            logo = Image(invoice.company_logo, width=2*inch, height=1*inch)
            story.append(logo)
            story.append(Spacer(1, 12))
        
        # Company name as title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=blue
        )
        story.append(Paragraph(invoice.company_name, title_style))
        story.append(Spacer(1, 12))
    
    def _add_addresses(self, story: List, invoice: Invoice):
        """Add company and customer addresses"""
        # Create table for addresses
        address_data = []
        
        # Company address
        company_info = [f"<b>{invoice.company_name}</b>"]
        if invoice.company_address:
            company_info.extend(invoice.company_address.to_display_format())
        if invoice.company_phone:
            company_info.append(f"Phone: {invoice.company_phone}")
        if invoice.company_email:
            company_info.append(f"Email: {invoice.company_email}")
        if invoice.tax_id:
            company_info.append(f"Tax ID: {invoice.tax_id}")
        
        # Customer address
        customer_info = [f"<b>Bill To:</b>", f"<b>{invoice.customer_name}</b>"]
        if invoice.customer_address:
            customer_info.extend(invoice.customer_address.to_display_format())
        if invoice.customer_phone:
            customer_info.append(f"Phone: {invoice.customer_phone}")
        if invoice.customer_email:
            customer_info.append(f"Email: {invoice.customer_email}")
        
        # Build table data
        max_lines = max(len(company_info), len(customer_info))
        for i in range(max_lines):
            company_line = company_info[i] if i < len(company_info) else ""
            customer_line = customer_info[i] if i < len(customer_info) else ""
            address_data.append([company_line, customer_line])
        
        address_table = Table(address_data, colWidths=[3.5*inch, 3.5*inch])
        address_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(address_table)
        story.append(Spacer(1, 30))
    
    def _add_invoice_details(self, story: List, invoice: Invoice):
        """Add invoice details section"""
        details_data = [
            ['Invoice Number:', invoice.invoice_number],
            ['Invoice Date:', invoice.issue_date.strftime('%B %d, %Y')],
            ['Due Date:', invoice.due_date.strftime('%B %d, %Y')],
            ['Payment Terms:', invoice.payment_terms]
        ]
        
        if invoice.purchase_order:
            details_data.append(['Purchase Order:', invoice.purchase_order])
        
        if invoice.project_reference:
            details_data.append(['Project:', invoice.project_reference])
        
        details_table = Table(details_data, colWidths=[2*inch, 3*inch])
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        
        story.append(details_table)
        story.append(Spacer(1, 30))
    
    def _add_line_items_table(self, story: List, invoice: Invoice):
        """Add line items table"""
        # Table headers
        headers = ['Description', 'Qty', 'Rate', 'Amount']
        table_data = [headers]
        
        # Add items
        for item in invoice.items:
            row = [
                item.description,
                str(item.quantity),
                f"${item.unit_price:,.2f}",
                f"${item.total:,.2f}"
            ]
            table_data.append(row)
        
        # Create table
        items_table = Table(table_data, colWidths=[4*inch, 1*inch, 1.25*inch, 1.25*inch])
        
        # Style the table
        items_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            
            # Grid lines
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.beige, colors.white]),
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 30))
    
    def _add_totals(self, story: List, invoice: Invoice):
        """Add totals section"""
        totals_data = []
        
        # Subtotal
        totals_data.append(['Subtotal:', f"${invoice.subtotal:,.2f}"])
        
        # Discount (if any)
        if invoice.total_discount > 0:
            totals_data.append(['Discount:', f"-${invoice.total_discount:,.2f}"])
        
        # Tax (if any)
        if invoice.total_tax > 0:
            totals_data.append(['Tax:', f"${invoice.total_tax:,.2f}"])
        
        # Total
        totals_data.append(['', ''])  # Empty row for spacing
        totals_data.append(['Total:', f"${invoice.total_amount:,.2f}"])
        
        # Right-align totals table
        totals_table = Table(totals_data, colWidths=[2*inch, 1.5*inch])
        totals_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('LINEBELOW', (0, -2), (-1, -2), 2, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ]))
        
        # Create wrapper table to right-align
        wrapper_table = Table([[totals_table]], colWidths=[7.5*inch])
        wrapper_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ]))
        
        story.append(wrapper_table)
        story.append(Spacer(1, 30))
    
    def _add_footer(self, story: List, invoice: Invoice):
        """Add footer with notes and payment info"""
        if invoice.notes:
            notes_style = ParagraphStyle(
                'Notes',
                parent=self.styles['Normal'],
                fontSize=10,
                spaceAfter=12
            )
            story.append(Paragraph(f"<b>Notes:</b> {invoice.notes}", notes_style))
        
        if invoice.terms_conditions:
            terms_style = ParagraphStyle(
                'Terms',
                parent=self.styles['Normal'],
                fontSize=9,
                spaceAfter=12
            )
            story.append(Paragraph(f"<b>Terms & Conditions:</b> {invoice.terms_conditions}", terms_style))
        
        # Payment methods
        payment_info = f"<b>Payment Methods:</b> {', '.join(invoice.payment_methods)}"
        if invoice.bank_details:
            payment_info += f"<br/><b>Bank Details:</b> {invoice.bank_details.get('bank_name', '')} - Account: {invoice.bank_details.get('account_number', '')}"
        
        payment_style = ParagraphStyle(
            'Payment',
            parent=self.styles['Normal'],
            fontSize=9
        )
        story.append(Paragraph(payment_info, payment_style))

class QRCodeGenerator:
    """Generate QR codes for invoices"""
    
    @staticmethod
    def generate_payment_qr(invoice: Invoice, payment_url: Optional[str] = None) -> str:
        """Generate QR code for payment"""
        if payment_url:
            qr_data = payment_url
        else:
            # Create a basic payment data structure
            qr_data = f"Invoice: {invoice.invoice_number}\nAmount: {invoice.currency} {invoice.total_amount}\nDue: {invoice.due_date.strftime('%Y-%m-%d')}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        qr_img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        buffer.close()
        
        return qr_base64

class InvoiceGenerator:
    """Main invoice generation service"""
    
    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)
        self.db_pool = None
        self.template_manager = InvoiceTemplateManager(
            self.config['templates']['directory']
        )
        self.pdf_generator = PDFInvoiceGenerator()
        self.qr_generator = QRCodeGenerator()
        
        # Initialize AWS S3 client if configured
        if self.config.get('storage', {}).get('type') == 's3':
            self.s3_client = boto3.client('s3')
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    async def initialize(self):
        """Initialize the service"""
        await self.connect_database()
        await self.create_tables()
        logger.info("Invoice generator initialized")
    
    async def connect_database(self):
        """Connect to PostgreSQL database"""
        db_config = self.config['database']
        self.db_pool = await asyncpg.create_pool(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            min_size=2,
            max_size=10
        )
    
    async def create_tables(self):
        """Create database tables"""
        async with self.db_pool.acquire() as conn:
            # Invoice templates table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS invoice_templates (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description TEXT,
                    template_file VARCHAR(255) NOT NULL,
                    is_default BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # Invoice generation history
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS invoice_generation_history (
                    id SERIAL PRIMARY KEY,
                    invoice_id INTEGER NOT NULL,
                    format VARCHAR(10) NOT NULL,
                    template_name VARCHAR(100),
                    file_path VARCHAR(500),
                    file_size INTEGER,
                    generation_time_ms INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
    
    async def create_invoice_from_data(self, invoice_data: Dict[str, Any]) -> Invoice:
        """Create Invoice object from data dictionary"""
        # Parse company address
        company_address = None
        if invoice_data.get('company_address'):
            company_address = InvoiceAddress(**invoice_data['company_address'])
        
        # Parse customer address
        customer_address = None
        if invoice_data.get('customer_address'):
            customer_address = InvoiceAddress(**invoice_data['customer_address'])
        
        # Parse line items
        items = []
        for item_data in invoice_data.get('items', []):
            item = InvoiceItem(
                description=item_data['description'],
                quantity=Decimal(str(item_data['quantity'])),
                unit_price=Decimal(str(item_data['unit_price'])),
                discount_percent=Decimal(str(item_data.get('discount_percent', 0))),
                tax_rate=Decimal(str(item_data.get('tax_rate', 0)))
            )
            items.append(item)
        
        # Create invoice
        invoice = Invoice(
            invoice_number=invoice_data['invoice_number'],
            issue_date=datetime.fromisoformat(invoice_data['issue_date']),
            due_date=datetime.fromisoformat(invoice_data['due_date']),
            company_name=invoice_data['company_name'],
            company_logo=invoice_data.get('company_logo'),
            company_address=company_address,
            company_phone=invoice_data.get('company_phone'),
            company_email=invoice_data.get('company_email'),
            company_website=invoice_data.get('company_website'),
            tax_id=invoice_data.get('tax_id'),
            customer_name=invoice_data['customer_name'],
            customer_address=customer_address,
            customer_email=invoice_data.get('customer_email'),
            customer_phone=invoice_data.get('customer_phone'),
            customer_id=invoice_data.get('customer_id'),
            items=items,
            payment_terms=invoice_data.get('payment_terms', 'Net 30'),
            payment_methods=invoice_data.get('payment_methods', ['Check', 'Bank Transfer']),
            bank_details=invoice_data.get('bank_details'),
            currency=invoice_data.get('currency', 'USD'),
            notes=invoice_data.get('notes'),
            terms_conditions=invoice_data.get('terms_conditions'),
            purchase_order=invoice_data.get('purchase_order'),
            project_reference=invoice_data.get('project_reference')
        )
        
        return invoice
    
    async def generate_invoice_pdf(self, invoice: Invoice, 
                                 template_name: str = "default",
                                 include_qr_code: bool = True) -> Tuple[bytes, str]:
        """Generate invoice PDF"""
        start_time = time.time()
        
        try:
            if template_name == "default" or template_name == "reportlab":
                # Use ReportLab for default template
                pdf_bytes = self.pdf_generator.generate_pdf(invoice)
            else:
                # Use HTML template with WeasyPrint
                html_content = self.template_manager.render_html(invoice, f"{template_name}.html")
                
                # Add QR code if requested
                if include_qr_code:
                    qr_code = self.qr_generator.generate_payment_qr(invoice)
                    qr_img_tag = f'<img src="data:image/png;base64,{qr_code}" style="width: 100px; height: 100px;">'
                    html_content = html_content.replace('{{QR_CODE}}', qr_img_tag)
                
                pdf_bytes = self.template_manager.render_pdf_from_html(html_content)
            
            generation_time = int((time.time() - start_time) * 1000)
            
            # Generate filename
            filename = f"invoice_{invoice.invoice_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            # Store generation history
            await self.store_generation_history(
                invoice_id=None,  # Would need to be passed or looked up
                format='pdf',
                template_name=template_name,
                file_size=len(pdf_bytes),
                generation_time_ms=generation_time,
                filename=filename
            )
            
            return pdf_bytes, filename
            
        except Exception as e:
            logger.error(f"Failed to generate PDF invoice: {e}")
            raise
    
    async def generate_invoice_html(self, invoice: Invoice, 
                                  template_name: str = "modern") -> str:
        """Generate invoice HTML"""
        try:
            html_content = self.template_manager.render_html(invoice, f"{template_name}.html")
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to generate HTML invoice: {e}")
            raise
    
    async def send_invoice_email(self, invoice: Invoice, recipient_email: str,
                               pdf_bytes: bytes, filename: str,
                               custom_message: Optional[str] = None) -> bool:
        """Send invoice via email"""
        try:
            email_config = self.config['email']
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_config['from_address']
            msg['To'] = recipient_email
            msg['Subject'] = f"Invoice {invoice.invoice_number} from {invoice.company_name}"
            
            # Email body
            if custom_message:
                body = custom_message
            else:
                body = f"""
Dear {invoice.customer_name},

Please find attached invoice {invoice.invoice_number} dated {invoice.issue_date.strftime('%B %d, %Y')}.

Invoice Details:
- Amount: {invoice.currency} {invoice.total_amount}
- Due Date: {invoice.due_date.strftime('%B %d, %Y')}
- Payment Terms: {invoice.payment_terms}

Thank you for your business!

Best regards,
{invoice.company_name}
"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach PDF
            pdf_attachment = MIMEApplication(pdf_bytes)
            pdf_attachment.add_header('Content-Disposition', 'attachment', filename=filename)
            msg.attach(pdf_attachment)
            
            # Send email (implementation depends on your email service)
            # This is a placeholder - implement based on your email provider
            logger.info(f"Invoice {invoice.invoice_number} email prepared for {recipient_email}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send invoice email: {e}")
            return False
    
    async def store_generation_history(self, invoice_id: Optional[int], 
                                     format: str, template_name: str,
                                     file_size: int, generation_time_ms: int,
                                     filename: str):
        """Store invoice generation history"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO invoice_generation_history 
                (invoice_id, format, template_name, file_path, file_size, generation_time_ms)
                VALUES ($1, $2, $3, $4, $5, $6)
            ''',
            invoice_id, format, template_name, filename, file_size, generation_time_ms
            )
    
    async def batch_generate_invoices(self, invoice_data_list: List[Dict[str, Any]],
                                    template_name: str = "default") -> List[Tuple[bytes, str]]:
        """Generate multiple invoices in batch"""
        results = []
        
        for invoice_data in invoice_data_list:
            try:
                invoice = await self.create_invoice_from_data(invoice_data)
                pdf_bytes, filename = await self.generate_invoice_pdf(invoice, template_name)
                results.append((pdf_bytes, filename))
                
            except Exception as e:
                logger.error(f"Failed to generate invoice {invoice_data.get('invoice_number')}: {e}")
                results.append((None, None))
        
        return results
    
    async def get_invoice_templates(self) -> List[Dict[str, Any]]:
        """Get available invoice templates"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch('SELECT * FROM invoice_templates ORDER BY name')
            return [dict(row) for row in rows]
    
    async def create_recurring_invoice_schedule(self, base_invoice_data: Dict[str, Any],
                                              frequency: str, end_date: datetime,
                                              next_invoice_date: datetime) -> int:
        """Create recurring invoice schedule"""
        # This would integrate with a job scheduler like Celery or APScheduler
        # For now, we'll just log the intent
        logger.info(f"Created recurring invoice schedule: {frequency} until {end_date}")
        return 1  # Return schedule ID

def main():
    """Example usage"""
    async def generate_sample_invoice():
        config_path = "invoice_config.yml"
        generator = InvoiceGenerator(config_path)
        
        # Sample invoice data
        invoice_data = {
            "invoice_number": "INV-2024-001",
            "issue_date": "2024-01-15T00:00:00",
            "due_date": "2024-02-14T00:00:00",
            "company_name": "ActiveLog Solutions",
            "company_address": {
                "name": "ActiveLog Solutions",
                "address_line1": "123 Business Ave",
                "city": "San Francisco",
                "state": "CA",
                "postal_code": "94105",
                "country": "USA"
            },
            "company_email": "billing@activelog.com",
            "company_phone": "555-123-4567",
            "customer_name": "Acme Corporation",
            "customer_address": {
                "name": "Acme Corporation",
                "address_line1": "456 Client Street",
                "city": "New York",
                "state": "NY",
                "postal_code": "10001",
                "country": "USA"
            },
            "customer_email": "accounting@acme.com",
            "items": [
                {
                    "description": "ActiveLog Professional Plan - Monthly Subscription",
                    "quantity": 1,
                    "unit_price": 299.00,
                    "tax_rate": 8.5
                },
                {
                    "description": "Premium Support Package",
                    "quantity": 1,
                    "unit_price": 99.00,
                    "tax_rate": 8.5
                }
            ],
            "payment_terms": "Net 30",
            "notes": "Thank you for choosing ActiveLog!"
        }
        
        try:
            await generator.initialize()
            
            # Create invoice
            invoice = await generator.create_invoice_from_data(invoice_data)
            
            # Generate PDF
            pdf_bytes, filename = await generator.generate_invoice_pdf(invoice)
            
            # Save PDF
            with open(f"sample_{filename}", 'wb') as f:
                f.write(pdf_bytes)
            
            print(f"Generated invoice: {filename}")
            print(f"Invoice total: ${invoice.total_amount}")
            
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(generate_sample_invoice())

if __name__ == '__main__':
    main()