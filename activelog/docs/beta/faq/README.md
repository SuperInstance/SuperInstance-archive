# Frequently Asked Questions

Interactive FAQ system for ActiveLog beta users. Find quick answers to common questions, search by topic, and get help when you need it.

## 🔍 Quick Search

**Popular Topics:**
- [Account & Login](#account--login) - Authentication, passwords, account setup
- [Beta Program](#beta-program) - Beta-specific questions and policies
- [Features & Usage](#features--usage) - How to use ActiveLog features
- [Technical Issues](#technical-issues) - Troubleshooting and error resolution
- [Integrations](#integrations) - Connecting external services
- [API & Development](#api--development) - Developer questions and API usage
- [Billing & Plans](#billing--plans) - Pricing and subscription questions
- [Privacy & Security](#privacy--security) - Data protection and security

## 📚 FAQ Categories

### 🔐 Account & Login

<details>
<summary><strong>How do I access the ActiveLog beta?</strong></summary>

You need a beta invitation to access ActiveLog. Once invited:
1. Check your email for the beta invitation
2. Click "Accept Beta Invitation"
3. Sign the NDA agreement
4. Create your account credentials
5. Complete profile setup

**Beta URL:** https://beta.activelog.dev

If you haven't received an invitation, you can join the waitlist at our main website.
</details>

<details>
<summary><strong>I forgot my password. How do I reset it?</strong></summary>

To reset your password:
1. Go to the login page
2. Click "Forgot Password"
3. Enter your email address
4. Check your email for a reset link (may take 2-3 minutes)
5. Click the link and set a new password

**Note:** Password reset emails are sent from `noreply@activelog.dev` - check your spam folder if you don't see it.

**Still having issues?** Contact beta-support@activelog.dev
</details>

<details>
<summary><strong>Why can't I log in with my correct password?</strong></summary>

Common login issues and solutions:

**Account Locked:** Wait 15 minutes after 5 failed attempts
**Browser Issues:** Try incognito/private mode or clear browser cache
**Beta Access:** Ensure your beta invitation hasn't expired
**NDA Required:** Make sure you've signed the NDA agreement
**Caps Lock:** Check if Caps Lock is accidentally enabled

**Beta-specific:** Use the beta login URL: https://beta.activelog.dev/login
</details>

<details>
<summary><strong>Can I use the same account for beta and production?</strong></summary>

No, beta and production are separate environments:
- **Beta account:** For testing new features (beta.activelog.dev)
- **Production account:** For regular use when available

You'll need to create separate accounts for each environment. Your beta data won't automatically transfer to production.
</details>

### 🧪 Beta Program

<details>
<summary><strong>What is the ActiveLog beta program?</strong></summary>

The ActiveLog beta program gives selected users early access to new features:

**Duration:** 6-month program (subject to extension)
**Participants:** 100 selected beta testers
**Access:** All core features plus experimental features
**Requirements:** Signed NDA, active feedback participation

**Benefits:**
- Early access to new features
- Direct influence on product development
- Priority support from our team
- Extended API limits and advanced features
</details>

<details>
<summary><strong>What are my responsibilities as a beta tester?</strong></summary>

As a beta tester, we ask you to:

**Required:**
- Sign and maintain NDA confidentiality
- Report bugs and issues promptly
- Provide feedback through surveys and interviews
- Use ActiveLog for real work/personal tasks

**Appreciated:**
- Share detailed use cases and workflows
- Suggest feature improvements
- Participate in community discussions
- Help other beta users when possible

**Forbidden:**
- Share screenshots or details publicly
- Invite non-beta users without permission
- Use beta for production-critical work
</details>

<details>
<summary><strong>Can I invite others to the beta program?</strong></summary>

**Standard/Premium Beta:** No, you cannot invite others
**Admin Beta:** Yes, limited invitations based on your tier

**To request invitations:**
1. Email beta-support@activelog.dev
2. Explain who you want to invite and why
3. Confirm they'll sign the NDA
4. We'll send invitations if approved

**Note:** All invitees must sign the NDA and follow beta program rules.
</details>

<details>
<summary><strong>What happens to my data when beta ends?</strong></summary>

**Your data is safe:**
- We'll provide export tools before beta ends
- You can download all your files and projects
- Data will be preserved for 90 days after beta
- Migration path to production will be provided

**Export options:**
- Full data export (JSON + files)
- Individual project exports
- API-based data extraction
- Migration assistance available
</details>

### ⚡ Features & Usage

<details>
<summary><strong>Which features are beta-only vs. production features?</strong></summary>

**Beta-Only Features (experimental):**
- AI-powered content insights
- Real-time collaboration
- Advanced analytics dashboard
- Custom integrations
- Extended API access

**Production Features (stable):**
- File upload and management
- Basic search and organization
- Project workspaces
- Standard integrations
- Core API functionality

**Feature flags control:** Check Settings → Beta Features to enable/disable experimental features.
</details>

<details>
<summary><strong>How do I enable or disable beta features?</strong></summary>

To manage beta features:
1. Go to Settings → Beta Features
2. Toggle features on/off individually
3. Some features require page refresh
4. Changes apply immediately to your account

**Via API:**
```bash
activelog features enable ai_powered_insights
activelog features disable real_time_sync
```

**Note:** Some features may be A/B tested and controlled automatically.
</details>

<details>
<summary><strong>Why is a feature missing or different from documentation?</strong></summary>

In beta, features may change frequently:

**Possible reasons:**
- Feature is A/B tested and you're in the control group
- Feature was disabled due to issues
- Feature is being updated/improved
- Feature flag is turned off in your settings

**What to do:**
1. Check Settings → Beta Features
2. Refresh your browser/app
3. Check #beta-announcements for updates
4. Report missing features to beta-support@activelog.dev
</details>

### 🔧 Technical Issues

<details>
<summary><strong>The app is running slowly. How can I improve performance?</strong></summary>

**Browser Optimization:**
- Use Chrome or Firefox for best performance
- Close unnecessary tabs
- Clear browser cache and cookies
- Disable unnecessary browser extensions
- Ensure good internet connection (5+ Mbps)

**App Settings:**
- Reduce file preview quality in settings
- Disable unused beta features
- Use desktop app instead of browser
- Switch to "Performance Mode" in settings

**Still slow?** Report performance issues with:
- Your browser and version
- Operating system
- Internet connection speed
- Specific slow actions
</details>

<details>
<summary><strong>Files won't upload or sync properly. What should I do?</strong></summary>

**Upload Troubleshooting:**
1. **Check file size:** Max 1GB per file in beta
2. **Verify file type:** Ensure it's a supported format
3. **Test connection:** Try uploading a small test file
4. **Clear browser cache:** May resolve upload issues
5. **Try different browser:** Switch to Chrome/Firefox

**Sync Issues:**
- Check internet connection stability
- Disable VPN temporarily
- Try uploading from different device
- Contact support if issue persists

**Beta limits:** 1GB per file, 10GB total storage
</details>

<details>
<summary><strong>I'm getting error codes. What do they mean?</strong></summary>

**Common Error Codes:**

**AUTH_001:** Invalid login credentials
- **Solution:** Reset password or check email/password

**UPLOAD_003:** File too large
- **Solution:** File exceeds 1GB limit, compress or split file

**SYNC_005:** Connection timeout
- **Solution:** Check internet connection, try again

**BETA_007:** Feature not available
- **Solution:** Feature may be disabled, check Settings → Beta Features

**API_429:** Rate limit exceeded
- **Solution:** Too many requests, wait and retry

**Full error code reference:** [Error Code Documentation](../troubleshooting/error-codes.md)
</details>

### 🔗 Integrations

<details>
<summary><strong>Which integrations are available in beta?</strong></summary>

**Fully Available:**
- Google Workspace (Drive, Docs, Sheets)
- Slack notifications
- Zapier webhooks
- REST API access

**Beta-Only Integrations:**
- Advanced Notion sync
- Microsoft 365 deep integration
- Custom webhook builders
- AI integration APIs

**Coming Soon:**
- GitHub integration
- Figma plugin
- Salesforce connector

**To enable:** Go to Settings → Integrations and authenticate with each service.
</details>

<details>
<summary><strong>My Google Drive integration isn't syncing. How do I fix it?</strong></summary>

**Troubleshooting Steps:**
1. **Re-authenticate:** Settings → Integrations → Google Drive → Reconnect
2. **Check permissions:** Ensure ActiveLog has necessary Google Drive permissions
3. **Verify folders:** Check that selected folders exist and are accessible
4. **Manual sync:** Try triggering a manual sync from integration settings
5. **Check quotas:** Ensure you haven't exceeded Google Drive API limits

**Common issues:**
- Google account has 2FA enabled (requires app-specific password)
- Selected folders were deleted or moved
- Google Drive API quota exceeded (rare in beta)

**Still not working?** Contact beta-support@activelog.dev with your Google account email.
</details>

### 👨‍💻 API & Development

<details>
<summary><strong>How do I get API access for the beta?</strong></summary>

Beta users get enhanced API access:
1. Go to Settings → API Keys
2. Click "Generate New Key"
3. Choose scopes (read, write, admin)
4. Copy and store your API key securely

**Beta API limits:**
- 10,000 requests/hour (vs 1,000 for regular users)
- Higher file upload limits
- Access to experimental endpoints

**Base URL:** `https://beta-api.activelog.dev/v1`
**Documentation:** [API Reference](../api/rest-api.md)
</details>

<details>
<summary><strong>Are there SDKs or libraries available?</strong></summary>

**Official SDKs:**
- JavaScript/Node.js: `npm install @activelog/sdk`
- Python: `pip install activelog-sdk`
- PHP: `composer require activelog/activelog-php`

**Community SDKs:**
- Go: Available on GitHub
- Ruby: Available on GitHub
- Java: In development

**Beta features:** SDKs include beta feature access and extended rate limits.

**Documentation:** [SDK Guide](../api/sdks.md)
</details>

### 💳 Billing & Plans

<details>
<summary><strong>Is the beta program free?</strong></summary>

**Yes, the beta program is completely free:**
- No charges during the 6-month beta period
- Full access to all beta features
- No credit card required
- Extended limits and priority support

**After beta:**
- You'll have options to continue with paid plans
- Export tools will be provided before any billing starts
- No surprise charges - we'll communicate pricing well in advance
</details>

<details>
<summary><strong>What happens when the beta ends?</strong></summary>

**Transition options:**
1. **Continue with paid plan** - Migrate to production with paid subscription
2. **Export data** - Download all your files and projects
3. **Free tier** - Use limited free version (if available)
4. **Extended beta** - Some users may get extended beta access

**Timeline:**
- 60 days notice before beta ends
- 30 days to choose transition option
- 90 days data retention after beta ends
</details>

### 🔒 Privacy & Security

<details>
<summary><strong>How is my data protected in the beta?</strong></summary>

**Security Measures:**
- End-to-end encryption for file storage
- TLS encryption for all data transmission
- Regular security audits and penetration testing
- SOC 2 Type II compliance preparation

**Data Protection:**
- GDPR compliant data handling
- Right to data export and deletion
- Minimal data collection (only what's necessary)
- No data sharing with third parties

**Beta-specific:**
- Enhanced monitoring and logging
- Dedicated security team oversight
- Priority incident response
</details>

<details>
<summary><strong>Can I delete my account and data?</strong></summary>

**Yes, you have full control:**

**Account Deletion:**
1. Go to Settings → Account → Delete Account
2. Confirm deletion (cannot be undone)
3. All data permanently deleted within 30 days

**Data Export (recommended first):**
1. Go to Settings → Data Export
2. Choose export format (JSON, ZIP)
3. Download complete data archive

**Partial Deletion:**
- Delete individual files/projects
- Clear specific data types
- Selective data removal

**GDPR Rights:** You have full rights under GDPR including data portability and erasure.
</details>

## 🎯 Quick Answer Generator

Can't find your question? Try our AI-powered answer generator:

```
🔍 Search: [Type your question here]

Example questions:
- "How do I change my password?"
- "Why isn't my file uploading?"
- "Can I use the API for commercial projects?"
- "What happens to my data after beta?"
```

## 📞 Still Need Help?

### Self-Service Options
1. **Search Documentation** - Full documentation at docs.activelog.dev
2. **Video Tutorials** - Step-by-step visual guides
3. **Community Forum** - Ask other beta users
4. **Troubleshooting Guide** - Systematic problem solving

### Direct Support
- **Email:** beta-support@activelog.dev
- **Response Time:** < 4 hours for beta users
- **Live Chat:** Available in app (business hours)
- **Phone:** Enterprise beta users only

### Emergency Support
For data loss or security issues:
- **Emergency Email:** critical@activelog.dev
- **Response Time:** < 1 hour
- **24/7 Availability:** For critical issues

## 📊 FAQ Statistics

### Most Searched Questions (Last 30 Days)
1. "How to reset password" - 234 searches
2. "File upload not working" - 189 searches
3. "Beta program duration" - 167 searches
4. "API rate limits" - 145 searches
5. "Data export options" - 123 searches

### Top Categories by Usage
1. Technical Issues (34%)
2. Beta Program (28%)
3. Features & Usage (22%)
4. Account & Login (16%)

### Satisfaction Ratings
- **Helpful answers:** 87% of users find answers helpful
- **Completeness:** 4.3/5 average rating
- **Response time:** 4.6/5 average rating
- **Overall satisfaction:** 4.4/5 average rating

## 🔄 FAQ Updates

This FAQ is updated weekly based on:
- **Common support questions** - Issues reported by users
- **Feature changes** - Updates to beta features
- **User feedback** - Suggestions for improvement
- **Product updates** - New features and changes

**Last Updated:** [Current Date]  
**Next Review:** Weekly every Monday  
**Contributors:** Beta support team + community feedback  

### Suggest Improvements
- **Missing questions?** Email faq-feedback@activelog.dev
- **Incorrect answers?** Use the feedback button on each answer
- **Better explanations?** Submit suggestions via in-app feedback

---

**Tip:** Bookmark this page and use Ctrl+F (Cmd+F on Mac) to quickly search for specific topics!

*This FAQ is specifically tailored for beta users and includes beta program information not available elsewhere.*