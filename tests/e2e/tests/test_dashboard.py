"""E2E tests for the benchmark application."""

import pytest
from playwright.sync_api import Playwright, expect
from typing import Generator
from local_llm_benchmark.runner import run_benchmark
from local_llm_benchmark.config import EngineConfig, JudgeConfig


class TestDashboard:
    """E2E tests for the dashboard."""
    
    def test_nav_to_dashboard(self, browser_url: str):
        """Test navigation to dashboard."""
        page = browser_url
        page.goto("/dashboard")
        
        # Check dashboard is loaded
        expect(page).to_have_title("Dashboard")
        
        # Check main heading exists
        expect(page.locator("h1")).to_be_visible()
    
    def test_select_all_models(self, browser_url: str):
        """Test selecting all available models."""
        page = browser_url
        page.goto("/dashboard")
        
        # Find model selector
        model_selector = page.locator("select[name='model']")
        expect(model_selector).to_be_visible()
        
        # Select a model
        page.click("select[name='model']")
        page.select_option("select[name='model']", value="default-model")
        expect(model_selector).to_contain_text("Default Model")
    
    def test_add_engine_button(self, browser_url: str):
        """Test adding a new engine."""
        page = browser_url
        page.goto("/dashboard")
        
        # Find add engine button
        add_button = page.locator("button:has-text('Add Engine')")
        expect(add_button).to_be_visible()
        
        # Click and verify interaction
        page.click("button:has-text('Add Engine')")
        
        # Check that engine configuration modal appears
        expect(page.locator("dialog")).to_be_opened()
    
    def test_run_benchmark(self, browser_url: str):
        """Test running a benchmark."""
        page = browser_url
        page.goto("/dashboard")
        
        # Configure model
        page.click("select[name='model']")
        page.select_option("select[name='model']", value="default-model")
        
        # Click run button
        page.click("button:has-text('Run Benchmark')")
        
        # Wait for progress
        expect(page.locator("text='Running...'" or "text='Benchmarking...'" or "text='Processing...'")).to_be_visible(timeout=30000)
        
        # Wait for completion
        page.wait_for_timeout(10000)  # Wait 10 seconds for results
    
    def test_view_results(self, browser_url: str):
        """Test viewing benchmark results."""
        page = browser_url
        page.goto("/results")
        
        # Check results table is loaded
        expect(page.locator("table")).to_be_visible()
        
        # Check header row exists
        expect(page.locator("th")).to_be_visible()
        
        # Check quality score column
        expect(page.locator("th:has-text('Quality')" or "th:has-text('Score')" or "th:has-text('Quality Score')")).to_be_visible()
    
    def test_results_pagination(self, browser_url: str):
        """Test results pagination."""
        page = browser_url
        page.goto("/results")
        
        # Check pagination controls
        pagination = page.locator(".pagination or .pagination or .paginate")
        expect(pagination).to_be_visible()
    
    def test_results_filtering(self, browser_url: str):
        """Test results filtering."""
        page = browser_url
        page.goto("/results")
        
        # Check filter controls
        filter_controls = page.locator(".filter or .filters or .filter-container")
        expect(filter_controls).to_be_visible()
    
    def test_results_export(self, browser_url: str):
        """Test exporting results."""
        page = browser_url
        page.goto("/results")
        
        # Check export button
        export_button = page.locator("button:has-text('Export') or button:has-text('Download')")
        expect(export_button).to_be_visible()
        
        # Click export
        page.click("button:has-text('Export')")
        
        # Check file download
        page.wait_for_timeout(2000)
        page.click("a:has-text('Download') or a:has-text('Save')")


class TestEngineConfiguration:
    """E2E tests for engine configuration."""
    
    def test_engine_list(self, browser_url: str):
        """Test listing configured engines."""
        page = browser_url
        page.goto("/engines")
        
        # Check engine list is loaded
        expect(page.locator("table")).to_be_visible()
    
    def test_engine_status_indicator(self, browser_url: str):
        """Test engine status indicators."""
        page = browser_url
        page.goto("/engines")
        
        # Check status indicators
        status_indicators = page.locator(".status or .status-indicator")
        expect(status_indicators).to_be_visible()
    
    def test_engine_edit(self, browser_url: str):
        """Test editing engine configuration."""
        page = browser_url
        page.goto("/engines")
        
        # Find edit button
        edit_button = page.locator("button:has-text('Edit')")
        expect(edit_button).to_be_visible()
        
        # Click edit
        page.click("button:has-text('Edit')")
        
        # Check edit modal
        expect(page.locator("dialog")).to_be_opened()
    
    def test_engine_delete(self, browser_url: str):
        """Test deleting an engine."""
        page = browser_url
        page.goto("/engines")
        
        # Find delete button
        delete_button = page.locator("button:has-text('Delete')")
        expect(delete_button).to_be_visible()
        
        # Click delete and confirm
        page.click("button:has-text('Delete')")
        page.click("button:has-text('Delete')")  # Confirm dialog


class TestChallenges:
    """E2E tests for challenges."""
    
    def test_challenge_list(self, browser_url: str):
        """Test listing challenges."""
        page = browser_url
        page.goto("/challenges")
        
        # Check challenge list is loaded
        expect(page.locator("table")).to_be_visible()
    
    def test_challenge_details(self, browser_url: str):
        """Test viewing challenge details."""
        page = browser_url
        page.goto("/challenges")
        
        # Click on a challenge
        page.click("a:has-text('Details')")
        
        # Check details page
        expect(page.locator("h1")).to_contain_text("Challenge Details")
    
    def test_challenge_tags(self, browser_url: str):
        """Test challenge tags display."""
        page = browser_url
        page.goto("/challenges")
        
        # Check tags are displayed
        tags = page.locator(".tag or .badge or span:has-text('tag')")
        expect(tags).to_be_visible()


class TestResultsVisualization:
    """E2E tests for results visualization."""
    
    def test_results_chart(self, browser_url: str):
        """Test results chart display."""
        page = browser_url
        page.goto("/results")
        
        # Check chart is loaded
        chart = page.locator(".chart or .visualization or svg")
        expect(chart).to_be_visible()
    
    def test_results_metric_cards(self, browser_url: str):
        """Test metric cards display."""
        page = browser_url
        page.goto("/results")
        
        # Check metric cards
        metric_cards = page.locator(".card or .metric-card or .stat")
        expect(metric_cards).to_be_visible()
    
    def test_results_comparison(self, browser_url: str):
        """Test results comparison view."""
        page = browser_url
        page.goto("/results")
        
        # Check comparison controls
        comparison = page.locator(".compare or .comparison")
        expect(comparison).to_be_visible()
