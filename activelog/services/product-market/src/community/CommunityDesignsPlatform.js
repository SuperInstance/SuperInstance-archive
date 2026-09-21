import { EventEmitter } from 'events';
import crypto from 'crypto';

class CommunityDesignsPlatform extends EventEmitter {
    constructor() {
        super();
        this.designs = new Map();
        this.users = new Map();
        this.forums = new Map();
        this.collaborations = new Map();
        this.competitions = new Map();
        this.ratings = new Map();
        this.comments = new Map();
        this.following = new Map();
        this.featured = new Map();
        
        this.initializeData();
    }

    initializeData() {
        // Initialize sample community users
        const sampleUsers = [
            {
                id: 'user_001',
                username: 'TechMaker2024',
                display_name: 'Alex Chen',
                reputation: 4850,
                level: 'Expert',
                specialties: ['IoT', 'Sensors', 'Hardware Design'],
                designs_published: 23,
                collaborations: 15,
                followers: 342,
                following: 127,
                badges: ['Innovation Award', 'Community Helper', 'Top Contributor'],
                joined_date: new Date('2023-01-15')
            },
            {
                id: 'user_002',
                username: 'OpenSourceBuilder',
                display_name: 'Maya Rodriguez',
                reputation: 3920,
                level: 'Advanced',
                specialties: ['3D Printing', 'Electronics', 'Solar Power'],
                designs_published: 31,
                collaborations: 22,
                followers: 278,
                following: 89,
                badges: ['Eco Warrior', 'Design Master', 'Collaboration Star'],
                joined_date: new Date('2023-03-22')
            },
            {
                id: 'user_003',
                username: 'FishingTechGuru',
                display_name: 'Sam Peterson',
                reputation: 2750,
                level: 'Intermediate',
                specialties: ['Marine Tech', 'Fish Counters', 'Waterproof Design'],
                designs_published: 18,
                collaborations: 8,
                followers: 156,
                following: 203,
                badges: ['Marine Expert', 'Problem Solver'],
                joined_date: new Date('2023-06-10')
            }
        ];

        sampleUsers.forEach(user => {
            this.users.set(user.id, user);
        });

        // Initialize sample community designs
        const sampleDesigns = [
            {
                id: 'community_design_001',
                title: 'Ultra-Low Power Fish Counter V3',
                author_id: 'user_003',
                description: 'Advanced fish counting system with AI image recognition and 6-month battery life',
                category: 'Fish Counters',
                tags: ['fish-counting', 'ai', 'low-power', 'marine', 'solar'],
                status: 'published',
                visibility: 'public',
                license: 'Creative Commons BY-SA',
                version: '3.2.1',
                downloads: 1247,
                forks: 23,
                stars: 189,
                views: 4521,
                created_date: new Date('2024-01-15'),
                last_updated: new Date('2024-08-10'),
                files: [
                    { name: 'schematic.pdf', type: 'schematic', size: '2.3MB' },
                    { name: 'pcb_design.gerber', type: 'pcb', size: '1.8MB' },
                    { name: 'ai_model.py', type: 'code', size: '45KB' },
                    { name: 'assembly_guide.md', type: 'documentation', size: '12KB' }
                ],
                specifications: {
                    power_consumption: '15mW average',
                    detection_accuracy: '96.5%',
                    supported_species: 25,
                    operating_temperature: '-20°C to 60°C',
                    waterproof_rating: 'IP68'
                },
                build_difficulty: 'Intermediate',
                estimated_cost: '$185',
                build_time: '8-12 hours',
                tools_required: ['Soldering Iron', 'Multimeter', '3D Printer', 'Drill'],
                rating: {
                    average: 4.7,
                    count: 89,
                    breakdown: { 5: 67, 4: 18, 3: 3, 2: 1, 1: 0 }
                }
            },
            {
                id: 'community_design_002',
                title: 'Modular Solar Camera System',
                author_id: 'user_002',
                description: 'Expandable solar-powered security camera with wireless mesh networking',
                category: 'Solar Cameras',
                tags: ['solar', 'camera', 'wireless', 'mesh', 'security', 'modular'],
                status: 'published',
                visibility: 'public',
                license: 'MIT',
                version: '2.1.0',
                downloads: 892,
                forks: 31,
                stars: 156,
                views: 3240,
                created_date: new Date('2024-02-20'),
                last_updated: new Date('2024-08-15'),
                files: [
                    { name: 'housing_design.stl', type: '3d_model', size: '5.2MB' },
                    { name: 'electronics_bom.csv', type: 'bom', size: '8KB' },
                    { name: 'firmware.ino', type: 'code', size: '78KB' },
                    { name: 'mesh_protocol.py', type: 'code', size: '23KB' }
                ],
                specifications: {
                    solar_panel: '20W monocrystalline',
                    battery_capacity: '10000mAh',
                    video_resolution: '1080p',
                    wireless_range: '500m (line of sight)',
                    storage: '32GB microSD'
                },
                build_difficulty: 'Advanced',
                estimated_cost: '$295',
                build_time: '12-16 hours',
                tools_required: ['3D Printer', 'Soldering Station', 'Drill Press', 'Crimping Tool'],
                rating: {
                    average: 4.5,
                    count: 62,
                    breakdown: { 5: 42, 4: 15, 3: 4, 2: 1, 1: 0 }
                }
            },
            {
                id: 'community_design_003',
                title: 'Smart Sensor Hub with AI',
                author_id: 'user_001',
                description: 'Central hub for multiple sensor types with edge AI processing',
                category: 'Sensor Packages',
                tags: ['sensors', 'ai', 'edge-computing', 'iot', 'hub', 'wireless'],
                status: 'published',
                visibility: 'public',
                license: 'Apache 2.0',
                version: '1.5.2',
                downloads: 1456,
                forks: 47,
                stars: 234,
                views: 6789,
                created_date: new Date('2023-11-08'),
                last_updated: new Date('2024-08-12'),
                files: [
                    { name: 'main_board.kicad_pro', type: 'pcb', size: '3.1MB' },
                    { name: 'ai_inference.cpp', type: 'code', size: '156KB' },
                    { name: 'sensor_drivers.h', type: 'code', size: '89KB' },
                    { name: 'enclosure.step', type: '3d_model', size: '8.7MB' }
                ],
                specifications: {
                    supported_sensors: '12 types',
                    processing_power: 'ARM Cortex-M7 480MHz',
                    wireless: 'WiFi 6, Bluetooth 5.2, LoRa',
                    storage: '1GB Flash, 512MB RAM',
                    power_options: 'Solar, Battery, USB-C'
                },
                build_difficulty: 'Expert',
                estimated_cost: '$425',
                build_time: '20-25 hours',
                tools_required: ['Hot Air Station', 'Microscope', 'Oscilloscope', 'SMD Soldering'],
                rating: {
                    average: 4.8,
                    count: 127,
                    breakdown: { 5: 102, 4: 21, 3: 3, 2: 1, 1: 0 }
                }
            }
        ];

        sampleDesigns.forEach(design => {
            this.designs.set(design.id, design);
        });

        // Initialize sample forums
        const sampleForums = [
            {
                id: 'forum_001',
                title: 'Fish Counter Innovations',
                description: 'Discuss improvements and innovations in fish counting technology',
                category: 'Fish Counters',
                moderators: ['user_003'],
                members: 342,
                posts: 1247,
                created_date: new Date('2023-12-01'),
                latest_activity: new Date('2024-08-23')
            },
            {
                id: 'forum_002',
                title: 'Solar Power Solutions',
                description: 'Share solar power designs and troubleshooting tips',
                category: 'Solar Systems',
                moderators: ['user_002'],
                members: 578,
                posts: 2156,
                created_date: new Date('2023-10-15'),
                latest_activity: new Date('2024-08-24')
            },
            {
                id: 'forum_003',
                title: 'AI Integration Help',
                description: 'Get help integrating AI into your hardware projects',
                category: 'AI & ML',
                moderators: ['user_001'],
                members: 891,
                posts: 3421,
                created_date: new Date('2023-09-20'),
                latest_activity: new Date('2024-08-24')
            }
        ];

        sampleForums.forEach(forum => {
            this.forums.set(forum.id, forum);
        });

        // Initialize sample collaborations
        const sampleCollaborations = [
            {
                id: 'collab_001',
                title: 'Universal Fish Species Database',
                description: 'Creating a comprehensive database of fish species for AI training',
                initiator_id: 'user_003',
                participants: ['user_001', 'user_002'],
                status: 'active',
                progress: 65,
                start_date: new Date('2024-06-01'),
                target_completion: new Date('2024-10-15'),
                contributions: {
                    'user_003': 'Project lead, marine expertise',
                    'user_001': 'AI model development',
                    'user_002': 'Data collection and validation'
                }
            },
            {
                id: 'collab_002',
                title: 'Open Source Solar Controller',
                description: 'Developing an advanced MPPT solar charge controller',
                initiator_id: 'user_002',
                participants: ['user_001'],
                status: 'active',
                progress: 40,
                start_date: new Date('2024-07-10'),
                target_completion: new Date('2024-11-30'),
                contributions: {
                    'user_002': 'Hardware design and testing',
                    'user_001': 'Firmware and optimization algorithms'
                }
            }
        ];

        sampleCollaborations.forEach(collab => {
            this.collaborations.set(collab.id, collab);
        });

        // Initialize sample competitions
        const sampleCompetitions = [
            {
                id: 'comp_001',
                title: 'Most Innovative Fish Counter 2024',
                description: 'Design the most innovative and practical fish counting solution',
                organizer_id: 'user_001',
                status: 'active',
                start_date: new Date('2024-08-01'),
                end_date: new Date('2024-10-31'),
                registration_deadline: new Date('2024-09-30'),
                prizes: {
                    first: '$2000 + Hardware Kit',
                    second: '$1000 + Components',
                    third: '$500 + Recognition'
                },
                participants: 47,
                submissions: 12,
                criteria: ['Innovation', 'Practicality', 'Cost Effectiveness', 'Documentation'],
                judges: ['user_002', 'user_003']
            },
            {
                id: 'comp_002',
                title: 'Ultra Low Power Challenge',
                description: 'Create the most energy-efficient sensor system',
                organizer_id: 'user_002',
                status: 'planning',
                start_date: new Date('2024-09-15'),
                end_date: new Date('2024-12-15'),
                registration_deadline: new Date('2024-10-15'),
                prizes: {
                    first: '$1500 + Solar Kit',
                    second: '$750 + Battery Pack',
                    third: '$300 + Components'
                },
                participants: 23,
                submissions: 0,
                criteria: ['Power Efficiency', 'Functionality', 'Real-world Application'],
                judges: ['user_001', 'user_003']
            }
        ];

        sampleCompetitions.forEach(comp => {
            this.competitions.set(comp.id, comp);
        });
    }

    generateId(prefix) {
        return `${prefix}_${crypto.randomBytes(8).toString('hex')}`;
    }

    // Design Management
    async publishDesign(designData) {
        try {
            const design = {
                id: this.generateId('community_design'),
                title: designData.title,
                author_id: designData.author_id,
                description: designData.description,
                category: designData.category,
                tags: designData.tags || [],
                status: 'published',
                visibility: designData.visibility || 'public',
                license: designData.license,
                version: '1.0.0',
                downloads: 0,
                forks: 0,
                stars: 0,
                views: 0,
                created_date: new Date(),
                last_updated: new Date(),
                files: designData.files || [],
                specifications: designData.specifications || {},
                build_difficulty: designData.build_difficulty,
                estimated_cost: designData.estimated_cost,
                build_time: designData.build_time,
                tools_required: designData.tools_required || [],
                rating: {
                    average: 0,
                    count: 0,
                    breakdown: { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 }
                }
            };

            this.designs.set(design.id, design);
            this.emit('design_published', design);

            return {
                success: true,
                design_id: design.id,
                message: 'Design published successfully'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async searchDesigns(searchParams = {}) {
        try {
            let designs = Array.from(this.designs.values());

            // Apply filters
            if (searchParams.category) {
                designs = designs.filter(d => d.category === searchParams.category);
            }

            if (searchParams.tags && searchParams.tags.length > 0) {
                designs = designs.filter(d => 
                    searchParams.tags.some(tag => d.tags.includes(tag))
                );
            }

            if (searchParams.difficulty) {
                designs = designs.filter(d => d.build_difficulty === searchParams.difficulty);
            }

            if (searchParams.license) {
                designs = designs.filter(d => d.license === searchParams.license);
            }

            if (searchParams.min_rating) {
                designs = designs.filter(d => d.rating.average >= searchParams.min_rating);
            }

            if (searchParams.search_text) {
                const text = searchParams.search_text.toLowerCase();
                designs = designs.filter(d => 
                    d.title.toLowerCase().includes(text) ||
                    d.description.toLowerCase().includes(text) ||
                    d.tags.some(tag => tag.toLowerCase().includes(text))
                );
            }

            // Apply sorting
            if (searchParams.sort_by) {
                switch (searchParams.sort_by) {
                    case 'popularity':
                        designs.sort((a, b) => (b.stars + b.downloads) - (a.stars + a.downloads));
                        break;
                    case 'rating':
                        designs.sort((a, b) => b.rating.average - a.rating.average);
                        break;
                    case 'recent':
                        designs.sort((a, b) => new Date(b.created_date) - new Date(a.created_date));
                        break;
                    case 'updated':
                        designs.sort((a, b) => new Date(b.last_updated) - new Date(a.last_updated));
                        break;
                    default:
                        designs.sort((a, b) => b.views - a.views);
                }
            }

            // Apply pagination
            const page = searchParams.page || 1;
            const limit = searchParams.limit || 20;
            const startIndex = (page - 1) * limit;
            const endIndex = startIndex + limit;
            const paginatedDesigns = designs.slice(startIndex, endIndex);

            return {
                success: true,
                designs: paginatedDesigns,
                total: designs.length,
                page: page,
                pages: Math.ceil(designs.length / limit),
                filters_applied: searchParams
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async rateDesign(designId, userId, rating, review = '') {
        try {
            const design = this.designs.get(designId);
            if (!design) {
                throw new Error('Design not found');
            }

            const ratingId = this.generateId('rating');
            const ratingData = {
                id: ratingId,
                design_id: designId,
                user_id: userId,
                rating: Math.max(1, Math.min(5, rating)),
                review: review,
                date: new Date(),
                helpful_votes: 0
            };

            this.ratings.set(ratingId, ratingData);

            // Update design rating
            design.rating.count += 1;
            design.rating.breakdown[rating] += 1;
            
            const totalRating = Object.entries(design.rating.breakdown)
                .reduce((sum, [stars, count]) => sum + (parseInt(stars) * count), 0);
            design.rating.average = Math.round((totalRating / design.rating.count) * 10) / 10;

            this.designs.set(designId, design);
            this.emit('design_rated', { design_id: designId, rating: ratingData });

            return {
                success: true,
                rating_id: ratingId,
                new_average: design.rating.average
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async forkDesign(designId, userId, modifications = {}) {
        try {
            const originalDesign = this.designs.get(designId);
            if (!originalDesign) {
                throw new Error('Original design not found');
            }

            const forkedDesign = {
                ...originalDesign,
                id: this.generateId('community_design'),
                title: modifications.title || `${originalDesign.title} (Fork)`,
                author_id: userId,
                description: modifications.description || originalDesign.description,
                forked_from: designId,
                version: '1.0.0-fork',
                downloads: 0,
                forks: 0,
                stars: 0,
                views: 0,
                created_date: new Date(),
                last_updated: new Date(),
                rating: {
                    average: 0,
                    count: 0,
                    breakdown: { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 }
                }
            };

            // Update specifications if provided
            if (modifications.specifications) {
                forkedDesign.specifications = { ...forkedDesign.specifications, ...modifications.specifications };
            }

            this.designs.set(forkedDesign.id, forkedDesign);

            // Update original design fork count
            originalDesign.forks += 1;
            this.designs.set(designId, originalDesign);

            this.emit('design_forked', { original_id: designId, forked_id: forkedDesign.id });

            return {
                success: true,
                forked_design_id: forkedDesign.id,
                message: 'Design forked successfully'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    // User Management
    async getUserProfile(userId) {
        try {
            const user = this.users.get(userId);
            if (!user) {
                throw new Error('User not found');
            }

            const userDesigns = Array.from(this.designs.values())
                .filter(d => d.author_id === userId);

            const userCollaborations = Array.from(this.collaborations.values())
                .filter(c => c.participants.includes(userId) || c.initiator_id === userId);

            return {
                success: true,
                user: user,
                designs: userDesigns,
                collaborations: userCollaborations,
                stats: {
                    total_designs: userDesigns.length,
                    total_downloads: userDesigns.reduce((sum, d) => sum + d.downloads, 0),
                    total_stars: userDesigns.reduce((sum, d) => sum + d.stars, 0),
                    average_rating: userDesigns.length > 0 ? 
                        userDesigns.reduce((sum, d) => sum + d.rating.average, 0) / userDesigns.length : 0
                }
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async followUser(followerId, targetUserId) {
        try {
            if (!this.following.has(followerId)) {
                this.following.set(followerId, new Set());
            }

            this.following.get(followerId).add(targetUserId);
            this.emit('user_followed', { follower_id: followerId, target_id: targetUserId });

            return {
                success: true,
                message: 'User followed successfully'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Collaboration System
    async createCollaboration(collaborationData) {
        try {
            const collaboration = {
                id: this.generateId('collab'),
                title: collaborationData.title,
                description: collaborationData.description,
                initiator_id: collaborationData.initiator_id,
                participants: collaborationData.participants || [],
                status: 'recruiting',
                progress: 0,
                start_date: new Date(),
                target_completion: collaborationData.target_completion,
                required_skills: collaborationData.required_skills || [],
                contributions: {},
                milestones: collaborationData.milestones || [],
                communication_channel: this.generateId('channel')
            };

            this.collaborations.set(collaboration.id, collaboration);
            this.emit('collaboration_created', collaboration);

            return {
                success: true,
                collaboration_id: collaboration.id,
                message: 'Collaboration created successfully'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async joinCollaboration(collaborationId, userId, skills = []) {
        try {
            const collaboration = this.collaborations.get(collaborationId);
            if (!collaboration) {
                throw new Error('Collaboration not found');
            }

            if (collaboration.participants.includes(userId)) {
                throw new Error('User already participating');
            }

            collaboration.participants.push(userId);
            collaboration.contributions[userId] = {
                skills: skills,
                joined_date: new Date(),
                contribution_level: 0
            };

            this.collaborations.set(collaborationId, collaboration);
            this.emit('collaboration_joined', { collaboration_id: collaborationId, user_id: userId });

            return {
                success: true,
                message: 'Successfully joined collaboration'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Competition System
    async createCompetition(competitionData) {
        try {
            const competition = {
                id: this.generateId('comp'),
                title: competitionData.title,
                description: competitionData.description,
                organizer_id: competitionData.organizer_id,
                status: 'planning',
                start_date: competitionData.start_date,
                end_date: competitionData.end_date,
                registration_deadline: competitionData.registration_deadline,
                prizes: competitionData.prizes || {},
                participants: 0,
                submissions: 0,
                criteria: competitionData.criteria || [],
                judges: competitionData.judges || [],
                rules: competitionData.rules || '',
                registration_fee: competitionData.registration_fee || 0,
                max_participants: competitionData.max_participants || null
            };

            this.competitions.set(competition.id, competition);
            this.emit('competition_created', competition);

            return {
                success: true,
                competition_id: competition.id,
                message: 'Competition created successfully'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async registerForCompetition(competitionId, userId) {
        try {
            const competition = this.competitions.get(competitionId);
            if (!competition) {
                throw new Error('Competition not found');
            }

            if (competition.status !== 'active' && competition.status !== 'registration_open') {
                throw new Error('Registration not currently open');
            }

            competition.participants += 1;
            this.competitions.set(competitionId, competition);

            this.emit('competition_registered', { competition_id: competitionId, user_id: userId });

            return {
                success: true,
                message: 'Successfully registered for competition'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Forum System
    async createForumPost(forumId, userId, postData) {
        try {
            const forum = this.forums.get(forumId);
            if (!forum) {
                throw new Error('Forum not found');
            }

            const post = {
                id: this.generateId('post'),
                forum_id: forumId,
                author_id: userId,
                title: postData.title,
                content: postData.content,
                created_date: new Date(),
                last_updated: new Date(),
                replies: [],
                views: 0,
                upvotes: 0,
                downvotes: 0,
                tags: postData.tags || []
            };

            if (!this.comments.has(forumId)) {
                this.comments.set(forumId, new Map());
            }
            this.comments.get(forumId).set(post.id, post);

            forum.posts += 1;
            forum.latest_activity = new Date();
            this.forums.set(forumId, forum);

            this.emit('forum_post_created', post);

            return {
                success: true,
                post_id: post.id,
                message: 'Post created successfully'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Featured Content Management
    async featureDesign(designId, reason = '', duration_days = 7) {
        try {
            const design = this.designs.get(designId);
            if (!design) {
                throw new Error('Design not found');
            }

            const featuredItem = {
                id: this.generateId('featured'),
                type: 'design',
                item_id: designId,
                reason: reason,
                featured_date: new Date(),
                expiry_date: new Date(Date.now() + (duration_days * 24 * 60 * 60 * 1000)),
                views_while_featured: 0
            };

            this.featured.set(featuredItem.id, featuredItem);
            this.emit('design_featured', featuredItem);

            return {
                success: true,
                featured_id: featuredItem.id,
                message: 'Design featured successfully'
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async getFeaturedContent() {
        try {
            const now = new Date();
            const activeFeatures = Array.from(this.featured.values())
                .filter(f => f.expiry_date > now)
                .sort((a, b) => b.featured_date - a.featured_date);

            const featuredWithDetails = activeFeatures.map(feature => {
                let item = null;
                if (feature.type === 'design') {
                    item = this.designs.get(feature.item_id);
                }

                return {
                    ...feature,
                    item: item
                };
            });

            return {
                success: true,
                featured_content: featuredWithDetails
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Analytics and Insights
    async getCommunityStats() {
        try {
            const designs = Array.from(this.designs.values());
            const users = Array.from(this.users.values());
            const collaborations = Array.from(this.collaborations.values());
            const competitions = Array.from(this.competitions.values());

            const totalDownloads = designs.reduce((sum, d) => sum + d.downloads, 0);
            const totalViews = designs.reduce((sum, d) => sum + d.views, 0);
            const activeCollaborations = collaborations.filter(c => c.status === 'active').length;
            const activeCompetitions = competitions.filter(c => c.status === 'active').length;

            const categoryStats = {};
            designs.forEach(design => {
                if (!categoryStats[design.category]) {
                    categoryStats[design.category] = {
                        count: 0,
                        downloads: 0,
                        average_rating: 0
                    };
                }
                categoryStats[design.category].count += 1;
                categoryStats[design.category].downloads += design.downloads;
            });

            return {
                success: true,
                stats: {
                    total_designs: designs.length,
                    total_users: users.length,
                    total_downloads: totalDownloads,
                    total_views: totalViews,
                    active_collaborations: activeCollaborations,
                    active_competitions: activeCompetitions,
                    category_breakdown: categoryStats,
                    top_contributors: users
                        .sort((a, b) => b.reputation - a.reputation)
                        .slice(0, 10)
                        .map(u => ({ username: u.username, reputation: u.reputation }))
                }
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    // Trending and Discovery
    async getTrendingDesigns(timeframe = '7d', limit = 10) {
        try {
            const designs = Array.from(this.designs.values());
            const now = new Date();
            let cutoffDate = new Date();

            switch (timeframe) {
                case '24h':
                    cutoffDate.setDate(now.getDate() - 1);
                    break;
                case '7d':
                    cutoffDate.setDate(now.getDate() - 7);
                    break;
                case '30d':
                    cutoffDate.setDate(now.getDate() - 30);
                    break;
                default:
                    cutoffDate.setDate(now.getDate() - 7);
            }

            const trendingDesigns = designs
                .filter(d => new Date(d.last_updated) >= cutoffDate)
                .sort((a, b) => {
                    const scoreA = a.views + (a.downloads * 2) + (a.stars * 3);
                    const scoreB = b.views + (b.downloads * 2) + (b.stars * 3);
                    return scoreB - scoreA;
                })
                .slice(0, limit);

            return {
                success: true,
                trending_designs: trendingDesigns,
                timeframe: timeframe,
                generated_at: new Date()
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }
}

export default CommunityDesignsPlatform;