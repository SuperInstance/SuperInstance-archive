import express from 'express';
import cors from 'cors';
import { createServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import path from 'path';
import fs from 'fs-extra';

import { ScriptExporter } from './narrative/ScriptExporter';
import { DialogueTreeGenerator } from './dialogue/DialogueTreeGenerator';
import { QuestSystemConverter } from './quests/QuestSystemConverter';
import { NPCBehaviorScripting } from './behavior/NPCBehaviorScripting';
import { LevelDesignGenerator } from './level/LevelDesignGenerator';
import { CombatMechanicAdapter } from './combat/CombatMechanicAdapter';
import { AssetRequirementGenerator } from './assets/AssetRequirementGenerator';
import { GameEngineTemplates } from './templates/GameEngineTemplates';
import { PlaytestingFramework } from './testing/PlaytestingFramework';
import { AchievementGenerator } from './achievements/AchievementGenerator';
import { SaveSystemDesigner } from './saves/SaveSystemDesigner';
import { MonetizationPlanner } from './monetization/MonetizationPlanner';
import { Campaign } from './types';

interface GameDevService {
  scriptExporter: ScriptExporter;
  dialogueGenerator: DialogueTreeGenerator;
  questConverter: QuestSystemConverter;
  npcBehavior: NPCBehaviorScripting;
  levelGenerator: LevelDesignGenerator;
  combatAdapter: CombatMechanicAdapter;
  assetGenerator: AssetRequirementGenerator;
  templateGenerator: GameEngineTemplates;
  playtestingFramework: PlaytestingFramework;
  achievementGenerator: AchievementGenerator;
  saveSystemDesigner: SaveSystemDesigner;
  monetizationPlanner: MonetizationPlanner;
}

class DMLogGameDevService {
  private app: express.Application;
  private server: any;
  private io: SocketIOServer;
  private services: GameDevService;

  constructor() {
    this.app = express();
    this.server = createServer(this.app);
    this.io = new SocketIOServer(this.server, {
      cors: {
        origin: "*",
        methods: ["GET", "POST"]
      }
    });

    this.services = {
      scriptExporter: new ScriptExporter(),
      dialogueGenerator: new DialogueTreeGenerator(),
      questConverter: new QuestSystemConverter(),
      npcBehavior: new NPCBehaviorScripting(),
      levelGenerator: new LevelDesignGenerator(),
      combatAdapter: new CombatMechanicAdapter(),
      assetGenerator: new AssetRequirementGenerator(),
      templateGenerator: new GameEngineTemplates(),
      playtestingFramework: new PlaytestingFramework(),
      achievementGenerator: new AchievementGenerator(),
      saveSystemDesigner: new SaveSystemDesigner(),
      monetizationPlanner: new MonetizationPlanner()
    };

    this.setupMiddleware();
    this.setupRoutes();
    this.setupWebSocket();
    this.setupEventListeners();
  }

  private setupMiddleware(): void {
    this.app.use(cors());
    this.app.use(express.json({ limit: '50mb' }));
    this.app.use(express.urlencoded({ extended: true }));
    this.app.use('/static', express.static(path.join(__dirname, '../static')));
  }

  private setupRoutes(): void {
    this.app.get('/health', (req, res) => {
      res.json({ status: 'healthy', timestamp: new Date().toISOString() });
    });

    this.app.post('/export/script', async (req, res) => {
      try {
        const { campaign, format, options } = req.body;
        const script = await this.services.scriptExporter.exportScript(campaign, format, options);
        res.json({ success: true, script });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/generate/dialogue-tree', async (req, res) => {
      try {
        const { character, scenarios, options } = req.body;
        const dialogueTree = await this.services.dialogueGenerator.generateDialogueTree(character, scenarios, options);
        res.json({ success: true, dialogueTree });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/export/dialogue-tree', async (req, res) => {
      try {
        const { dialogueTree, format, outputPath } = req.body;
        await this.services.dialogueGenerator.exportDialogueTree(dialogueTree, format, outputPath);
        res.json({ success: true, message: 'Dialogue tree exported successfully' });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/convert/quests', async (req, res) => {
      try {
        const { campaign, options } = req.body;
        const questSystems = await this.services.questConverter.convertCampaignQuests(campaign, options);
        res.json({ success: true, questSystems });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/export/quests', async (req, res) => {
      try {
        const { questSystem, format, outputPath } = req.body;
        await this.services.questConverter.exportQuestSystem(questSystem, format, outputPath);
        res.json({ success: true, message: 'Quest system exported successfully' });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/generate/npc-behavior', async (req, res) => {
      try {
        const { character, context, options } = req.body;
        const behaviorScript = await this.services.npcBehavior.generateBehaviorScript(character, context, options);
        res.json({ success: true, behaviorScript });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/export/npc-behavior', async (req, res) => {
      try {
        const { behaviorScript, format, outputPath } = req.body;
        await this.services.npcBehavior.exportBehaviorScript(behaviorScript, format, outputPath);
        res.json({ success: true, message: 'NPC behavior script exported successfully' });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/generate/level-design', async (req, res) => {
      try {
        const { map, encounters } = req.body;
        const levelDesign = await this.services.levelGenerator.generateLevelDesign(map, encounters);
        res.json({ success: true, levelDesign });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/export/level-design', async (req, res) => {
      try {
        const { levelDesign, outputPath, options } = req.body;
        await this.services.levelGenerator.exportLevelDesign(levelDesign, outputPath, options);
        res.json({ success: true, message: 'Level design exported successfully' });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/adapt/combat-system', async (req, res) => {
      try {
        const { campaign, encounters, options } = req.body;
        const combatSystem = await this.services.combatAdapter.adaptCombatSystem(campaign, encounters, options);
        res.json({ success: true, combatSystem });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/export/combat-system', async (req, res) => {
      try {
        const { combatSystem, outputPath, options } = req.body;
        await this.services.combatAdapter.exportCombatSystem(combatSystem, outputPath, options);
        res.json({ success: true, message: 'Combat system exported successfully' });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/generate/asset-requirements', async (req, res) => {
      try {
        const { campaign, options } = req.body;
        const requirements = await this.services.assetGenerator.generateAssetRequirements(campaign, options);
        res.json({ success: true, requirements });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/generate/asset-budget', async (req, res) => {
      try {
        const { categories } = req.body;
        const budget = await this.services.assetGenerator.generateBudget(categories);
        res.json({ success: true, budget });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/export/asset-requirements', async (req, res) => {
      try {
        const { categories, outputPath, options } = req.body;
        await this.services.assetGenerator.exportAssetRequirements(categories, outputPath, options);
        res.json({ success: true, message: 'Asset requirements exported successfully' });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/generate/engine-template', async (req, res) => {
      try {
        const { campaign, options } = req.body;
        const template = await this.services.templateGenerator.generateTemplate(campaign, options);
        res.json({ success: true, template });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/export/engine-template', async (req, res) => {
      try {
        const { template, outputPath } = req.body;
        await this.services.templateGenerator.exportTemplate(template, outputPath);
        res.json({ success: true, message: 'Engine template exported successfully' });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/create/playtest-plan', async (req, res) => {
      try {
        const { campaign, objectives, options } = req.body;
        const plan = await this.services.playtestingFramework.createPlaytestPlan(campaign, objectives, options);
        res.json({ success: true, plan });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/execute/playtest-session', async (req, res) => {
      try {
        const { plan, participants } = req.body;
        const session = await this.services.playtestingFramework.executePlaytestSession(plan, participants);
        res.json({ success: true, session });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/analyze/playtest-session', async (req, res) => {
      try {
        const { sessionId } = req.body;
        const report = await this.services.playtestingFramework.analyzeSessionData(sessionId);
        res.json({ success: true, report });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/export/playtest-report', async (req, res) => {
      try {
        const { report, format, outputPath } = req.body;
        await this.services.playtestingFramework.exportReport(report, format, outputPath);
        res.json({ success: true, message: 'Playtest report exported successfully' });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/generate/achievement-system', async (req, res) => {
      try {
        const { campaign, options } = req.body;
        const achievementSystem = await this.services.achievementGenerator.generateAchievementSystem(campaign, options);
        res.json({ success: true, achievementSystem });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/export/achievement-system', async (req, res) => {
      try {
        const { achievementSystem, outputPath, options } = req.body;
        await this.services.achievementGenerator.exportAchievementSystem(achievementSystem, outputPath, options);
        res.json({ success: true, message: 'Achievement system exported successfully' });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/generate/save-system', async (req, res) => {
      try {
        const { campaign, options } = req.body;
        const saveSystem = await this.services.saveSystemDesigner.generateSaveSystem(campaign, options);
        res.json({ success: true, saveSystem });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/export/save-system', async (req, res) => {
      try {
        const { saveSystem, outputPath, options } = req.body;
        await this.services.saveSystemDesigner.exportSaveSystem(saveSystem, outputPath, options);
        res.json({ success: true, message: 'Save system exported successfully' });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/generate/monetization-plan', async (req, res) => {
      try {
        const { campaign, options } = req.body;
        const plan = await this.services.monetizationPlanner.generateMonetizationPlan(campaign, options);
        res.json({ success: true, plan });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/export/monetization-plan', async (req, res) => {
      try {
        const { plan, outputPath, options } = req.body;
        await this.services.monetizationPlanner.exportMonetizationPlan(plan, outputPath, options);
        res.json({ success: true, message: 'Monetization plan exported successfully' });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.get('/assets/list', async (req, res) => {
      try {
        const assetsDir = path.join(__dirname, '../assets');
        if (await fs.pathExists(assetsDir)) {
          const assets = await fs.readdir(assetsDir);
          res.json({ success: true, assets });
        } else {
          res.json({ success: true, assets: [] });
        }
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });

    this.app.post('/convert/full-campaign', async (req, res) => {
      try {
        const { campaign, options } = req.body;
        const results = await this.convertFullCampaign(campaign, options);
        res.json({ success: true, results });
      } catch (error) {
        res.status(500).json({ success: false, error: (error as Error).message });
      }
    });
  }

  private setupWebSocket(): void {
    this.io.on('connection', (socket) => {
      console.log('Client connected:', socket.id);

      socket.on('convert:campaign', async (data) => {
        try {
          const results = await this.convertFullCampaign(data.campaign, data.options);
          socket.emit('convert:complete', { success: true, results });
        } catch (error) {
          socket.emit('convert:error', { success: false, error: (error as Error).message });
        }
      });

      socket.on('export:all', async (data) => {
        try {
          await this.exportAllAssets(data.results, data.outputPath, data.options);
          socket.emit('export:complete', { success: true });
        } catch (error) {
          socket.emit('export:error', { success: false, error: (error as Error).message });
        }
      });

      socket.on('disconnect', () => {
        console.log('Client disconnected:', socket.id);
      });
    });
  }

  private setupEventListeners(): void {
    Object.values(this.services).forEach(service => {
      if (service instanceof EventTarget || typeof service.on === 'function') {
        const emitter = service as any;
        
        emitter.on?.('progress', (data: any) => {
          this.io.emit('conversion:progress', data);
        });

        emitter.on?.('generation:started', (data: any) => {
          this.io.emit('generation:started', data);
        });

        emitter.on?.('generation:completed', (data: any) => {
          this.io.emit('generation:completed', data);
        });

        emitter.on?.('export:started', (data: any) => {
          this.io.emit('export:started', data);
        });

        emitter.on?.('export:completed', (data: any) => {
          this.io.emit('export:completed', data);
        });
      }
    });
  }

  private async convertFullCampaign(campaign: Campaign, options: any = {}): Promise<any> {
    const results: any = {};

    if (options.includeScript !== false) {
      results.scripts = {};
      const formats = options.scriptFormats || ['markdown', 'fountain'];
      for (const format of formats) {
        results.scripts[format] = await this.services.scriptExporter.exportScript(
          campaign, 
          format as any, 
          options.scriptOptions
        );
      }
    }

    if (options.includeDialogue !== false && campaign.characters) {
      results.dialogueTrees = [];
      for (const character of campaign.characters) {
        if (character.type === 'npc') {
          const scenarios = campaign.scenes?.map(scene => ({
            id: scene.id,
            context: scene.description,
            objectives: scene.objectives || [],
            mood: scene.mood || 'neutral'
          })) || [];

          const dialogueTree = await this.services.dialogueGenerator.generateDialogueTree(
            character, 
            scenarios, 
            options.dialogueOptions
          );
          results.dialogueTrees.push(dialogueTree);
        }
      }
    }

    if (options.includeQuests !== false) {
      results.questSystems = await this.services.questConverter.convertCampaignQuests(
        campaign, 
        options.questOptions
      );
    }

    if (options.includeNPCBehavior !== false && campaign.characters) {
      results.npcBehaviors = [];
      for (const character of campaign.characters) {
        if (character.type === 'npc') {
          const context = {
            campaign: campaign.title,
            setting: campaign.setting,
            currentArc: campaign.currentArc
          };

          const behaviorScript = await this.services.npcBehavior.generateBehaviorScript(
            character, 
            context, 
            options.behaviorOptions
          );
          results.npcBehaviors.push(behaviorScript);
        }
      }
    }

    if (options.includeLevelDesign !== false && campaign.maps) {
      results.levelDesigns = [];
      for (const map of campaign.maps) {
        const encounters = campaign.encounters?.filter(enc => 
          enc.location && enc.mapId === map.id
        ) || [];

        const levelDesign = await this.services.levelGenerator.generateLevelDesign(map, encounters);
        results.levelDesigns.push(levelDesign);
      }
    }

    return results;
  }

  private async exportAllAssets(results: any, outputPath: string, options: any = {}): Promise<void> {
    await fs.ensureDir(outputPath);

    if (results.scripts) {
      const scriptsDir = path.join(outputPath, 'scripts');
      await fs.ensureDir(scriptsDir);
      
      for (const [format, script] of Object.entries(results.scripts)) {
        const filename = `campaign_script.${format}`;
        await fs.writeFile(path.join(scriptsDir, filename), script as string);
      }
    }

    if (results.dialogueTrees) {
      const dialogueDir = path.join(outputPath, 'dialogue');
      await fs.ensureDir(dialogueDir);

      for (const [index, dialogueTree] of results.dialogueTrees.entries()) {
        const formats = options.dialogueFormats || ['json'];
        for (const format of formats) {
          const filename = `dialogue_${(dialogueTree as any).characterId || index}.${format}`;
          await this.services.dialogueGenerator.exportDialogueTree(
            dialogueTree, 
            format as any, 
            path.join(dialogueDir, filename)
          );
        }
      }
    }

    if (results.questSystems) {
      const questsDir = path.join(outputPath, 'quests');
      await fs.ensureDir(questsDir);

      const formats = options.questFormats || ['json'];
      for (const format of formats) {
        const filename = `quest_system.${format}`;
        await this.services.questConverter.exportQuestSystem(
          results.questSystems, 
          format as any, 
          path.join(questsDir, filename)
        );
      }
    }

    if (results.npcBehaviors) {
      const behaviorsDir = path.join(outputPath, 'behaviors');
      await fs.ensureDir(behaviorsDir);

      for (const [index, behaviorScript] of results.npcBehaviors.entries()) {
        const formats = options.behaviorFormats || ['json'];
        for (const format of formats) {
          const filename = `behavior_${(behaviorScript as any).characterId || index}.${format}`;
          await this.services.npcBehavior.exportBehaviorScript(
            behaviorScript, 
            format as any, 
            path.join(behaviorsDir, filename)
          );
        }
      }
    }

    if (results.levelDesigns) {
      const levelsDir = path.join(outputPath, 'levels');
      await fs.ensureDir(levelsDir);

      for (const levelDesign of results.levelDesigns) {
        const formats = options.levelFormats || ['json'];
        for (const format of formats) {
          const filename = `${(levelDesign as any).name}_level.${format}`;
          const exportOptions = {
            format: format as any,
            includeGeometry: true,
            includeLighting: true,
            includeNavMesh: true,
            optimizeForEngine: true,
            textureAtlas: false,
            compressionLevel: 1
          };
          await this.services.levelGenerator.exportLevelDesign(
            levelDesign, 
            path.join(levelsDir, filename),
            exportOptions
          );
        }
      }
    }
  }

  start(port: number = 3006): void {
    this.server.listen(port, () => {
      console.log(`DMLog Game Development Service running on port ${port}`);
      console.log(`Health check: http://localhost:${port}/health`);
    });
  }
}

if (require.main === module) {
  const service = new DMLogGameDevService();
  service.start();
}

export default DMLogGameDevService;