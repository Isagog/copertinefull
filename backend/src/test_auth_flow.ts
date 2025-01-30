import puppeteer from 'puppeteer';
import { randomBytes } from 'crypto';
import nodemailer from 'nodemailer';

async function testAuthFlow() {
  // Create test email
  const randomString = randomBytes(4).toString('hex');
  const testEmail = `newuser${randomString}@manifesto.it`;
  const testPassword = 'TestPassword123!';

  console.log(`Testing with email: ${testEmail}`);

  // Create SMTP connection to catch emails
  const testAccount = await nodemailer.createTestAccount();
  const transport = nodemailer.createTransport({
    host: 'localhost',
    port: 1025,
    secure: false,
    tls: {
      rejectUnauthorized: false
    }
  });

  // Launch browser
  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();

  try {
    // Set viewport
    await page.setViewport({ width: 1280, height: 800 });

    // Navigate to registration page
    console.log('Navigating to registration page...');
    await page.goto('http://localhost:3000/auth/register');
    await page.waitForSelector('input[name="email"]');

    // Fill registration form
    console.log('Filling registration form...');
    await page.type('input[name="email"]', testEmail);
    await page.type('input[name="password"]', testPassword);
    await page.type('input[name="confirmPassword"]', testPassword);

    // Submit form
    console.log('Submitting registration form...');
    await Promise.all([
      page.click('button[type="submit"]'),
      page.waitForNavigation(),
    ]);

    // Wait for verification page
    console.log('Waiting for verification page...');
    await page.waitForSelector('h2');
    const verifyTitle = await page.$eval('h2', el => el.textContent);
    console.log('Verification page title:', verifyTitle);

    // Get verification email
    console.log('Waiting for verification email...');
    await new Promise(resolve => setTimeout(resolve, 2000)); // Wait for email to arrive

    // Connect to Mailpit API to get the verification link
    const response = await fetch('http://localhost:8025/api/v1/messages');
    const messages = await response.json();
    
    if (messages.length === 0) {
      throw new Error('No verification email received');
    }

    const latestEmail = messages[0];
    const htmlContent = latestEmail.HTML;

    // Extract verification link
    const verificationUrlMatch = htmlContent.match(/href="([^"]*verify[^"]*)"/);
    if (!verificationUrlMatch) {
      throw new Error('Verification URL not found in email');
    }

    const verificationUrl = verificationUrlMatch[1];
    console.log('Verification URL:', verificationUrl);

    // Navigate to verification link
    console.log('Clicking verification link...');
    const verifyPage = await browser.newPage();
    const response1 = await verifyPage.goto(verificationUrl);
    console.log('Verification page status:', response1.status());

    // Log the page content for debugging
    const content = await verifyPage.content();
    console.log('Page content:', content);

    // Wait to see the result
    await new Promise(resolve => setTimeout(resolve, 5000));

  } catch (error) {
    console.error('Test failed:', error);
  } finally {
    await browser.close();
  }
}

testAuthFlow().catch(console.error);
