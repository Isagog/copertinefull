import asyncio
from playwright.async_api import async_playwright
import secrets
import aiohttp
import json
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_mailpit_messages() -> List[Dict]:
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:8025/api/v1/messages') as response:
            data = await response.json()
            return data

async def test_auth_flow():
    # Generate test email
    random_suffix = secrets.token_hex(4)
    test_email = f"newuser{random_suffix}@manifesto.it"
    test_password = "TestPassword123!"

    logger.info(f"Testing with email: {test_email}")

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Navigate to registration page
            logger.info("Navigating to registration page...")
            await page.goto('http://localhost:3000/auth/register')
            await page.wait_for_selector('input[name="email"]')

            # Fill registration form
            logger.info("Filling registration form...")
            await page.fill('input[name="email"]', test_email)
            await page.fill('input[name="password"]', test_password)
            await page.fill('input[name="confirmPassword"]', test_password)

            # Submit form
            logger.info("Submitting registration form...")
            async with page.expect_navigation():
                await page.click('button[type="submit"]')

            # Wait for verification page
            logger.info("Waiting for verification page...")
            await page.wait_for_selector('h2')
            verify_title = await page.text_content('h2')
            logger.info(f"Verification page title: {verify_title}")

            # Wait for email
            logger.info("Waiting for verification email...")
            await asyncio.sleep(2)  # Wait for email to arrive

            # Get verification email from Mailpit
            messages = await get_mailpit_messages()
            if not messages:
                raise Exception("No verification email received")

            latest_email = messages[0]
            html_content = latest_email['HTML']

            # Extract verification link
            import re
            verification_url_match = re.search(r'href="([^"]*verify[^"]*)"', html_content)
            if not verification_url_match:
                raise Exception("Verification URL not found in email")

            verification_url = verification_url_match.group(1)
            logger.info(f"Verification URL: {verification_url}")

            # Open verification link in new page
            logger.info("Opening verification link...")
            verify_page = await context.new_page()
            response = await verify_page.goto(verification_url)
            logger.info(f"Verification page status: {response.status}")

            # Wait for verification result
            await verify_page.wait_for_selector('h2')
            verification_result = await verify_page.text_content('h2')
            logger.info(f"Verification result: {verification_result}")

            # Log any console errors
            verify_page.on("console", lambda msg: logger.error(f"Console error: {msg.text}") if msg.type == "error" else None)

            # Wait to see the result
            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            raise
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_auth_flow())
