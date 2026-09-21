import express from 'express';
import path from 'path';

const router = express.Router();

// GET /api/backup/list - List available backups
router.get('/list', async (req, res) => {
  try {
    const { backup } = req.app.locals.services;
    const backups = await backup.getBackupsList();
    res.json(backups);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// POST /api/backup/create - Create manual backup
router.post('/create', async (req, res) => {
  try {
    const { backup } = req.app.locals.services;
    const result = await backup.performFullBackup();
    res.json(result);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// POST /api/backup/restore - Restore from backup
router.post('/restore', async (req, res) => {
  try {
    const { backup } = req.app.locals.services;
    const { backupPath, options } = req.body;
    const result = await backup.restoreFromBackup(backupPath, options);
    res.json(result);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

// GET /api/backup/download/:filename - Download backup file
router.get('/download/:filename', async (req, res) => {
  try {
    const { backup } = req.app.locals.services;
    const filePath = path.join(backup.backupPath, req.params.filename);
    
    // Check if file exists and user has permission
    res.download(filePath);
  } catch (error) {
    res.status(404).json({ error: 'Backup file not found' });
  }
});

export default router;