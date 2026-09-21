from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Dict, List, Optional, Any
from datetime import datetime, time, timedelta
import pytz
from decimal import Decimal
import logging

from ..database import PeakPricingSchedule

logger = logging.getLogger(__name__)

class PeakPricingScheduler:
    """Advanced off-peak pricing scheduler with multiple strategies"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.default_peak_multiplier = Decimal('1.5')  # 50% premium during peak
        self.default_off_peak_multiplier = Decimal('0.8')  # 20% discount during off-peak
    
    async def get_pricing_multiplier(self, timestamp: datetime) -> Dict[str, Any]:
        """Get pricing multiplier for a specific timestamp"""
        
        try:
            # Get active pricing schedules
            result = await self.db.execute(
                select(PeakPricingSchedule).where(
                    PeakPricingSchedule.is_active == True
                ).order_by(PeakPricingSchedule.created_at.desc())
            )
            schedules = result.scalars().all()
            
            if not schedules:
                # No schedules configured, return neutral pricing
                return {
                    "multiplier": Decimal('1.0'),
                    "is_peak": False,
                    "schedule_name": "default",
                    "reason": "No peak pricing schedules configured"
                }
            
            # Check each schedule to find applicable one
            for schedule in schedules:
                multiplier_result = await self._evaluate_schedule(schedule, timestamp)
                if multiplier_result:
                    return multiplier_result
            
            # No matching schedule found, return neutral
            return {
                "multiplier": Decimal('1.0'),
                "is_peak": False,
                "schedule_name": "fallback",
                "reason": "No applicable schedules for this time"
            }
            
        except Exception as e:
            logger.error(f"Failed to get pricing multiplier: {e}")
            # Return safe default
            return {
                "multiplier": Decimal('1.0'),
                "is_peak": False,
                "schedule_name": "error_fallback",
                "reason": f"Error: {str(e)}"
            }
    
    async def create_peak_schedule(
        self,
        name: str,
        timezone_name: str = "UTC",
        peak_start_hour: int = 9,
        peak_end_hour: int = 17,
        peak_days: List[int] = None,  # 0=Monday, 6=Sunday
        peak_multiplier: Decimal = None,
        off_peak_multiplier: Decimal = None
    ) -> Dict[str, Any]:
        """Create a new peak pricing schedule"""
        
        try:
            # Validate timezone
            try:
                tz = pytz.timezone(timezone_name)
            except pytz.exceptions.UnknownTimeZoneError:
                raise ValueError(f"Unknown timezone: {timezone_name}")
            
            # Default to business days if not specified
            if peak_days is None:
                peak_days = [0, 1, 2, 3, 4]  # Monday-Friday
            
            # Use default multipliers if not provided
            peak_mult = peak_multiplier or self.default_peak_multiplier
            off_peak_mult = off_peak_multiplier or self.default_off_peak_multiplier
            
            # Create schedule
            schedule = PeakPricingSchedule(
                name=name,
                timezone=timezone_name,
                peak_start_hour=peak_start_hour,
                peak_end_hour=peak_end_hour,
                peak_days=peak_days,
                peak_multiplier=peak_mult,
                off_peak_multiplier=off_peak_mult,
                is_active=True
            )
            
            self.db.add(schedule)
            await self.db.commit()
            await self.db.refresh(schedule)
            
            return {
                "schedule_id": str(schedule.id),
                "name": schedule.name,
                "timezone": schedule.timezone,
                "peak_hours": f"{peak_start_hour:02d}:00 - {peak_end_hour:02d}:00",
                "peak_days": [self._day_name(day) for day in peak_days],
                "peak_multiplier": float(peak_mult),
                "off_peak_multiplier": float(off_peak_mult),
                "created_at": schedule.created_at.isoformat(),
                "is_active": True
            }
            
        except Exception as e:
            logger.error(f"Failed to create peak schedule: {e}")
            raise
    
    async def get_peak_schedule_preview(
        self,
        schedule_name: str,
        preview_hours: int = 168  # 1 week
    ) -> Dict[str, Any]:
        """Preview how pricing multipliers will apply over time"""
        
        try:
            # Get the schedule
            result = await self.db.execute(
                select(PeakPricingSchedule).where(
                    and_(
                        PeakPricingSchedule.name == schedule_name,
                        PeakPricingSchedule.is_active == True
                    )
                )
            )
            schedule = result.scalar_one_or_none()
            
            if not schedule:
                raise ValueError(f"Schedule '{schedule_name}' not found")
            
            # Generate hourly preview
            preview = []
            current_time = datetime.utcnow()
            
            for hour_offset in range(preview_hours):
                check_time = current_time + timedelta(hours=hour_offset)
                multiplier_data = await self._evaluate_schedule(schedule, check_time)
                
                if multiplier_data:
                    preview.append({
                        "datetime": check_time.isoformat(),
                        "day_of_week": check_time.strftime("%A"),
                        "hour": check_time.hour,
                        "multiplier": float(multiplier_data["multiplier"]),
                        "is_peak": multiplier_data["is_peak"],
                        "pricing_type": "peak" if multiplier_data["is_peak"] else "off-peak"
                    })
            
            # Calculate statistics
            peak_hours = len([p for p in preview if p["is_peak"]])
            off_peak_hours = len([p for p in preview if not p["is_peak"]])
            
            avg_multiplier = sum(p["multiplier"] for p in preview) / len(preview) if preview else 1.0
            
            return {
                "schedule_name": schedule_name,
                "preview_period_hours": preview_hours,
                "statistics": {
                    "peak_hours": peak_hours,
                    "off_peak_hours": off_peak_hours,
                    "peak_percentage": (peak_hours / len(preview)) * 100 if preview else 0,
                    "average_multiplier": avg_multiplier,
                    "potential_savings": (1.0 - avg_multiplier) * 100  # Approximate savings percentage
                },
                "hourly_preview": preview[:24],  # First 24 hours for display
                "daily_patterns": await self._calculate_daily_patterns(preview)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate schedule preview: {e}")
            raise
    
    async def optimize_job_scheduling(
        self,
        job_duration_hours: int,
        max_delay_hours: int = 24,
        cost_threshold: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Find optimal time to run a job for cost savings"""
        
        try:
            current_time = datetime.utcnow()
            best_time = current_time
            best_cost_multiplier = Decimal('2.0')  # Start with high value
            
            # Check different start times within the delay window
            for hour_delay in range(max_delay_hours):
                candidate_start = current_time + timedelta(hours=hour_delay)
                
                # Calculate average cost multiplier for the job duration
                total_multiplier = Decimal('0')
                for hour_offset in range(job_duration_hours):
                    job_time = candidate_start + timedelta(hours=hour_offset)
                    multiplier_data = await self.get_pricing_multiplier(job_time)
                    total_multiplier += multiplier_data["multiplier"]
                
                avg_multiplier = total_multiplier / job_duration_hours
                
                # Check if this is better than current best
                if avg_multiplier < best_cost_multiplier:
                    best_cost_multiplier = avg_multiplier
                    best_time = candidate_start
                
                # Early exit if we found a time under threshold
                if cost_threshold and avg_multiplier <= cost_threshold:
                    break
            
            # Calculate immediate start cost for comparison
            immediate_total = Decimal('0')
            for hour_offset in range(job_duration_hours):
                job_time = current_time + timedelta(hours=hour_offset)
                multiplier_data = await self.get_pricing_multiplier(job_time)
                immediate_total += multiplier_data["multiplier"]
            
            immediate_avg = immediate_total / job_duration_hours
            
            # Calculate savings
            potential_savings = ((immediate_avg - best_cost_multiplier) / immediate_avg) * 100 if immediate_avg > 0 else 0
            
            return {
                "job_duration_hours": job_duration_hours,
                "immediate_start": {
                    "start_time": current_time.isoformat(),
                    "average_multiplier": float(immediate_avg),
                    "total_cost_factor": float(immediate_total)
                },
                "optimal_start": {
                    "start_time": best_time.isoformat(),
                    "delay_hours": int((best_time - current_time).total_seconds() / 3600),
                    "average_multiplier": float(best_cost_multiplier),
                    "total_cost_factor": float(best_cost_multiplier * job_duration_hours)
                },
                "savings": {
                    "percentage": float(potential_savings),
                    "cost_reduction": float(immediate_avg - best_cost_multiplier),
                    "recommendation": "optimal" if potential_savings > 5 else "immediate"
                },
                "analysis_window_hours": max_delay_hours
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize job scheduling: {e}")
            raise
    
    async def get_demand_based_pricing(
        self,
        current_load_percentage: float,
        resource_type: str = "general"
    ) -> Dict[str, Any]:
        """Calculate demand-based pricing multiplier"""
        
        try:
            # Base multiplier on current system load
            if current_load_percentage >= 90:
                demand_multiplier = Decimal('2.0')  # 100% premium during very high load
                demand_level = "critical"
            elif current_load_percentage >= 75:
                demand_multiplier = Decimal('1.5')  # 50% premium during high load
                demand_level = "high"
            elif current_load_percentage >= 50:
                demand_multiplier = Decimal('1.2')  # 20% premium during medium load
                demand_level = "medium"
            elif current_load_percentage >= 25:
                demand_multiplier = Decimal('1.0')  # Standard pricing during low load
                demand_level = "low"
            else:
                demand_multiplier = Decimal('0.8')  # 20% discount during very low load
                demand_level = "very_low"
            
            # Get time-based multiplier
            time_multiplier_data = await self.get_pricing_multiplier(datetime.utcnow())
            time_multiplier = time_multiplier_data["multiplier"]
            
            # Combine demand and time-based pricing
            combined_multiplier = (demand_multiplier + time_multiplier) / 2
            
            return {
                "current_load_percentage": current_load_percentage,
                "demand_level": demand_level,
                "demand_multiplier": float(demand_multiplier),
                "time_multiplier": float(time_multiplier),
                "combined_multiplier": float(combined_multiplier),
                "pricing_factors": {
                    "demand_weight": 0.5,
                    "time_weight": 0.5
                },
                "recommendation": await self._generate_demand_recommendation(
                    current_load_percentage, combined_multiplier
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate demand-based pricing: {e}")
            raise
    
    async def _evaluate_schedule(
        self, 
        schedule: PeakPricingSchedule, 
        timestamp: datetime
    ) -> Optional[Dict[str, Any]]:
        """Evaluate if timestamp falls within schedule parameters"""
        
        try:
            # Convert timestamp to schedule timezone
            tz = pytz.timezone(schedule.timezone)
            local_time = timestamp.replace(tzinfo=pytz.UTC).astimezone(tz)
            
            # Check if day is in peak days
            weekday = local_time.weekday()  # 0=Monday, 6=Sunday
            if weekday not in schedule.peak_days:
                # Not a peak day, use off-peak pricing
                return {
                    "multiplier": schedule.off_peak_multiplier,
                    "is_peak": False,
                    "schedule_name": schedule.name,
                    "reason": f"Off-peak day ({self._day_name(weekday)})"
                }
            
            # Check if time is in peak hours
            current_hour = local_time.hour
            
            # Handle overnight peak periods (e.g., 22:00 to 06:00)
            if schedule.peak_start_hour > schedule.peak_end_hour:
                is_peak_hour = (current_hour >= schedule.peak_start_hour or 
                               current_hour < schedule.peak_end_hour)
            else:
                is_peak_hour = (schedule.peak_start_hour <= current_hour < schedule.peak_end_hour)
            
            if is_peak_hour:
                return {
                    "multiplier": schedule.peak_multiplier,
                    "is_peak": True,
                    "schedule_name": schedule.name,
                    "reason": f"Peak hours ({schedule.peak_start_hour:02d}:00-{schedule.peak_end_hour:02d}:00)"
                }
            else:
                return {
                    "multiplier": schedule.off_peak_multiplier,
                    "is_peak": False,
                    "schedule_name": schedule.name,
                    "reason": f"Off-peak hours"
                }
                
        except Exception as e:
            logger.error(f"Failed to evaluate schedule: {e}")
            return None
    
    def _day_name(self, day_number: int) -> str:
        """Convert day number to name"""
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return days[day_number] if 0 <= day_number <= 6 else "Unknown"
    
    async def _calculate_daily_patterns(self, preview: List[Dict]) -> Dict[str, Any]:
        """Calculate daily pricing patterns from preview data"""
        
        daily_stats = {}
        
        for entry in preview:
            day = entry["day_of_week"]
            if day not in daily_stats:
                daily_stats[day] = {
                    "total_hours": 0,
                    "peak_hours": 0,
                    "avg_multiplier": 0.0,
                    "multipliers": []
                }
            
            daily_stats[day]["total_hours"] += 1
            daily_stats[day]["multipliers"].append(entry["multiplier"])
            if entry["is_peak"]:
                daily_stats[day]["peak_hours"] += 1
        
        # Calculate averages
        for day_data in daily_stats.values():
            day_data["avg_multiplier"] = sum(day_data["multipliers"]) / len(day_data["multipliers"])
            day_data["peak_percentage"] = (day_data["peak_hours"] / day_data["total_hours"]) * 100
            # Remove raw multipliers list for cleaner output
            del day_data["multipliers"]
        
        return daily_stats
    
    async def _generate_demand_recommendation(
        self,
        load_percentage: float,
        multiplier: float
    ) -> str:
        """Generate recommendation based on demand and pricing"""
        
        if load_percentage >= 90:
            return "Delay non-critical jobs until load decreases"
        elif load_percentage >= 75:
            return "Consider scheduling jobs during off-peak hours"
        elif load_percentage <= 25:
            return "Excellent time for running compute-intensive jobs"
        else:
            return "Standard pricing conditions - job timing is flexible"