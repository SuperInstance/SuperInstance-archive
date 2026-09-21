"""
Shipping Calculator
Handles shipping rate calculations, carrier integrations, and delivery estimates
"""

import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class ShippingCarrier(Enum):
    USPS = "usps"
    UPS = "ups" 
    FEDEX = "fedex"
    DHL = "dhl"
    CUSTOM = "custom"


class ShippingService(Enum):
    STANDARD = "standard"
    EXPEDITED = "expedited"
    OVERNIGHT = "overnight"
    SAME_DAY = "same_day"
    PICKUP = "pickup"


@dataclass
class Address:
    first_name: str
    last_name: str
    company: Optional[str]
    address1: str
    address2: Optional[str]
    city: str
    state: str
    zip: str
    country: str
    phone: Optional[str]


@dataclass
class Package:
    weight: float  # in pounds
    length: float  # in inches
    width: float
    height: float
    value: float  # for insurance
    description: Optional[str] = None


@dataclass
class ShippingRate:
    carrier: ShippingCarrier
    service: str
    rate: float
    delivery_days: int
    delivery_date: str
    currency: str = "USD"


class ShippingCalculator:
    """Handles shipping calculations and carrier integrations"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        
        # Carrier API configurations
        self.usps_config = config.get('usps', {})
        self.ups_config = config.get('ups', {})
        self.fedex_config = config.get('fedex', {})
        self.dhl_config = config.get('dhl', {})
        
        # Default shipping zones and rates
        self.shipping_zones = self.load_shipping_zones()
        self.free_shipping_threshold = config.get('free_shipping_threshold', 50.0)
        
    def calculate_shipping_rates(self, shipping_data: Dict[str, Any]) -> List[ShippingRate]:
        """Calculate shipping rates for all carriers"""
        try:
            origin_address = Address(**shipping_data['origin_address'])
            destination_address = Address(**shipping_data['destination_address'])
            packages = [Package(**pkg) for pkg in shipping_data['packages']]
            
            rates = []
            
            # Calculate rates for each carrier
            if self.usps_config.get('enabled', False):
                usps_rates = self.calculate_usps_rates(origin_address, destination_address, packages)
                rates.extend(usps_rates)
                
            if self.ups_config.get('enabled', False):
                ups_rates = self.calculate_ups_rates(origin_address, destination_address, packages)
                rates.extend(ups_rates)
                
            if self.fedex_config.get('enabled', False):
                fedex_rates = self.calculate_fedex_rates(origin_address, destination_address, packages)
                rates.extend(fedex_rates)
                
            if self.dhl_config.get('enabled', False):
                dhl_rates = self.calculate_dhl_rates(origin_address, destination_address, packages)
                rates.extend(dhl_rates)
                
            # Add custom/local delivery rates
            custom_rates = self.calculate_custom_rates(origin_address, destination_address, packages)
            rates.extend(custom_rates)
            
            # Apply discounts and adjustments
            rates = self.apply_shipping_adjustments(rates, shipping_data)
            
            # Sort by price
            rates.sort(key=lambda r: r.rate)
            
            return rates
            
        except Exception as e:
            raise Exception(f"Error calculating shipping rates: {e}")
            
    def calculate_usps_rates(self, origin: Address, destination: Address, packages: List[Package]) -> List[ShippingRate]:
        """Calculate USPS shipping rates"""
        try:
            rates = []
            total_weight = sum(pkg.weight for pkg in packages)
            
            # USPS API integration (simplified for demo)
            base_rates = {
                'Priority Mail': 8.95,
                'Priority Mail Express': 24.90,
                'Ground Advantage': 6.50,
                'Media Mail': 3.65
            }
            
            for service, base_rate in base_rates.items():
                # Calculate rate based on weight and distance
                weight_multiplier = max(1, total_weight / 2)  # Every 2 lbs
                zone_multiplier = self.get_zone_multiplier(origin.zip, destination.zip)
                
                final_rate = base_rate * weight_multiplier * zone_multiplier
                
                # Estimate delivery days
                delivery_days = self.estimate_delivery_days('usps', service, origin.zip, destination.zip)
                delivery_date = (datetime.now() + timedelta(days=delivery_days)).strftime('%Y-%m-%d')
                
                rate = ShippingRate(
                    carrier=ShippingCarrier.USPS,
                    service=service,
                    rate=round(final_rate, 2),
                    delivery_days=delivery_days,
                    delivery_date=delivery_date
                )
                rates.append(rate)
                
            return rates
            
        except Exception as e:
            print(f"Error calculating USPS rates: {e}")
            return []
            
    def calculate_ups_rates(self, origin: Address, destination: Address, packages: List[Package]) -> List[ShippingRate]:
        """Calculate UPS shipping rates"""
        try:
            rates = []
            total_weight = sum(pkg.weight for pkg in packages)
            
            # UPS API integration (simplified for demo)
            base_rates = {
                'UPS Ground': 9.45,
                'UPS 3 Day Select': 18.20,
                'UPS 2nd Day Air': 24.85,
                'UPS Next Day Air': 45.90
            }
            
            for service, base_rate in base_rates.items():
                weight_multiplier = max(1, total_weight / 2)
                zone_multiplier = self.get_zone_multiplier(origin.zip, destination.zip)
                
                final_rate = base_rate * weight_multiplier * zone_multiplier
                
                delivery_days = self.estimate_delivery_days('ups', service, origin.zip, destination.zip)
                delivery_date = (datetime.now() + timedelta(days=delivery_days)).strftime('%Y-%m-%d')
                
                rate = ShippingRate(
                    carrier=ShippingCarrier.UPS,
                    service=service,
                    rate=round(final_rate, 2),
                    delivery_days=delivery_days,
                    delivery_date=delivery_date
                )
                rates.append(rate)
                
            return rates
            
        except Exception as e:
            print(f"Error calculating UPS rates: {e}")
            return []
            
    def calculate_fedex_rates(self, origin: Address, destination: Address, packages: List[Package]) -> List[ShippingRate]:
        """Calculate FedEx shipping rates"""
        try:
            rates = []
            total_weight = sum(pkg.weight for pkg in packages)
            
            # FedEx API integration (simplified for demo)
            base_rates = {
                'FedEx Ground': 8.75,
                'FedEx Express Saver': 19.50,
                'FedEx 2Day': 26.40,
                'FedEx Standard Overnight': 48.20,
                'FedEx Priority Overnight': 65.85
            }
            
            for service, base_rate in base_rates.items():
                weight_multiplier = max(1, total_weight / 2)
                zone_multiplier = self.get_zone_multiplier(origin.zip, destination.zip)
                
                final_rate = base_rate * weight_multiplier * zone_multiplier
                
                delivery_days = self.estimate_delivery_days('fedex', service, origin.zip, destination.zip)
                delivery_date = (datetime.now() + timedelta(days=delivery_days)).strftime('%Y-%m-%d')
                
                rate = ShippingRate(
                    carrier=ShippingCarrier.FEDEX,
                    service=service,
                    rate=round(final_rate, 2),
                    delivery_days=delivery_days,
                    delivery_date=delivery_date
                )
                rates.append(rate)
                
            return rates
            
        except Exception as e:
            print(f"Error calculating FedEx rates: {e}")
            return []
            
    def calculate_dhl_rates(self, origin: Address, destination: Address, packages: List[Package]) -> List[ShippingRate]:
        """Calculate DHL shipping rates"""
        try:
            rates = []
            total_weight = sum(pkg.weight for pkg in packages)
            
            # DHL is primarily international, check if needed
            if origin.country != destination.country:
                base_rates = {
                    'DHL Express Worldwide': 45.00,
                    'DHL Express 12:00': 65.00,
                    'DHL Express 10:30': 85.00
                }
                
                for service, base_rate in base_rates.items():
                    weight_multiplier = max(1, total_weight / 2)
                    international_multiplier = 1.5  # International shipping premium
                    
                    final_rate = base_rate * weight_multiplier * international_multiplier
                    
                    delivery_days = self.estimate_delivery_days('dhl', service, origin.zip, destination.zip)
                    delivery_date = (datetime.now() + timedelta(days=delivery_days)).strftime('%Y-%m-%d')
                    
                    rate = ShippingRate(
                        carrier=ShippingCarrier.DHL,
                        service=service,
                        rate=round(final_rate, 2),
                        delivery_days=delivery_days,
                        delivery_date=delivery_date
                    )
                    rates.append(rate)
                    
            return rates
            
        except Exception as e:
            print(f"Error calculating DHL rates: {e}")
            return []
            
    def calculate_custom_rates(self, origin: Address, destination: Address, packages: List[Package]) -> List[ShippingRate]:
        """Calculate custom/local delivery rates"""
        try:
            rates = []
            total_weight = sum(pkg.weight for pkg in packages)
            
            # Local delivery options
            if self.is_local_delivery(origin, destination):
                # Same-day delivery
                if self.config.get('same_day_delivery_enabled', False):
                    rate = ShippingRate(
                        carrier=ShippingCarrier.CUSTOM,
                        service="Same Day Delivery",
                        rate=15.00,
                        delivery_days=0,
                        delivery_date=datetime.now().strftime('%Y-%m-%d')
                    )
                    rates.append(rate)
                    
                # Local pickup
                if self.config.get('pickup_enabled', False):
                    rate = ShippingRate(
                        carrier=ShippingCarrier.CUSTOM,
                        service="Store Pickup",
                        rate=0.00,
                        delivery_days=0,
                        delivery_date=datetime.now().strftime('%Y-%m-%d')
                    )
                    rates.append(rate)
                    
            # Flat rate shipping option
            if self.config.get('flat_rate_enabled', False):
                flat_rate = self.config.get('flat_rate_amount', 5.99)
                rate = ShippingRate(
                    carrier=ShippingCarrier.CUSTOM,
                    service="Flat Rate Shipping",
                    rate=flat_rate,
                    delivery_days=5,
                    delivery_date=(datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')
                )
                rates.append(rate)
                
            return rates
            
        except Exception as e:
            print(f"Error calculating custom rates: {e}")
            return []
            
    def apply_shipping_adjustments(self, rates: List[ShippingRate], shipping_data: Dict[str, Any]) -> List[ShippingRate]:
        """Apply discounts, surcharges, and other adjustments"""
        try:
            adjusted_rates = []
            order_total = shipping_data.get('order_total', 0)
            
            for rate in rates:
                adjusted_rate = rate.rate
                
                # Free shipping threshold
                if order_total >= self.free_shipping_threshold:
                    if rate.service in ['Standard Shipping', 'Ground', 'Flat Rate Shipping']:
                        adjusted_rate = 0.00
                        
                # Handling fee
                handling_fee = self.config.get('handling_fee', 0)
                adjusted_rate += handling_fee
                
                # Oversized package surcharge
                packages = shipping_data.get('packages', [])
                for pkg in packages:
                    if self.is_oversized_package(pkg):
                        adjusted_rate += self.config.get('oversized_surcharge', 15.00)
                        break
                        
                # Residential delivery surcharge
                if shipping_data.get('residential_delivery', True):
                    if rate.carrier in [ShippingCarrier.UPS, ShippingCarrier.FEDEX]:
                        adjusted_rate += 4.95
                        
                # Create new rate with adjustments
                adjusted_rate_obj = ShippingRate(
                    carrier=rate.carrier,
                    service=rate.service,
                    rate=round(max(0, adjusted_rate), 2),  # Never negative
                    delivery_days=rate.delivery_days,
                    delivery_date=rate.delivery_date
                )
                adjusted_rates.append(adjusted_rate_obj)
                
            return adjusted_rates
            
        except Exception as e:
            print(f"Error applying shipping adjustments: {e}")
            return rates
            
    def get_zone_multiplier(self, origin_zip: str, destination_zip: str) -> float:
        """Calculate shipping zone multiplier based on distance"""
        try:
            # Simplified zone calculation
            origin_zone = int(origin_zip[:3]) if origin_zip else 0
            dest_zone = int(destination_zip[:3]) if destination_zip else 0
            
            distance = abs(origin_zone - dest_zone)
            
            if distance < 100:
                return 1.0  # Local
            elif distance < 300:
                return 1.2  # Regional
            elif distance < 600:
                return 1.5  # Zone 2-4
            else:
                return 1.8  # Zone 5-8
                
        except Exception:
            return 1.0
            
    def estimate_delivery_days(self, carrier: str, service: str, origin_zip: str, destination_zip: str) -> int:
        """Estimate delivery days based on carrier, service, and distance"""
        try:
            # Base delivery times by service type
            service_times = {
                'overnight': 1,
                'express': 1,
                '2day': 2,
                '3day': 3,
                'ground': 5,
                'standard': 7,
                'media': 8
            }
            
            # Find matching service time
            base_days = 7  # Default
            service_lower = service.lower()
            
            for key, days in service_times.items():
                if key in service_lower:
                    base_days = days
                    break
                    
            # Adjust for distance
            zone_multiplier = self.get_zone_multiplier(origin_zip, destination_zip)
            if zone_multiplier > 1.5:  # Long distance
                base_days = min(base_days + 1, 10)
                
            return base_days
            
        except Exception:
            return 7
            
    def is_local_delivery(self, origin: Address, destination: Address) -> bool:
        """Check if delivery is local/same city"""
        try:
            # Simple check - same city and state
            return (origin.city.lower() == destination.city.lower() and 
                   origin.state.lower() == destination.state.lower())
        except Exception:
            return False
            
    def is_oversized_package(self, package: Dict[str, Any]) -> bool:
        """Check if package is oversized"""
        try:
            length = package.get('length', 0)
            width = package.get('width', 0) 
            height = package.get('height', 0)
            weight = package.get('weight', 0)
            
            # Oversized if any dimension > 36" or weight > 50 lbs
            return (max(length, width, height) > 36 or weight > 50)
        except Exception:
            return False
            
    def load_shipping_zones(self) -> Dict[str, Any]:
        """Load shipping zones configuration"""
        try:
            # This would typically load from database or config file
            return {
                'domestic_zones': {
                    'zone_1': {'states': ['CA', 'NV', 'OR', 'WA'], 'multiplier': 1.0},
                    'zone_2': ['TX', 'AZ', 'NM', 'CO'],
                    'zone_3': ['IL', 'IN', 'OH', 'MI'],
                    'zone_4': ['NY', 'NJ', 'PA', 'CT'],
                    'zone_5': ['FL', 'GA', 'SC', 'NC']
                },
                'international_zones': {
                    'canada': {'multiplier': 1.8},
                    'mexico': {'multiplier': 2.0},
                    'europe': {'multiplier': 2.5},
                    'asia': {'multiplier': 3.0}
                }
            }
        except Exception:
            return {}
            
    def get_shipping_methods(self) -> List[Dict[str, Any]]:
        """Get available shipping methods for frontend"""
        try:
            methods = []
            
            # Standard methods available
            if self.config.get('standard_shipping_enabled', True):
                methods.append({
                    'id': 'standard',
                    'name': 'Standard Shipping',
                    'description': '5-7 business days',
                    'base_rate': 5.99
                })
                
            if self.config.get('expedited_shipping_enabled', True):
                methods.append({
                    'id': 'expedited', 
                    'name': 'Expedited Shipping',
                    'description': '2-3 business days',
                    'base_rate': 12.99
                })
                
            if self.config.get('overnight_shipping_enabled', True):
                methods.append({
                    'id': 'overnight',
                    'name': 'Overnight Shipping', 
                    'description': 'Next business day',
                    'base_rate': 24.99
                })
                
            if self.config.get('pickup_enabled', False):
                methods.append({
                    'id': 'pickup',
                    'name': 'Store Pickup',
                    'description': 'Pick up at our location',
                    'base_rate': 0.00
                })
                
            return methods
            
        except Exception as e:
            raise Exception(f"Error getting shipping methods: {e}")
            
    def validate_shipping_address(self, address_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and standardize shipping address"""
        try:
            required_fields = ['first_name', 'last_name', 'address1', 'city', 'state', 'zip', 'country']
            
            for field in required_fields:
                if field not in address_data or not address_data[field]:
                    return {
                        'valid': False,
                        'error': f'Missing required field: {field}'
                    }
                    
            # Basic ZIP code validation for US
            if address_data['country'].upper() == 'US':
                zip_code = address_data['zip'].replace('-', '').replace(' ', '')
                if not zip_code.isdigit() or len(zip_code) not in [5, 9]:
                    return {
                        'valid': False,
                        'error': 'Invalid ZIP code format'
                    }
                    
            # Address standardization would happen here via USPS API
            standardized_address = address_data.copy()
            
            return {
                'valid': True,
                'standardized_address': standardized_address,
                'suggestions': []
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Address validation error: {e}'
            }
            
    def track_shipment(self, tracking_number: str, carrier: str) -> Dict[str, Any]:
        """Track shipment status"""
        try:
            # This would integrate with carrier tracking APIs
            
            # Mock tracking data
            tracking_data = {
                'tracking_number': tracking_number,
                'carrier': carrier,
                'status': 'In Transit',
                'estimated_delivery': (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
                'tracking_events': [
                    {
                        'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M'),
                        'status': 'Package picked up',
                        'location': 'Origin facility'
                    },
                    {
                        'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        'status': 'In transit',
                        'location': 'Sorting facility'
                    }
                ]
            }
            
            return {
                'success': True,
                'tracking_data': tracking_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error tracking shipment: {e}'
            }
            
    def calculate_dimensional_weight(self, length: float, width: float, height: float) -> float:
        """Calculate dimensional weight for shipping"""
        try:
            # Standard dimensional weight divisor for domestic shipments
            dim_divisor = 139  # inches³/lb
            
            dimensional_weight = (length * width * height) / dim_divisor
            return round(dimensional_weight, 2)
            
        except Exception:
            return 0.0
            
    def get_delivery_options(self, shipping_address: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get available delivery options for address"""
        try:
            options = ['standard']  # Always available
            
            # Check if express delivery available
            if self.is_express_delivery_available(shipping_address):
                options.append('express')
                
            # Check if same-day delivery available
            if self.is_same_day_delivery_available(shipping_address):
                options.append('same_day')
                
            # Check if pickup available
            if self.config.get('pickup_enabled', False):
                options.append('pickup')
                
            return options
            
        except Exception as e:
            raise Exception(f"Error getting delivery options: {e}")
            
    def is_express_delivery_available(self, address: Dict[str, Any]) -> bool:
        """Check if express delivery is available to address"""
        try:
            # Express delivery available to major cities
            major_cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia']
            return address.get('city', '') in major_cities
        except Exception:
            return False
            
    def is_same_day_delivery_available(self, address: Dict[str, Any]) -> bool:
        """Check if same-day delivery is available"""
        try:
            # Same-day only in local area
            local_cities = self.config.get('same_day_cities', ['San Francisco', 'Oakland'])
            return address.get('city', '') in local_cities
        except Exception:
            return False