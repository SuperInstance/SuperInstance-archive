"""
Value Perception Testing System
Test and analyze how users perceive value at different price points
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import sqlite3
import json
import uuid
import statistics
from dataclasses import dataclass
from enum import Enum
import random

logger = logging.getLogger(__name__)

class TestType(str, Enum):
    VAN_WESTENDORP = "van_westendorp"  # Price sensitivity meter
    CONJOINT = "conjoint"              # Feature-price trade-offs
    MONADIC = "monadic"                # Single price point evaluation
    SEQUENTIAL_MONADIC = "sequential_monadic"  # Multiple price comparisons
    GABOR_GRANGER = "gabor_granger"    # Purchase intention at price points

class PerceptionLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    FAIR = "fair"
    HIGH = "high"
    VERY_HIGH = "very_high"

@dataclass
class ValueTest:
    test_id: str
    test_type: TestType
    feature_set: List[str]
    price_points: List[Decimal]
    target_users: List[str]
    status: str
    created_at: datetime

@dataclass
class PricePerceptionResult:
    price_point: Decimal
    perceived_value: float
    purchase_likelihood: float
    quality_perception: float
    price_fairness: float
    value_for_money: float

class ValuePerceptionTester:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/beta-pricing/data/beta_pricing.db"
        self._initialize_tables()
        
        # Standard Van Westendorp questions
        self.vw_questions = [
            "At what price would you consider this product to be priced so low that you would feel the quality couldn't be very good?",
            "At what price would you consider this product to be a bargain—a great buy for the money?",
            "At what price would you consider this product to be getting expensive, so that it is not out of the question, but you would have to give some thought to buying it?",
            "At what price would you consider this product to be so expensive that you would not consider buying it?"
        ]
    
    def _initialize_tables(self):
        """Initialize database tables for value perception testing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Value perception tests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS value_perception_tests (
                id TEXT PRIMARY KEY,
                test_name TEXT NOT NULL,
                test_type TEXT NOT NULL,
                feature_set TEXT NOT NULL,
                price_points TEXT NOT NULL,
                target_users TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        # Test responses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS value_test_responses (
                id TEXT PRIMARY KEY,
                test_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                price_point DECIMAL NOT NULL,
                perceived_value REAL NOT NULL,
                purchase_likelihood REAL NOT NULL,
                quality_perception REAL NOT NULL,
                price_fairness REAL NOT NULL,
                value_for_money REAL NOT NULL,
                response_time_seconds INTEGER,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,
                FOREIGN KEY (test_id) REFERENCES value_perception_tests (id),
                FOREIGN KEY (user_id) REFERENCES beta_users (id)
            )
        ''')
        
        # Van Westendorp responses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS van_westendorp_responses (
                id TEXT PRIMARY KEY,
                test_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                too_cheap DECIMAL,
                bargain DECIMAL,
                expensive DECIMAL,
                too_expensive DECIMAL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,
                FOREIGN KEY (test_id) REFERENCES value_perception_tests (id),
                FOREIGN KEY (user_id) REFERENCES beta_users (id)
            )
        ''')
        
        # Conjoint analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conjoint_responses (
                id TEXT PRIMARY KEY,
                test_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                feature_combination TEXT NOT NULL,
                price_point DECIMAL NOT NULL,
                preference_score REAL NOT NULL,
                ranking INTEGER,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,
                FOREIGN KEY (test_id) REFERENCES value_perception_tests (id),
                FOREIGN KEY (user_id) REFERENCES beta_users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def create_value_test(
        self,
        test_name: str,
        test_type: TestType,
        feature_set: List[str],
        price_points: List[Decimal],
        target_users: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a new value perception test"""
        try:
            test_id = f"VT_{uuid.uuid4().hex[:8].upper()}"
            
            test_data = {
                "id": test_id,
                "test_name": test_name,
                "test_type": test_type.value,
                "feature_set": feature_set,
                "price_points": [float(p) for p in price_points],
                "target_users": target_users or [],
                "created_at": datetime.now().isoformat()
            }
            
            # Generate test scenarios based on type
            scenarios = self._generate_test_scenarios(test_type, feature_set, price_points)
            test_data["scenarios"] = scenarios
            
            # Store test
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO value_perception_tests 
                (id, test_name, test_type, feature_set, price_points, target_users, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                test_id, test_name, test_type.value,
                json.dumps(feature_set), json.dumps([float(p) for p in price_points]),
                json.dumps(target_users or []), json.dumps(test_data)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created value perception test {test_id}: {test_name}")
            
            return test_data
            
        except Exception as e:
            logger.error(f"Error creating value test: {str(e)}")
            return {"error": str(e)}
    
    def _generate_test_scenarios(
        self, 
        test_type: TestType, 
        features: List[str], 
        price_points: List[Decimal]
    ) -> List[Dict[str, Any]]:
        """Generate test scenarios based on test type"""
        scenarios = []
        
        if test_type == TestType.VAN_WESTENDORP:
            # Single scenario with all features
            scenarios.append({
                "scenario_id": "VW001",
                "features": features,
                "description": f"Product with: {', '.join(features)}",
                "questions": self.vw_questions
            })
        
        elif test_type == TestType.MONADIC:
            # One scenario per price point
            for i, price in enumerate(price_points):
                scenarios.append({
                    "scenario_id": f"MON{i+1:03d}",
                    "features": features,
                    "price": float(price),
                    "description": f"Product with {', '.join(features)} at ${float(price):.2f}/month"
                })
        
        elif test_type == TestType.SEQUENTIAL_MONADIC:
            # Multiple price points shown sequentially
            for i, price in enumerate(price_points):
                scenarios.append({
                    "scenario_id": f"SEQ{i+1:03d}",
                    "features": features,
                    "price": float(price),
                    "order": i + 1,
                    "description": f"Option {i+1}: {', '.join(features)} at ${float(price):.2f}/month"
                })
        
        elif test_type == TestType.CONJOINT:
            # Generate feature-price combinations
            feature_combinations = self._generate_feature_combinations(features)
            scenario_id = 1
            
            for combo in feature_combinations:
                for price in price_points:
                    scenarios.append({
                        "scenario_id": f"CON{scenario_id:03d}",
                        "features": combo,
                        "price": float(price),
                        "description": f"{', '.join(combo)} at ${float(price):.2f}/month"
                    })
                    scenario_id += 1
        
        elif test_type == TestType.GABOR_GRANGER:
            # Price ladder scenarios
            for i, price in enumerate(price_points):
                scenarios.append({
                    "scenario_id": f"GG{i+1:03d}",
                    "features": features,
                    "price": float(price),
                    "question": f"Would you purchase this product for ${float(price):.2f}/month?",
                    "follow_up": "How likely are you to purchase at this price?"
                })
        
        return scenarios
    
    def _generate_feature_combinations(self, features: List[str]) -> List[List[str]]:
        """Generate different combinations of features for conjoint analysis"""
        if len(features) <= 3:
            return [features]  # Use all features if small set
        
        combinations = [
            features[:2],  # Basic package
            features[:4] if len(features) >= 4 else features,  # Standard package
            features,  # Premium package (all features)
        ]
        
        # Add some random combinations
        if len(features) > 4:
            for _ in range(3):
                combo_size = random.randint(2, len(features) - 1)
                combo = random.sample(features, combo_size)
                combinations.append(combo)
        
        return combinations
    
    async def run_test(
        self,
        test_id: str,
        user_id: str,
        responses: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run value perception test for a user"""
        try:
            # Get test details
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT test_type, data FROM value_perception_tests WHERE id = ?
            ''', (test_id,))
            
            test_result = cursor.fetchone()
            if not test_result:
                conn.close()
                return {"error": "Test not found"}
            
            test_type, test_data_json = test_result
            test_data = json.loads(test_data_json)
            
            # Process responses based on test type
            if test_type == TestType.VAN_WESTENDORP.value:
                result = await self._process_van_westendorp_response(test_id, user_id, responses, conn)
            elif test_type == TestType.CONJOINT.value:
                result = await self._process_conjoint_response(test_id, user_id, responses, conn)
            else:
                result = await self._process_standard_response(test_id, user_id, responses, conn)
            
            conn.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Error running test: {str(e)}")
            return {"error": str(e)}
    
    async def _process_van_westendorp_response(
        self, 
        test_id: str, 
        user_id: str, 
        responses: Dict[str, Any],
        conn: sqlite3.Connection
    ) -> Dict[str, Any]:
        """Process Van Westendorp Price Sensitivity Meter responses"""
        cursor = conn.cursor()
        
        response_id = f"VW_{uuid.uuid4().hex[:8].upper()}"
        
        # Extract price points
        too_cheap = Decimal(str(responses.get("too_cheap", 0)))
        bargain = Decimal(str(responses.get("bargain", 0)))
        expensive = Decimal(str(responses.get("expensive", 0)))
        too_expensive = Decimal(str(responses.get("too_expensive", 0)))
        
        # Validate price hierarchy
        if not (too_cheap <= bargain <= expensive <= too_expensive):
            return {"error": "Invalid price hierarchy in Van Westendorp responses"}
        
        response_data = {
            "id": response_id,
            "test_id": test_id,
            "user_id": user_id,
            "too_cheap": float(too_cheap),
            "bargain": float(bargain),
            "expensive": float(expensive),
            "too_expensive": float(too_expensive),
            "submitted_at": datetime.now().isoformat()
        }
        
        cursor.execute('''
            INSERT INTO van_westendorp_responses 
            (id, test_id, user_id, too_cheap, bargain, expensive, too_expensive, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            response_id, test_id, user_id,
            float(too_cheap), float(bargain), float(expensive), float(too_expensive),
            json.dumps(response_data)
        ))
        
        conn.commit()
        
        # Calculate individual analysis
        price_range_acceptable = float(expensive - bargain)
        optimal_price = float((bargain + expensive) / 2)
        
        return {
            "response_id": response_id,
            "analysis": {
                "acceptable_price_range": {
                    "min": float(bargain),
                    "max": float(expensive),
                    "width": price_range_acceptable
                },
                "optimal_price_point": optimal_price,
                "price_sensitivity": price_range_acceptable / optimal_price if optimal_price > 0 else 0
            }
        }
    
    async def _process_conjoint_response(
        self, 
        test_id: str, 
        user_id: str, 
        responses: Dict[str, Any],
        conn: sqlite3.Connection
    ) -> Dict[str, Any]:
        """Process conjoint analysis responses"""
        cursor = conn.cursor()
        
        rankings = responses.get("rankings", [])
        stored_responses = []
        
        for ranking in rankings:
            response_id = f"CON_{uuid.uuid4().hex[:8].upper()}"
            
            response_data = {
                "id": response_id,
                "test_id": test_id,
                "user_id": user_id,
                "scenario_id": ranking["scenario_id"],
                "features": ranking["features"],
                "price": ranking["price"],
                "ranking": ranking["rank"],
                "preference_score": ranking.get("score", 0),
                "submitted_at": datetime.now().isoformat()
            }
            
            cursor.execute('''
                INSERT INTO conjoint_responses 
                (id, test_id, user_id, feature_combination, price_point, preference_score, ranking, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                response_id, test_id, user_id,
                json.dumps(ranking["features"]), ranking["price"],
                ranking.get("score", 0), ranking["rank"],
                json.dumps(response_data)
            ))
            
            stored_responses.append(response_data)
        
        conn.commit()
        
        # Calculate feature importance
        feature_importance = self._calculate_feature_importance(rankings)
        
        return {
            "responses_stored": len(stored_responses),
            "feature_importance": feature_importance
        }
    
    async def _process_standard_response(
        self, 
        test_id: str, 
        user_id: str, 
        responses: Dict[str, Any],
        conn: sqlite3.Connection
    ) -> Dict[str, Any]:
        """Process standard value perception responses"""
        cursor = conn.cursor()
        
        stored_responses = []
        
        for price_response in responses.get("price_evaluations", []):
            response_id = f"VP_{uuid.uuid4().hex[:8].upper()}"
            
            price_point = Decimal(str(price_response["price"]))
            
            response_data = {
                "id": response_id,
                "test_id": test_id,
                "user_id": user_id,
                "price_point": float(price_point),
                "perceived_value": price_response.get("perceived_value", 0),
                "purchase_likelihood": price_response.get("purchase_likelihood", 0),
                "quality_perception": price_response.get("quality_perception", 0),
                "price_fairness": price_response.get("price_fairness", 0),
                "value_for_money": price_response.get("value_for_money", 0),
                "response_time": price_response.get("response_time", 0),
                "submitted_at": datetime.now().isoformat()
            }
            
            cursor.execute('''
                INSERT INTO value_test_responses 
                (id, test_id, user_id, price_point, perceived_value, purchase_likelihood,
                 quality_perception, price_fairness, value_for_money, response_time_seconds, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                response_id, test_id, user_id, float(price_point),
                response_data["perceived_value"], response_data["purchase_likelihood"],
                response_data["quality_perception"], response_data["price_fairness"],
                response_data["value_for_money"], response_data["response_time"],
                json.dumps(response_data)
            ))
            
            stored_responses.append(response_data)
        
        conn.commit()
        
        return {
            "responses_stored": len(stored_responses),
            "individual_analysis": self._analyze_individual_responses(stored_responses)
        }
    
    def _calculate_feature_importance(self, rankings: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate relative importance of features from conjoint analysis"""
        feature_scores = {}
        
        for ranking in rankings:
            features = ranking["features"]
            rank = ranking["rank"]
            score = len(rankings) - rank + 1  # Convert rank to score (higher is better)
            
            for feature in features:
                if feature not in feature_scores:
                    feature_scores[feature] = []
                feature_scores[feature].append(score)
        
        # Calculate average importance
        feature_importance = {}
        for feature, scores in feature_scores.items():
            feature_importance[feature] = statistics.mean(scores) if scores else 0
        
        # Normalize to percentages
        total_importance = sum(feature_importance.values())
        if total_importance > 0:
            feature_importance = {
                feature: (importance / total_importance) * 100
                for feature, importance in feature_importance.items()
            }
        
        return feature_importance
    
    def _analyze_individual_responses(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze individual user's value perception responses"""
        if not responses:
            return {}
        
        # Calculate price-value relationships
        prices = [r["price_point"] for r in responses]
        values = [r["perceived_value"] for r in responses]
        
        # Find optimal price point (highest value score)
        best_response = max(responses, key=lambda x: x["perceived_value"])
        
        # Calculate price elasticity of value
        price_value_correlation = statistics.correlation(prices, values) if len(prices) > 1 else 0
        
        return {
            "optimal_price": best_response["price_point"],
            "max_perceived_value": best_response["perceived_value"],
            "price_value_correlation": round(price_value_correlation, 3),
            "value_sensitivity": "high" if abs(price_value_correlation) > 0.7 else "medium" if abs(price_value_correlation) > 0.3 else "low"
        }
    
    async def get_test_results(self, test_id: str) -> Dict[str, Any]:
        """Get comprehensive test results and analysis"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get test details
            cursor.execute('''
                SELECT test_name, test_type, feature_set, price_points, data
                FROM value_perception_tests WHERE id = ?
            ''', (test_id,))
            
            test_result = cursor.fetchone()
            if not test_result:
                conn.close()
                return {"error": "Test not found"}
            
            test_name, test_type, feature_set_json, price_points_json, test_data_json = test_result
            test_data = json.loads(test_data_json)
            
            # Get responses based on test type
            if test_type == TestType.VAN_WESTENDORP.value:
                results = await self._analyze_van_westendorp_results(test_id, cursor)
            elif test_type == TestType.CONJOINT.value:
                results = await self._analyze_conjoint_results(test_id, cursor)
            else:
                results = await self._analyze_standard_results(test_id, cursor)
            
            conn.close()
            
            # Add test metadata
            results.update({
                "test_id": test_id,
                "test_name": test_name,
                "test_type": test_type,
                "feature_set": json.loads(feature_set_json),
                "price_points": json.loads(price_points_json),
                "analysis_date": datetime.now().isoformat()
            })
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting test results: {str(e)}")
            return {"error": str(e)}
    
    async def _analyze_van_westendorp_results(self, test_id: str, cursor: sqlite3.Cursor) -> Dict[str, Any]:
        """Analyze Van Westendorp results"""
        cursor.execute('''
            SELECT too_cheap, bargain, expensive, too_expensive
            FROM van_westendorp_responses WHERE test_id = ?
        ''', (test_id,))
        
        responses = cursor.fetchall()
        
        if not responses:
            return {"error": "No responses found"}
        
        # Calculate price ranges
        too_cheap_prices = [r[0] for r in responses]
        bargain_prices = [r[1] for r in responses]
        expensive_prices = [r[2] for r in responses]
        too_expensive_prices = [r[3] for r in responses]
        
        # Van Westendorp analysis
        results = {
            "response_count": len(responses),
            "price_points": {
                "point_of_marginal_cheapness": statistics.median(too_cheap_prices),
                "point_of_marginal_expensiveness": statistics.median(expensive_prices),
                "optimal_price_point": statistics.median([(b + e) / 2 for b, e in zip(bargain_prices, expensive_prices)]),
                "indifference_price_point": statistics.median([(t + te) / 2 for t, te in zip(too_cheap_prices, too_expensive_prices)])
            },
            "acceptable_range": {
                "min": statistics.median(bargain_prices),
                "max": statistics.median(expensive_prices),
                "width": statistics.median(expensive_prices) - statistics.median(bargain_prices)
            }
        }
        
        return results
    
    async def _analyze_conjoint_results(self, test_id: str, cursor: sqlite3.Cursor) -> Dict[str, Any]:
        """Analyze conjoint analysis results"""
        cursor.execute('''
            SELECT feature_combination, price_point, preference_score, ranking
            FROM conjoint_responses WHERE test_id = ?
        ''', (test_id,))
        
        responses = cursor.fetchall()
        
        if not responses:
            return {"error": "No responses found"}
        
        # Aggregate feature importance
        all_features = set()
        feature_scores = {}
        
        for feature_combo_json, price, score, rank in responses:
            features = json.loads(feature_combo_json)
            all_features.update(features)
            
            for feature in features:
                if feature not in feature_scores:
                    feature_scores[feature] = []
                feature_scores[feature].append(score)
        
        # Calculate feature importance
        feature_importance = {}
        for feature in all_features:
            scores = feature_scores.get(feature, [0])
            feature_importance[feature] = statistics.mean(scores)
        
        # Find optimal feature-price combinations
        sorted_responses = sorted(responses, key=lambda x: x[2], reverse=True)  # Sort by preference score
        top_combinations = sorted_responses[:5]  # Top 5 combinations
        
        return {
            "response_count": len(responses),
            "feature_importance": feature_importance,
            "top_combinations": [
                {
                    "features": json.loads(combo[0]),
                    "price": combo[1],
                    "avg_preference": combo[2],
                    "avg_ranking": combo[3]
                }
                for combo in top_combinations
            ]
        }
    
    async def _analyze_standard_results(self, test_id: str, cursor: sqlite3.Cursor) -> Dict[str, Any]:
        """Analyze standard value perception test results"""
        cursor.execute('''
            SELECT price_point, perceived_value, purchase_likelihood, quality_perception,
                   price_fairness, value_for_money
            FROM value_test_responses WHERE test_id = ?
        ''', (test_id,))
        
        responses = cursor.fetchall()
        
        if not responses:
            return {"error": "No responses found"}
        
        # Aggregate results by price point
        price_analysis = {}
        
        for price, value, likelihood, quality, fairness, vfm in responses:
            if price not in price_analysis:
                price_analysis[price] = {
                    "responses": [],
                    "perceived_value": [],
                    "purchase_likelihood": [],
                    "quality_perception": [],
                    "price_fairness": [],
                    "value_for_money": []
                }
            
            price_analysis[price]["perceived_value"].append(value)
            price_analysis[price]["purchase_likelihood"].append(likelihood)
            price_analysis[price]["quality_perception"].append(quality)
            price_analysis[price]["price_fairness"].append(fairness)
            price_analysis[price]["value_for_money"].append(vfm)
        
        # Calculate averages for each price point
        price_results = {}
        for price, data in price_analysis.items():
            price_results[price] = {
                "avg_perceived_value": statistics.mean(data["perceived_value"]),
                "avg_purchase_likelihood": statistics.mean(data["purchase_likelihood"]),
                "avg_quality_perception": statistics.mean(data["quality_perception"]),
                "avg_price_fairness": statistics.mean(data["price_fairness"]),
                "avg_value_for_money": statistics.mean(data["value_for_money"]),
                "response_count": len(data["perceived_value"])
            }
        
        # Find optimal price point
        optimal_price = max(price_results.keys(), 
                           key=lambda p: price_results[p]["avg_perceived_value"])
        
        return {
            "response_count": len(responses),
            "price_analysis": price_results,
            "optimal_price_point": optimal_price,
            "recommendations": self._generate_value_recommendations(price_results)
        }
    
    def _generate_value_recommendations(self, price_results: Dict[float, Dict[str, float]]) -> List[str]:
        """Generate recommendations based on value perception results"""
        recommendations = []
        
        if not price_results:
            return ["Insufficient data for recommendations"]
        
        # Find best performing metrics
        best_value = max(price_results.items(), key=lambda x: x[1]["avg_perceived_value"])
        best_likelihood = max(price_results.items(), key=lambda x: x[1]["avg_purchase_likelihood"])
        best_fairness = max(price_results.items(), key=lambda x: x[1]["avg_price_fairness"])
        
        if best_value[0] == best_likelihood[0]:
            recommendations.append(f"${best_value[0]:.2f} shows optimal balance of value perception and purchase intent")
        else:
            recommendations.append(f"Consider ${best_value[0]:.2f} for value positioning or ${best_likelihood[0]:.2f} for conversion optimization")
        
        # Quality-price relationship
        quality_scores = [(price, data["avg_quality_perception"]) for price, data in price_results.items()]
        quality_scores.sort(key=lambda x: x[0])  # Sort by price
        
        if len(quality_scores) > 1:
            if quality_scores[-1][1] > quality_scores[0][1] * 1.2:  # Higher price = higher quality perception
                recommendations.append("Higher prices enhance quality perception - consider premium positioning")
            elif quality_scores[0][1] > quality_scores[-1][1]:  # Lower price doesn't hurt quality perception
                recommendations.append("Quality perception remains strong at lower prices - competitive pricing viable")
        
        return recommendations

# Global instance
value_perception_tester = ValuePerceptionTester()