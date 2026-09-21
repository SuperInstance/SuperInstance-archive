import express from 'express';

export function createSSORoutes(ssoService) {
    const router = express.Router();

    router.post('/configure-sso', async (req, res) => {
        try {
            const { orgId, provider, configuration } = req.body;
            const config = await ssoService.configureSSOProvider(orgId, provider, configuration);
            res.json({ success: true, config });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.post('/initiate-saml-login', async (req, res) => {
        try {
            const { orgId, redirectUrl } = req.body;
            const authUrl = await ssoService.initiateSAMLLogin(orgId, redirectUrl);
            res.json({ success: true, authUrl });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.post('/callback/saml', async (req, res) => {
        try {
            const { samlResponse, orgId } = req.body;
            const result = await ssoService.handleSAMLCallback(samlResponse, orgId);
            res.json({ success: true, result });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/providers', async (req, res) => {
        try {
            const providers = await ssoService.getSupportedProviders();
            res.json({ success: true, providers });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    router.get('/stats', async (req, res) => {
        try {
            const stats = await ssoService.getStats();
            res.json({ success: true, stats });
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    });

    return router;
}