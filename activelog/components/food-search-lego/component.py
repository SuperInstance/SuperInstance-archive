# SUPERINSTANCE LEGO COMPONENT: Food Database Search
# EXTRACTED FROM: services/nutrition-tracking/main.py:429-470
# LEGO PRINCIPLE: Software = Data + Tools + Configuration

from typing import Dict, Any, List, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class FoodSearchLego:
    """
    🧩 LEGO COMPONENT: Food Database Search
    
    DATA: Food nutrition database, serving sizes, aliases
    TOOLS: Text search, similarity matching, nutrition calculation
    CONFIGURATION: Search algorithms, database sources, result formatting
    
    INTERFACES:
    - Input: Search query, result limit, filters
    - Output: Ranked food matches with nutrition data
    - Integration: Nutrition APIs, recipe services, meal planners
    
    DEPLOYMENT OPTIONS:
    - Device: Offline food database for privacy
    - Edge: Regional food preferences and brands
    - Cloud: Global food database with real-time updates
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.database_source = config.get("database_source", "builtin")
        self.search_algorithm = config.get("search_algorithm", "tfidf")
        self.food_database = self._load_food_database()
        self.search_vectorizer = None
        if self.search_algorithm == "tfidf":
            self._initialize_search_vectorizer()
    
    def _load_food_database(self) -> Dict[str, Dict]:
        """Load food database based on configuration"""
        
        # Built-in comprehensive food database
        builtin_foods = {
            # Fruits
            "apple": {
                "category": "fruits",
                "calories_per_100g": 52,
                "protein_per_100g": 0.3,
                "carbs_per_100g": 14,
                "fat_per_100g": 0.2,
                "fiber_per_100g": 2.4,
                "common_serving_sizes": [
                    {"serving": "1 small", "grams": 150},
                    {"serving": "1 medium", "grams": 180},
                    {"serving": "1 large", "grams": 230}
                ],
                "aliases": ["red apple", "green apple", "granny smith", "gala apple"]
            },
            "banana": {
                "category": "fruits",
                "calories_per_100g": 89,
                "protein_per_100g": 1.1,
                "carbs_per_100g": 23,
                "fat_per_100g": 0.3,
                "fiber_per_100g": 2.6,
                "common_serving_sizes": [
                    {"serving": "1 small", "grams": 100},
                    {"serving": "1 medium", "grams": 120},
                    {"serving": "1 large", "grams": 140}
                ],
                "aliases": ["yellow banana", "ripe banana", "green banana"]
            },
            
            # Proteins
            "chicken_breast": {
                "category": "proteins",
                "calories_per_100g": 165,
                "protein_per_100g": 31,
                "carbs_per_100g": 0,
                "fat_per_100g": 3.6,
                "fiber_per_100g": 0,
                "common_serving_sizes": [
                    {"serving": "1 breast (small)", "grams": 120},
                    {"serving": "1 breast (medium)", "grams": 180},
                    {"serving": "1 breast (large)", "grams": 250}
                ],
                "aliases": ["chicken breast", "grilled chicken", "boneless chicken", "skinless chicken breast"]
            },
            "salmon": {
                "category": "proteins",
                "calories_per_100g": 208,
                "protein_per_100g": 25,
                "carbs_per_100g": 0,
                "fat_per_100g": 12,
                "fiber_per_100g": 0,
                "common_serving_sizes": [
                    {"serving": "1 fillet", "grams": 150},
                    {"serving": "1 serving", "grams": 100}
                ],
                "aliases": ["atlantic salmon", "grilled salmon", "baked salmon", "salmon fillet"]
            },
            
            # Grains
            "oatmeal": {
                "category": "grains",
                "calories_per_100g": 389,
                "protein_per_100g": 17,
                "carbs_per_100g": 66,
                "fat_per_100g": 7,
                "fiber_per_100g": 11,
                "common_serving_sizes": [
                    {"serving": "1/2 cup dry", "grams": 40},
                    {"serving": "1 cup cooked", "grams": 240}
                ],
                "aliases": ["rolled oats", "steel cut oats", "porridge", "oats"]
            },
            "brown_rice": {
                "category": "grains",
                "calories_per_100g": 111,
                "protein_per_100g": 2.6,
                "carbs_per_100g": 23,
                "fat_per_100g": 0.9,
                "fiber_per_100g": 1.8,
                "common_serving_sizes": [
                    {"serving": "1 cup cooked", "grams": 195}
                ],
                "aliases": ["brown rice", "whole grain rice", "long grain brown rice"]
            },
            
            # Vegetables
            "broccoli": {
                "category": "vegetables",
                "calories_per_100g": 34,
                "protein_per_100g": 2.8,
                "carbs_per_100g": 7,
                "fat_per_100g": 0.4,
                "fiber_per_100g": 2.6,
                "common_serving_sizes": [
                    {"serving": "1 cup chopped", "grams": 90},
                    {"serving": "1 medium head", "grams": 600}
                ],
                "aliases": ["fresh broccoli", "steamed broccoli", "broccoli florets"]
            },
            "spinach": {
                "category": "vegetables",
                "calories_per_100g": 23,
                "protein_per_100g": 2.9,
                "carbs_per_100g": 3.6,
                "fat_per_100g": 0.4,
                "fiber_per_100g": 2.2,
                "common_serving_sizes": [
                    {"serving": "1 cup fresh", "grams": 30},
                    {"serving": "1 cup cooked", "grams": 180}
                ],
                "aliases": ["baby spinach", "fresh spinach", "cooked spinach", "spinach leaves"]
            },
            
            # Dairy
            "greek_yogurt": {
                "category": "dairy",
                "calories_per_100g": 59,
                "protein_per_100g": 10,
                "carbs_per_100g": 3.6,
                "fat_per_100g": 0.4,
                "fiber_per_100g": 0,
                "common_serving_sizes": [
                    {"serving": "1 cup", "grams": 245},
                    {"serving": "1 container (small)", "grams": 170}
                ],
                "aliases": ["plain greek yogurt", "nonfat greek yogurt", "strained yogurt"]
            }
        }
        
        if self.database_source == "external_api":
            # Would integrate with external food APIs like USDA, Edamam, etc.
            return self._fetch_external_database()
        
        return builtin_foods
    
    def _initialize_search_vectorizer(self):
        """Initialize TF-IDF vectorizer for semantic food search"""
        # Create searchable text from food database
        food_texts = []
        self.food_keys = []
        
        for food_key, food_data in self.food_database.items():
            # Combine food name, aliases, and category for rich search
            text_parts = [food_key.replace("_", " ")]
            text_parts.extend(food_data.get("aliases", []))
            text_parts.append(food_data.get("category", ""))
            
            food_text = " ".join(text_parts)
            food_texts.append(food_text)
            self.food_keys.append(food_key)
        
        # Initialize and fit TF-IDF vectorizer
        self.search_vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=1000
        )
        self.food_vectors = self.search_vectorizer.fit_transform(food_texts)
    
    def search_foods(self, query: str, limit: int = 10, category_filter: Optional[str] = None) -> List[Dict]:
        """
        Main search function - core LEGO functionality
        
        Args:
            query: Search term (e.g., "grilled chicken", "apple")
            limit: Maximum results to return
            category_filter: Optional category filter ("proteins", "fruits", etc.)
        
        Returns:
            List of food matches with nutrition data and similarity scores
        """
        if self.search_algorithm == "tfidf":
            return self._search_with_tfidf(query, limit, category_filter)
        else:
            return self._search_simple_match(query, limit, category_filter)
    
    def _search_with_tfidf(self, query: str, limit: int, category_filter: Optional[str]) -> List[Dict]:
        """Advanced TF-IDF based semantic search"""
        if not self.search_vectorizer:
            return self._search_simple_match(query, limit, category_filter)
        
        # Transform query to vector space
        query_vector = self.search_vectorizer.transform([query])
        
        # Calculate cosine similarity
        similarities = cosine_similarity(query_vector, self.food_vectors).flatten()
        
        # Get top matches
        top_indices = np.argsort(similarities)[::-1][:limit * 2]  # Get extra for filtering
        
        results = []
        for idx in top_indices:
            if len(results) >= limit:
                break
                
            food_key = self.food_keys[idx]
            food_data = self.food_database[food_key]
            similarity_score = similarities[idx]
            
            # Apply category filter if specified
            if category_filter and food_data.get("category") != category_filter:
                continue
            
            # Skip very low similarity matches
            if similarity_score < 0.1:
                continue
            
            result = self._format_food_result(food_key, food_data, similarity_score)
            results.append(result)
        
        return results
    
    def _search_simple_match(self, query: str, limit: int, category_filter: Optional[str]) -> List[Dict]:
        """Simple substring matching search"""
        query_lower = query.lower()
        results = []
        
        for food_key, food_data in self.food_database.items():
            if len(results) >= limit:
                break
            
            # Apply category filter
            if category_filter and food_data.get("category") != category_filter:
                continue
            
            # Check if query matches food name or aliases
            food_name = food_key.replace("_", " ")
            if query_lower in food_name.lower():
                result = self._format_food_result(food_key, food_data, 1.0)
                results.append(result)
                continue
            
            # Check aliases
            for alias in food_data.get("aliases", []):
                if query_lower in alias.lower():
                    result = self._format_food_result(food_key, food_data, 0.8)
                    results.append(result)
                    break
        
        return results
    
    def _format_food_result(self, food_key: str, food_data: Dict, similarity_score: float) -> Dict:
        """Format food search result in standard LEGO interface format"""
        return {
            "food_name": food_key.replace("_", " ").title(),
            "category": food_data.get("category", "unknown"),
            "calories_per_100g": food_data.get("calories_per_100g", 0),
            "protein_per_100g": food_data.get("protein_per_100g", 0),
            "carbs_per_100g": food_data.get("carbs_per_100g", 0),
            "fat_per_100g": food_data.get("fat_per_100g", 0),
            "fiber_per_100g": food_data.get("fiber_per_100g", 0),
            "common_serving_sizes": food_data.get("common_serving_sizes", []),
            "similarity_score": round(similarity_score, 3),
            "aliases": food_data.get("aliases", [])
        }
    
    def get_food_by_name(self, food_name: str) -> Optional[Dict]:
        """Get exact food match by name - utility LEGO function"""
        food_key = food_name.lower().replace(" ", "_")
        if food_key in self.food_database:
            return self._format_food_result(food_key, self.food_database[food_key], 1.0)
        return None
    
    def calculate_nutrition_for_serving(self, food_name: str, serving_size: str, quantity: float = 1.0) -> Optional[Dict]:
        """Calculate nutrition for specific serving - calculation LEGO function"""
        food_data = self.get_food_by_name(food_name)
        if not food_data:
            return None
        
        # Find matching serving size
        serving_grams = None
        for serving in food_data["common_serving_sizes"]:
            if serving["serving"].lower() == serving_size.lower():
                serving_grams = serving["grams"]
                break
        
        if serving_grams is None:
            return None
        
        # Calculate nutrition based on serving size and quantity
        multiplier = (serving_grams * quantity) / 100  # Convert to per-100g basis
        
        return {
            "food_name": food_data["food_name"],
            "serving": f"{quantity} {serving_size}",
            "total_grams": serving_grams * quantity,
            "calories": round(food_data["calories_per_100g"] * multiplier),
            "protein_g": round(food_data["protein_per_100g"] * multiplier, 1),
            "carbs_g": round(food_data["carbs_per_100g"] * multiplier, 1),
            "fat_g": round(food_data["fat_per_100g"] * multiplier, 1),
            "fiber_g": round(food_data["fiber_per_100g"] * multiplier, 1)
        }
    
    def get_categories(self) -> List[str]:
        """Get all available food categories - discovery LEGO function"""
        categories = set()
        for food_data in self.food_database.values():
            categories.add(food_data.get("category", "unknown"))
        return sorted(list(categories))

# LEGO CONFIGURATION OPTIONS
DEPLOYMENT_CONFIGS = {
    "device_offline": {
        "database_source": "builtin",
        "search_algorithm": "simple",
        "features": ["offline_search", "basic_nutrition"]
    },
    "edge_enhanced": {
        "database_source": "builtin",
        "search_algorithm": "tfidf",
        "features": ["semantic_search", "regional_foods", "nutrition_calculation"]
    },
    "cloud_comprehensive": {
        "database_source": "external_api",
        "search_algorithm": "tfidf",
        "features": ["global_database", "real_time_updates", "ml_recommendations"]
    }
}

# USAGE EXAMPLES
def create_food_search_lego(deployment_type: str = "edge_enhanced"):
    """Factory function to create configured Food Search Lego"""
    config = DEPLOYMENT_CONFIGS.get(deployment_type, DEPLOYMENT_CONFIGS["edge_enhanced"])
    return FoodSearchLego(config)

# INTEGRATION INTERFACES
def integrate_with_nutrition_api(food_search: FoodSearchLego, nutrition_api):
    """Connect food search results directly to nutrition logging"""
    # Integration logic would go here
    pass

def integrate_with_meal_planner(food_search: FoodSearchLego, meal_planner):
    """Connect to meal planning Lego for recipe suggestions"""
    # Integration logic would go here  
    pass