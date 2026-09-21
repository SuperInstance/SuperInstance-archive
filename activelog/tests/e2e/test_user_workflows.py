"""
End-to-end tests using Playwright
Tests complete user workflows through the browser interface
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, BrowserContext

# Test configuration
E2E_CONFIG = {
    "base_url": "http://localhost:3000",
    "api_url": "http://localhost:8000", 
    "timeout": 30000,  # 30 seconds
    "screenshot_dir": "e2e_screenshots",
    "video_dir": "e2e_videos"
}


@pytest.fixture(scope="session")
async def browser():
    """Create browser instance for testing"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # Set to False for debugging
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        yield browser
        await browser.close()


@pytest.fixture
async def context(browser):
    """Create browser context with recording"""
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        record_video_dir=E2E_CONFIG["video_dir"],
        record_video_size={"width": 1280, "height": 720}
    )
    yield context
    await context.close()


@pytest.fixture
async def page(context):
    """Create page for testing"""
    page = await context.new_page()
    
    # Set default timeout
    page.set_default_timeout(E2E_CONFIG["timeout"])
    
    # Enable request/response logging for debugging
    async def log_request(request):
        print(f"Request: {request.method} {request.url}")
    
    async def log_response(response):
        print(f"Response: {response.status} {response.url}")
    
    page.on("request", log_request)
    page.on("response", log_response)
    
    yield page


@pytest.fixture
def test_user():
    """Generate test user data"""
    user_id = str(uuid.uuid4())
    return {
        "id": user_id,
        "email": f"e2e_test_{user_id[:8]}@example.com",
        "password": "E2ETest123!",
        "name": f"E2E Test User {user_id[:8]}"
    }


@pytest.fixture
def test_files():
    """Generate test file data"""
    return [
        {
            "name": "test_document.pdf",
            "content": "This is a test PDF document for e2e testing.",
            "type": "application/pdf",
            "size": 1024
        },
        {
            "name": "test_image.jpg", 
            "content": "fake-image-data",
            "type": "image/jpeg",
            "size": 2048
        },
        {
            "name": "test_presentation.pptx",
            "content": "Test presentation content",
            "type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "size": 4096
        }
    ]


class E2ETestHelper:
    """Helper class for E2E testing utilities"""
    
    @staticmethod
    async def wait_for_loading(page: Page):
        """Wait for loading indicators to disappear"""
        await page.wait_for_selector(".loading-placeholder", state="hidden", timeout=10000)
        await page.wait_for_selector(".spinner", state="hidden", timeout=5000)
    
    @staticmethod
    async def take_screenshot(page: Page, name: str):
        """Take screenshot for debugging"""
        screenshot_dir = Path(E2E_CONFIG["screenshot_dir"])
        screenshot_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = screenshot_dir / f"{name}_{timestamp}.png"
        
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"Screenshot saved: {screenshot_path}")
    
    @staticmethod
    async def fill_form_field(page: Page, selector: str, value: str):
        """Fill form field with proper waiting"""
        await page.wait_for_selector(selector, state="visible")
        await page.fill(selector, value)
        await page.wait_for_timeout(100)  # Small delay for form validation
    
    @staticmethod
    async def click_and_wait(page: Page, selector: str, wait_for_selector: str = None):
        """Click element and wait for navigation or specific element"""
        await page.wait_for_selector(selector, state="visible")
        
        if wait_for_selector:
            async with page.expect_response("**/api/**"):
                await page.click(selector)
            await page.wait_for_selector(wait_for_selector, state="visible")
        else:
            await page.click(selector)


@pytest.mark.e2e
class TestAuthenticationWorkflow:
    """Test user authentication workflows"""
    
    async def test_user_registration_flow(self, page: Page, test_user):
        """Test complete user registration flow"""
        
        # Navigate to app
        await page.goto(E2E_CONFIG["base_url"])
        
        # Should be redirected to auth page
        await page.wait_for_selector("h1:has-text('Welcome to ActiveLog')", timeout=10000)
        
        # Click register tab
        await page.click("button:has-text('Register')")
        await page.wait_for_selector("form#register-form", state="visible")
        
        # Fill registration form
        await E2ETestHelper.fill_form_field(page, "input[name='name']", test_user["name"])
        await E2ETestHelper.fill_form_field(page, "input[name='email']", test_user["email"])
        await E2ETestHelper.fill_form_field(page, "input[name='password']", test_user["password"])
        await E2ETestHelper.fill_form_field(page, "input[name='confirmPassword']", test_user["password"])
        
        # Submit registration
        async with page.expect_response("**/auth/register"):
            await page.click("button[type='submit']:has-text('Register')")
        
        # Should show success message
        await page.wait_for_selector(".notification.success", timeout=5000)
        success_message = await page.text_content(".notification.success")
        assert "Registration successful" in success_message
        
        # Should redirect to dashboard
        await page.wait_for_url("**/dashboard", timeout=10000)
        await page.wait_for_selector("h1:has-text('Dashboard')", state="visible")
        
        await E2ETestHelper.take_screenshot(page, "registration_success")
    
    async def test_user_login_flow(self, page: Page, test_user):
        """Test user login flow"""
        
        # Navigate to app
        await page.goto(E2E_CONFIG["base_url"])
        
        # Fill login form
        await page.wait_for_selector("form#login-form", state="visible")
        await E2ETestHelper.fill_form_field(page, "input[name='email']", test_user["email"])
        await E2ETestHelper.fill_form_field(page, "input[name='password']", test_user["password"])
        
        # Submit login
        async with page.expect_response("**/auth/login"):
            await page.click("button[type='submit']:has-text('Login')")
        
        # Should redirect to dashboard
        await page.wait_for_url("**/dashboard", timeout=10000)
        await page.wait_for_selector("h1:has-text('Dashboard')", state="visible")
        
        # Verify user is logged in
        await page.wait_for_selector(".user-menu", state="visible")
        user_name = await page.text_content(".user-menu .user-name")
        assert test_user["name"] in user_name
        
        await E2ETestHelper.take_screenshot(page, "login_success")
    
    async def test_logout_flow(self, page: Page, test_user):
        """Test user logout flow"""
        
        # First login
        await self.test_user_login_flow(page, test_user)
        
        # Open user menu
        await page.click(".user-menu")
        await page.wait_for_selector(".user-menu-dropdown", state="visible")
        
        # Click logout
        async with page.expect_response("**/auth/logout"):
            await page.click("button:has-text('Logout')")
        
        # Should redirect to login page
        await page.wait_for_url("**/", timeout=10000)
        await page.wait_for_selector("form#login-form", state="visible")
        
        await E2ETestHelper.take_screenshot(page, "logout_success")
    
    async def test_invalid_login(self, page: Page):
        """Test login with invalid credentials"""
        
        await page.goto(E2E_CONFIG["base_url"])
        
        # Fill invalid credentials
        await E2ETestHelper.fill_form_field(page, "input[name='email']", "invalid@example.com")
        await E2ETestHelper.fill_form_field(page, "input[name='password']", "wrongpassword")
        
        # Submit login
        await page.click("button[type='submit']:has-text('Login')")
        
        # Should show error message
        await page.wait_for_selector(".notification.error", timeout=5000)
        error_message = await page.text_content(".notification.error")
        assert "Invalid credentials" in error_message
        
        await E2ETestHelper.take_screenshot(page, "invalid_login")


@pytest.mark.e2e
class TestFileManagementWorkflow:
    """Test file management workflows"""
    
    async def setup_authenticated_user(self, page: Page, test_user):
        """Helper to login user before file operations"""
        await page.goto(E2E_CONFIG["base_url"])
        await E2ETestHelper.fill_form_field(page, "input[name='email']", test_user["email"])
        await E2ETestHelper.fill_form_field(page, "input[name='password']", test_user["password"])
        
        async with page.expect_response("**/auth/login"):
            await page.click("button[type='submit']:has-text('Login')")
        
        await page.wait_for_url("**/dashboard", timeout=10000)
    
    async def test_file_upload_flow(self, page: Page, test_user, test_files):
        """Test file upload workflow"""
        
        await self.setup_authenticated_user(page, test_user)
        
        # Navigate to files section
        await page.click("nav a:has-text('Files')")
        await page.wait_for_url("**/files", timeout=10000)
        
        # Open upload dialog
        await page.click("button:has-text('Upload Files')")
        await page.wait_for_selector(".upload-modal", state="visible")
        
        # Create temporary test file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test file for e2e testing")
            temp_file_path = f.name
        
        try:
            # Upload file
            await page.set_input_files("input[type='file']", temp_file_path)
            
            # Wait for upload progress
            await page.wait_for_selector(".upload-progress", state="visible")
            await page.wait_for_selector(".upload-progress", state="hidden", timeout=15000)
            
            # Should show success notification
            await page.wait_for_selector(".notification.success", timeout=5000)
            
            # File should appear in file list
            await page.wait_for_selector(f".file-item:has-text('{Path(temp_file_path).name}')", timeout=10000)
            
            await E2ETestHelper.take_screenshot(page, "file_upload_success")
            
        finally:
            # Clean up temp file
            Path(temp_file_path).unlink(missing_ok=True)
    
    async def test_file_search_flow(self, page: Page, test_user):
        """Test file search workflow"""
        
        await self.setup_authenticated_user(page, test_user)
        
        # Navigate to search
        await page.click("nav a:has-text('Search')")
        await page.wait_for_url("**/search", timeout=10000)
        
        # Perform search
        search_query = "test document"
        await E2ETestHelper.fill_form_field(page, "input[name='search']", search_query)
        
        async with page.expect_response("**/metadata/search"):
            await page.click("button:has-text('Search')")
        
        # Wait for results
        await E2ETestHelper.wait_for_loading(page)
        
        # Should show search results
        await page.wait_for_selector(".search-results", state="visible")
        
        # Check if results are displayed
        results_count = await page.locator(".search-result-item").count()
        print(f"Found {results_count} search results")
        
        await E2ETestHelper.take_screenshot(page, "search_results")
    
    async def test_file_details_view(self, page: Page, test_user):
        """Test viewing file details"""
        
        await self.setup_authenticated_user(page, test_user)
        
        # Navigate to files
        await page.click("nav a:has-text('Files')")
        await page.wait_for_url("**/files", timeout=10000)
        
        # Wait for files to load
        await E2ETestHelper.wait_for_loading(page)
        
        # Click on first file if available
        first_file = page.locator(".file-item").first
        if await first_file.count() > 0:
            await first_file.click()
            
            # Should open file details modal
            await page.wait_for_selector(".file-viewer-modal", state="visible")
            
            # Verify file details are shown
            await page.wait_for_selector(".file-viewer-title", state="visible")
            await page.wait_for_selector(".file-meta", state="visible")
            
            # Close modal
            await page.click(".modal-close")
            await page.wait_for_selector(".file-viewer-modal", state="hidden")
            
            await E2ETestHelper.take_screenshot(page, "file_details_view")
    
    async def test_file_organization_flow(self, page: Page, test_user):
        """Test file organization with tags"""
        
        await self.setup_authenticated_user(page, test_user)
        
        # Navigate to files
        await page.click("nav a:has-text('Files')")
        await page.wait_for_url("**/files", timeout=10000)
        
        # Wait for files to load
        await E2ETestHelper.wait_for_loading(page)
        
        # Select a file and add tags
        first_file = page.locator(".file-item").first
        if await first_file.count() > 0:
            # Right-click for context menu
            await first_file.click(button="right")
            await page.wait_for_selector(".context-menu", state="visible")
            
            # Click "Edit Tags"
            await page.click(".context-menu button:has-text('Edit Tags')")
            await page.wait_for_selector(".tag-editor-modal", state="visible")
            
            # Add new tag
            await E2ETestHelper.fill_form_field(page, "input[name='tagName']", "e2e-test")
            await page.click("button:has-text('Add Tag')")
            
            # Save changes
            await page.click("button:has-text('Save')")
            await page.wait_for_selector(".tag-editor-modal", state="hidden")
            
            # Verify tag was added
            await page.wait_for_selector(".file-tag:has-text('e2e-test')", timeout=5000)
            
            await E2ETestHelper.take_screenshot(page, "file_tags_added")


@pytest.mark.e2e
class TestDashboardWorkflow:
    """Test dashboard and analytics workflows"""
    
    async def test_dashboard_overview(self, page: Page, test_user):
        """Test dashboard overview display"""
        
        # Login
        await page.goto(E2E_CONFIG["base_url"])
        await E2ETestHelper.fill_form_field(page, "input[name='email']", test_user["email"])
        await E2ETestHelper.fill_form_field(page, "input[name='password']", test_user["password"])
        
        async with page.expect_response("**/auth/login"):
            await page.click("button[type='submit']:has-text('Login')")
        
        await page.wait_for_url("**/dashboard", timeout=10000)
        
        # Wait for dashboard to load
        await E2ETestHelper.wait_for_loading(page)
        
        # Verify dashboard components
        await page.wait_for_selector(".dashboard-stats", state="visible")
        await page.wait_for_selector(".recent-files", state="visible")
        await page.wait_for_selector(".activity-feed", state="visible")
        
        # Check stats cards
        stats_cards = await page.locator(".stat-card").count()
        assert stats_cards >= 3  # Should have at least 3 stat cards
        
        await E2ETestHelper.take_screenshot(page, "dashboard_overview")
    
    async def test_analytics_charts(self, page: Page, test_user):
        """Test analytics charts display"""
        
        # Setup authenticated user
        await page.goto(E2E_CONFIG["base_url"])
        await E2ETestHelper.fill_form_field(page, "input[name='email']", test_user["email"])
        await E2ETestHelper.fill_form_field(page, "input[name='password']", test_user["password"])
        
        async with page.expect_response("**/auth/login"):
            await page.click("button[type='submit']:has-text('Login')")
        
        await page.wait_for_url("**/dashboard", timeout=10000)
        
        # Navigate to analytics
        await page.click("nav a:has-text('Analytics')")
        await page.wait_for_url("**/analytics", timeout=10000)
        
        # Wait for charts to load
        await E2ETestHelper.wait_for_loading(page)
        
        # Verify chart components
        await page.wait_for_selector(".analytics-chart", state="visible")
        
        # Should have multiple charts
        chart_count = await page.locator(".analytics-chart").count()
        assert chart_count >= 2
        
        await E2ETestHelper.take_screenshot(page, "analytics_charts")


@pytest.mark.e2e
class TestSemanticSearchWorkflow:
    """Test semantic search functionality"""
    
    async def test_semantic_search_flow(self, page: Page, test_user):
        """Test semantic search workflow"""
        
        # Login
        await page.goto(E2E_CONFIG["base_url"])
        await E2ETestHelper.fill_form_field(page, "input[name='email']", test_user["email"])
        await E2ETestHelper.fill_form_field(page, "input[name='password']", test_user["password"])
        
        async with page.expect_response("**/auth/login"):
            await page.click("button[type='submit']:has-text('Login')")
        
        await page.wait_for_url("**/dashboard", timeout=10000)
        
        # Navigate to semantic search
        await page.click("nav a:has-text('Search')")
        await page.wait_for_url("**/search", timeout=10000)
        
        # Switch to semantic search tab
        await page.click("button:has-text('Semantic Search')")
        await page.wait_for_selector(".semantic-search-panel", state="visible")
        
        # Perform semantic search
        search_query = "machine learning algorithms and data science"
        await E2ETestHelper.fill_form_field(page, "input[name='semanticQuery']", search_query)
        
        # Adjust similarity threshold
        await page.locator("input[name='similarityThreshold']").fill("0.7")
        
        # Execute search
        async with page.expect_response("**/ai/semantic-search"):
            await page.click("button:has-text('Search')")
        
        # Wait for results
        await E2ETestHelper.wait_for_loading(page)
        
        # Verify semantic search results
        await page.wait_for_selector(".semantic-results", state="visible")
        
        # Check for similarity scores
        await page.wait_for_selector(".similarity-score", state="visible")
        
        await E2ETestHelper.take_screenshot(page, "semantic_search_results")
    
    async def test_visual_similarity_search(self, page: Page, test_user):
        """Test visual similarity search"""
        
        # Setup authenticated user
        await page.goto(E2E_CONFIG["base_url"])
        await E2ETestHelper.fill_form_field(page, "input[name='email']", test_user["email"])
        await E2ETestHelper.fill_form_field(page, "input[name='password']", test_user["password"])
        
        async with page.expect_response("**/auth/login"):
            await page.click("button[type='submit']:has-text('Login')")
        
        await page.wait_for_url("**/dashboard", timeout=10000)
        
        # Navigate to search
        await page.click("nav a:has-text('Search')")
        await page.wait_for_url("**/search", timeout=10000)
        
        # Switch to visual similarity tab
        await page.click("button:has-text('Visual Similarity')")
        await page.wait_for_selector(".visual-similarity-panel", state="visible")
        
        # Create a small test image
        import tempfile
        from PIL import Image
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            # Create a simple test image
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(f.name, 'PNG')
            temp_image_path = f.name
        
        try:
            # Upload image for similarity search
            await page.set_input_files("input[type='file'][accept='image/*']", temp_image_path)
            
            # Wait for image preview
            await page.wait_for_selector(".image-preview", state="visible")
            
            # Execute visual search
            async with page.expect_response("**/ai/visual-search"):
                await page.click("button:has-text('Find Similar')")
            
            # Wait for results
            await E2ETestHelper.wait_for_loading(page)
            
            await E2ETestHelper.take_screenshot(page, "visual_similarity_search")
            
        finally:
            # Clean up temp file
            Path(temp_image_path).unlink(missing_ok=True)


@pytest.mark.e2e
class TestSettingsWorkflow:
    """Test settings and preferences workflows"""
    
    async def test_user_settings_flow(self, page: Page, test_user):
        """Test user settings modification"""
        
        # Login
        await page.goto(E2E_CONFIG["base_url"])
        await E2ETestHelper.fill_form_field(page, "input[name='email']", test_user["email"])
        await E2ETestHelper.fill_form_field(page, "input[name='password']", test_user["password"])
        
        async with page.expect_response("**/auth/login"):
            await page.click("button[type='submit']:has-text('Login')")
        
        await page.wait_for_url("**/dashboard", timeout=10000)
        
        # Navigate to settings
        await page.click(".user-menu")
        await page.wait_for_selector(".user-menu-dropdown", state="visible")
        await page.click("a:has-text('Settings')")
        await page.wait_for_url("**/settings", timeout=10000)
        
        # Update user profile
        await E2ETestHelper.fill_form_field(page, "input[name='name']", f"{test_user['name']} Updated")
        
        # Save changes
        async with page.expect_response("**/auth/profile"):
            await page.click("button:has-text('Save Profile')")
        
        # Should show success notification
        await page.wait_for_selector(".notification.success", timeout=5000)
        
        await E2ETestHelper.take_screenshot(page, "settings_updated")
    
    async def test_sync_settings_flow(self, page: Page, test_user):
        """Test sync settings configuration"""
        
        # Setup authenticated user
        await page.goto(E2E_CONFIG["base_url"])
        await E2ETestHelper.fill_form_field(page, "input[name='email']", test_user["email"])
        await E2ETestHelper.fill_form_field(page, "input[name='password']", test_user["password"])
        
        async with page.expect_response("**/auth/login"):
            await page.click("button[type='submit']:has-text('Login')")
        
        await page.wait_for_url("**/dashboard", timeout=10000)
        
        # Navigate to settings
        await page.click(".user-menu")
        await page.wait_for_selector(".user-menu-dropdown", state="visible")
        await page.click("a:has-text('Settings')")
        await page.wait_for_url("**/settings", timeout=10000)
        
        # Switch to sync settings tab
        await page.click("button:has-text('Sync Settings')")
        await page.wait_for_selector(".sync-settings-panel", state="visible")
        
        # Configure sync rules
        await page.check("input[name='autoSync']")
        await page.select_option("select[name='syncFrequency']", "hourly")
        
        # Save sync settings
        async with page.expect_response("**/settings/sync"):
            await page.click("button:has-text('Save Sync Settings')")
        
        # Should show success notification
        await page.wait_for_selector(".notification.success", timeout=5000)
        
        await E2ETestHelper.take_screenshot(page, "sync_settings_updated")


@pytest.mark.e2e
class TestResponsivenessAndAccessibility:
    """Test responsive design and accessibility"""
    
    async def test_mobile_responsiveness(self, browser, test_user):
        """Test mobile responsive design"""
        
        # Create mobile context
        mobile_context = await browser.new_context(
            viewport={"width": 375, "height": 667},  # iPhone SE size
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        )
        
        try:
            page = await mobile_context.new_page()
            
            # Navigate to app
            await page.goto(E2E_CONFIG["base_url"])
            
            # Should have mobile navigation
            await page.wait_for_selector(".mobile-nav-toggle", state="visible")
            
            # Login on mobile
            await E2ETestHelper.fill_form_field(page, "input[name='email']", test_user["email"])
            await E2ETestHelper.fill_form_field(page, "input[name='password']", test_user["password"])
            
            await page.click("button[type='submit']:has-text('Login')")
            await page.wait_for_url("**/dashboard", timeout=10000)
            
            # Test mobile navigation
            await page.click(".mobile-nav-toggle")
            await page.wait_for_selector(".mobile-nav-menu", state="visible")
            
            # Navigate to files
            await page.click(".mobile-nav-menu a:has-text('Files')")
            await page.wait_for_url("**/files", timeout=10000)
            
            # Verify mobile layout
            await page.wait_for_selector(".file-grid.mobile-layout", state="visible")
            
            await E2ETestHelper.take_screenshot(page, "mobile_responsive")
            
        finally:
            await mobile_context.close()
    
    async def test_keyboard_navigation(self, page: Page, test_user):
        """Test keyboard navigation accessibility"""
        
        # Navigate to app
        await page.goto(E2E_CONFIG["base_url"])
        
        # Use Tab to navigate through login form
        await page.keyboard.press("Tab")  # Focus email field
        await page.keyboard.type(test_user["email"])
        
        await page.keyboard.press("Tab")  # Focus password field
        await page.keyboard.type(test_user["password"])
        
        await page.keyboard.press("Tab")  # Focus login button
        await page.keyboard.press("Enter")  # Submit form
        
        await page.wait_for_url("**/dashboard", timeout=10000)
        
        # Test navigation with keyboard
        await page.keyboard.press("Tab")  # Navigate through dashboard
        await page.keyboard.press("Tab")
        await page.keyboard.press("Tab")
        
        await E2ETestHelper.take_screenshot(page, "keyboard_navigation")
    
    async def test_screen_reader_compatibility(self, page: Page):
        """Test screen reader accessibility features"""
        
        await page.goto(E2E_CONFIG["base_url"])
        
        # Check for proper ARIA labels
        email_input = page.locator("input[name='email']")
        await expect(email_input).to_have_attribute("aria-label")
        
        password_input = page.locator("input[name='password']")
        await expect(password_input).to_have_attribute("aria-label")
        
        # Check for proper heading structure
        main_heading = page.locator("h1")
        await expect(main_heading).to_be_visible()
        
        # Check for landmark roles
        main_content = page.locator("main")
        await expect(main_content).to_have_attribute("role", "main")
        
        await E2ETestHelper.take_screenshot(page, "accessibility_check")


@pytest.mark.e2e
class TestErrorHandling:
    """Test error handling and edge cases"""
    
    async def test_network_error_handling(self, page: Page, test_user):
        """Test handling of network errors"""
        
        # Setup authenticated user
        await page.goto(E2E_CONFIG["base_url"])
        await E2ETestHelper.fill_form_field(page, "input[name='email']", test_user["email"])
        await E2ETestHelper.fill_form_field(page, "input[name='password']", test_user["password"])
        
        await page.click("button[type='submit']:has-text('Login')")
        await page.wait_for_url("**/dashboard", timeout=10000)
        
        # Simulate network failure by blocking API requests
        await page.route("**/api/**", lambda route: route.abort())
        
        # Try to perform an action that requires API call
        await page.click("nav a:has-text('Files')")
        
        # Should show error message
        await page.wait_for_selector(".error-message", timeout=10000)
        error_text = await page.text_content(".error-message")
        assert "connection" in error_text.lower() or "error" in error_text.lower()
        
        await E2ETestHelper.take_screenshot(page, "network_error")
    
    async def test_large_file_upload_handling(self, page: Page, test_user):
        """Test handling of large file uploads"""
        
        # Setup authenticated user
        await page.goto(E2E_CONFIG["base_url"])
        await E2ETestHelper.fill_form_field(page, "input[name='email']", test_user["email"])
        await E2ETestHelper.fill_form_field(page, "input[name='password']", test_user["password"])
        
        await page.click("button[type='submit']:has-text('Login')")
        await page.wait_for_url("**/dashboard", timeout=10000)
        
        # Navigate to files
        await page.click("nav a:has-text('Files')")
        await page.wait_for_url("**/files", timeout=10000)
        
        # Create a mock large file (simulated)
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            # Write enough content to simulate a larger file
            f.write("Large file content " * 1000)
            large_file_path = f.name
        
        try:
            # Open upload dialog
            await page.click("button:has-text('Upload Files')")
            await page.wait_for_selector(".upload-modal", state="visible")
            
            # Try to upload large file
            await page.set_input_files("input[type='file']", large_file_path)
            
            # Should show progress indicator for large files
            await page.wait_for_selector(".upload-progress", state="visible", timeout=5000)
            
            await E2ETestHelper.take_screenshot(page, "large_file_upload")
            
        finally:
            Path(large_file_path).unlink(missing_ok=True)


# Performance testing helpers
@pytest.mark.e2e
class TestPerformance:
    """Test frontend performance"""
    
    async def test_page_load_performance(self, page: Page, test_user):
        """Test page load performance"""
        
        # Enable performance monitoring
        await page.add_init_script("""
            window.performanceMarks = {};
            window.performance.mark('navigation-start');
        """)
        
        # Navigate to app and login
        start_time = datetime.now()
        await page.goto(E2E_CONFIG["base_url"])
        
        # Measure login performance
        await E2ETestHelper.fill_form_field(page, "input[name='email']", test_user["email"])
        await E2ETestHelper.fill_form_field(page, "input[name='password']", test_user["password"])
        
        await page.click("button[type='submit']:has-text('Login')")
        await page.wait_for_url("**/dashboard", timeout=10000)
        
        # Wait for dashboard to fully load
        await E2ETestHelper.wait_for_loading(page)
        
        end_time = datetime.now()
        load_time = (end_time - start_time).total_seconds()
        
        print(f"Page load time: {load_time:.2f} seconds")
        
        # Assert reasonable load time (adjust threshold as needed)
        assert load_time < 10.0, f"Page load took too long: {load_time:.2f} seconds"
        
        await E2ETestHelper.take_screenshot(page, "performance_test")


# Test data cleanup
@pytest.fixture(autouse=True, scope="session")
async def cleanup_test_data():
    """Clean up test data after all tests"""
    yield
    
    # Cleanup logic would go here
    # For example, delete test users, files, etc.
    print("Cleaning up E2E test data...")


if __name__ == "__main__":
    # Run specific test
    pytest.main([__file__, "-v", "--tb=short"])