# Invoice Templates API Documentation

The Invoice Template System provides comprehensive template management for professional invoice generation with customizable layouts, branding, and PDF generation.

## Features

- **Template Management**: Create, update, list, and delete invoice templates
- **Multiple Formats**: Modern, Classic, Minimalist, Creative, and Corporate templates
- **Customizable Styling**: Colors, fonts, layout, and branding options
- **PDF Generation**: Professional PDF invoices with ReportLab
- **HTML Previews**: Generate HTML previews of templates
- **Version Control**: Track template changes with version history
- **Usage Statistics**: Monitor template usage and revenue
- **Dashboard Analytics**: Comprehensive invoice and template statistics

## Template Formats

### Modern
- Clean, contemporary design with gradients
- Professional color scheme with blue primary
- Suitable for tech companies and startups

### Classic
- Traditional business invoice layout
- Conservative styling with dark colors
- Perfect for established businesses

### Minimalist
- Clean, simple design with minimal visual elements
- Black and white color scheme
- Ideal for creative professionals

### Creative
- Vibrant colors with decorative elements
- Creative typography and layouts
- Great for design agencies and creative services

### Corporate
- Formal, professional business layout
- Corporate blue color scheme
- Perfect for large enterprises and B2B

## API Endpoints

### Template Management

#### Create Template
```http
POST /api/v1/templates
Content-Type: application/json

{
    "name": "My Custom Template",
    "format": "modern",
    "layout_config": {
        "header_height": 2.0,
        "footer_height": 1.0,
        "style": "modern",
        "use_gradients": true
    },
    "styling_config": {
        "colors": {
            "primary": "#3B82F6",
            "secondary": "#64748B",
            "accent": "#F59E0B",
            "text": "#1E293B",
            "background": "#FFFFFF"
        },
        "fonts": {
            "primary": "Helvetica-Bold",
            "secondary": "Helvetica"
        }
    }
}
```

#### List Templates
```http
GET /api/v1/templates
```

Response:
```json
{
    "success": true,
    "templates": [
        {
            "id": "template-id",
            "name": "Default Modern Template",
            "format": "modern",
            "is_default": true,
            "version": 1,
            "usage_count": 15,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
    ]
}
```

#### Get Template
```http
GET /api/v1/templates/{template_id}
```

#### Preview Template
```http
GET /api/v1/templates/{template_id}/preview
```

### Invoice Generation

#### Create Invoice
```http
POST /api/v1/invoices
Content-Type: application/json

{
    "customer_id": "CUSTOMER_001",
    "template_id": "template-id",
    "items": [
        {
            "description": "Web Development",
            "quantity": 10,
            "unit_price": 125.00
        }
    ],
    "customer_details": {
        "name": "Customer Name",
        "address": "123 Street\nCity, State 12345"
    },
    "company_details": {
        "name": "Your Company",
        "address": "456 Business Ave\nCity, State 67890"
    },
    "tax_rate": 8.25,
    "due_date": "2024-02-01",
    "notes": "Thank you for your business!"
}
```

Response:
```json
{
    "success": true,
    "invoice_id": "invoice-id",
    "invoice_number": "INV-20240101-001",
    "pdf_path": "data/invoices/invoice-id.pdf",
    "total_amount": 1353.13,
    "message": "Invoice generated successfully"
}
```

## Configuration Options

### Layout Configuration
```json
{
    "header_height": 2.0,
    "footer_height": 1.0,
    "margin_top": 0.75,
    "margin_bottom": 0.75,
    "margin_left": 0.75,
    "margin_right": 0.75,
    "sections": {
        "header": {"position": "top", "height": 2.0},
        "company_info": {"position": "top-left", "width": 50},
        "invoice_info": {"position": "top-right", "width": 50},
        "items_table": {"position": "center", "width": 100},
        "totals": {"position": "bottom-right", "width": 40}
    }
}
```

### Styling Configuration
```json
{
    "colors": {
        "primary": "#3B82F6",
        "secondary": "#64748B",
        "accent": "#F59E0B",
        "text": "#1E293B",
        "background": "#FFFFFF"
    },
    "fonts": {
        "primary": "Helvetica-Bold",
        "secondary": "Helvetica",
        "heading": "Helvetica-Bold",
        "body": "Helvetica"
    },
    "font_sizes": {
        "title": 24,
        "heading": 16,
        "body": 10,
        "small": 8
    }
}
```

### Branding Configuration
```json
{
    "logo": {
        "show": true,
        "position": "top-left",
        "max_width": 2.0,
        "max_height": 1.0
    },
    "company_colors": true,
    "watermark": {
        "show": false,
        "text": "SAMPLE",
        "opacity": 0.1
    },
    "qr_code": {
        "show": true,
        "position": "bottom-right",
        "size": 1.0
    }
}
```

## Database Schema

### Templates Table
- `id`: Unique template identifier
- `name`: Template display name
- `format`: Template format (modern, classic, etc.)
- `layout_config`: JSON layout configuration
- `styling_config`: JSON styling configuration
- `branding_config`: JSON branding configuration
- `fields_config`: JSON field configuration
- `is_default`: Whether template is a default template
- `version`: Current version number
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

### Invoices Table
- `id`: Unique invoice identifier
- `invoice_number`: Human-readable invoice number
- `template_id`: Associated template ID
- `customer_id`: Customer identifier
- `status`: Invoice status (draft, sent, paid, etc.)
- `subtotal`: Invoice subtotal amount
- `tax_amount`: Tax amount
- `total_amount`: Final total amount
- `currency`: Currency code
- `due_date`: Payment due date
- `issue_date`: Invoice issue date
- `items`: JSON array of invoice items
- `customer_details`: JSON customer information
- `company_details`: JSON company information
- `pdf_path`: Path to generated PDF file
- `html_content`: Generated HTML content

## Usage Examples

### Python Client Example
```python
import asyncio
from invoice_templates import template_system

async def create_invoice():
    # Initialize system
    await template_system.initialize()
    
    # Create invoice
    result = await template_system.generate_invoice({
        "customer_id": "CUSTOMER_001",
        "items": [
            {
                "description": "Consulting Services",
                "quantity": 8,
                "unit_price": 150.00
            }
        ],
        "customer_details": {
            "name": "Acme Corp",
            "address": "123 Business St"
        },
        "tax_rate": 8.25
    })
    
    if result["success"]:
        print(f"Invoice generated: {result['invoice_number']}")
        print(f"Total: ${result['total_amount']:.2f}")

asyncio.run(create_invoice())
```

## Error Handling

All API endpoints return a consistent response format:

Success:
```json
{
    "success": true,
    "data": {...},
    "message": "Operation completed successfully"
}
```

Error:
```json
{
    "success": false,
    "error": "Error description",
    "details": "Additional error details"
}
```

## Best Practices

1. **Template Versioning**: Always increment version when making significant changes
2. **Color Accessibility**: Use high-contrast colors for better readability
3. **PDF Optimization**: Keep layouts simple for reliable PDF generation
4. **Field Validation**: Validate all required fields before invoice generation
5. **Error Handling**: Always check the `success` field in API responses
6. **Template Testing**: Use the preview endpoint to test templates before use

## Performance Considerations

- Templates are cached in memory for faster access
- PDF generation is performed asynchronously
- Database queries are optimized with proper indexing
- Large batch operations should be handled with background tasks