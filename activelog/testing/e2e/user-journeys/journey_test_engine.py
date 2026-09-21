"""
User Journey Testing Engine for ActiveLog Platform

This module provides comprehensive user journey testing across all applications
with scenario-based testing, visual regression, and cross-platform validation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
import json
import asyncio
import time
import random
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import requests
import websocket
from PIL import Image, ImageChops
import subprocess


class JourneyType(Enum):
    """Types of user journeys"""
    NEW_USER_ONBOARDING = "new_user_onboarding"
    RETURNING_USER_LOGIN = "returning_user_login"
    CONTENT_CREATION = "content_creation"
    COLLABORATION = "collaboration"
    PAYMENT_FLOW = "payment_flow"
    TUTORIAL_COMPLETION = "tutorial_completion"
    DATA_EXPORT = "data_export"
    ACCOUNT_MANAGEMENT = "account_management"
    MOBILE_APP_USAGE = "mobile_app_usage"
    CROSS_DEVICE_SYNC = "cross_device_sync"


class TestEnvironment(Enum):
    """Test environments"""
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"
    MOBILE_SIMULATOR = "mobile_simulator"
    BROWSER_STACK = "browser_stack"


class UserPersona(Enum):
    """Different user personas for testing"""
    TECH_SAVVY_PROFESSIONAL = "tech_savvy_professional"
    CASUAL_USER = "casual_user"
    STUDENT = "student"
    TEACHER = "teacher"
    ENTERPRISE_ADMIN = "enterprise_admin"
    ACCESSIBILITY_USER = "accessibility_user"
    MOBILE_FIRST_USER = "mobile_first_user"
    INTERNATIONAL_USER = "international_user"


@dataclass
class JourneyStep:
    """Individual step in a user journey"""
    step_id: str
    description: str
    action_type: str  # click, type, wait, verify, api_call, etc.
    selector: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    expected_outcome: Optional[Dict[str, Any]] = None
    timeout: float = 10.0
    screenshot: bool = False
    api_endpoint: Optional[str] = None
    validation_rules: List[Dict[str, Any]] = field(default_factory=list)
    retry_count: int = 3
    optional: bool = False


@dataclass
class UserJourney:
    """Complete user journey definition"""
    journey_id: str
    name: str
    description: str
    journey_type: JourneyType
    persona: UserPersona
    environment: TestEnvironment
    steps: List[JourneyStep]
    prerequisites: List[str] = field(default_factory=list)
    cleanup_steps: List[JourneyStep] = field(default_factory=list)
    expected_duration: float = 300.0  # 5 minutes default
    tags: List[str] = field(default_factory=list)
    data_dependencies: List[str] = field(default_factory=list)


@dataclass
class JourneyExecution:
    """Result of journey execution"""
    journey_id: str
    execution_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "running"  # running, passed, failed, skipped
    steps_executed: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    environment_info: Dict[str, Any] = field(default_factory=dict)


class WebDriverManager:
    """Manages web driver instances for different browsers"""
    
    def __init__(self):
        self.drivers: Dict[str, webdriver.Chrome] = {}
        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
    
    def get_driver(self, browser: str = "chrome", headless: bool = True, 
                   mobile: bool = False) -> webdriver.Chrome:
        """Get or create web driver instance"""
        driver_key = f"{browser}_{headless}_{mobile}"
        
        if driver_key not in self.drivers:
            options = Options()
            
            if headless:
                options.add_argument("--headless")
            
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-web-security")
            options.add_argument("--allow-running-insecure-content")
            
            if mobile:
                mobile_emulation = {
                    "deviceMetrics": {"width": 375, "height": 667, "pixelRatio": 2.0},
                    "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
                }
                options.add_experimental_option("mobileEmulation", mobile_emulation)
            
            self.drivers[driver_key] = webdriver.Chrome(options=options)
        
        return self.drivers[driver_key]
    
    def take_screenshot(self, driver: webdriver.Chrome, filename: str) -> str:
        """Take screenshot and save to file"""
        filepath = self.screenshot_dir / f"{filename}_{int(time.time())}.png"
        driver.save_screenshot(str(filepath))
        return str(filepath)
    
    def compare_screenshots(self, baseline: str, current: str) -> float:
        """Compare two screenshots and return similarity score"""
        try:
            baseline_img = Image.open(baseline)
            current_img = Image.open(current)
            
            # Resize images to same size if different
            if baseline_img.size != current_img.size:
                current_img = current_img.resize(baseline_img.size)
            
            # Calculate difference
            diff = ImageChops.difference(baseline_img, current_img)
            
            # Calculate similarity percentage
            stat = list(diff.getdata())
            total_pixels = len(stat)
            different_pixels = sum(1 for pixel in stat if pixel != 0)
            
            similarity = ((total_pixels - different_pixels) / total_pixels) * 100
            return similarity
            
        except Exception as e:
            logging.error(f"Error comparing screenshots: {e}")
            return 0.0
    
    def cleanup(self):
        """Close all web drivers"""
        for driver in self.drivers.values():
            try:
                driver.quit()
            except Exception as e:
                logging.error(f"Error closing driver: {e}")
        self.drivers.clear()


class APITestClient:
    """HTTP API testing client"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.auth_token: Optional[str] = None
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with the API"""
        try:
            response = self.session.post(f"{self.base_url}/auth/login", json={
                "username": username,
                "password": password
            })
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_token}"
                })
                return True
        except Exception as e:
            logging.error(f"API authentication failed: {e}")
        
        return False
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request and return response data"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                "response_time": response.elapsed.total_seconds()
            }
        except Exception as e:
            return {
                "status_code": 0,
                "error": str(e),
                "response_time": 0
            }


class JourneyStepExecutor:
    """Executes individual journey steps"""
    
    def __init__(self, driver_manager: WebDriverManager, api_client: APITestClient):
        self.driver_manager = driver_manager
        self.api_client = api_client
        self.wait_timeout = 10
    
    async def execute_step(self, step: JourneyStep, driver: webdriver.Chrome,
                          context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single journey step"""
        start_time = time.time()
        result = {
            "step_id": step.step_id,
            "status": "failed",
            "start_time": start_time,
            "error": None,
            "screenshot": None,
            "execution_time": 0,
            "data": {}
        }
        
        try:
            if step.action_type == "navigate":
                await self._execute_navigate(step, driver, context, result)
            elif step.action_type == "click":
                await self._execute_click(step, driver, context, result)
            elif step.action_type == "type":
                await self._execute_type(step, driver, context, result)
            elif step.action_type == "wait":
                await self._execute_wait(step, driver, context, result)
            elif step.action_type == "verify":
                await self._execute_verify(step, driver, context, result)
            elif step.action_type == "api_call":
                await self._execute_api_call(step, context, result)
            elif step.action_type == "scroll":
                await self._execute_scroll(step, driver, context, result)
            elif step.action_type == "hover":
                await self._execute_hover(step, driver, context, result)
            elif step.action_type == "select":
                await self._execute_select(step, driver, context, result)
            elif step.action_type == "upload":
                await self._execute_upload(step, driver, context, result)
            else:
                result["error"] = f"Unknown action type: {step.action_type}"
            
            # Take screenshot if requested
            if step.screenshot:
                result["screenshot"] = self.driver_manager.take_screenshot(
                    driver, f"{step.step_id}_screenshot"
                )
            
            # Run validation rules
            if step.validation_rules and result["status"] != "failed":
                await self._validate_step_results(step, driver, result)
            
            result["execution_time"] = time.time() - start_time
            
        except Exception as e:
            result["error"] = str(e)
            result["execution_time"] = time.time() - start_time
            logging.error(f"Step execution failed: {step.step_id} - {e}")
        
        return result
    
    async def _execute_navigate(self, step: JourneyStep, driver: webdriver.Chrome,
                              context: Dict[str, Any], result: Dict[str, Any]):
        """Execute navigation step"""
        url = step.input_data.get("url") if step.input_data else step.selector
        if not url:
            raise ValueError("Navigate step requires URL")
        
        # Replace context variables in URL
        for key, value in context.items():
            url = url.replace(f"{{{key}}}", str(value))
        
        driver.get(url)
        
        # Wait for page load
        WebDriverWait(driver, self.wait_timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        
        result["status"] = "passed"
        result["data"]["current_url"] = driver.current_url
    
    async def _execute_click(self, step: JourneyStep, driver: webdriver.Chrome,
                           context: Dict[str, Any], result: Dict[str, Any]):
        """Execute click step"""
        if not step.selector:
            raise ValueError("Click step requires selector")
        
        wait = WebDriverWait(driver, self.wait_timeout)
        element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, step.selector)))
        
        # Scroll element into view
        driver.execute_script("arguments[0].scrollIntoView(true);", element)
        time.sleep(0.5)  # Brief pause for scroll
        
        element.click()
        result["status"] = "passed"
        result["data"]["element_text"] = element.text
    
    async def _execute_type(self, step: JourneyStep, driver: webdriver.Chrome,
                          context: Dict[str, Any], result: Dict[str, Any]):
        """Execute typing step"""
        if not step.selector or not step.input_data:
            raise ValueError("Type step requires selector and input_data")
        
        text = step.input_data.get("text", "")
        clear_first = step.input_data.get("clear", True)
        
        # Replace context variables
        for key, value in context.items():
            text = text.replace(f"{{{key}}}", str(value))
        
        wait = WebDriverWait(driver, self.wait_timeout)
        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, step.selector)))
        
        if clear_first:
            element.clear()
        
        element.send_keys(text)
        result["status"] = "passed"
        result["data"]["input_text"] = text
    
    async def _execute_wait(self, step: JourneyStep, driver: webdriver.Chrome,
                          context: Dict[str, Any], result: Dict[str, Any]):
        """Execute wait step"""
        if step.input_data and "duration" in step.input_data:
            # Wait for specific duration
            await asyncio.sleep(step.input_data["duration"])
        elif step.selector:
            # Wait for element
            wait = WebDriverWait(driver, step.timeout)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, step.selector)))
        else:
            # Default wait
            await asyncio.sleep(1)
        
        result["status"] = "passed"
    
    async def _execute_verify(self, step: JourneyStep, driver: webdriver.Chrome,
                            context: Dict[str, Any], result: Dict[str, Any]):
        """Execute verification step"""
        if not step.expected_outcome:
            raise ValueError("Verify step requires expected_outcome")
        
        verification_results = {}
        
        for check_type, expected_value in step.expected_outcome.items():
            if check_type == "url_contains":
                actual = driver.current_url
                verification_results[check_type] = expected_value in actual
            elif check_type == "title_equals":
                actual = driver.title
                verification_results[check_type] = actual == expected_value
            elif check_type == "element_text":
                element = driver.find_element(By.CSS_SELECTOR, step.selector)
                actual = element.text
                verification_results[check_type] = actual == expected_value
            elif check_type == "element_visible":
                try:
                    element = driver.find_element(By.CSS_SELECTOR, step.selector)
                    verification_results[check_type] = element.is_displayed()
                except:
                    verification_results[check_type] = False
            elif check_type == "page_source_contains":
                verification_results[check_type] = expected_value in driver.page_source
        
        # All verifications must pass
        if all(verification_results.values()):
            result["status"] = "passed"
        else:
            result["status"] = "failed"
            result["error"] = f"Verification failed: {verification_results}"
        
        result["data"]["verifications"] = verification_results
    
    async def _execute_api_call(self, step: JourneyStep, context: Dict[str, Any],
                              result: Dict[str, Any]):
        """Execute API call step"""
        if not step.api_endpoint:
            raise ValueError("API call step requires api_endpoint")
        
        method = step.input_data.get("method", "GET") if step.input_data else "GET"
        data = step.input_data.get("data", {}) if step.input_data else {}
        
        # Replace context variables in data
        data_str = json.dumps(data)
        for key, value in context.items():
            data_str = data_str.replace(f"{{{key}}}", str(value))
        data = json.loads(data_str)
        
        api_result = self.api_client.make_request(method, step.api_endpoint, json=data)
        
        if 200 <= api_result.get("status_code", 0) < 300:
            result["status"] = "passed"
        else:
            result["status"] = "failed"
            result["error"] = f"API call failed: {api_result.get('error', 'Unknown error')}"
        
        result["data"]["api_response"] = api_result
        
        # Store response data in context for later steps
        if isinstance(api_result.get("data"), dict):
            context.update(api_result["data"])
    
    async def _execute_scroll(self, step: JourneyStep, driver: webdriver.Chrome,
                            context: Dict[str, Any], result: Dict[str, Any]):
        """Execute scroll step"""
        if step.selector:
            element = driver.find_element(By.CSS_SELECTOR, step.selector)
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
        else:
            # Scroll by pixels
            x = step.input_data.get("x", 0) if step.input_data else 0
            y = step.input_data.get("y", 300) if step.input_data else 300
            driver.execute_script(f"window.scrollBy({x}, {y});")
        
        result["status"] = "passed"
    
    async def _execute_hover(self, step: JourneyStep, driver: webdriver.Chrome,
                           context: Dict[str, Any], result: Dict[str, Any]):
        """Execute hover step"""
        if not step.selector:
            raise ValueError("Hover step requires selector")
        
        element = driver.find_element(By.CSS_SELECTOR, step.selector)
        ActionChains(driver).move_to_element(element).perform()
        result["status"] = "passed"
    
    async def _execute_select(self, step: JourneyStep, driver: webdriver.Chrome,
                            context: Dict[str, Any], result: Dict[str, Any]):
        """Execute select dropdown step"""
        from selenium.webdriver.support.ui import Select
        
        if not step.selector or not step.input_data:
            raise ValueError("Select step requires selector and input_data")
        
        select_element = Select(driver.find_element(By.CSS_SELECTOR, step.selector))
        
        if "value" in step.input_data:
            select_element.select_by_value(step.input_data["value"])
        elif "text" in step.input_data:
            select_element.select_by_visible_text(step.input_data["text"])
        elif "index" in step.input_data:
            select_element.select_by_index(step.input_data["index"])
        
        result["status"] = "passed"
    
    async def _execute_upload(self, step: JourneyStep, driver: webdriver.Chrome,
                            context: Dict[str, Any], result: Dict[str, Any]):
        """Execute file upload step"""
        if not step.selector or not step.input_data:
            raise ValueError("Upload step requires selector and input_data")
        
        file_path = step.input_data.get("file_path")
        if not file_path:
            raise ValueError("Upload step requires file_path in input_data")
        
        element = driver.find_element(By.CSS_SELECTOR, step.selector)
        element.send_keys(file_path)
        result["status"] = "passed"
    
    async def _validate_step_results(self, step: JourneyStep, driver: webdriver.Chrome,
                                   result: Dict[str, Any]):
        """Validate step results against validation rules"""
        for rule in step.validation_rules:
            rule_type = rule.get("type")
            
            if rule_type == "response_time":
                max_time = rule.get("max_seconds", 5.0)
                if result["execution_time"] > max_time:
                    result["status"] = "failed"
                    result["error"] = f"Step took {result['execution_time']:.2f}s, max allowed: {max_time}s"
            
            elif rule_type == "memory_usage":
                # Check memory usage (simplified)
                memory_info = driver.execute_script("return performance.memory;")
                if memory_info and memory_info.get("usedJSHeapSize", 0) > rule.get("max_mb", 100) * 1024 * 1024:
                    result["status"] = "failed"
                    result["error"] = "Memory usage exceeded limit"


class JourneyTestEngine:
    """Main engine for executing user journey tests"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.driver_manager = WebDriverManager()
        self.api_clients: Dict[str, APITestClient] = {}
        self.journeys: Dict[str, UserJourney] = {}
        self.executions: Dict[str, JourneyExecution] = {}
        
        # Initialize API clients for different services
        for service_name, base_url in config.get("services", {}).items():
            self.api_clients[service_name] = APITestClient(base_url)
    
    def register_journey(self, journey: UserJourney):
        """Register a user journey for testing"""
        self.journeys[journey.journey_id] = journey
    
    async def execute_journey(self, journey_id: str, context: Optional[Dict[str, Any]] = None) -> JourneyExecution:
        """Execute a specific user journey"""
        if journey_id not in self.journeys:
            raise ValueError(f"Journey not found: {journey_id}")
        
        journey = self.journeys[journey_id]
        execution_id = f"{journey_id}_{int(time.time())}"
        
        execution = JourneyExecution(
            journey_id=journey_id,
            execution_id=execution_id,
            start_time=datetime.now(),
            environment_info={
                "environment": journey.environment.value,
                "persona": journey.persona.value,
                "browser": "chrome",
                "platform": "linux"
            }
        )
        
        self.executions[execution_id] = execution
        
        # Initialize context
        test_context = context or {}
        test_context.update({
            "execution_id": execution_id,
            "journey_id": journey_id,
            "start_time": execution.start_time.isoformat()
        })
        
        try:
            # Get web driver
            driver = self.driver_manager.get_driver(
                mobile=journey.persona == UserPersona.MOBILE_FIRST_USER
            )
            
            # Get API client
            api_client = self.api_clients.get("main", list(self.api_clients.values())[0])
            
            # Initialize step executor
            step_executor = JourneyStepExecutor(self.driver_manager, api_client)
            
            # Execute journey steps
            for step in journey.steps:
                step_result = await step_executor.execute_step(step, driver, test_context)
                execution.steps_executed.append(step_result)
                
                if step_result["status"] == "failed" and not step.optional:
                    execution.status = "failed"
                    execution.errors.append({
                        "step_id": step.step_id,
                        "error": step_result.get("error", "Unknown error"),
                        "timestamp": datetime.now().isoformat()
                    })
                    break
                
                # Brief pause between steps
                await asyncio.sleep(0.5)
            
            # Execute cleanup steps if needed
            if journey.cleanup_steps:
                for step in journey.cleanup_steps:
                    try:
                        await step_executor.execute_step(step, driver, test_context)
                    except Exception as e:
                        logging.warning(f"Cleanup step failed: {step.step_id} - {e}")
            
            # Calculate performance metrics
            execution.performance_metrics = self._calculate_performance_metrics(execution)
            
            # Determine overall status
            if execution.status != "failed":
                execution.status = "passed"
            
        except Exception as e:
            execution.status = "failed"
            execution.errors.append({
                "step_id": "general",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            logging.error(f"Journey execution failed: {journey_id} - {e}")
        
        finally:
            execution.end_time = datetime.now()
        
        return execution
    
    async def execute_journey_batch(self, journey_ids: List[str], 
                                  parallel: bool = False) -> List[JourneyExecution]:
        """Execute multiple journeys"""
        if parallel:
            tasks = [self.execute_journey(journey_id) for journey_id in journey_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            executions = []
            for result in results:
                if isinstance(result, Exception):
                    logging.error(f"Journey execution failed: {result}")
                else:
                    executions.append(result)
            
            return executions
        else:
            executions = []
            for journey_id in journey_ids:
                execution = await self.execute_journey(journey_id)
                executions.append(execution)
                
                # Brief pause between sequential journeys
                await asyncio.sleep(2)
            
            return executions
    
    def _calculate_performance_metrics(self, execution: JourneyExecution) -> Dict[str, float]:
        """Calculate performance metrics for journey execution"""
        total_time = (execution.end_time - execution.start_time).total_seconds()
        step_times = [step.get("execution_time", 0) for step in execution.steps_executed]
        
        return {
            "total_execution_time": total_time,
            "average_step_time": sum(step_times) / len(step_times) if step_times else 0,
            "max_step_time": max(step_times) if step_times else 0,
            "min_step_time": min(step_times) if step_times else 0,
            "successful_steps": len([s for s in execution.steps_executed if s["status"] == "passed"]),
            "failed_steps": len([s for s in execution.steps_executed if s["status"] == "failed"]),
            "success_rate": len([s for s in execution.steps_executed if s["status"] == "passed"]) / len(execution.steps_executed) * 100 if execution.steps_executed else 0
        }
    
    def generate_report(self, execution_ids: List[str]) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        executions = [self.executions[exec_id] for exec_id in execution_ids if exec_id in self.executions]
        
        if not executions:
            return {"error": "No executions found"}
        
        # Calculate summary statistics
        total_journeys = len(executions)
        passed_journeys = len([e for e in executions if e.status == "passed"])
        failed_journeys = len([e for e in executions if e.status == "failed"])
        
        total_time = sum((e.end_time - e.start_time).total_seconds() for e in executions if e.end_time)
        avg_time = total_time / len(executions) if executions else 0
        
        # Group by journey type
        journey_types = {}
        for execution in executions:
            journey = self.journeys.get(execution.journey_id)
            if journey:
                journey_type = journey.journey_type.value
                if journey_type not in journey_types:
                    journey_types[journey_type] = {"passed": 0, "failed": 0, "total": 0}
                
                journey_types[journey_type]["total"] += 1
                if execution.status == "passed":
                    journey_types[journey_type]["passed"] += 1
                else:
                    journey_types[journey_type]["failed"] += 1
        
        # Most common errors
        error_counts = {}
        for execution in executions:
            for error in execution.errors:
                error_msg = error.get("error", "Unknown error")
                error_counts[error_msg] = error_counts.get(error_msg, 0) + 1
        
        return {
            "summary": {
                "total_journeys": total_journeys,
                "passed_journeys": passed_journeys,
                "failed_journeys": failed_journeys,
                "success_rate": (passed_journeys / total_journeys) * 100 if total_journeys > 0 else 0,
                "total_execution_time": total_time,
                "average_execution_time": avg_time
            },
            "journey_types": journey_types,
            "common_errors": dict(sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "executions": [
                {
                    "execution_id": e.execution_id,
                    "journey_id": e.journey_id,
                    "status": e.status,
                    "duration": (e.end_time - e.start_time).total_seconds() if e.end_time else 0,
                    "steps_count": len(e.steps_executed),
                    "errors_count": len(e.errors)
                }
                for e in executions
            ],
            "generated_at": datetime.now().isoformat()
        }
    
    def cleanup(self):
        """Cleanup resources"""
        self.driver_manager.cleanup()
        for client in self.api_clients.values():
            if hasattr(client.session, 'close'):
                client.session.close()


# Pre-built journey definitions for ActiveLog platform
def create_default_journeys(engine: JourneyTestEngine):
    """Create default user journeys for testing"""
    
    # New User Onboarding Journey
    onboarding_journey = UserJourney(
        journey_id="new_user_onboarding",
        name="New User Onboarding",
        description="Complete onboarding flow for new user",
        journey_type=JourneyType.NEW_USER_ONBOARDING,
        persona=UserPersona.CASUAL_USER,
        environment=TestEnvironment.LOCAL,
        steps=[
            JourneyStep("navigate_home", "Navigate to home page", "navigate", 
                       selector="http://localhost:3000", screenshot=True),
            JourneyStep("click_signup", "Click sign up button", "click",
                       selector="button[data-testid='signup-btn']"),
            JourneyStep("enter_email", "Enter email address", "type",
                       selector="input[name='email']", 
                       input_data={"text": "testuser{timestamp}@example.com"}),
            JourneyStep("enter_password", "Enter password", "type",
                       selector="input[name='password']",
                       input_data={"text": "TestPassword123!"}),
            JourneyStep("click_create_account", "Click create account", "click",
                       selector="button[type='submit']"),
            JourneyStep("verify_welcome", "Verify welcome message", "verify",
                       expected_outcome={"element_visible": "div[data-testid='welcome-message']"}),
            JourneyStep("complete_profile", "Complete profile setup", "click",
                       selector="button[data-testid='complete-profile']"),
            JourneyStep("enter_name", "Enter full name", "type",
                       selector="input[name='fullName']",
                       input_data={"text": "Test User"}),
            JourneyStep("select_role", "Select user role", "select",
                       selector="select[name='role']",
                       input_data={"text": "Individual"}),
            JourneyStep("finish_onboarding", "Finish onboarding", "click",
                       selector="button[data-testid='finish-onboarding']"),
            JourneyStep("verify_dashboard", "Verify dashboard loaded", "verify",
                       expected_outcome={
                           "url_contains": "/dashboard",
                           "element_visible": "div[data-testid='dashboard']"
                       }, screenshot=True)
        ]
    )
    
    # Content Creation Journey
    content_creation_journey = UserJourney(
        journey_id="content_creation",
        name="Content Creation Flow",
        description="Create and publish content",
        journey_type=JourneyType.CONTENT_CREATION,
        persona=UserPersona.TECH_SAVVY_PROFESSIONAL,
        environment=TestEnvironment.LOCAL,
        steps=[
            JourneyStep("navigate_dashboard", "Navigate to dashboard", "navigate",
                       selector="http://localhost:3000/dashboard"),
            JourneyStep("click_create_content", "Click create content", "click",
                       selector="button[data-testid='create-content']"),
            JourneyStep("select_content_type", "Select blog post", "click",
                       selector="div[data-testid='content-type-blog']"),
            JourneyStep("enter_title", "Enter content title", "type",
                       selector="input[name='title']",
                       input_data={"text": "Test Blog Post {timestamp}"}),
            JourneyStep("enter_content", "Enter content body", "type",
                       selector="textarea[name='content']",
                       input_data={"text": "This is a test blog post created during automated testing."}),
            JourneyStep("add_tags", "Add tags", "type",
                       selector="input[name='tags']",
                       input_data={"text": "test, automation, blog"}),
            JourneyStep("save_draft", "Save as draft", "click",
                       selector="button[data-testid='save-draft']"),
            JourneyStep("verify_draft_saved", "Verify draft saved", "verify",
                       expected_outcome={"element_visible": "div[data-testid='draft-saved-message']"}),
            JourneyStep("publish_content", "Publish content", "click",
                       selector="button[data-testid='publish']"),
            JourneyStep("verify_published", "Verify content published", "verify",
                       expected_outcome={
                           "url_contains": "/content/",
                           "element_visible": "div[data-testid='published-content']"
                       }, screenshot=True)
        ]
    )
    
    # Tutorial Completion Journey
    tutorial_journey = UserJourney(
        journey_id="tutorial_completion",
        name="Complete Interactive Tutorial",
        description="Complete tutorial from interactive tutorials service",
        journey_type=JourneyType.TUTORIAL_COMPLETION,
        persona=UserPersona.STUDENT,
        environment=TestEnvironment.LOCAL,
        steps=[
            JourneyStep("navigate_tutorials", "Navigate to tutorials", "navigate",
                       selector="http://localhost:8216/dashboard"),
            JourneyStep("select_beginner_tutorial", "Select beginner tutorial", "click",
                       selector="div[data-testid='tutorial-beginner-tech']"),
            JourneyStep("start_tutorial", "Start tutorial", "click",
                       selector="button[data-testid='start-tutorial']"),
            JourneyStep("complete_step_1", "Complete first step", "click",
                       selector="button[data-testid='complete-step-1']"),
            JourneyStep("verify_progress", "Verify progress updated", "verify",
                       expected_outcome={"element_visible": "div[data-testid='progress-bar']"}),
            JourneyStep("complete_step_2", "Complete second step", "click",
                       selector="button[data-testid='complete-step-2']"),
            JourneyStep("complete_step_3", "Complete third step", "click",
                       selector="button[data-testid='complete-step-3']"),
            JourneyStep("verify_completion", "Verify tutorial completed", "verify",
                       expected_outcome={
                           "element_visible": "div[data-testid='tutorial-complete']",
                           "element_text": "Congratulations!"
                       }, screenshot=True),
            JourneyStep("view_certificate", "View completion certificate", "click",
                       selector="button[data-testid='view-certificate']"),
            JourneyStep("verify_certificate", "Verify certificate displayed", "verify",
                       expected_outcome={"element_visible": "div[data-testid='completion-certificate']"})
        ]
    )
    
    # Mobile App Journey
    mobile_journey = UserJourney(
        journey_id="mobile_app_usage",
        name="Mobile App Usage",
        description="Test mobile app functionality",
        journey_type=JourneyType.MOBILE_APP_USAGE,
        persona=UserPersona.MOBILE_FIRST_USER,
        environment=TestEnvironment.MOBILE_SIMULATOR,
        steps=[
            JourneyStep("navigate_mobile_home", "Navigate to mobile home", "navigate",
                       selector="http://localhost:3000/mobile", screenshot=True),
            JourneyStep("tap_menu", "Tap mobile menu", "click",
                       selector="button[data-testid='mobile-menu']"),
            JourneyStep("tap_dashboard", "Tap dashboard link", "click",
                       selector="a[data-testid='mobile-dashboard-link']"),
            JourneyStep("verify_mobile_dashboard", "Verify mobile dashboard", "verify",
                       expected_outcome={"element_visible": "div[data-testid='mobile-dashboard']"}),
            JourneyStep("swipe_content", "Swipe through content", "scroll",
                       input_data={"y": 300}),
            JourneyStep("tap_content_item", "Tap content item", "click",
                       selector="div[data-testid='content-item-mobile']:first-child"),
            JourneyStep("verify_content_view", "Verify content view", "verify",
                       expected_outcome={"element_visible": "div[data-testid='content-mobile-view']"},
                       screenshot=True)
        ]
    )
    
    # Register all journeys
    engine.register_journey(onboarding_journey)
    engine.register_journey(content_creation_journey)
    engine.register_journey(tutorial_journey)
    engine.register_journey(mobile_journey)


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    # Configuration
    config = {
        "services": {
            "main": "http://localhost:3000",
            "tutorials": "http://localhost:8216",
            "api": "http://localhost:8000"
        }
    }
    
    # Initialize test engine
    engine = JourneyTestEngine(config)
    
    # Create default journeys
    create_default_journeys(engine)
    
    async def run_tests():
        try:
            print("Starting user journey tests...")
            
            # Execute single journey
            execution = await engine.execute_journey("new_user_onboarding", {
                "timestamp": int(time.time())
            })
            
            print(f"Journey {execution.journey_id} completed with status: {execution.status}")
            print(f"Execution time: {(execution.end_time - execution.start_time).total_seconds():.2f}s")
            
            if execution.errors:
                print("Errors encountered:")
                for error in execution.errors:
                    print(f"  - {error['step_id']}: {error['error']}")
            
            # Generate report
            report = engine.generate_report([execution.execution_id])
            print(f"\nTest Report:")
            print(f"Success Rate: {report['summary']['success_rate']:.1f}%")
            print(f"Total Time: {report['summary']['total_execution_time']:.2f}s")
            
        finally:
            engine.cleanup()
    
    # Run the tests
    asyncio.run(run_tests())