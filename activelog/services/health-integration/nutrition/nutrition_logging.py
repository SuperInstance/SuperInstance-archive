"""
ActiveLog Health Integration - Nutrition Logging with Image Recognition

This module provides comprehensive nutrition tracking capabilities including:
- Food database integration with USDA and custom databases
- Image recognition for automatic food identification
- Barcode scanning for packaged foods
- Nutritional analysis and macro/micronutrient tracking
- Meal planning and recipe management
- Dietary restriction and allergy management
- Integration with fitness goals and health trends
"""

import asyncio
import base64
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from uuid import uuid4

import aiohttp
import cv2
import numpy as np
from PIL import Image
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FoodCategory(Enum):
    """Food category classifications"""
    FRUITS = "fruits"
    VEGETABLES = "vegetables"
    GRAINS = "grains"
    PROTEIN = "protein"
    DAIRY = "dairy"
    FATS = "fats"
    BEVERAGES = "beverages"
    SNACKS = "snacks"
    PREPARED_FOODS = "prepared_foods"
    SUPPLEMENTS = "supplements"


class MealType(Enum):
    """Types of meals throughout the day"""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    PRE_WORKOUT = "pre_workout"
    POST_WORKOUT = "post_workout"


class NutrientType(Enum):
    """Types of nutrients tracked"""
    CALORIES = "calories"
    PROTEIN = "protein"
    CARBS = "carbohydrates"
    FAT = "fat"
    FIBER = "fiber"
    SUGAR = "sugar"
    SODIUM = "sodium"
    POTASSIUM = "potassium"
    CALCIUM = "calcium"
    IRON = "iron"
    VITAMIN_A = "vitamin_a"
    VITAMIN_C = "vitamin_c"
    VITAMIN_D = "vitamin_d"


class DietaryRestriction(Enum):
    """Common dietary restrictions and preferences"""
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    KETO = "keto"
    PALEO = "paleo"
    LOW_CARB = "low_carb"
    LOW_FAT = "low_fat"
    LOW_SODIUM = "low_sodium"
    DIABETIC = "diabetic"


class ImageProcessingStatus(Enum):
    """Status of image processing for food recognition"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    MANUAL_REVIEW = "manual_review"


@dataclass
class NutrientInfo:
    """Nutritional information for a food item"""
    nutrient_type: NutrientType
    amount: float
    unit: str
    daily_value_percentage: Optional[float] = None


@dataclass
class FoodItem:
    """Represents a food item in the database"""
    food_id: str
    name: str
    brand: Optional[str]
    category: FoodCategory
    nutrients: List[NutrientInfo]
    serving_size: float
    serving_unit: str
    barcode: Optional[str] = None
    description: Optional[str] = None
    ingredients: List[str] = field(default_factory=list)
    allergens: Set[str] = field(default_factory=set)
    dietary_restrictions: Set[DietaryRestriction] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class FoodEntry:
    """Represents a logged food entry"""
    entry_id: str
    user_id: str
    food_item: FoodItem
    quantity: float
    meal_type: MealType
    logged_at: datetime
    notes: Optional[str] = None
    image_path: Optional[str] = None
    location: Optional[str] = None
    confidence_score: Optional[float] = None


@dataclass
class MealPlan:
    """Represents a meal plan for a specific day or period"""
    plan_id: str
    user_id: str
    name: str
    start_date: datetime
    end_date: datetime
    target_calories: float
    target_nutrients: Dict[NutrientType, float]
    meals: Dict[MealType, List[FoodItem]]
    dietary_restrictions: Set[DietaryRestriction] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class NutritionGoal:
    """Nutrition-related goals and targets"""
    goal_id: str
    user_id: str
    nutrient_type: NutrientType
    target_amount: float
    target_unit: str
    time_period: str  # daily, weekly, monthly
    start_date: datetime
    end_date: Optional[datetime] = None
    current_progress: float = 0.0
    is_active: bool = True


@dataclass
class ImageRecognitionResult:
    """Result from image recognition processing"""
    result_id: str
    image_path: str
    detected_foods: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    processing_time: float
    status: ImageProcessingStatus
    error_message: Optional[str] = None
    manual_corrections: List[Dict[str, Any]] = field(default_factory=list)
    processed_at: datetime = field(default_factory=datetime.now)


@dataclass
class NutritionalAnalysis:
    """Comprehensive nutritional analysis for a time period"""
    analysis_id: str
    user_id: str
    start_date: datetime
    end_date: datetime
    total_nutrients: Dict[NutrientType, float]
    daily_averages: Dict[NutrientType, float]
    goal_progress: Dict[str, float]
    recommendations: List[str]
    deficiencies: List[NutrientType]
    excesses: List[NutrientType]
    meal_distribution: Dict[MealType, Dict[NutrientType, float]]
    generated_at: datetime = field(default_factory=datetime.now)


class FoodDatabaseInterface(ABC):
    """Abstract interface for food database implementations"""
    
    @abstractmethod
    async def search_food(self, query: str, limit: int = 10) -> List[FoodItem]:
        """Search for food items by name or description"""
        pass
    
    @abstractmethod
    async def get_food_by_barcode(self, barcode: str) -> Optional[FoodItem]:
        """Get food item by barcode"""
        pass
    
    @abstractmethod
    async def get_food_by_id(self, food_id: str) -> Optional[FoodItem]:
        """Get food item by unique identifier"""
        pass
    
    @abstractmethod
    async def add_custom_food(self, food_item: FoodItem) -> bool:
        """Add a custom food item to the database"""
        pass


class ImageRecognitionInterface(ABC):
    """Abstract interface for image recognition implementations"""
    
    @abstractmethod
    async def recognize_food(self, image_data: bytes) -> ImageRecognitionResult:
        """Recognize food items in an image"""
        pass
    
    @abstractmethod
    async def process_batch_images(self, image_paths: List[str]) -> List[ImageRecognitionResult]:
        """Process multiple images in batch"""
        pass
    
    @abstractmethod
    async def validate_recognition(self, result: ImageRecognitionResult) -> bool:
        """Validate and improve recognition results"""
        pass


class NutritionAnalyzer(ABC):
    """Abstract interface for nutrition analysis implementations"""
    
    @abstractmethod
    async def analyze_daily_intake(self, user_id: str, date: datetime) -> NutritionalAnalysis:
        """Analyze nutritional intake for a specific day"""
        pass
    
    @abstractmethod
    async def analyze_period_intake(self, user_id: str, start_date: datetime, end_date: datetime) -> NutritionalAnalysis:
        """Analyze nutritional intake over a period"""
        pass
    
    @abstractmethod
    async def generate_recommendations(self, user_id: str, analysis: NutritionalAnalysis) -> List[str]:
        """Generate personalized nutrition recommendations"""
        pass


class USDAFoodDatabase(FoodDatabaseInterface):
    """USDA Food Database implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.nal.usda.gov/fdc/v1"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def search_food(self, query: str, limit: int = 10) -> List[FoodItem]:
        """Search USDA database for food items"""
        try:
            session = await self._get_session()
            params = {
                'query': query,
                'pageSize': limit,
                'api_key': self.api_key
            }
            
            async with session.get(f"{self.base_url}/foods/search", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    foods = []
                    
                    for item in data.get('foods', []):
                        nutrients = []
                        for nutrient in item.get('foodNutrients', []):
                            if nutrient.get('value') is not None:
                                nutrient_name = nutrient.get('nutrientName', '').lower()
                                nutrient_type = self._map_nutrient_name(nutrient_name)
                                if nutrient_type:
                                    nutrients.append(NutrientInfo(
                                        nutrient_type=nutrient_type,
                                        amount=float(nutrient['value']),
                                        unit=nutrient.get('unitName', 'g')
                                    ))
                        
                        food_item = FoodItem(
                            food_id=str(item.get('fdcId')),
                            name=item.get('description', ''),
                            brand=item.get('brandOwner'),
                            category=self._determine_category(item.get('description', '')),
                            nutrients=nutrients,
                            serving_size=100.0,
                            serving_unit='g'
                        )
                        foods.append(food_item)
                    
                    return foods
                else:
                    logger.error(f"USDA API error: {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"Error searching USDA database: {e}")
            return []
    
    async def get_food_by_barcode(self, barcode: str) -> Optional[FoodItem]:
        """Get food by barcode (USDA doesn't directly support this)"""
        return None
    
    async def get_food_by_id(self, food_id: str) -> Optional[FoodItem]:
        """Get food by FDC ID"""
        try:
            session = await self._get_session()
            params = {'api_key': self.api_key}
            
            async with session.get(f"{self.base_url}/food/{food_id}", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    # Process similar to search_food
                    return None  # Simplified for now
                
        except Exception as e:
            logger.error(f"Error getting food by ID: {e}")
        
        return None
    
    async def add_custom_food(self, food_item: FoodItem) -> bool:
        """USDA database is read-only"""
        return False
    
    def _map_nutrient_name(self, nutrient_name: str) -> Optional[NutrientType]:
        """Map USDA nutrient names to our enum"""
        mapping = {
            'energy': NutrientType.CALORIES,
            'protein': NutrientType.PROTEIN,
            'carbohydrate': NutrientType.CARBS,
            'total lipid': NutrientType.FAT,
            'fiber': NutrientType.FIBER,
            'sugars': NutrientType.SUGAR,
            'sodium': NutrientType.SODIUM,
            'potassium': NutrientType.POTASSIUM,
            'calcium': NutrientType.CALCIUM,
            'iron': NutrientType.IRON,
            'vitamin a': NutrientType.VITAMIN_A,
            'vitamin c': NutrientType.VITAMIN_C,
            'vitamin d': NutrientType.VITAMIN_D
        }
        
        for key, nutrient_type in mapping.items():
            if key in nutrient_name.lower():
                return nutrient_type
        
        return None
    
    def _determine_category(self, description: str) -> FoodCategory:
        """Determine food category from description"""
        description_lower = description.lower()
        
        if any(word in description_lower for word in ['apple', 'banana', 'orange', 'berry']):
            return FoodCategory.FRUITS
        elif any(word in description_lower for word in ['carrot', 'broccoli', 'spinach', 'lettuce']):
            return FoodCategory.VEGETABLES
        elif any(word in description_lower for word in ['bread', 'rice', 'pasta', 'cereal']):
            return FoodCategory.GRAINS
        elif any(word in description_lower for word in ['chicken', 'beef', 'fish', 'egg']):
            return FoodCategory.PROTEIN
        elif any(word in description_lower for word in ['milk', 'cheese', 'yogurt']):
            return FoodCategory.DAIRY
        else:
            return FoodCategory.PREPARED_FOODS


class ComputerVisionFoodRecognition(ImageRecognitionInterface):
    """Computer vision implementation for food recognition"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.confidence_threshold = 0.7
        self.food_classes = [
            'apple', 'banana', 'orange', 'pizza', 'burger', 'sandwich',
            'salad', 'pasta', 'rice', 'chicken', 'beef', 'fish'
        ]  # Simplified list
    
    async def recognize_food(self, image_data: bytes) -> ImageRecognitionResult:
        """Recognize food items in image using computer vision"""
        start_time = datetime.now()
        
        try:
            # Convert bytes to image
            image = Image.open(io.BytesIO(image_data))
            image_array = np.array(image)
            
            # Simulate food detection (in real implementation, use trained model)
            detected_foods = await self._simulate_detection(image_array)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return ImageRecognitionResult(
                result_id=str(uuid4()),
                image_path="temp_image_path",
                detected_foods=detected_foods,
                confidence_scores={food['name']: food['confidence'] for food in detected_foods},
                processing_time=processing_time,
                status=ImageProcessingStatus.COMPLETED
            )
            
        except Exception as e:
            logger.error(f"Error in food recognition: {e}")
            return ImageRecognitionResult(
                result_id=str(uuid4()),
                image_path="temp_image_path",
                detected_foods=[],
                confidence_scores={},
                processing_time=(datetime.now() - start_time).total_seconds(),
                status=ImageProcessingStatus.FAILED,
                error_message=str(e)
            )
    
    async def _simulate_detection(self, image_array: np.ndarray) -> List[Dict[str, Any]]:
        """Simulate food detection (replace with actual model inference)"""
        # In real implementation, this would use a trained CNN model
        detected_foods = []
        
        # Simulate detection of 1-3 foods
        import random
        num_foods = random.randint(1, 3)
        
        for i in range(num_foods):
            food_name = random.choice(self.food_classes)
            confidence = random.uniform(0.6, 0.95)
            
            detected_foods.append({
                'name': food_name,
                'confidence': confidence,
                'bounding_box': {
                    'x': random.randint(0, 200),
                    'y': random.randint(0, 200),
                    'width': random.randint(50, 150),
                    'height': random.randint(50, 150)
                },
                'estimated_quantity': random.uniform(0.5, 2.0)
            })
        
        return detected_foods
    
    async def process_batch_images(self, image_paths: List[str]) -> List[ImageRecognitionResult]:
        """Process multiple images"""
        results = []
        
        for image_path in image_paths:
            try:
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                result = await self.recognize_food(image_data)
                result.image_path = image_path
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing image {image_path}: {e}")
                results.append(ImageRecognitionResult(
                    result_id=str(uuid4()),
                    image_path=image_path,
                    detected_foods=[],
                    confidence_scores={},
                    processing_time=0.0,
                    status=ImageProcessingStatus.FAILED,
                    error_message=str(e)
                ))
        
        return results
    
    async def validate_recognition(self, result: ImageRecognitionResult) -> bool:
        """Validate recognition results"""
        if result.status != ImageProcessingStatus.COMPLETED:
            return False
        
        # Check if we have confident detections
        confident_detections = [
            food for food in result.detected_foods 
            if food.get('confidence', 0) >= self.confidence_threshold
        ]
        
        return len(confident_detections) > 0


class ComprehensiveNutritionAnalyzer(NutritionAnalyzer):
    """Comprehensive nutrition analysis implementation"""
    
    def __init__(self):
        self.daily_targets = {
            NutrientType.CALORIES: 2000.0,
            NutrientType.PROTEIN: 150.0,
            NutrientType.CARBS: 250.0,
            NutrientType.FAT: 65.0,
            NutrientType.FIBER: 25.0,
            NutrientType.SODIUM: 2300.0
        }
    
    async def analyze_daily_intake(self, user_id: str, date: datetime) -> NutritionalAnalysis:
        """Analyze daily nutritional intake"""
        # Get user's food entries for the day
        entries = await self._get_daily_entries(user_id, date)
        
        # Calculate total nutrients
        total_nutrients = await self._calculate_total_nutrients(entries)
        
        # Analyze against goals
        goal_progress = await self._calculate_goal_progress(user_id, total_nutrients)
        
        # Generate recommendations
        recommendations = await self.generate_recommendations(user_id, None)
        
        # Identify deficiencies and excesses
        deficiencies = []
        excesses = []
        
        for nutrient_type, amount in total_nutrients.items():
            target = self.daily_targets.get(nutrient_type, 0)
            if target > 0:
                if amount < target * 0.8:  # Less than 80% of target
                    deficiencies.append(nutrient_type)
                elif amount > target * 1.2:  # More than 120% of target
                    excesses.append(nutrient_type)
        
        # Calculate meal distribution
        meal_distribution = await self._calculate_meal_distribution(entries)
        
        return NutritionalAnalysis(
            analysis_id=str(uuid4()),
            user_id=user_id,
            start_date=date,
            end_date=date,
            total_nutrients=total_nutrients,
            daily_averages=total_nutrients,  # Same for single day
            goal_progress=goal_progress,
            recommendations=recommendations,
            deficiencies=deficiencies,
            excesses=excesses,
            meal_distribution=meal_distribution
        )
    
    async def analyze_period_intake(self, user_id: str, start_date: datetime, end_date: datetime) -> NutritionalAnalysis:
        """Analyze nutritional intake over a period"""
        # Get all entries in the period
        entries = await self._get_period_entries(user_id, start_date, end_date)
        
        # Calculate totals and averages
        total_nutrients = await self._calculate_total_nutrients(entries)
        days = (end_date - start_date).days + 1
        daily_averages = {k: v / days for k, v in total_nutrients.items()}
        
        # Other calculations similar to daily analysis
        goal_progress = await self._calculate_goal_progress(user_id, daily_averages)
        recommendations = await self.generate_recommendations(user_id, None)
        
        return NutritionalAnalysis(
            analysis_id=str(uuid4()),
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            total_nutrients=total_nutrients,
            daily_averages=daily_averages,
            goal_progress=goal_progress,
            recommendations=recommendations,
            deficiencies=[],
            excesses=[],
            meal_distribution={}
        )
    
    async def generate_recommendations(self, user_id: str, analysis: Optional[NutritionalAnalysis]) -> List[str]:
        """Generate personalized nutrition recommendations"""
        recommendations = []
        
        # Generic recommendations (in real implementation, would be personalized)
        recommendations.extend([
            "Increase vegetable intake to reach 5-7 servings per day",
            "Choose whole grains over refined grains",
            "Include lean protein sources in each meal",
            "Stay hydrated with 8-10 glasses of water daily",
            "Limit processed foods and added sugars"
        ])
        
        if analysis:
            # Specific recommendations based on analysis
            if NutrientType.FIBER in analysis.deficiencies:
                recommendations.append("Add more fiber-rich foods like beans, whole grains, and vegetables")
            
            if NutrientType.PROTEIN in analysis.deficiencies:
                recommendations.append("Include more protein sources like lean meats, fish, eggs, or legumes")
            
            if NutrientType.SODIUM in analysis.excesses:
                recommendations.append("Reduce sodium intake by limiting processed foods and restaurant meals")
        
        return recommendations
    
    async def _get_daily_entries(self, user_id: str, date: datetime) -> List[FoodEntry]:
        """Get food entries for a specific day"""
        # In real implementation, query database
        return []
    
    async def _get_period_entries(self, user_id: str, start_date: datetime, end_date: datetime) -> List[FoodEntry]:
        """Get food entries for a period"""
        # In real implementation, query database
        return []
    
    async def _calculate_total_nutrients(self, entries: List[FoodEntry]) -> Dict[NutrientType, float]:
        """Calculate total nutrients from food entries"""
        totals = {}
        
        for entry in entries:
            for nutrient in entry.food_item.nutrients:
                if nutrient.nutrient_type not in totals:
                    totals[nutrient.nutrient_type] = 0.0
                
                # Calculate based on quantity
                portion_multiplier = entry.quantity / entry.food_item.serving_size
                totals[nutrient.nutrient_type] += nutrient.amount * portion_multiplier
        
        return totals
    
    async def _calculate_goal_progress(self, user_id: str, nutrients: Dict[NutrientType, float]) -> Dict[str, float]:
        """Calculate progress toward nutrition goals"""
        progress = {}
        
        # Get user's nutrition goals (in real implementation, from database)
        for nutrient_type, amount in nutrients.items():
            target = self.daily_targets.get(nutrient_type, 0)
            if target > 0:
                progress[nutrient_type.value] = min((amount / target) * 100, 100)
        
        return progress
    
    async def _calculate_meal_distribution(self, entries: List[FoodEntry]) -> Dict[MealType, Dict[NutrientType, float]]:
        """Calculate nutrient distribution across meals"""
        distribution = {}
        
        for meal_type in MealType:
            meal_entries = [e for e in entries if e.meal_type == meal_type]
            meal_nutrients = await self._calculate_total_nutrients(meal_entries)
            distribution[meal_type] = meal_nutrients
        
        return distribution


class NutritionLogging:
    """Main nutrition logging service with image recognition capabilities"""
    
    def __init__(self, 
                 food_database: FoodDatabaseInterface,
                 image_recognition: ImageRecognitionInterface,
                 nutrition_analyzer: NutritionAnalyzer):
        self.food_database = food_database
        self.image_recognition = image_recognition
        self.nutrition_analyzer = nutrition_analyzer
        
        # In-memory storage (replace with database in production)
        self.food_entries: Dict[str, List[FoodEntry]] = {}
        self.meal_plans: Dict[str, List[MealPlan]] = {}
        self.nutrition_goals: Dict[str, List[NutritionGoal]] = {}
        self.custom_foods: List[FoodItem] = []
        self.recognition_results: List[ImageRecognitionResult] = []
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._running = False
    
    async def start(self):
        """Start the nutrition logging service"""
        if self._running:
            return
        
        self._running = True
        logger.info("Starting Nutrition Logging Service")
        
        # Start background tasks
        self._background_tasks = [
            asyncio.create_task(self._process_image_queue()),
            asyncio.create_task(self._generate_daily_reports()),
            asyncio.create_task(self._sync_nutrition_goals())
        ]
    
    async def stop(self):
        """Stop the nutrition logging service"""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping Nutrition Logging Service")
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()
    
    async def log_food_by_image(self, user_id: str, image_data: bytes, meal_type: MealType, 
                               notes: Optional[str] = None) -> List[FoodEntry]:
        """Log food by analyzing an image"""
        try:
            # Process image for food recognition
            recognition_result = await self.image_recognition.recognize_food(image_data)
            self.recognition_results.append(recognition_result)
            
            if recognition_result.status != ImageProcessingStatus.COMPLETED:
                logger.error(f"Image recognition failed: {recognition_result.error_message}")
                return []
            
            # Convert detected foods to food entries
            food_entries = []
            
            for detected_food in recognition_result.detected_foods:
                food_name = detected_food['name']
                confidence = detected_food['confidence']
                estimated_quantity = detected_food.get('estimated_quantity', 1.0)
                
                # Search for food in database
                food_items = await self.food_database.search_food(food_name, limit=1)
                
                if food_items:
                    food_item = food_items[0]
                    
                    # Create food entry
                    entry = FoodEntry(
                        entry_id=str(uuid4()),
                        user_id=user_id,
                        food_item=food_item,
                        quantity=estimated_quantity * food_item.serving_size,
                        meal_type=meal_type,
                        logged_at=datetime.now(),
                        notes=notes,
                        image_path=recognition_result.image_path,
                        confidence_score=confidence
                    )
                    
                    food_entries.append(entry)
                    
                    # Store entry
                    if user_id not in self.food_entries:
                        self.food_entries[user_id] = []
                    self.food_entries[user_id].append(entry)
            
            logger.info(f"Logged {len(food_entries)} food items from image for user {user_id}")
            return food_entries
            
        except Exception as e:
            logger.error(f"Error logging food by image: {e}")
            return []
    
    async def log_food_manual(self, user_id: str, food_name: str, quantity: float, 
                             meal_type: MealType, notes: Optional[str] = None) -> Optional[FoodEntry]:
        """Manually log a food item"""
        try:
            # Search for food in database
            food_items = await self.food_database.search_food(food_name, limit=1)
            
            if not food_items:
                logger.warning(f"Food not found: {food_name}")
                return None
            
            food_item = food_items[0]
            
            # Create food entry
            entry = FoodEntry(
                entry_id=str(uuid4()),
                user_id=user_id,
                food_item=food_item,
                quantity=quantity,
                meal_type=meal_type,
                logged_at=datetime.now(),
                notes=notes
            )
            
            # Store entry
            if user_id not in self.food_entries:
                self.food_entries[user_id] = []
            self.food_entries[user_id].append(entry)
            
            logger.info(f"Manually logged food: {food_name} for user {user_id}")
            return entry
            
        except Exception as e:
            logger.error(f"Error manually logging food: {e}")
            return None
    
    async def log_food_by_barcode(self, user_id: str, barcode: str, quantity: float, 
                                 meal_type: MealType, notes: Optional[str] = None) -> Optional[FoodEntry]:
        """Log food by scanning barcode"""
        try:
            # Get food by barcode
            food_item = await self.food_database.get_food_by_barcode(barcode)
            
            if not food_item:
                logger.warning(f"Food not found for barcode: {barcode}")
                return None
            
            # Create food entry
            entry = FoodEntry(
                entry_id=str(uuid4()),
                user_id=user_id,
                food_item=food_item,
                quantity=quantity,
                meal_type=meal_type,
                logged_at=datetime.now(),
                notes=notes
            )
            
            # Store entry
            if user_id not in self.food_entries:
                self.food_entries[user_id] = []
            self.food_entries[user_id].append(entry)
            
            logger.info(f"Logged food by barcode: {barcode} for user {user_id}")
            return entry
            
        except Exception as e:
            logger.error(f"Error logging food by barcode: {e}")
            return None
    
    async def create_meal_plan(self, user_id: str, name: str, start_date: datetime, 
                              end_date: datetime, target_calories: float,
                              dietary_restrictions: Set[DietaryRestriction]) -> Optional[MealPlan]:
        """Create a new meal plan"""
        try:
            # Generate meal plan based on targets and restrictions
            meals = await self._generate_meal_suggestions(target_calories, dietary_restrictions)
            
            meal_plan = MealPlan(
                plan_id=str(uuid4()),
                user_id=user_id,
                name=name,
                start_date=start_date,
                end_date=end_date,
                target_calories=target_calories,
                target_nutrients=await self._calculate_target_nutrients(target_calories),
                meals=meals,
                dietary_restrictions=dietary_restrictions
            )
            
            # Store meal plan
            if user_id not in self.meal_plans:
                self.meal_plans[user_id] = []
            self.meal_plans[user_id].append(meal_plan)
            
            logger.info(f"Created meal plan '{name}' for user {user_id}")
            return meal_plan
            
        except Exception as e:
            logger.error(f"Error creating meal plan: {e}")
            return None
    
    async def set_nutrition_goal(self, user_id: str, nutrient_type: NutrientType, 
                                target_amount: float, target_unit: str, time_period: str) -> NutritionGoal:
        """Set a nutrition goal for a user"""
        goal = NutritionGoal(
            goal_id=str(uuid4()),
            user_id=user_id,
            nutrient_type=nutrient_type,
            target_amount=target_amount,
            target_unit=target_unit,
            time_period=time_period,
            start_date=datetime.now()
        )
        
        # Store goal
        if user_id not in self.nutrition_goals:
            self.nutrition_goals[user_id] = []
        self.nutrition_goals[user_id].append(goal)
        
        logger.info(f"Set nutrition goal for {nutrient_type.value}: {target_amount} {target_unit} {time_period}")
        return goal
    
    async def get_daily_analysis(self, user_id: str, date: datetime) -> Optional[NutritionalAnalysis]:
        """Get nutritional analysis for a specific day"""
        try:
            return await self.nutrition_analyzer.analyze_daily_intake(user_id, date)
        except Exception as e:
            logger.error(f"Error getting daily analysis: {e}")
            return None
    
    async def get_period_analysis(self, user_id: str, start_date: datetime, end_date: datetime) -> Optional[NutritionalAnalysis]:
        """Get nutritional analysis for a period"""
        try:
            return await self.nutrition_analyzer.analyze_period_intake(user_id, start_date, end_date)
        except Exception as e:
            logger.error(f"Error getting period analysis: {e}")
            return None
    
    async def add_custom_food(self, food_item: FoodItem) -> bool:
        """Add a custom food item"""
        try:
            # Add to database
            success = await self.food_database.add_custom_food(food_item)
            
            if success:
                # Also store locally
                self.custom_foods.append(food_item)
                logger.info(f"Added custom food: {food_item.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error adding custom food: {e}")
            return False
    
    async def get_user_entries(self, user_id: str, start_date: Optional[datetime] = None, 
                              end_date: Optional[datetime] = None) -> List[FoodEntry]:
        """Get food entries for a user"""
        if user_id not in self.food_entries:
            return []
        
        entries = self.food_entries[user_id]
        
        if start_date or end_date:
            filtered_entries = []
            for entry in entries:
                if start_date and entry.logged_at < start_date:
                    continue
                if end_date and entry.logged_at > end_date:
                    continue
                filtered_entries.append(entry)
            return filtered_entries
        
        return entries
    
    async def _generate_meal_suggestions(self, target_calories: float, 
                                        dietary_restrictions: Set[DietaryRestriction]) -> Dict[MealType, List[FoodItem]]:
        """Generate meal suggestions based on targets and restrictions"""
        # Simplified meal generation (in real implementation, use ML or nutritionist algorithms)
        meals = {
            MealType.BREAKFAST: [],
            MealType.LUNCH: [],
            MealType.DINNER: [],
            MealType.SNACK: []
        }
        
        # Distribute calories across meals
        breakfast_calories = target_calories * 0.25
        lunch_calories = target_calories * 0.35
        dinner_calories = target_calories * 0.30
        snack_calories = target_calories * 0.10
        
        # Generate sample foods for each meal (simplified)
        breakfast_foods = await self.food_database.search_food("oatmeal", limit=3)
        lunch_foods = await self.food_database.search_food("salad", limit=3)
        dinner_foods = await self.food_database.search_food("chicken", limit=3)
        snack_foods = await self.food_database.search_food("apple", limit=2)
        
        meals[MealType.BREAKFAST] = breakfast_foods
        meals[MealType.LUNCH] = lunch_foods
        meals[MealType.DINNER] = dinner_foods
        meals[MealType.SNACK] = snack_foods
        
        return meals
    
    async def _calculate_target_nutrients(self, target_calories: float) -> Dict[NutrientType, float]:
        """Calculate target nutrients based on calories"""
        return {
            NutrientType.CALORIES: target_calories,
            NutrientType.PROTEIN: target_calories * 0.15 / 4,  # 15% of calories from protein
            NutrientType.CARBS: target_calories * 0.55 / 4,    # 55% of calories from carbs
            NutrientType.FAT: target_calories * 0.30 / 9,      # 30% of calories from fat
            NutrientType.FIBER: 25.0,
            NutrientType.SODIUM: 2300.0
        }
    
    async def _process_image_queue(self):
        """Background task to process image recognition queue"""
        while self._running:
            try:
                # Process any pending image recognition tasks
                await asyncio.sleep(30)  # Check every 30 seconds
                
                # Find pending results that need reprocessing
                pending_results = [r for r in self.recognition_results 
                                 if r.status == ImageProcessingStatus.PENDING]
                
                for result in pending_results:
                    # Reprocess if needed
                    if result.error_message:
                        logger.info(f"Reprocessing failed image recognition: {result.result_id}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in image processing queue: {e}")
                await asyncio.sleep(60)
    
    async def _generate_daily_reports(self):
        """Background task to generate daily nutrition reports"""
        while self._running:
            try:
                # Generate daily reports at midnight
                now = datetime.now()
                
                # Check if it's a new day and generate reports
                for user_id in self.food_entries.keys():
                    yesterday = now - timedelta(days=1)
                    
                    try:
                        analysis = await self.get_daily_analysis(user_id, yesterday)
                        if analysis:
                            logger.info(f"Generated daily report for user {user_id}")
                    except Exception as e:
                        logger.error(f"Error generating daily report for user {user_id}: {e}")
                
                # Sleep until next check
                await asyncio.sleep(3600)  # Check every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in daily report generation: {e}")
                await asyncio.sleep(3600)
    
    async def _sync_nutrition_goals(self):
        """Background task to sync and update nutrition goals"""
        while self._running:
            try:
                # Update goal progress for all users
                for user_id, goals in self.nutrition_goals.items():
                    for goal in goals:
                        if goal.is_active and goal.time_period == "daily":
                            # Calculate current progress
                            today = datetime.now().date()
                            entries = await self.get_user_entries(
                                user_id,
                                datetime.combine(today, datetime.min.time()),
                                datetime.combine(today, datetime.max.time())
                            )
                            
                            # Calculate nutrient total for the day
                            total = 0.0
                            for entry in entries:
                                for nutrient in entry.food_item.nutrients:
                                    if nutrient.nutrient_type == goal.nutrient_type:
                                        portion_multiplier = entry.quantity / entry.food_item.serving_size
                                        total += nutrient.amount * portion_multiplier
                            
                            goal.current_progress = total
                
                await asyncio.sleep(1800)  # Update every 30 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error syncing nutrition goals: {e}")
                await asyncio.sleep(1800)


# Singleton instance
_nutrition_logging_instance: Optional[NutritionLogging] = None


def get_nutrition_logging_service() -> NutritionLogging:
    """Get the singleton nutrition logging service instance"""
    global _nutrition_logging_instance
    
    if _nutrition_logging_instance is None:
        # Initialize with default implementations
        usda_db = USDAFoodDatabase(api_key="your-usda-api-key")
        cv_recognition = ComputerVisionFoodRecognition()
        analyzer = ComprehensiveNutritionAnalyzer()
        
        _nutrition_logging_instance = NutritionLogging(
            food_database=usda_db,
            image_recognition=cv_recognition,
            nutrition_analyzer=analyzer
        )
    
    return _nutrition_logging_instance


async def main():
    """Example usage of the nutrition logging service"""
    nutrition_service = get_nutrition_logging_service()
    
    try:
        await nutrition_service.start()
        
        user_id = "user123"
        
        # Example 1: Log food manually
        entry = await nutrition_service.log_food_manual(
            user_id=user_id,
            food_name="banana",
            quantity=120.0,  # grams
            meal_type=MealType.BREAKFAST,
            notes="Medium size banana"
        )
        
        if entry:
            print(f"Logged: {entry.food_item.name} - {entry.quantity}g")
        
        # Example 2: Set nutrition goals
        calorie_goal = await nutrition_service.set_nutrition_goal(
            user_id=user_id,
            nutrient_type=NutrientType.CALORIES,
            target_amount=2000.0,
            target_unit="kcal",
            time_period="daily"
        )
        
        protein_goal = await nutrition_service.set_nutrition_goal(
            user_id=user_id,
            nutrient_type=NutrientType.PROTEIN,
            target_amount=150.0,
            target_unit="g",
            time_period="daily"
        )
        
        print(f"Set calorie goal: {calorie_goal.target_amount} {calorie_goal.target_unit}")
        print(f"Set protein goal: {protein_goal.target_amount} {protein_goal.target_unit}")
        
        # Example 3: Create meal plan
        meal_plan = await nutrition_service.create_meal_plan(
            user_id=user_id,
            name="Healthy Week",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7),
            target_calories=2000.0,
            dietary_restrictions={DietaryRestriction.VEGETARIAN}
        )
        
        if meal_plan:
            print(f"Created meal plan: {meal_plan.name}")
        
        # Example 4: Get daily analysis
        analysis = await nutrition_service.get_daily_analysis(user_id, datetime.now())
        if analysis:
            print(f"Daily analysis - Total calories: {analysis.total_nutrients.get(NutrientType.CALORIES, 0):.1f}")
            print(f"Recommendations: {', '.join(analysis.recommendations[:3])}")
        
        # Let it run for a bit to see background tasks
        await asyncio.sleep(5)
        
    finally:
        await nutrition_service.stop()


if __name__ == "__main__":
    asyncio.run(main())