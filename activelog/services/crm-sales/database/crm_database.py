"""
CRM Database Management
Handles all database operations for the CRM system
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from contextlib import contextmanager


class CRMDatabase:
    """CRM database manager"""
    
    def __init__(self, db_path: str = "data/crm_sales.db"):
        self.db_path = db_path
        self.ensure_data_directory()
        
    def ensure_data_directory(self):
        """Ensure data directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
            
    def initialize_tables(self):
        """Initialize all CRM database tables"""
        with self.get_connection() as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Companies/Accounts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    company_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    industry TEXT,
                    size TEXT,
                    revenue REAL,
                    website TEXT,
                    phone TEXT,
                    address TEXT,
                    city TEXT,
                    state TEXT,
                    country TEXT,
                    zip_code TEXT,
                    description TEXT,
                    tags TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Contacts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS contacts (
                    contact_id TEXT PRIMARY KEY,
                    company_id TEXT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    email TEXT UNIQUE,
                    phone TEXT,
                    mobile TEXT,
                    title TEXT,
                    department TEXT,
                    address TEXT,
                    city TEXT,
                    state TEXT,
                    country TEXT,
                    zip_code TEXT,
                    lead_source TEXT,
                    lead_score INTEGER DEFAULT 0,
                    contact_status TEXT DEFAULT 'active',
                    owner_id TEXT,
                    tags TEXT,
                    custom_fields TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (company_id) REFERENCES companies (company_id)
                )
            """)
            
            # Opportunities table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS opportunities (
                    opportunity_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    company_id TEXT,
                    contact_id TEXT,
                    owner_id TEXT,
                    stage TEXT NOT NULL,
                    amount REAL,
                    probability REAL DEFAULT 0,
                    close_date TEXT,
                    description TEXT,
                    lead_source TEXT,
                    campaign_id TEXT,
                    territory_id TEXT,
                    tags TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    closed_at TEXT,
                    close_reason TEXT,
                    FOREIGN KEY (company_id) REFERENCES companies (company_id),
                    FOREIGN KEY (contact_id) REFERENCES contacts (contact_id)
                )
            """)
            
            # Activities table (calls, meetings, emails, etc.)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    activity_id TEXT PRIMARY KEY,
                    activity_type TEXT NOT NULL,
                    subject TEXT,
                    description TEXT,
                    contact_id TEXT,
                    company_id TEXT,
                    opportunity_id TEXT,
                    owner_id TEXT,
                    status TEXT DEFAULT 'completed',
                    priority TEXT DEFAULT 'medium',
                    due_date TEXT,
                    completed_at TEXT,
                    duration_minutes INTEGER,
                    outcome TEXT,
                    follow_up_required BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (contact_id) REFERENCES contacts (contact_id),
                    FOREIGN KEY (company_id) REFERENCES companies (company_id),
                    FOREIGN KEY (opportunity_id) REFERENCES opportunities (opportunity_id)
                )
            """)
            
            # Tasks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    contact_id TEXT,
                    company_id TEXT,
                    opportunity_id TEXT,
                    assigned_to TEXT,
                    created_by TEXT,
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'medium',
                    due_date TEXT,
                    completed_at TEXT,
                    tags TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (contact_id) REFERENCES contacts (contact_id),
                    FOREIGN KEY (company_id) REFERENCES companies (company_id),
                    FOREIGN KEY (opportunity_id) REFERENCES opportunities (opportunity_id)
                )
            """)
            
            # Email campaigns table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS email_campaigns (
                    campaign_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sender_email TEXT,
                    sender_name TEXT,
                    status TEXT DEFAULT 'draft',
                    target_segment TEXT,
                    send_date TEXT,
                    created_by TEXT,
                    total_recipients INTEGER DEFAULT 0,
                    delivered_count INTEGER DEFAULT 0,
                    opened_count INTEGER DEFAULT 0,
                    clicked_count INTEGER DEFAULT 0,
                    bounced_count INTEGER DEFAULT 0,
                    unsubscribed_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Campaign recipients table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS campaign_recipients (
                    recipient_id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    contact_id TEXT NOT NULL,
                    email TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    delivered_at TEXT,
                    opened_at TEXT,
                    clicked_at TEXT,
                    bounced_at TEXT,
                    unsubscribed_at TEXT,
                    FOREIGN KEY (campaign_id) REFERENCES email_campaigns (campaign_id),
                    FOREIGN KEY (contact_id) REFERENCES contacts (contact_id)
                )
            """)
            
            # Lead scoring rules table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lead_scoring_rules (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    condition_field TEXT NOT NULL,
                    condition_operator TEXT NOT NULL,
                    condition_value TEXT NOT NULL,
                    score_change INTEGER NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Pipeline stages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_stages (
                    stage_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    probability REAL DEFAULT 0,
                    stage_order INTEGER NOT NULL,
                    is_closed BOOLEAN DEFAULT FALSE,
                    is_won BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Territories table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS territories (
                    territory_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    territory_type TEXT DEFAULT 'geographic',
                    criteria TEXT,
                    assigned_to TEXT,
                    manager_id TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Commission plans table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS commission_plans (
                    plan_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    plan_type TEXT NOT NULL,
                    base_rate REAL DEFAULT 0,
                    tiers TEXT,
                    effective_date TEXT NOT NULL,
                    end_date TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Commission calculations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS commission_calculations (
                    calculation_id TEXT PRIMARY KEY,
                    opportunity_id TEXT NOT NULL,
                    sales_rep_id TEXT NOT NULL,
                    plan_id TEXT NOT NULL,
                    base_amount REAL NOT NULL,
                    commission_rate REAL NOT NULL,
                    commission_amount REAL NOT NULL,
                    calculation_date TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    status TEXT DEFAULT 'calculated',
                    paid_date TEXT,
                    FOREIGN KEY (opportunity_id) REFERENCES opportunities (opportunity_id)
                )
            """)
            
            # Automation workflows table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS automation_workflows (
                    workflow_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    trigger_conditions TEXT NOT NULL,
                    actions TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    execution_count INTEGER DEFAULT 0,
                    last_executed TEXT,
                    created_by TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Customer segments table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS customer_segments (
                    segment_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    criteria TEXT NOT NULL,
                    segment_type TEXT DEFAULT 'dynamic',
                    contact_count INTEGER DEFAULT 0,
                    last_updated TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Forecasts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sales_forecasts (
                    forecast_id TEXT PRIMARY KEY,
                    forecast_name TEXT NOT NULL,
                    forecast_period TEXT NOT NULL,
                    forecast_type TEXT NOT NULL,
                    territory_id TEXT,
                    sales_rep_id TEXT,
                    forecasted_amount REAL NOT NULL,
                    confidence_level REAL,
                    created_by TEXT,
                    forecast_date TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    actual_amount REAL,
                    variance_amount REAL,
                    variance_percentage REAL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Notes table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    note_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    contact_id TEXT,
                    company_id TEXT,
                    opportunity_id TEXT,
                    created_by TEXT,
                    is_private BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (contact_id) REFERENCES contacts (contact_id),
                    FOREIGN KEY (company_id) REFERENCES companies (company_id),
                    FOREIGN KEY (opportunity_id) REFERENCES opportunities (opportunity_id)
                )
            """)
            
            # Call logs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS call_logs (
                    call_id TEXT PRIMARY KEY,
                    contact_id TEXT,
                    company_id TEXT,
                    opportunity_id TEXT,
                    caller_id TEXT,
                    call_type TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    duration_seconds INTEGER,
                    disposition TEXT,
                    notes TEXT,
                    recording_url TEXT,
                    transcription TEXT,
                    sentiment_score REAL,
                    follow_up_required BOOLEAN DEFAULT FALSE,
                    call_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (contact_id) REFERENCES contacts (contact_id),
                    FOREIGN KEY (company_id) REFERENCES companies (company_id),
                    FOREIGN KEY (opportunity_id) REFERENCES opportunities (opportunity_id)
                )
            """)
            
            # User/Sales rep table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    manager_id TEXT,
                    territory_id TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    last_login TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_contacts_owner ON contacts(owner_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_stage ON opportunities(stage)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_owner ON opportunities(owner_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_close_date ON opportunities(close_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_contact ON activities(contact_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_type ON activities(activity_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activities_date ON activities(due_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            
            conn.commit()
            
    def dict_from_row(self, row) -> Dict[str, Any]:
        """Convert database row to dictionary"""
        if row is None:
            return None
        return dict(row)
        
    def execute_query(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results as list of dictionaries"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [self.dict_from_row(row) for row in cursor.fetchall()]
            
    def execute_single_query(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """Execute SELECT query and return single result as dictionary"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return self.dict_from_row(row)
            
    def execute_update(self, query: str, params: Tuple = ()) -> bool:
        """Execute INSERT/UPDATE/DELETE query"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(query, params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Database update error: {e}")
            return False
            
    def execute_batch_update(self, query: str, params_list: List[Tuple]) -> bool:
        """Execute batch INSERT/UPDATE operations"""
        try:
            with self.get_connection() as conn:
                conn.executemany(query, params_list)
                conn.commit()
                return True
        except Exception as e:
            print(f"Database batch update error: {e}")
            return False
            
    # Contact management methods
    def save_contact(self, contact: Dict[str, Any]) -> bool:
        """Save contact to database"""
        query = """
            INSERT INTO contacts (
                contact_id, company_id, first_name, last_name, email, phone, mobile,
                title, department, address, city, state, country, zip_code,
                lead_source, lead_score, contact_status, owner_id, tags, custom_fields,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            contact['contact_id'], contact.get('company_id'), contact['first_name'],
            contact['last_name'], contact.get('email'), contact.get('phone'),
            contact.get('mobile'), contact.get('title'), contact.get('department'),
            contact.get('address'), contact.get('city'), contact.get('state'),
            contact.get('country'), contact.get('zip_code'), contact.get('lead_source'),
            contact.get('lead_score', 0), contact.get('contact_status', 'active'),
            contact.get('owner_id'), json.dumps(contact.get('tags', [])),
            json.dumps(contact.get('custom_fields', {})),
            contact['created_at'], contact['updated_at']
        )
        
        return self.execute_update(query, params)
        
    def get_contact(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Get contact by ID"""
        query = "SELECT * FROM contacts WHERE contact_id = ?"
        contact = self.execute_single_query(query, (contact_id,))
        
        if contact:
            # Parse JSON fields
            contact['tags'] = json.loads(contact.get('tags', '[]'))
            contact['custom_fields'] = json.loads(contact.get('custom_fields', '{}'))
            
        return contact
        
    def update_contact(self, contact_id: str, updates: Dict[str, Any]) -> bool:
        """Update contact"""
        # Build dynamic update query
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if key in ['tags', 'custom_fields']:
                value = json.dumps(value)
            set_clauses.append(f"{key} = ?")
            params.append(value)
            
        params.append(contact_id)
        
        query = f"UPDATE contacts SET {', '.join(set_clauses)} WHERE contact_id = ?"
        return self.execute_update(query, tuple(params))
        
    def list_contacts(self, filters: Dict[str, Any], page: int, limit: int) -> List[Dict[str, Any]]:
        """List contacts with filtering and pagination"""
        where_clauses = []
        params = []
        
        # Build WHERE clause from filters
        for key, value in filters.items():
            if key in ['first_name', 'last_name', 'email', 'company_id', 'owner_id', 'contact_status']:
                where_clauses.append(f"{key} = ?")
                params.append(value)
            elif key == 'search':
                where_clauses.append("(first_name LIKE ? OR last_name LIKE ? OR email LIKE ?)")
                search_term = f"%{value}%"
                params.extend([search_term, search_term, search_term])
                
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Add pagination
        offset = (page - 1) * limit
        params.extend([limit, offset])
        
        query = f"SELECT * FROM contacts {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?"
        contacts = self.execute_query(query, tuple(params))
        
        # Parse JSON fields
        for contact in contacts:
            contact['tags'] = json.loads(contact.get('tags', '[]'))
            contact['custom_fields'] = json.loads(contact.get('custom_fields', '{}'))
            
        return contacts
        
    def get_contact_count(self, filters: Dict[str, Any] = None) -> int:
        """Get total contact count with filters"""
        where_clauses = []
        params = []
        
        if filters:
            for key, value in filters.items():
                if key in ['first_name', 'last_name', 'email', 'company_id', 'owner_id', 'contact_status']:
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
                elif key == 'search':
                    where_clauses.append("(first_name LIKE ? OR last_name LIKE ? OR email LIKE ?)")
                    search_term = f"%{value}%"
                    params.extend([search_term, search_term, search_term])
                    
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"SELECT COUNT(*) as count FROM contacts {where_clause}"
        
        result = self.execute_single_query(query, tuple(params))
        return result['count'] if result else 0
        
    # Company methods
    def save_company(self, company: Dict[str, Any]) -> bool:
        """Save company to database"""
        query = """
            INSERT INTO companies (
                company_id, name, industry, size, revenue, website, phone,
                address, city, state, country, zip_code, description, tags,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            company['company_id'], company['name'], company.get('industry'),
            company.get('size'), company.get('revenue'), company.get('website'),
            company.get('phone'), company.get('address'), company.get('city'),
            company.get('state'), company.get('country'), company.get('zip_code'),
            company.get('description'), json.dumps(company.get('tags', [])),
            company['created_at'], company['updated_at']
        )
        
        return self.execute_update(query, params)
        
    def get_company(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Get company by ID"""
        query = "SELECT * FROM companies WHERE company_id = ?"
        company = self.execute_single_query(query, (company_id,))
        
        if company:
            company['tags'] = json.loads(company.get('tags', '[]'))
            
        return company
        
    # Opportunity methods
    def save_opportunity(self, opportunity: Dict[str, Any]) -> bool:
        """Save opportunity to database"""
        query = """
            INSERT INTO opportunities (
                opportunity_id, name, company_id, contact_id, owner_id, stage,
                amount, probability, close_date, description, lead_source,
                campaign_id, territory_id, tags, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            opportunity['opportunity_id'], opportunity['name'],
            opportunity.get('company_id'), opportunity.get('contact_id'),
            opportunity.get('owner_id'), opportunity['stage'],
            opportunity.get('amount'), opportunity.get('probability'),
            opportunity.get('close_date'), opportunity.get('description'),
            opportunity.get('lead_source'), opportunity.get('campaign_id'),
            opportunity.get('territory_id'), json.dumps(opportunity.get('tags', [])),
            opportunity['created_at'], opportunity['updated_at']
        )
        
        return self.execute_update(query, params)
        
    def get_opportunity(self, opportunity_id: str) -> Optional[Dict[str, Any]]:
        """Get opportunity by ID"""
        query = "SELECT * FROM opportunities WHERE opportunity_id = ?"
        opportunity = self.execute_single_query(query, (opportunity_id,))
        
        if opportunity:
            opportunity['tags'] = json.loads(opportunity.get('tags', '[]'))
            
        return opportunity
        
    def update_opportunity(self, opportunity_id: str, updates: Dict[str, Any]) -> bool:
        """Update opportunity"""
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            if key == 'tags':
                value = json.dumps(value)
            set_clauses.append(f"{key} = ?")
            params.append(value)
            
        params.append(opportunity_id)
        
        query = f"UPDATE opportunities SET {', '.join(set_clauses)} WHERE opportunity_id = ?"
        return self.execute_update(query, tuple(params))
        
    # Activity methods
    def save_activity(self, activity: Dict[str, Any]) -> bool:
        """Save activity to database"""
        query = """
            INSERT INTO activities (
                activity_id, activity_type, subject, description, contact_id,
                company_id, opportunity_id, owner_id, status, priority,
                due_date, completed_at, duration_minutes, outcome,
                follow_up_required, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            activity['activity_id'], activity['activity_type'],
            activity.get('subject'), activity.get('description'),
            activity.get('contact_id'), activity.get('company_id'),
            activity.get('opportunity_id'), activity.get('owner_id'),
            activity.get('status', 'completed'), activity.get('priority', 'medium'),
            activity.get('due_date'), activity.get('completed_at'),
            activity.get('duration_minutes'), activity.get('outcome'),
            activity.get('follow_up_required', False),
            activity['created_at'], activity['updated_at']
        )
        
        return self.execute_update(query, params)
        
    def get_contact_activities(self, contact_id: str) -> List[Dict[str, Any]]:
        """Get activities for a contact"""
        query = """
            SELECT * FROM activities 
            WHERE contact_id = ? 
            ORDER BY created_at DESC
        """
        return self.execute_query(query, (contact_id,))
        
    # Generic methods for other tables
    def save_record(self, table: str, record: Dict[str, Any]) -> bool:
        """Generic method to save a record to any table"""
        columns = list(record.keys())
        placeholders = ', '.join(['?' for _ in columns])
        
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        params = tuple(record.values())
        
        return self.execute_update(query, params)
        
    def get_record(self, table: str, id_field: str, id_value: str) -> Optional[Dict[str, Any]]:
        """Generic method to get a record from any table"""
        query = f"SELECT * FROM {table} WHERE {id_field} = ?"
        return self.execute_single_query(query, (id_value,))
        
    def update_record(self, table: str, id_field: str, id_value: str, updates: Dict[str, Any]) -> bool:
        """Generic method to update a record in any table"""
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            params.append(value)
            
        params.append(id_value)
        
        query = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {id_field} = ?"
        return self.execute_update(query, tuple(params))
        
    def delete_record(self, table: str, id_field: str, id_value: str) -> bool:
        """Generic method to delete a record from any table"""
        query = f"DELETE FROM {table} WHERE {id_field} = ?"
        return self.execute_update(query, (id_value,))