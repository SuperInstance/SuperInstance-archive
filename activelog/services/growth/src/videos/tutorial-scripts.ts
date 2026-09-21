import crypto from 'crypto';

export interface VideoScript {
  id: string;
  title: string;
  description: string;
  category: 'onboarding' | 'features' | 'advanced' | 'troubleshooting' | 'tips';
  appVariant: 'PersonalLog' | 'BusinessLog' | 'FamilyLog' | 'FitnessLog' | 'TravelLog' | 'EducationLog' | 'all';
  targetAudience: string[];
  estimatedDuration: number;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  script: VideoScriptSection[];
  notes: string[];
  callToAction?: string;
  relatedVideos: string[];
  published: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export interface VideoScriptSection {
  id: string;
  type: 'intro' | 'demonstration' | 'explanation' | 'tip' | 'warning' | 'conclusion' | 'cta';
  title: string;
  duration: number;
  voiceover: string;
  screenActions: ScreenAction[];
  visualElements?: VisualElement[];
}

export interface ScreenAction {
  id: string;
  action: 'click' | 'type' | 'scroll' | 'hover' | 'navigate' | 'highlight' | 'zoom' | 'wait';
  element: string;
  value?: string;
  duration: number;
  notes?: string;
}

export interface VisualElement {
  id: string;
  type: 'overlay' | 'annotation' | 'arrow' | 'highlight' | 'callout' | 'transition';
  position: { x: number; y: number };
  size?: { width: number; height: number };
  content: string;
  style: {
    color: string;
    fontSize?: number;
    fontWeight?: string;
    backgroundColor?: string;
    opacity?: number;
  };
  timing: { start: number; end: number };
}

export interface VideoAnalytics {
  scriptId: string;
  views: number;
  completionRate: number;
  averageWatchTime: number;
  engagementScore: number;
  userFeedback: {
    helpful: number;
    notHelpful: number;
    comments: string[];
  };
}

export class VideoTutorialScriptSystem {
  private scripts: Map<string, VideoScript> = new Map();
  private analytics: Map<string, VideoAnalytics> = new Map();

  constructor() {
    this.initializeDefaultScripts();
  }

  private initializeDefaultScripts(): void {
    const personalLogGettingStarted = this.createGettingStartedScript();
    const businessLogTeamCollab = this.createBusinessCollaborationScript();
    const fitnessLogWorkout = this.createFitnessWorkoutScript();
    const advancedSearch = this.createAdvancedSearchScript();
    const dataExport = this.createDataExportScript();

    [personalLogGettingStarted, businessLogTeamCollab, fitnessLogWorkout, advancedSearch, dataExport]
      .forEach(script => {
        this.scripts.set(script.id, script);
        this.analytics.set(script.id, {
          scriptId: script.id,
          views: Math.floor(Math.random() * 10000),
          completionRate: Math.random() * 100,
          averageWatchTime: Math.random() * script.estimatedDuration,
          engagementScore: Math.random() * 10,
          userFeedback: {
            helpful: Math.floor(Math.random() * 100),
            notHelpful: Math.floor(Math.random() * 20),
            comments: []
          }
        });
      });
  }

  private createGettingStartedScript(): VideoScript {
    return {
      id: crypto.randomUUID(),
      title: 'Getting Started with PersonalLog',
      description: 'A complete walkthrough of creating your first personal log entry',
      category: 'onboarding',
      appVariant: 'PersonalLog',
      targetAudience: ['new-users', 'beginners'],
      estimatedDuration: 180,
      difficulty: 'beginner',
      published: true,
      createdAt: new Date(),
      updatedAt: new Date(),
      notes: [
        'Keep pace slow for beginners',
        'Emphasize privacy and security',
        'Show multiple entry types'
      ],
      callToAction: 'Create your first entry today!',
      relatedVideos: [],
      script: [
        {
          id: crypto.randomUUID(),
          type: 'intro',
          title: 'Welcome to PersonalLog',
          duration: 15,
          voiceover: 'Welcome to PersonalLog! I\'m going to show you how to create your very first personal log entry in just a few simple steps.',
          screenActions: [
            {
              id: crypto.randomUUID(),
              action: 'navigate',
              element: 'dashboard',
              duration: 3,
              notes: 'Show clean dashboard'
            },
            {
              id: crypto.randomUUID(),
              action: 'wait',
              element: 'dashboard',
              duration: 2
            }
          ],
          visualElements: [
            {
              id: crypto.randomUUID(),
              type: 'overlay',
              position: { x: 50, y: 20 },
              content: 'PersonalLog Tutorial',
              style: {
                color: '#ffffff',
                fontSize: 24,
                fontWeight: 'bold',
                backgroundColor: '#007bff',
                opacity: 0.9
              },
              timing: { start: 0, end: 15 }
            }
          ]
        },
        {
          id: crypto.randomUUID(),
          type: 'demonstration',
          title: 'Creating a New Entry',
          duration: 45,
          voiceover: 'To create your first entry, simply click the "New Entry" button. You\'ll see a clean, simple editor where you can write your thoughts, experiences, or anything you want to remember.',
          screenActions: [
            {
              id: crypto.randomUUID(),
              action: 'highlight',
              element: '[data-tour="new-entry-button"]',
              duration: 3,
              notes: 'Highlight the new entry button'
            },
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-tour="new-entry-button"]',
              duration: 2
            },
            {
              id: crypto.randomUUID(),
              action: 'wait',
              element: 'editor',
              duration: 2,
              notes: 'Wait for editor to load'
            },
            {
              id: crypto.randomUUID(),
              action: 'type',
              element: '[data-tour="title-input"]',
              value: 'My First PersonalLog Entry',
              duration: 4
            },
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-tour="editor"]',
              duration: 1
            },
            {
              id: crypto.randomUUID(),
              action: 'type',
              element: '[data-tour="editor"]',
              value: 'Today I started using PersonalLog to document my thoughts and experiences. I\'m excited to see how this helps me reflect and remember important moments.',
              duration: 8
            }
          ],
          visualElements: [
            {
              id: crypto.randomUUID(),
              type: 'arrow',
              position: { x: 200, y: 100 },
              content: 'Click here to start',
              style: {
                color: '#007bff',
                fontSize: 14
              },
              timing: { start: 0, end: 5 }
            }
          ]
        },
        {
          id: crypto.randomUUID(),
          type: 'explanation',
          title: 'Using Categories',
          duration: 30,
          voiceover: 'Categories help you organize your entries. You can create custom categories or use the suggested ones. For this entry, let\'s add it to the "Daily Life" category.',
          screenActions: [
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-tour="categories"]',
              duration: 2
            },
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-category="daily-life"]',
              duration: 2
            },
            {
              id: crypto.randomUUID(),
              action: 'wait',
              element: 'categories',
              duration: 3
            }
          ]
        },
        {
          id: crypto.randomUUID(),
          type: 'demonstration',
          title: 'Saving Your Entry',
          duration: 20,
          voiceover: 'When you\'re finished writing, click the Save button. Your entry is now securely stored and only visible to you.',
          screenActions: [
            {
              id: crypto.randomUUID(),
              action: 'highlight',
              element: '[data-tour="save-button"]',
              duration: 3
            },
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-tour="save-button"]',
              duration: 2
            },
            {
              id: crypto.randomUUID(),
              action: 'wait',
              element: 'success-message',
              duration: 3
            }
          ]
        },
        {
          id: crypto.randomUUID(),
          type: 'conclusion',
          title: 'You\'re All Set!',
          duration: 25,
          voiceover: 'Congratulations! You\'ve created your first PersonalLog entry. Remember, the key to successful journaling is consistency. Try to write something every day, even if it\'s just a few sentences.',
          screenActions: [
            {
              id: crypto.randomUUID(),
              action: 'navigate',
              element: 'dashboard',
              duration: 3
            },
            {
              id: crypto.randomUUID(),
              action: 'scroll',
              element: 'recent-entries',
              duration: 5
            }
          ],
          visualElements: [
            {
              id: crypto.randomUUID(),
              type: 'overlay',
              position: { x: 50, y: 50 },
              content: 'Well done! 🎉',
              style: {
                color: '#28a745',
                fontSize: 20,
                fontWeight: 'bold'
              },
              timing: { start: 15, end: 25 }
            }
          ]
        },
        {
          id: crypto.randomUUID(),
          type: 'cta',
          title: 'Next Steps',
          duration: 15,
          voiceover: 'Ready to explore more features? Check out our advanced tutorials or start creating more entries to build your personal archive.',
          screenActions: [
            {
              id: crypto.randomUUID(),
              action: 'highlight',
              element: 'help-menu',
              duration: 5
            }
          ]
        }
      ]
    };
  }

  private createBusinessCollaborationScript(): VideoScript {
    return {
      id: crypto.randomUUID(),
      title: 'Team Collaboration in BusinessLog',
      description: 'Learn how to collaborate effectively with your team using BusinessLog features',
      category: 'features',
      appVariant: 'BusinessLog',
      targetAudience: ['business-users', 'team-leaders'],
      estimatedDuration: 240,
      difficulty: 'intermediate',
      published: true,
      createdAt: new Date(),
      updatedAt: new Date(),
      notes: [
        'Focus on real business scenarios',
        'Show different user roles',
        'Emphasize security features'
      ],
      callToAction: 'Invite your team to BusinessLog today!',
      relatedVideos: [],
      script: [
        {
          id: crypto.randomUUID(),
          type: 'intro',
          title: 'Team Collaboration Overview',
          duration: 20,
          voiceover: 'BusinessLog makes team collaboration seamless. In this tutorial, I\'ll show you how to share logs, manage permissions, and work together effectively.',
          screenActions: [
            {
              id: crypto.randomUUID(),
              action: 'navigate',
              element: 'team-dashboard',
              duration: 5
            }
          ]
        },
        {
          id: crypto.randomUUID(),
          type: 'demonstration',
          title: 'Inviting Team Members',
          duration: 60,
          voiceover: 'First, let\'s invite team members. Go to the Team section and click "Invite Members". You can set different permission levels for each person.',
          screenActions: [
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-nav="team"]',
              duration: 2
            },
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-action="invite-members"]',
              duration: 2
            },
            {
              id: crypto.randomUUID(),
              action: 'type',
              element: '[data-input="email"]',
              value: 'colleague@company.com',
              duration: 5
            },
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-select="role"]',
              duration: 2
            },
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-role="editor"]',
              duration: 2
            }
          ]
        },
        {
          id: crypto.randomUUID(),
          type: 'demonstration',
          title: 'Sharing and Collaborating on Logs',
          duration: 80,
          voiceover: 'Now let\'s create a shared project log. Team members can add comments, make edits, and track progress together in real-time.',
          screenActions: [
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-action="new-project-log"]',
              duration: 2
            },
            {
              id: crypto.randomUUID(),
              action: 'type',
              element: '[data-input="project-title"]',
              value: 'Q4 Marketing Campaign',
              duration: 4
            },
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-action="add-collaborators"]',
              duration: 3
            }
          ]
        }
      ]
    };
  }

  private createFitnessWorkoutScript(): VideoScript {
    return {
      id: crypto.randomUUID(),
      title: 'Logging Your First Workout',
      description: 'Step-by-step guide to tracking your workouts in FitnessLog',
      category: 'onboarding',
      appVariant: 'FitnessLog',
      targetAudience: ['fitness-beginners', 'new-users'],
      estimatedDuration: 200,
      difficulty: 'beginner',
      published: true,
      createdAt: new Date(),
      updatedAt: new Date(),
      notes: [
        'Show both gym and home workouts',
        'Emphasize proper form notes',
        'Include progress tracking'
      ],
      callToAction: 'Start tracking your fitness journey!',
      relatedVideos: [],
      script: [
        {
          id: crypto.randomUUID(),
          type: 'intro',
          title: 'Welcome to FitnessLog',
          duration: 20,
          voiceover: 'Ready to take your fitness tracking to the next level? I\'ll show you how to log your first workout and start building your fitness history.',
          screenActions: [
            {
              id: crypto.randomUUID(),
              action: 'navigate',
              element: 'fitness-dashboard',
              duration: 3
            }
          ]
        },
        {
          id: crypto.randomUUID(),
          type: 'demonstration',
          title: 'Starting a New Workout',
          duration: 60,
          voiceover: 'Click "New Workout" to get started. You can choose from preset workout types or create a custom workout.',
          screenActions: [
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-action="new-workout"]',
              duration: 2
            },
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-workout-type="strength"]',
              duration: 3
            },
            {
              id: crypto.randomUUID(),
              action: 'type',
              element: '[data-input="workout-name"]',
              value: 'Upper Body Strength',
              duration: 4
            }
          ]
        },
        {
          id: crypto.randomUUID(),
          type: 'demonstration',
          title: 'Adding Exercises and Sets',
          duration: 90,
          voiceover: 'Now let\'s add exercises. Search for exercises in our database or create custom ones. For each exercise, you can track sets, reps, weight, and rest time.',
          screenActions: [
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-action="add-exercise"]',
              duration: 2
            },
            {
              id: crypto.randomUUID(),
              action: 'type',
              element: '[data-input="exercise-search"]',
              value: 'bench press',
              duration: 3
            },
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-exercise="bench-press"]',
              duration: 2
            }
          ]
        }
      ]
    };
  }

  private createAdvancedSearchScript(): VideoScript {
    return {
      id: crypto.randomUUID(),
      title: 'Advanced Search and Filtering',
      description: 'Master the search features to quickly find any log entry',
      category: 'advanced',
      appVariant: 'all',
      targetAudience: ['power-users', 'experienced-users'],
      estimatedDuration: 180,
      difficulty: 'advanced',
      published: true,
      createdAt: new Date(),
      updatedAt: new Date(),
      notes: [
        'Show complex search queries',
        'Demonstrate filter combinations',
        'Include saved search feature'
      ],
      callToAction: 'Master your data with advanced search!',
      relatedVideos: [],
      script: [
        {
          id: crypto.randomUUID(),
          type: 'intro',
          title: 'Advanced Search Features',
          duration: 15,
          voiceover: 'As your log grows, finding specific entries becomes crucial. Let me show you how to use our powerful search and filtering tools.',
          screenActions: [
            {
              id: crypto.randomUUID(),
              action: 'navigate',
              element: 'search-page',
              duration: 3
            }
          ]
        },
        {
          id: crypto.randomUUID(),
          type: 'demonstration',
          title: 'Using Search Operators',
          duration: 90,
          voiceover: 'You can use operators like AND, OR, and quotes for exact phrases. Date ranges, categories, and tags can all be combined for precise results.',
          screenActions: [
            {
              id: crypto.randomUUID(),
              action: 'type',
              element: '[data-input="search"]',
              value: '"workout routine" AND category:fitness',
              duration: 8
            },
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-action="search"]',
              duration: 2
            }
          ]
        }
      ]
    };
  }

  private createDataExportScript(): VideoScript {
    return {
      id: crypto.randomUUID(),
      title: 'Exporting and Backing Up Your Data',
      description: 'Learn how to export your logs for backup or analysis',
      category: 'features',
      appVariant: 'all',
      targetAudience: ['all-users'],
      estimatedDuration: 150,
      difficulty: 'intermediate',
      published: true,
      createdAt: new Date(),
      updatedAt: new Date(),
      notes: [
        'Emphasize data ownership',
        'Show different export formats',
        'Include backup best practices'
      ],
      callToAction: 'Keep your data safe with regular backups!',
      relatedVideos: [],
      script: [
        {
          id: crypto.randomUUID(),
          type: 'intro',
          title: 'Data Export Options',
          duration: 20,
          voiceover: 'Your data belongs to you. I\'ll show you how to export your logs in various formats for backup, analysis, or migration.',
          screenActions: [
            {
              id: crypto.randomUUID(),
              action: 'navigate',
              element: 'export-page',
              duration: 3
            }
          ]
        },
        {
          id: crypto.randomUUID(),
          type: 'demonstration',
          title: 'Export Formats and Options',
          duration: 80,
          voiceover: 'You can export as PDF for reading, CSV for analysis, or JSON for technical use. Choose your date range and filtering options.',
          screenActions: [
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-format="pdf"]',
              duration: 2
            },
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-range="last-year"]',
              duration: 2
            },
            {
              id: crypto.randomUUID(),
              action: 'click',
              element: '[data-action="start-export"]',
              duration: 3
            }
          ]
        }
      ]
    };
  }

  async createScript(scriptData: Omit<VideoScript, 'id' | 'createdAt' | 'updatedAt'>): Promise<VideoScript> {
    const script: VideoScript = {
      ...scriptData,
      id: crypto.randomUUID(),
      createdAt: new Date(),
      updatedAt: new Date()
    };

    this.scripts.set(script.id, script);
    return script;
  }

  async updateScript(scriptId: string, updates: Partial<VideoScript>): Promise<boolean> {
    const script = this.scripts.get(scriptId);
    if (!script) return false;

    Object.assign(script, { ...updates, updatedAt: new Date() });
    return true;
  }

  async deleteScript(scriptId: string): Promise<boolean> {
    this.scripts.delete(scriptId);
    this.analytics.delete(scriptId);
    return true;
  }

  async getScript(scriptId: string): Promise<VideoScript | null> {
    return this.scripts.get(scriptId) || null;
  }

  async getScriptsByCategory(category: VideoScript['category'], appVariant?: string): Promise<VideoScript[]> {
    return Array.from(this.scripts.values())
      .filter(script => {
        if (script.category !== category) return false;
        if (appVariant && script.appVariant !== 'all' && script.appVariant !== appVariant) return false;
        return script.published;
      })
      .sort((a, b) => a.title.localeCompare(b.title));
  }

  async getScriptsByAppVariant(appVariant: string): Promise<VideoScript[]> {
    return Array.from(this.scripts.values())
      .filter(script => {
        if (!script.published) return false;
        return script.appVariant === appVariant || script.appVariant === 'all';
      })
      .sort((a, b) => {
        const categoryOrder = ['onboarding', 'features', 'advanced', 'troubleshooting', 'tips'];
        const aCategoryIndex = categoryOrder.indexOf(a.category);
        const bCategoryIndex = categoryOrder.indexOf(b.category);
        
        if (aCategoryIndex !== bCategoryIndex) {
          return aCategoryIndex - bCategoryIndex;
        }
        
        return a.title.localeCompare(b.title);
      });
  }

  async generateScriptDocument(scriptId: string, format: 'markdown' | 'html' | 'plain'): Promise<string> {
    const script = this.scripts.get(scriptId);
    if (!script) return '';

    let document = '';

    if (format === 'markdown') {
      document += `# ${script.title}\n\n`;
      document += `**Description:** ${script.description}\n\n`;
      document += `**Duration:** ${Math.floor(script.estimatedDuration / 60)}:${(script.estimatedDuration % 60).toString().padStart(2, '0')}\n\n`;
      document += `**App:** ${script.appVariant}\n\n`;
      document += `**Difficulty:** ${script.difficulty}\n\n`;
      
      if (script.notes.length > 0) {
        document += `## Production Notes\n\n`;
        script.notes.forEach(note => {
          document += `- ${note}\n`;
        });
        document += '\n';
      }

      document += `## Script Sections\n\n`;
      
      script.script.forEach((section, index) => {
        document += `### ${index + 1}. ${section.title} (${section.duration}s)\n\n`;
        document += `**Type:** ${section.type}\n\n`;
        document += `**Voiceover:**\n> ${section.voiceover}\n\n`;
        
        if (section.screenActions.length > 0) {
          document += `**Screen Actions:**\n`;
          section.screenActions.forEach((action, actionIndex) => {
            document += `${actionIndex + 1}. ${action.action.toUpperCase()}`;
            if (action.element) document += ` on "${action.element}"`;
            if (action.value) document += ` with value "${action.value}"`;
            document += ` (${action.duration}s)`;
            if (action.notes) document += ` - ${action.notes}`;
            document += '\n';
          });
          document += '\n';
        }

        if (section.visualElements && section.visualElements.length > 0) {
          document += `**Visual Elements:**\n`;
          section.visualElements.forEach(element => {
            document += `- ${element.type}: "${element.content}" at (${element.position.x}, ${element.position.y}) from ${element.timing.start}s to ${element.timing.end}s\n`;
          });
          document += '\n';
        }
      });

      if (script.callToAction) {
        document += `## Call to Action\n\n${script.callToAction}\n\n`;
      }

    } else if (format === 'html') {
      document += `<!DOCTYPE html><html><head><title>${script.title}</title></head><body>`;
      document += `<h1>${script.title}</h1>`;
      document += `<p><strong>Description:</strong> ${script.description}</p>`;
      document += `<p><strong>Duration:</strong> ${Math.floor(script.estimatedDuration / 60)}:${(script.estimatedDuration % 60).toString().padStart(2, '0')}</p>`;
      
      script.script.forEach((section, index) => {
        document += `<h2>${index + 1}. ${section.title}</h2>`;
        document += `<p><strong>Voiceover:</strong> ${section.voiceover}</p>`;
      });
      
      document += `</body></html>`;

    } else {
      document += `${script.title}\n`;
      document += `${script.description}\n\n`;
      
      script.script.forEach((section, index) => {
        document += `${index + 1}. ${section.title}\n`;
        document += `${section.voiceover}\n\n`;
      });
    }

    return document;
  }

  async generateStoryboard(scriptId: string): Promise<{ sections: any[]; totalDuration: number }> {
    const script = this.scripts.get(scriptId);
    if (!script) return { sections: [], totalDuration: 0 };

    const storyboard = script.script.map((section, index) => {
      const startTime = script.script.slice(0, index).reduce((sum, s) => sum + s.duration, 0);
      
      return {
        sectionNumber: index + 1,
        title: section.title,
        type: section.type,
        startTime,
        endTime: startTime + section.duration,
        duration: section.duration,
        voiceover: section.voiceover,
        keyFrames: section.screenActions.map((action, actionIndex) => {
          const actionStartTime = startTime + section.screenActions.slice(0, actionIndex).reduce((sum, a) => sum + a.duration, 0);
          
          return {
            time: actionStartTime,
            action: action.action,
            element: action.element,
            value: action.value,
            notes: action.notes
          };
        }),
        visualElements: section.visualElements || []
      };
    });

    return {
      sections: storyboard,
      totalDuration: script.estimatedDuration
    };
  }

  async getScriptAnalytics(scriptId: string): Promise<VideoAnalytics | null> {
    return this.analytics.get(scriptId) || null;
  }

  async updateAnalytics(scriptId: string, data: Partial<VideoAnalytics>): Promise<boolean> {
    const analytics = this.analytics.get(scriptId);
    if (!analytics) return false;

    Object.assign(analytics, data);
    return true;
  }

  async getTopPerformingScripts(limit: number = 10): Promise<{ script: VideoScript; analytics: VideoAnalytics }[]> {
    const results = Array.from(this.scripts.entries())
      .map(([id, script]) => ({
        script,
        analytics: this.analytics.get(id)!
      }))
      .filter(item => item.analytics && item.script.published)
      .sort((a, b) => b.analytics.engagementScore - a.analytics.engagementScore)
      .slice(0, limit);

    return results;
  }

  async searchScripts(query: string, filters?: {
    category?: string;
    appVariant?: string;
    difficulty?: string;
  }): Promise<VideoScript[]> {
    const queryLower = query.toLowerCase();
    
    return Array.from(this.scripts.values())
      .filter(script => {
        if (!script.published) return false;
        
        if (filters?.category && script.category !== filters.category) return false;
        if (filters?.appVariant && script.appVariant !== 'all' && script.appVariant !== filters.appVariant) return false;
        if (filters?.difficulty && script.difficulty !== filters.difficulty) return false;
        
        return (
          script.title.toLowerCase().includes(queryLower) ||
          script.description.toLowerCase().includes(queryLower) ||
          script.script.some(section => 
            section.title.toLowerCase().includes(queryLower) ||
            section.voiceover.toLowerCase().includes(queryLower)
          )
        );
      })
      .sort((a, b) => {
        const aAnalytics = this.analytics.get(a.id);
        const bAnalytics = this.analytics.get(b.id);
        
        if (aAnalytics && bAnalytics) {
          return bAnalytics.views - aAnalytics.views;
        }
        
        return a.title.localeCompare(b.title);
      });
  }

  getAllScripts(): VideoScript[] {
    return Array.from(this.scripts.values());
  }

  getPublishedScripts(): VideoScript[] {
    return Array.from(this.scripts.values()).filter(script => script.published);
  }

  async exportScriptsDatabase(): Promise<any> {
    return {
      scripts: Array.from(this.scripts.values()),
      analytics: Array.from(this.analytics.entries()).map(([id, analytics]) => ({
        scriptId: id,
        ...analytics
      })),
      exportedAt: new Date()
    };
  }
}

export const tutorialScripts = new VideoTutorialScriptSystem();