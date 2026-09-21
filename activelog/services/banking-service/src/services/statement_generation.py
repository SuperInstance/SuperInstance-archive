import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
from jinja2 import Environment, DictLoader
import json
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class StatementType(Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    ON_DEMAND = "on_demand"

class StatementFormat(Enum):
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    CSV = "csv"

@dataclass
class Statement:
    statement_id: str
    account_id: str
    customer_id: str
    statement_type: StatementType
    period_start: datetime
    period_end: datetime
    balance_start: Decimal
    balance_end: Decimal
    total_credits: Decimal
    total_debits: Decimal
    transaction_count: int
    interest_earned: Decimal
    fees_charged: Decimal
    generated_at: datetime
    format: StatementFormat
    file_path: str

@dataclass
class TransactionSummary:
    transaction_id: str
    date: datetime
    description: str
    amount: Decimal
    balance: Decimal
    transaction_type: str

class StatementGenerationService:
    def __init__(self):
        self.statements = {}
        self.generation_active = False
        self.template_env = Environment(loader=DictLoader(self._get_templates()))
        
    async def start_auto_generation(self):
        """Start automatic statement generation"""
        self.generation_active = True
        asyncio.create_task(self._auto_generation_loop())
        logger.info("Automatic statement generation started")
    
    async def stop_generation(self):
        """Stop statement generation"""
        self.generation_active = False
        logger.info("Statement generation stopped")
    
    async def generate_statement(self, request_data: Dict) -> Dict:
        """Generate account statement"""
        try:
            statement_id = str(uuid.uuid4())
            account_id = request_data['account_id']
            customer_id = request_data['customer_id']
            statement_type = StatementType(request_data.get('statement_type', 'monthly'))
            statement_format = StatementFormat(request_data.get('format', 'pdf'))
            
            # Calculate period dates
            period_end = datetime.now()
            if statement_type == StatementType.MONTHLY:
                period_start = period_end.replace(day=1) - timedelta(days=1)
                period_start = period_start.replace(day=1)
            elif statement_type == StatementType.QUARTERLY:
                quarter = (period_end.month - 1) // 3
                period_start = period_end.replace(month=quarter * 3 + 1, day=1)
            else:
                period_start = period_end.replace(month=1, day=1)
            
            # Get transaction data for period
            transactions = await self._get_transactions_for_period(
                account_id, period_start, period_end
            )
            
            # Calculate summary data
            balance_start = Decimal(str(request_data.get('balance_start', 0)))
            balance_end = Decimal(str(request_data.get('balance_end', 0)))
            total_credits = sum(t.amount for t in transactions if t.amount > 0)
            total_debits = sum(abs(t.amount) for t in transactions if t.amount < 0)
            interest_earned = Decimal(str(request_data.get('interest_earned', 0)))
            fees_charged = Decimal(str(request_data.get('fees_charged', 0)))
            
            # Generate statement file
            file_path = await self._generate_statement_file(
                account_id, statement_id, statement_format, {
                    'account_id': account_id,
                    'customer_id': customer_id,
                    'period_start': period_start,
                    'period_end': period_end,
                    'balance_start': balance_start,
                    'balance_end': balance_end,
                    'total_credits': total_credits,
                    'total_debits': total_debits,
                    'interest_earned': interest_earned,
                    'fees_charged': fees_charged,
                    'transactions': transactions
                }
            )
            
            statement = Statement(
                statement_id=statement_id,
                account_id=account_id,
                customer_id=customer_id,
                statement_type=statement_type,
                period_start=period_start,
                period_end=period_end,
                balance_start=balance_start,
                balance_end=balance_end,
                total_credits=total_credits,
                total_debits=total_debits,
                transaction_count=len(transactions),
                interest_earned=interest_earned,
                fees_charged=fees_charged,
                generated_at=datetime.now(),
                format=statement_format,
                file_path=file_path
            )
            
            self.statements[statement_id] = statement
            
            return {
                'success': True,
                'statement_id': statement_id,
                'file_path': file_path,
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'transaction_count': len(transactions),
                'balance_end': float(balance_end)
            }
        
        except Exception as e:
            logger.error(f"Error generating statement: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_statement_history(self, customer_id: str) -> Dict:
        """Get statement history for customer"""
        try:
            customer_statements = [
                {
                    'statement_id': stmt.statement_id,
                    'account_id': stmt.account_id,
                    'statement_type': stmt.statement_type.value,
                    'period_start': stmt.period_start.isoformat(),
                    'period_end': stmt.period_end.isoformat(),
                    'generated_at': stmt.generated_at.isoformat(),
                    'format': stmt.format.value,
                    'file_path': stmt.file_path
                }
                for stmt in self.statements.values()
                if stmt.customer_id == customer_id
            ]
            
            return {
                'success': True,
                'customer_id': customer_id,
                'statements': customer_statements,
                'total_statements': len(customer_statements)
            }
        
        except Exception as e:
            logger.error(f"Error getting statement history: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _get_transactions_for_period(self, account_id: str, start_date: datetime, end_date: datetime) -> List[TransactionSummary]:
        """Get transactions for statement period"""
        # This would integrate with the virtual accounts service
        # For now, return mock data
        transactions = []
        
        # Generate sample transactions
        current_balance = Decimal('1000.00')
        for i in range(10):
            transaction = TransactionSummary(
                transaction_id=str(uuid.uuid4()),
                date=start_date + timedelta(days=i * 2),
                description=f"Transaction {i + 1}",
                amount=Decimal(str((-1) ** i * (50 + i * 10))),
                balance=current_balance,
                transaction_type="debit" if i % 2 == 0 else "credit"
            )
            current_balance += transaction.amount
            transaction.balance = current_balance
            transactions.append(transaction)
        
        return transactions
    
    async def _generate_statement_file(self, account_id: str, statement_id: str, format: StatementFormat, data: Dict) -> str:
        """Generate statement file in specified format"""
        file_dir = f"/tmp/statements/{account_id}"
        file_name = f"statement_{statement_id}.{format.value}"
        file_path = f"{file_dir}/{file_name}"
        
        # Ensure directory exists (in production, use proper file storage)
        import os
        os.makedirs(file_dir, exist_ok=True)
        
        if format == StatementFormat.JSON:
            with open(file_path, 'w') as f:
                json.dump({
                    'statement_id': statement_id,
                    'account_id': data['account_id'],
                    'period_start': data['period_start'].isoformat(),
                    'period_end': data['period_end'].isoformat(),
                    'balance_start': float(data['balance_start']),
                    'balance_end': float(data['balance_end']),
                    'total_credits': float(data['total_credits']),
                    'total_debits': float(data['total_debits']),
                    'transactions': [
                        {
                            'transaction_id': t.transaction_id,
                            'date': t.date.isoformat(),
                            'description': t.description,
                            'amount': float(t.amount),
                            'balance': float(t.balance)
                        }
                        for t in data['transactions']
                    ]
                }, f, indent=2)
        
        elif format == StatementFormat.HTML:
            template = self.template_env.get_template('statement_html')
            html_content = template.render(**data)
            with open(file_path, 'w') as f:
                f.write(html_content)
        
        elif format == StatementFormat.CSV:
            import csv
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Date', 'Description', 'Amount', 'Balance', 'Type'])
                for t in data['transactions']:
                    writer.writerow([
                        t.date.strftime('%Y-%m-%d'),
                        t.description,
                        float(t.amount),
                        float(t.balance),
                        t.transaction_type
                    ])
        
        return file_path
    
    def _get_templates(self) -> Dict[str, str]:
        """Get statement templates"""
        return {
            'statement_html': '''
<!DOCTYPE html>
<html>
<head>
    <title>Account Statement</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .account-info { margin-bottom: 20px; }
        .summary { background-color: #f5f5f5; padding: 15px; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Account Statement</h1>
        <p>{{ period_start.strftime('%B %d, %Y') }} - {{ period_end.strftime('%B %d, %Y') }}</p>
    </div>
    
    <div class="account-info">
        <p><strong>Account ID:</strong> {{ account_id }}</p>
        <p><strong>Customer ID:</strong> {{ customer_id }}</p>
    </div>
    
    <div class="summary">
        <h3>Summary</h3>
        <p><strong>Opening Balance:</strong> ${{ "%.2f"|format(balance_start) }}</p>
        <p><strong>Closing Balance:</strong> ${{ "%.2f"|format(balance_end) }}</p>
        <p><strong>Total Credits:</strong> ${{ "%.2f"|format(total_credits) }}</p>
        <p><strong>Total Debits:</strong> ${{ "%.2f"|format(total_debits) }}</p>
        <p><strong>Interest Earned:</strong> ${{ "%.2f"|format(interest_earned) }}</p>
        <p><strong>Fees Charged:</strong> ${{ "%.2f"|format(fees_charged) }}</p>
    </div>
    
    <h3>Transaction Details</h3>
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Description</th>
                <th>Amount</th>
                <th>Balance</th>
            </tr>
        </thead>
        <tbody>
            {% for transaction in transactions %}
            <tr>
                <td>{{ transaction.date.strftime('%m/%d/%Y') }}</td>
                <td>{{ transaction.description }}</td>
                <td>${{ "%.2f"|format(transaction.amount) }}</td>
                <td>${{ "%.2f"|format(transaction.balance) }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
            '''
        }
    
    async def _auto_generation_loop(self):
        """Automatic statement generation loop"""
        while self.generation_active:
            try:
                # Check if it's time to generate monthly statements
                now = datetime.now()
                if now.day == 1 and now.hour == 2:  # Generate on 1st at 2 AM
                    await self._generate_monthly_statements()
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in auto generation loop: {e}")
                await asyncio.sleep(3600)
    
    async def _generate_monthly_statements(self):
        """Generate monthly statements for all accounts"""
        logger.info("Starting monthly statement generation")
        # This would integrate with virtual accounts service
        # to get all active accounts and generate statements