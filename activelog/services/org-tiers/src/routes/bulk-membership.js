import express from 'express';

export function createBulkMembershipRoutes(bulkMembershipService) {
    const router = express.Router();

    router.post('/bulk-invite', async (req, res) => {
        try {
            const { orgId, invitations, permissions } = req.body;
            const result = await bulkMembershipService.bulkInvite(orgId, invitations, permissions);
            res.json({ success: true, result });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.post('/bulk-update-roles', async (req, res) => {
        try {
            const { orgId, userRoleUpdates } = req.body;
            const result = await bulkMembershipService.bulkUpdateRoles(orgId, userRoleUpdates);
            res.json({ success: true, result });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/invitation-status/:invitationId', async (req, res) => {
        try {
            const { invitationId } = req.params;
            const status = await bulkMembershipService.getInvitationStatus(invitationId);
            res.json({ success: true, status });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await bulkMembershipService.getStats();
            res.json({ success: true, stats });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    return router;
}