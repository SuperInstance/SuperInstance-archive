# File Management Guide

Master file organization, management, and optimization in ActiveLog.

## File Upload

### Basic Upload Methods

**Drag and Drop** (Recommended)
1. Drag files from your desktop directly to ActiveLog
2. Files appear in the current folder
3. Multiple files upload simultaneously
4. Progress shown for each file

![Screenshot Placeholder: Drag and drop interface]

**Upload Button**
1. Click **"Upload"** button in toolbar
2. Select **"Files"** or **"Folder"**
3. Choose files from file picker
4. Click **"Upload"**

**Email Upload**
Every folder has a unique email address:
1. Right-click folder → **"Email Address"**
2. Copy the address (e.g., `upload-xyz@files.activelog.com`)
3. Email files as attachments
4. Files automatically appear in the folder

![Screenshot Placeholder: Email upload address dialog]

### Advanced Upload Options

**Bulk Upload**
- Upload entire folders with structure preserved
- Supports up to 10,000 files per batch
- Resumes interrupted uploads automatically
- Deduplicates identical files

**URL Import**
1. Click **Upload** → **"From URL"**
2. Paste URLs of files to download
3. ActiveLog downloads and processes them
4. Supports direct links, cloud storage shares

![Screenshot Placeholder: URL import dialog]

**Cloud Service Import**
Connect and import from:
- Google Drive
- Dropbox
- OneDrive
- Box
- iCloud Drive

Steps:
1. Settings → **"Integrations"**
2. Connect your cloud service
3. Choose files/folders to import
4. Set up ongoing sync (optional)

### Upload Processing

When files upload, ActiveLog automatically:

1. **🦠 Virus Scanning** - All files scanned for malware
2. **🔍 Metadata Extraction** - File properties, EXIF data, etc.
3. **📝 Text Extraction** - OCR for images, text from documents
4. **🎯 AI Classification** - Content categorization
5. **🖼️ Thumbnail Generation** - Preview images for all file types
6. **🔗 Relationship Detection** - Links between related files

![Screenshot Placeholder: Upload processing status]

## File Organization

### Folder Structure

**Create Folders**
- Click **"New Folder"** in toolbar
- Right-click in empty space → **"New Folder"**
- Use keyboard shortcut `Ctrl/Cmd + Shift + N`

**Folder Types**
- **Regular Folders** - Standard organization
- **Smart Folders** - Auto-populate based on rules
- **Shared Folders** - Team collaboration spaces
- **Sync Folders** - Synchronized with local directories

![Screenshot Placeholder: Different folder types]

**Best Practices**
- Use descriptive names: "2024 Tax Documents" not "Taxes"
- Create hierarchy: Projects → Client → Year → Documents
- Limit folder depth to 5-6 levels maximum
- Use consistent naming conventions

### File Naming Conventions

**Automatic Renaming**
ActiveLog can automatically standardize file names:

1. Settings → **"File Management"** → **"Auto Rename"**
2. Set patterns like `{Year}-{Month}-{OriginalName}`
3. Apply to new uploads or existing files
4. Preview changes before applying

**Smart Naming Suggestions**
AI suggests better names based on content:
- `IMG_1234.jpg` → `golden-gate-bridge-sunset.jpg`
- `Document1.pdf` → `quarterly-report-q3-2024.pdf`

![Screenshot Placeholder: Rename suggestions]

### File Operations

**Move Files**
- Drag and drop to new location
- Cut (`Ctrl/Cmd + X`) and paste (`Ctrl/Cmd + V`)
- Right-click → **"Move to"** → Select destination
- Bulk move: Select multiple files → **"Move"**

**Copy Files**
- `Ctrl/Cmd + C` to copy, `Ctrl/Cmd + V` to paste
- Right-click → **"Copy to"**
- Hold `Ctrl/Cmd` while dragging to copy

**Duplicate Detection**
ActiveLog prevents duplicate uploads:
- Hash-based comparison detects identical files
- Similar name detection for near-duplicates
- Merge or replace options when duplicates found

![Screenshot Placeholder: Duplicate detection dialog]

## File Metadata and Properties

### Viewing File Information

**Quick Info Panel** (Right sidebar)
- File size, type, and dates
- AI-extracted metadata
- Tags and categories
- Sharing and permissions

**Detailed Properties** (`Ctrl/Cmd + I`)
- Technical specifications
- Edit history and versions
- Access logs and analytics
- Embedded metadata (EXIF, ID3, etc.)

![Screenshot Placeholder: File properties dialog]

### Custom Metadata

**Add Custom Fields**
1. Right-click file → **"Properties"** → **"Custom Fields"**
2. Add key-value pairs
3. Use across files for consistency
4. Search using custom metadata

**Metadata Templates**
Create templates for consistent tagging:
1. Settings → **"Metadata Templates"**
2. Define fields for different file types
3. Auto-apply based on file type or folder
4. Include required fields and validation

## File Versioning

### Automatic Versioning

ActiveLog automatically creates versions when:
- File content changes
- File is re-uploaded with same name
- Collaborative editing occurs
- Manual version creation

### Version History

**View Versions**
1. Right-click file → **"Version History"**
2. See timeline of all changes
3. Compare versions side-by-side
4. Preview each version

![Screenshot Placeholder: Version history timeline]

**Restore Previous Version**
1. Open version history
2. Select version to restore
3. Choose restore method:
   - **Replace current** - Overwrites current version
   - **Restore as new** - Creates copy with version number
   - **Create branch** - Maintains both versions

### Version Management Settings

**Retention Policy**
- Keep all versions (default)
- Keep last N versions (e.g., 10)
- Keep versions for X days (e.g., 90 days)
- Custom rules per folder

**Storage Optimization**
- Delta compression reduces storage usage
- Automatic cleanup of identical versions
- Compress old versions to save space

## Advanced File Management

### Batch Operations

**Multi-Select Options**
- Click and drag to select range
- `Ctrl/Cmd + Click` for individual selection
- `Ctrl/Cmd + A` to select all
- `Shift + Click` to select range

**Bulk Actions**
With files selected:
- **Move** - Change location
- **Tag** - Add/remove tags
- **Share** - Set permissions
- **Download** - Create zip archive
- **Delete** - Move to trash
- **Properties** - Edit metadata

![Screenshot Placeholder: Bulk actions toolbar]

### File Filters and Views

**Filter Options**
- **File Type** - Documents, Images, Videos, etc.
- **Date Range** - Created, modified, or accessed
- **Size Range** - From bytes to gigabytes
- **Tags** - Files with specific tags
- **Shared Status** - Private, shared, public
- **Processing Status** - Processed, pending, failed

**Custom Views**
1. Apply filters for desired files
2. Click **"Save View"**
3. Name your view (e.g., "Large Videos")
4. Access from sidebar for quick filtering

### File Compression and Archives

**Automatic Compression**
- Files over 100MB automatically compressed
- Lossless compression maintains quality
- Transparent decompression on access
- Significant storage savings

**Archive Management**
- Extract ZIP, RAR, 7Z archives automatically  
- Browse archive contents without extracting
- Search inside compressed files
- Preserve folder structure on extraction

![Screenshot Placeholder: Archive browser interface]

## File Sharing and Permissions

### Quick Sharing

**Share Button**
1. Select file(s)
2. Click **"Share"** button
3. Add recipients by email
4. Set permissions and expiration
5. Send notification

**Share Links**
- **View Link** - Read-only access
- **Edit Link** - Collaborative editing
- **Download Link** - File download only
- **Upload Link** - Allow file uploads to folder

![Screenshot Placeholder: Sharing dialog with options]

### Advanced Permissions

**Permission Levels**
- **Viewer** - Can view and download
- **Editor** - Can edit and comment
- **Admin** - Can share and manage permissions
- **Owner** - Full control including deletion

**Access Controls**
- Password protection for links
- IP address restrictions
- Device-based access controls
- Time-based access (expire after X days)

### Collaboration Features

**Real-time Editing**
Supported file types:
- Microsoft Office documents
- Google Workspace files
- Plain text files
- Markdown documents
- Code files

**Comments and Annotations**
- Add comments to any file
- Highlight sections for discussion
- @mention team members for notifications
- Resolve discussions when complete

![Screenshot Placeholder: Collaborative editing interface]

## File Security

### Encryption

**Encryption at Rest**
- AES-256 encryption for all stored files
- Unique encryption key per file
- Keys stored separately from data
- Zero-knowledge architecture option

**Encryption in Transit**
- TLS 1.3 for all data transfers
- End-to-end encryption for sensitive files
- Encrypted sync protocols
- Secure file sharing links

### Access Auditing

**Activity Logs**
Track all file operations:
- Who accessed files and when
- What actions were performed
- IP addresses and device info
- Failed access attempts

**Compliance Reporting**
- Export audit logs for compliance
- Real-time alerts for suspicious activity
- Integration with SIEM systems
- Automated compliance reports

## Performance Optimization

### Sync Optimization

**Selective Sync**
- Choose which folders sync to each device
- Reduces bandwidth and storage usage
- Online-only files available on demand
- Automatic management based on usage patterns

**Bandwidth Management**
- Set upload/download speed limits
- Schedule sync during off-peak hours
- Pause sync when on metered connections
- Priority queues for important files

### Storage Management

**Storage Analytics**
- View storage usage by file type
- Identify large files and duplicates
- Track storage growth over time
- Recommend optimization actions

**Automated Cleanup**
- Delete files in trash after 30 days
- Compress infrequently accessed files
- Move old files to archive storage
- Remove duplicate files automatically

## Troubleshooting Common Issues

### Upload Problems

**Slow Uploads**
- Check internet connection speed
- Pause other bandwidth-intensive activities
- Upload smaller batches of files
- Use resume capability for large files

**Failed Uploads**
- Verify file isn't corrupted
- Check file size limits (5GB per file)
- Ensure sufficient storage space
- Try different upload method

### Sync Issues

**Files Not Syncing**
1. Check sync status in toolbar
2. Verify internet connection
3. Restart ActiveLog application
4. Check for conflicting file names

**Sync Conflicts**
- Review conflict resolution options
- Choose to keep both versions or merge
- Rename conflicting files
- Set up automatic conflict resolution

### Performance Issues

**Slow File Access**
- Clear browser cache (web app)
- Restart desktop application  
- Check available RAM and disk space
- Verify network connection stability

For more troubleshooting help, see our [Troubleshooting Guide](../troubleshooting/common-issues.md).

---

*Need help with file management? Contact support at support@activelog.com or use the in-app chat.*