"""
Contact Management System
Handles contact creation, management, and relationship tracking
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class ContactStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    CONVERTED = "converted"


class LeadSource(Enum):
    WEBSITE = "website"
    SOCIAL_MEDIA = "social_media"
    REFERRAL = "referral"
    TRADE_SHOW = "trade_show"
    COLD_CALL = "cold_call"
    EMAIL_CAMPAIGN = "email_campaign"
    ADVERTISEMENT = "advertisement"
    OTHER = "other"


@dataclass
class ContactActivity:
    activity_id: str
    activity_type: str
    subject: str
    description: str
    created_at: datetime
    owner_id: str


class ContactManager:
    """Manages contact relationships and interactions"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        
        # Contact management settings
        self.duplicate_detection_enabled = config.get('contact_management.duplicate_detection_enabled', True)
        self.auto_merge_duplicates = config.get('contact_management.auto_merge_duplicates', False)
        self.data_enrichment_enabled = config.get('contact_management.data_enrichment_enabled', True)
        self.activity_tracking_enabled = config.get('contact_management.activity_tracking_enabled', True)
        self.contact_scoring_enabled = config.get('contact_management.contact_scoring_enabled', True)
        
        # Data validation settings
        self.required_fields = ['first_name', 'last_name']
        self.email_validation_enabled = True
        self.phone_validation_enabled = True
        
    def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new contact"""
        try:
            # Validate required fields
            validation_result = self.validate_contact_data(contact_data)
            if not validation_result['valid']:
                raise ValueError(validation_result['error'])
                
            # Check for duplicates if enabled
            if self.duplicate_detection_enabled:
                duplicate_check = self.check_for_duplicates(contact_data)
                if duplicate_check['has_duplicates']:
                    if self.auto_merge_duplicates:
                        return self.merge_with_existing(duplicate_check['matches'][0], contact_data)
                    else:
                        return {
                            'success': False,
                            'error': 'Duplicate contact found',
                            'duplicates': duplicate_check['matches']
                        }
                        
            # Generate contact ID
            contact_id = f"contact_{datetime.now().timestamp()}"
            
            # Enrich contact data if enabled
            if self.data_enrichment_enabled:
                contact_data = self.enrich_contact_data(contact_data)
                
            # Create contact record
            contact = {
                'contact_id': contact_id,
                'company_id': contact_data.get('company_id'),
                'first_name': contact_data['first_name'],
                'last_name': contact_data['last_name'],
                'email': contact_data.get('email', '').lower() if contact_data.get('email') else None,
                'phone': contact_data.get('phone'),
                'mobile': contact_data.get('mobile'),
                'title': contact_data.get('title'),
                'department': contact_data.get('department'),
                'address': contact_data.get('address'),
                'city': contact_data.get('city'),
                'state': contact_data.get('state'),
                'country': contact_data.get('country'),
                'zip_code': contact_data.get('zip_code'),
                'lead_source': contact_data.get('lead_source', LeadSource.OTHER.value),
                'lead_score': contact_data.get('lead_score', 0),
                'contact_status': contact_data.get('contact_status', ContactStatus.ACTIVE.value),
                'owner_id': contact_data.get('owner_id'),
                'tags': contact_data.get('tags', []),
                'custom_fields': contact_data.get('custom_fields', {}),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Save contact
            success = self.db.save_contact(contact)
            if not success:
                raise Exception("Failed to save contact")
                
            # Create associated company if provided
            if contact_data.get('company_name') and not contact.get('company_id'):
                company_id = self.create_or_get_company({
                    'name': contact_data['company_name'],
                    'industry': contact_data.get('industry'),
                    'website': contact_data.get('company_website')
                })
                contact['company_id'] = company_id
                self.db.update_contact(contact_id, {'company_id': company_id})
                
            # Create initial activity
            if self.activity_tracking_enabled:
                self.create_contact_activity(contact_id, {
                    'activity_type': 'contact_created',
                    'subject': 'Contact Created',
                    'description': f'Contact {contact["first_name"]} {contact["last_name"]} was created',
                    'owner_id': contact.get('owner_id')
                })
                
            # Calculate initial lead score if enabled
            if self.contact_scoring_enabled:
                initial_score = self.calculate_contact_score(contact)
                if initial_score != contact['lead_score']:
                    self.db.update_contact(contact_id, {'lead_score': initial_score})
                    contact['lead_score'] = initial_score
                    
            return {
                'success': True,
                'contact_id': contact_id,
                'contact': contact,
                'message': 'Contact created successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error creating contact: {e}")
            
    def get_contact(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Get contact with enriched data"""
        try:
            contact = self.db.get_contact(contact_id)
            if not contact:
                return None
                
            # Enrich contact data
            contact = self.enrich_contact_display_data(contact)
            
            return contact
            
        except Exception as e:
            raise Exception(f"Error getting contact: {e}")
            
    def update_contact(self, contact_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update contact"""
        try:
            # Get existing contact
            existing_contact = self.db.get_contact(contact_id)
            if not existing_contact:
                raise ValueError("Contact not found")
                
            # Validate update data
            if 'email' in update_data and update_data['email']:
                if not self.validate_email(update_data['email']):
                    raise ValueError("Invalid email format")
                update_data['email'] = update_data['email'].lower()
                
            if 'phone' in update_data and update_data['phone']:
                if not self.validate_phone(update_data['phone']):
                    raise ValueError("Invalid phone format")
                    
            # Check for duplicates if email is being changed
            if 'email' in update_data and update_data['email'] != existing_contact.get('email'):
                if self.duplicate_detection_enabled:
                    duplicate_check = self.check_email_duplicate(update_data['email'], contact_id)
                    if duplicate_check['has_duplicates']:
                        raise ValueError("Email already exists for another contact")
                        
            # Add update timestamp
            update_data['updated_at'] = datetime.now().isoformat()
            
            # Update contact
            success = self.db.update_contact(contact_id, update_data)
            if not success:
                raise Exception("Failed to update contact")
                
            # Create update activity
            if self.activity_tracking_enabled:
                self.create_contact_activity(contact_id, {
                    'activity_type': 'contact_updated',
                    'subject': 'Contact Updated',
                    'description': f'Contact information updated: {", ".join(update_data.keys())}',
                    'owner_id': update_data.get('owner_id') or existing_contact.get('owner_id')
                })
                
            # Recalculate lead score if relevant fields changed
            if self.contact_scoring_enabled:
                score_affecting_fields = ['title', 'department', 'company_id', 'lead_source']
                if any(field in update_data for field in score_affecting_fields):
                    updated_contact = self.db.get_contact(contact_id)
                    new_score = self.calculate_contact_score(updated_contact)
                    if new_score != updated_contact['lead_score']:
                        self.db.update_contact(contact_id, {'lead_score': new_score})
                        
            return {
                'success': True,
                'contact_id': contact_id,
                'updated_fields': list(update_data.keys()),
                'message': 'Contact updated successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error updating contact: {e}")
            
    def list_contacts(self, filters: Dict[str, Any] = None, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """List contacts with filtering and pagination"""
        try:
            if filters is None:
                filters = {}
                
            contacts = self.db.list_contacts(filters, page, limit)
            total_count = self.db.get_contact_count(filters)
            
            # Enrich contact data
            enriched_contacts = []
            for contact in contacts:
                enriched_contact = self.enrich_contact_display_data(contact)
                enriched_contacts.append(enriched_contact)
                
            total_pages = (total_count + limit - 1) // limit
            
            return {
                'contacts': enriched_contacts,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                },
                'filters_applied': filters
            }
            
        except Exception as e:
            raise Exception(f"Error listing contacts: {e}")
            
    def get_contact_activities(self, contact_id: str) -> List[Dict[str, Any]]:
        """Get contact activity history"""
        try:
            activities = self.db.get_contact_activities(contact_id)
            
            # Enrich activity data
            enriched_activities = []
            for activity in activities:
                enriched_activity = self.enrich_activity_data(activity)
                enriched_activities.append(enriched_activity)
                
            return enriched_activities
            
        except Exception as e:
            raise Exception(f"Error getting contact activities: {e}")
            
    def create_contact_activity(self, contact_id: str, activity_data: Dict[str, Any]) -> str:
        """Create contact activity"""
        try:
            activity_id = f"activity_{datetime.now().timestamp()}"
            
            activity = {
                'activity_id': activity_id,
                'activity_type': activity_data['activity_type'],
                'subject': activity_data['subject'],
                'description': activity_data.get('description', ''),
                'contact_id': contact_id,
                'company_id': activity_data.get('company_id'),
                'opportunity_id': activity_data.get('opportunity_id'),
                'owner_id': activity_data.get('owner_id'),
                'status': activity_data.get('status', 'completed'),
                'priority': activity_data.get('priority', 'medium'),
                'due_date': activity_data.get('due_date'),
                'completed_at': activity_data.get('completed_at', datetime.now().isoformat()),
                'duration_minutes': activity_data.get('duration_minutes'),
                'outcome': activity_data.get('outcome'),
                'follow_up_required': activity_data.get('follow_up_required', False),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            success = self.db.save_activity(activity)
            if success:
                return activity_id
            else:
                raise Exception("Failed to save activity")
                
        except Exception as e:
            raise Exception(f"Error creating contact activity: {e}")
            
    def merge_contacts(self, primary_contact_id: str, secondary_contact_id: str) -> Dict[str, Any]:
        """Merge two contacts"""
        try:
            primary_contact = self.db.get_contact(primary_contact_id)
            secondary_contact = self.db.get_contact(secondary_contact_id)
            
            if not primary_contact or not secondary_contact:
                raise ValueError("One or both contacts not found")
                
            # Merge data from secondary into primary
            merged_data = self.merge_contact_data(primary_contact, secondary_contact)
            
            # Update primary contact
            self.db.update_contact(primary_contact_id, merged_data)
            
            # Transfer activities from secondary to primary
            self.transfer_contact_activities(secondary_contact_id, primary_contact_id)
            
            # Transfer opportunities from secondary to primary
            self.transfer_contact_opportunities(secondary_contact_id, primary_contact_id)
            
            # Deactivate secondary contact
            self.db.update_contact(secondary_contact_id, {
                'contact_status': ContactStatus.INACTIVE.value,
                'merged_into': primary_contact_id,
                'updated_at': datetime.now().isoformat()
            })
            
            # Create merge activity
            self.create_contact_activity(primary_contact_id, {
                'activity_type': 'contact_merged',
                'subject': 'Contact Merged',
                'description': f'Merged with contact {secondary_contact["first_name"]} {secondary_contact["last_name"]} ({secondary_contact_id})'
            })
            
            return {
                'success': True,
                'primary_contact_id': primary_contact_id,
                'merged_contact_id': secondary_contact_id,
                'message': 'Contacts merged successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error merging contacts: {e}")
            
    def search_contacts(self, query: str) -> List[Dict[str, Any]]:
        """Search contacts by name, email, company"""
        try:
            filters = {'search': query}
            contacts = self.db.list_contacts(filters, 1, 50)
            
            # Enrich and rank results
            enriched_contacts = []
            for contact in contacts:
                enriched_contact = self.enrich_contact_display_data(contact)
                enriched_contact['relevance_score'] = self.calculate_search_relevance(contact, query)
                enriched_contacts.append(enriched_contact)
                
            # Sort by relevance
            enriched_contacts.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return enriched_contacts
            
        except Exception as e:
            raise Exception(f"Error searching contacts: {e}")
            
    def get_contact_summary(self) -> Dict[str, Any]:
        """Get contact summary for dashboard"""
        try:
            total_contacts = self.db.get_contact_count()
            active_contacts = self.db.get_contact_count({'contact_status': 'active'})
            qualified_contacts = self.db.get_contact_count({'contact_status': 'qualified'})
            
            # Get recent contacts (last 7 days)
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            recent_contacts = self.db.execute_query(
                "SELECT COUNT(*) as count FROM contacts WHERE created_at >= ?",
                (week_ago,)
            )
            
            return {
                'total_contacts': total_contacts,
                'active_contacts': active_contacts,
                'qualified_contacts': qualified_contacts,
                'new_this_week': recent_contacts[0]['count'] if recent_contacts else 0,
                'conversion_rate': (qualified_contacts / max(total_contacts, 1)) * 100
            }
            
        except Exception as e:
            raise Exception(f"Error getting contact summary: {e}")
            
    def validate_contact_data(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate contact data"""
        try:
            errors = []
            
            # Check required fields
            for field in self.required_fields:
                if field not in contact_data or not contact_data[field]:
                    errors.append(f"Missing required field: {field}")
                    
            # Validate email if provided
            if contact_data.get('email') and self.email_validation_enabled:
                if not self.validate_email(contact_data['email']):
                    errors.append("Invalid email format")
                    
            # Validate phone if provided
            if contact_data.get('phone') and self.phone_validation_enabled:
                if not self.validate_phone(contact_data['phone']):
                    errors.append("Invalid phone format")
                    
            return {
                'valid': len(errors) == 0,
                'error': '; '.join(errors) if errors else None
            }
            
        except Exception as e:
            return {'valid': False, 'error': f'Validation error: {e}'}
            
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        try:
            import re
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return re.match(pattern, email) is not None
        except Exception:
            return False
            
    def validate_phone(self, phone: str) -> bool:
        """Validate phone format"""
        try:
            import re
            # Remove all non-digit characters
            digits_only = re.sub(r'\D', '', phone)
            # Check if it's between 10-15 digits
            return 10 <= len(digits_only) <= 15
        except Exception:
            return False
            
    def check_for_duplicates(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check for duplicate contacts"""
        try:
            matches = []
            
            # Check by email
            if contact_data.get('email'):
                email_matches = self.db.execute_query(
                    "SELECT * FROM contacts WHERE email = ? AND contact_status != 'inactive'",
                    (contact_data['email'].lower(),)
                )
                matches.extend(email_matches)
                
            # Check by name and company
            if contact_data.get('company_id'):
                name_matches = self.db.execute_query(
                    "SELECT * FROM contacts WHERE first_name = ? AND last_name = ? AND company_id = ? AND contact_status != 'inactive'",
                    (contact_data['first_name'], contact_data['last_name'], contact_data['company_id'])
                )
                matches.extend(name_matches)
                
            # Remove duplicates from matches
            unique_matches = []
            seen_ids = set()
            for match in matches:
                if match['contact_id'] not in seen_ids:
                    unique_matches.append(match)
                    seen_ids.add(match['contact_id'])
                    
            return {
                'has_duplicates': len(unique_matches) > 0,
                'matches': unique_matches
            }
            
        except Exception as e:
            print(f"Error checking duplicates: {e}")
            return {'has_duplicates': False, 'matches': []}
            
    def check_email_duplicate(self, email: str, exclude_contact_id: str = None) -> Dict[str, Any]:
        """Check if email already exists"""
        try:
            query = "SELECT * FROM contacts WHERE email = ? AND contact_status != 'inactive'"
            params = [email.lower()]
            
            if exclude_contact_id:
                query += " AND contact_id != ?"
                params.append(exclude_contact_id)
                
            matches = self.db.execute_query(query, tuple(params))
            
            return {
                'has_duplicates': len(matches) > 0,
                'matches': matches
            }
            
        except Exception:
            return {'has_duplicates': False, 'matches': []}
            
    def enrich_contact_data(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich contact data with external sources"""
        try:
            # This would integrate with data enrichment services
            # For now, we'll do basic enrichment
            
            enriched_data = contact_data.copy()
            
            # Standardize phone format
            if contact_data.get('phone'):
                enriched_data['phone'] = self.format_phone(contact_data['phone'])
                
            # Extract domain from email for company matching
            if contact_data.get('email') and not contact_data.get('company_id'):
                domain = contact_data['email'].split('@')[1] if '@' in contact_data['email'] else None
                if domain:
                    # Try to find existing company by domain
                    company = self.find_company_by_domain(domain)
                    if company:
                        enriched_data['company_id'] = company['company_id']
                        
            return enriched_data
            
        except Exception:
            return contact_data
            
    def enrich_contact_display_data(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich contact data for display"""
        try:
            enriched = contact.copy()
            
            # Add full name
            enriched['full_name'] = f"{contact['first_name']} {contact['last_name']}"
            
            # Add company information if available
            if contact.get('company_id'):
                company = self.db.get_company(contact['company_id'])
                if company:
                    enriched['company_name'] = company['name']
                    enriched['company_industry'] = company.get('industry')
                    
            # Add lead score interpretation
            enriched['lead_score_level'] = self.get_lead_score_level(contact.get('lead_score', 0))
            
            # Add days since creation
            if contact.get('created_at'):
                created_date = datetime.fromisoformat(contact['created_at'])
                days_since = (datetime.now() - created_date).days
                enriched['days_since_created'] = days_since
                
            return enriched
            
        except Exception:
            return contact
            
    def enrich_activity_data(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich activity data for display"""
        try:
            enriched = activity.copy()
            
            # Add time ago
            if activity.get('created_at'):
                created_date = datetime.fromisoformat(activity['created_at'])
                enriched['time_ago'] = self.format_time_ago(datetime.now() - created_date)
                
            # Add owner name if available
            if activity.get('owner_id'):
                owner = self.db.get_record('users', 'user_id', activity['owner_id'])
                if owner:
                    enriched['owner_name'] = f"{owner['first_name']} {owner['last_name']}"
                    
            return enriched
            
        except Exception:
            return activity
            
    def calculate_contact_score(self, contact: Dict[str, Any]) -> int:
        """Calculate contact lead score"""
        try:
            score = 0
            
            # Email provided
            if contact.get('email'):
                score += 10
                
            # Phone provided
            if contact.get('phone'):
                score += 5
                
            # Title indicates decision maker
            title = contact.get('title', '').lower()
            decision_maker_titles = ['ceo', 'cto', 'cfo', 'president', 'director', 'manager', 'vp']
            if any(keyword in title for keyword in decision_maker_titles):
                score += 20
                
            # Company size (if available)
            if contact.get('company_id'):
                company = self.db.get_company(contact['company_id'])
                if company and company.get('size'):
                    size = company['size'].lower()
                    if 'enterprise' in size or 'large' in size:
                        score += 15
                    elif 'medium' in size:
                        score += 10
                    elif 'small' in size:
                        score += 5
                        
            # Lead source quality
            lead_source = contact.get('lead_source', '').lower()
            source_scores = {
                'referral': 25,
                'website': 15,
                'trade_show': 20,
                'social_media': 10,
                'cold_call': 5,
                'advertisement': 8
            }
            score += source_scores.get(lead_source, 0)
            
            return min(score, 100)  # Cap at 100
            
        except Exception:
            return 0
            
    def calculate_search_relevance(self, contact: Dict[str, Any], query: str) -> float:
        """Calculate search relevance score"""
        try:
            score = 0.0
            query_lower = query.lower()
            
            # Name match (highest weight)
            full_name = f"{contact['first_name']} {contact['last_name']}".lower()
            if query_lower in full_name:
                score += 10.0
                if full_name.startswith(query_lower):
                    score += 5.0
                    
            # Email match
            if contact.get('email') and query_lower in contact['email'].lower():
                score += 8.0
                
            # Company match
            if contact.get('company_name') and query_lower in contact['company_name'].lower():
                score += 6.0
                
            # Phone match
            if contact.get('phone') and query in contact['phone']:
                score += 4.0
                
            return score
            
        except Exception:
            return 0.0
            
    def get_lead_score_level(self, score: int) -> str:
        """Get lead score level description"""
        if score >= 80:
            return "Hot"
        elif score >= 60:
            return "Warm"
        elif score >= 40:
            return "Cool"
        else:
            return "Cold"
            
    def format_phone(self, phone: str) -> str:
        """Format phone number"""
        try:
            import re
            digits = re.sub(r'\D', '', phone)
            
            if len(digits) == 10:
                return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
            elif len(digits) == 11 and digits[0] == '1':
                return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
            else:
                return phone
        except Exception:
            return phone
            
    def format_time_ago(self, delta) -> str:
        """Format time delta as human readable"""
        try:
            days = delta.days
            hours = delta.seconds // 3600
            
            if days > 0:
                return f"{days} day{'s' if days != 1 else ''} ago"
            elif hours > 0:
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            else:
                return "Less than an hour ago"
        except Exception:
            return "Unknown"
            
    def create_or_get_company(self, company_data: Dict[str, Any]) -> str:
        """Create company or get existing one"""
        try:
            # Check if company exists by name
            existing = self.db.execute_single_query(
                "SELECT company_id FROM companies WHERE name = ?",
                (company_data['name'],)
            )
            
            if existing:
                return existing['company_id']
                
            # Create new company
            company_id = f"company_{datetime.now().timestamp()}"
            company = {
                'company_id': company_id,
                'name': company_data['name'],
                'industry': company_data.get('industry'),
                'website': company_data.get('website'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            success = self.db.save_company(company)
            if success:
                return company_id
            else:
                raise Exception("Failed to create company")
                
        except Exception as e:
            print(f"Error creating company: {e}")
            return None
            
    def find_company_by_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """Find company by email domain"""
        try:
            company = self.db.execute_single_query(
                "SELECT * FROM companies WHERE website LIKE ?",
                (f"%{domain}%",)
            )
            return company
        except Exception:
            return None
            
    def merge_contact_data(self, primary: Dict[str, Any], secondary: Dict[str, Any]) -> Dict[str, Any]:
        """Merge data from secondary contact into primary"""
        try:
            merged = {}
            
            # Merge non-empty fields from secondary to primary
            for key, value in secondary.items():
                if key not in ['contact_id', 'created_at', 'updated_at']:
                    if value and not primary.get(key):
                        merged[key] = value
                        
            # Merge tags
            primary_tags = set(primary.get('tags', []))
            secondary_tags = set(secondary.get('tags', []))
            merged_tags = list(primary_tags.union(secondary_tags))
            if merged_tags != primary.get('tags', []):
                merged['tags'] = merged_tags
                
            # Merge custom fields
            primary_custom = primary.get('custom_fields', {})
            secondary_custom = secondary.get('custom_fields', {})
            merged_custom = {**primary_custom, **secondary_custom}
            if merged_custom != primary_custom:
                merged['custom_fields'] = merged_custom
                
            merged['updated_at'] = datetime.now().isoformat()
            
            return merged
            
        except Exception:
            return {'updated_at': datetime.now().isoformat()}
            
    def transfer_contact_activities(self, from_contact_id: str, to_contact_id: str):
        """Transfer activities from one contact to another"""
        try:
            self.db.execute_update(
                "UPDATE activities SET contact_id = ? WHERE contact_id = ?",
                (to_contact_id, from_contact_id)
            )
        except Exception as e:
            print(f"Error transferring activities: {e}")
            
    def transfer_contact_opportunities(self, from_contact_id: str, to_contact_id: str):
        """Transfer opportunities from one contact to another"""
        try:
            self.db.execute_update(
                "UPDATE opportunities SET contact_id = ? WHERE contact_id = ?",
                (to_contact_id, from_contact_id)
            )
        except Exception as e:
            print(f"Error transferring opportunities: {e}")
            
    def merge_with_existing(self, existing_contact: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge new data with existing contact"""
        try:
            contact_id = existing_contact['contact_id']
            
            # Merge data
            merged_data = self.merge_contact_data(existing_contact, new_data)
            
            if merged_data:
                # Update existing contact
                self.db.update_contact(contact_id, merged_data)
                
                # Create merge activity
                self.create_contact_activity(contact_id, {
                    'activity_type': 'contact_updated',
                    'subject': 'Contact Auto-Merged',
                    'description': 'Contact data automatically merged with duplicate submission'
                })
                
            return {
                'success': True,
                'contact_id': contact_id,
                'merged': True,
                'message': 'Contact merged with existing record'
            }
            
        except Exception as e:
            raise Exception(f"Error merging with existing contact: {e}")