import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';

class InstallationGuidesSystem extends EventEmitter {
    constructor() {
        super();
        this.guides = new Map();
        this.guideTemplates = new Map();
        this.mediaAssets = new Map();
        this.userProgress = new Map();
        this.guideFeedback = new Map();
        this.interactiveSteps = new Map();
        this.guideMetrics = {
            total_guides: 0,
            completion_rate: 0,
            average_rating: 0,
            help_requests: 0
        };
        this.initializeGuideTemplates();
        this.initializeInstallationGuides();
    }

    initializeGuideTemplates() {
        const templates = [
            {
                id: 'electronics_installation',
                name: 'Electronics Installation Template',
                category: 'electronics',
                description: 'Standard template for electronic device installations',
                sections: [
                    {
                        name: 'Safety Precautions',
                        required: true,
                        content_types: ['text', 'checklist', 'warning_box']
                    },
                    {
                        name: 'Required Tools and Materials',
                        required: true,
                        content_types: ['list', 'images', 'tool_checklist']
                    },
                    {
                        name: 'Pre-Installation Checklist',
                        required: true,
                        content_types: ['checklist', 'verification_steps']
                    },
                    {
                        name: 'Installation Steps',
                        required: true,
                        content_types: ['step_by_step', 'images', 'videos', 'diagrams']
                    },
                    {
                        name: 'Testing and Verification',
                        required: true,
                        content_types: ['test_procedures', 'expected_results', 'troubleshooting']
                    },
                    {
                        name: 'Troubleshooting',
                        required: false,
                        content_types: ['problem_solution', 'diagnostic_flowchart']
                    },
                    {
                        name: 'Maintenance',
                        required: false,
                        content_types: ['maintenance_schedule', 'replacement_parts']
                    }
                ]
            },
            {
                id: 'mechanical_assembly',
                name: 'Mechanical Assembly Template',
                category: 'mechanical',
                description: 'Template for mechanical installation and assembly projects',
                sections: [
                    {
                        name: 'Safety Guidelines',
                        required: true,
                        content_types: ['safety_warnings', 'protective_equipment']
                    },
                    {
                        name: 'Parts Inventory',
                        required: true,
                        content_types: ['parts_list', 'identification_guide', 'quantity_check']
                    },
                    {
                        name: 'Assembly Sequence',
                        required: true,
                        content_types: ['step_sequence', 'assembly_diagrams', 'torque_specifications']
                    },
                    {
                        name: 'Quality Control',
                        required: true,
                        content_types: ['inspection_points', 'measurement_procedures']
                    }
                ]
            },
            {
                id: 'software_configuration',
                name: 'Software Configuration Template',
                category: 'software',
                description: 'Template for software setup and configuration guides',
                sections: [
                    {
                        name: 'System Requirements',
                        required: true,
                        content_types: ['requirements_checklist', 'compatibility_matrix']
                    },
                    {
                        name: 'Installation Process',
                        required: true,
                        content_types: ['download_links', 'installation_steps', 'screenshots']
                    },
                    {
                        name: 'Configuration Setup',
                        required: true,
                        content_types: ['configuration_steps', 'settings_screenshots', 'code_examples']
                    },
                    {
                        name: 'Testing and Validation',
                        required: true,
                        content_types: ['test_procedures', 'expected_outputs', 'validation_checks']
                    }
                ]
            }
        ];

        templates.forEach(template => {
            this.guideTemplates.set(template.id, template);
        });
    }

    initializeInstallationGuides() {
        const guides = [
            {
                id: 'activelog_core_setup',
                title: 'ActiveLog Core Module Installation Guide',
                category: 'electronics',
                subcategory: 'microcontrollers',
                difficulty_level: 'beginner',
                estimated_time: '30-45 minutes',
                last_updated: new Date(),
                version: '2.1',
                product_compatibility: ['activelog_core_v2', 'activelog_starter_kit'],
                description: 'Complete guide for setting up your ActiveLog Core Module from unboxing to first data transmission',
                sections: [
                    {
                        id: 'safety_precautions',
                        title: 'Safety Precautions',
                        order: 1,
                        content: {
                            type: 'safety_guidelines',
                            text: 'Before beginning the installation, please observe these important safety precautions to protect both yourself and your equipment.',
                            warnings: [
                                'Always handle the module by its edges to avoid damaging sensitive components',
                                'Ensure power is disconnected before making any connections',
                                'Use anti-static precautions when handling electronic components',
                                'Never force connections - if something doesn\'t fit easily, double-check the orientation'
                            ],
                            safety_checklist: [
                                'Anti-static wrist strap or grounding mat available',
                                'Clean, well-lit workspace prepared',
                                'All tools properly insulated',
                                'Emergency contact information readily available'
                            ]
                        },
                        media: [
                            {
                                type: 'image',
                                url: '/guides/images/safety_workspace.jpg',
                                caption: 'Example of a properly prepared workspace'
                            }
                        ]
                    },
                    {
                        id: 'required_materials',
                        title: 'Required Tools and Materials',
                        order: 2,
                        content: {
                            type: 'materials_list',
                            tools: [
                                {
                                    name: 'USB-C Cable',
                                    description: 'For programming and power (included in kit)',
                                    required: true,
                                    alternative: 'Any USB-C data cable'
                                },
                                {
                                    name: 'Computer',
                                    description: 'Windows, Mac, or Linux with USB port',
                                    required: true,
                                    specifications: 'Minimum 4GB RAM, USB 2.0 or higher'
                                },
                                {
                                    name: 'Breadboard',
                                    description: 'For prototyping connections (optional)',
                                    required: false,
                                    alternative: 'Direct wiring to sensors'
                                },
                                {
                                    name: 'Jumper Wires',
                                    description: 'For making connections to sensors',
                                    required: false,
                                    quantity: '10-20 wires recommended'
                                }
                            ],
                            components: [
                                {
                                    name: 'ActiveLog Core Module',
                                    description: 'Main microcontroller unit',
                                    part_number: 'AL-CORE-V2',
                                    quantity: 1
                                },
                                {
                                    name: 'Quick Start Guide',
                                    description: 'Printed reference card',
                                    included: true
                                }
                            ]
                        },
                        interactive_checklist: {
                            enabled: true,
                            items: [
                                'ActiveLog Core Module inspected and undamaged',
                                'USB-C cable available and tested',
                                'Computer meets system requirements',
                                'ActiveLog development environment installed'
                            ]
                        }
                    },
                    {
                        id: 'initial_setup',
                        title: 'Initial Setup and Connection',
                        order: 3,
                        content: {
                            type: 'step_by_step',
                            steps: [
                                {
                                    step_number: 1,
                                    title: 'Connect the Module',
                                    description: 'Connect the ActiveLog Core Module to your computer using the USB-C cable',
                                    detailed_instructions: [
                                        'Locate the USB-C port on the ActiveLog Core Module (marked with USB symbol)',
                                        'Connect the USB-C cable to the module',
                                        'Connect the other end to an available USB port on your computer',
                                        'The module should power on automatically (blue LED should illuminate)'
                                    ],
                                    expected_result: 'Blue power LED lights up, computer recognizes new device',
                                    troubleshooting: {
                                        'No LED lights up': 'Try different USB port or cable',
                                        'Computer doesn\'t recognize device': 'Install ActiveLog drivers first'
                                    }
                                },
                                {
                                    step_number: 2,
                                    title: 'Install Development Environment',
                                    description: 'Set up the ActiveLog development environment on your computer',
                                    detailed_instructions: [
                                        'Visit activelogdev.com/downloads',
                                        'Download ActiveLog Studio for your operating system',
                                        'Run the installer with administrator privileges',
                                        'Follow the installation wizard prompts',
                                        'Restart your computer when installation completes'
                                    ],
                                    expected_result: 'ActiveLog Studio launches successfully and detects the connected module'
                                }
                            ]
                        },
                        media: [
                            {
                                type: 'video',
                                url: '/guides/videos/core_module_connection.mp4',
                                duration: '2:30',
                                caption: 'Connecting the ActiveLog Core Module'
                            },
                            {
                                type: 'interactive_diagram',
                                url: '/guides/diagrams/core_module_ports.svg',
                                caption: 'ActiveLog Core Module port locations'
                            }
                        ]
                    },
                    {
                        id: 'first_program',
                        title: 'First Program Upload',
                        order: 4,
                        content: {
                            type: 'programming_guide',
                            steps: [
                                {
                                    step_number: 1,
                                    title: 'Open ActiveLog Studio',
                                    description: 'Launch the development environment and create a new project',
                                    code_example: {
                                        language: 'cpp',
                                        code: `#include <ActiveLog.h>

void setup() {
  ActiveLog.begin();
  ActiveLog.println("Hello, ActiveLog World!");
}

void loop() {
  ActiveLog.println("System running...");
  delay(5000);
}`
                                    }
                                },
                                {
                                    step_number: 2,
                                    title: 'Upload Program',
                                    description: 'Compile and upload your first program to the module',
                                    detailed_instructions: [
                                        'Click the "Compile" button (checkmark icon)',
                                        'Wait for compilation to complete',
                                        'Click the "Upload" button (arrow icon)',
                                        'Monitor the progress bar during upload'
                                    ]
                                }
                            ]
                        }
                    },
                    {
                        id: 'testing_verification',
                        title: 'Testing and Verification',
                        order: 5,
                        content: {
                            type: 'verification_procedures',
                            tests: [
                                {
                                    test_name: 'Power LED Test',
                                    procedure: 'Verify blue power LED remains lit during operation',
                                    expected_result: 'Steady blue light',
                                    pass_criteria: 'LED is solid blue without flickering'
                                },
                                {
                                    test_name: 'Communication Test',
                                    procedure: 'Open serial monitor and observe output messages',
                                    expected_result: 'Regular "System running..." messages every 5 seconds',
                                    pass_criteria: 'Messages appear consistently without errors'
                                },
                                {
                                    test_name: 'WiFi Connection Test',
                                    procedure: 'Configure WiFi credentials and test connectivity',
                                    expected_result: 'Successful connection to local network',
                                    pass_criteria: 'Module obtains IP address and can ping gateway'
                                }
                            ]
                        },
                        interactive_elements: {
                            live_serial_monitor: true,
                            wifi_setup_wizard: true,
                            connectivity_checker: true
                        }
                    }
                ],
                completion_criteria: [
                    'Module powers on successfully',
                    'Development environment installed and configured',
                    'First program uploaded and running',
                    'Serial communication working',
                    'WiFi connectivity established'
                ],
                next_steps: [
                    'Connect your first sensor',
                    'Set up data logging',
                    'Configure cloud connectivity',
                    'Explore advanced features'
                ],
                related_guides: [
                    'sensor_connection_basics',
                    'wifi_configuration_advanced',
                    'data_logging_setup'
                ]
            },
            {
                id: 'solar_camera_installation',
                title: 'Solar Security Camera Installation Guide',
                category: 'mechanical',
                subcategory: 'outdoor_installation',
                difficulty_level: 'intermediate',
                estimated_time: '2-4 hours',
                last_updated: new Date(),
                version: '1.3',
                product_compatibility: ['solar_cam_4k_pro', 'solar_cam_hd_basic'],
                description: 'Complete outdoor installation guide for solar-powered security cameras',
                sections: [
                    {
                        id: 'site_preparation',
                        title: 'Site Preparation and Planning',
                        order: 1,
                        content: {
                            type: 'planning_guide',
                            planning_steps: [
                                {
                                    title: 'Site Survey',
                                    description: 'Evaluate the installation location for optimal performance',
                                    considerations: [
                                        'Solar panel receives 6+ hours of direct sunlight daily',
                                        'Camera has clear view of target area',
                                        'WiFi signal strength is adequate (minimum -70dBm)',
                                        'Location is secure from tampering',
                                        'Mounting surface can support camera weight (3.2kg)',
                                        'Local regulations permit security camera installation'
                                    ]
                                },
                                {
                                    title: 'Weather Considerations',
                                    description: 'Plan installation around weather conditions',
                                    requirements: [
                                        'Install during dry weather conditions',
                                        'Temperature between 10°C and 30°C for optimal sealant curing',
                                        'Wind speed less than 15 mph for safe ladder work',
                                        'No precipitation forecast for 24 hours after installation'
                                    ]
                                }
                            ]
                        },
                        tools: [
                            { name: 'WiFi Signal Meter App', purpose: 'Test signal strength at installation site' },
                            { name: 'Compass or GPS', purpose: 'Determine optimal solar panel orientation' },
                            { name: 'Measuring Tape', purpose: 'Verify mounting dimensions and clearances' }
                        ]
                    },
                    {
                        id: 'mounting_installation',
                        title: 'Camera and Solar Panel Mounting',
                        order: 2,
                        content: {
                            type: 'mechanical_assembly',
                            assembly_steps: [
                                {
                                    step_number: 1,
                                    title: 'Mount the Bracket',
                                    description: 'Install the universal mounting bracket on wall or pole',
                                    tools_required: ['Drill', 'Masonry bits', 'Level', 'Socket wrench'],
                                    hardware: ['4x M8x60 bolts', '4x Wall anchors', '4x Washers'],
                                    detailed_procedure: [
                                        'Mark mounting hole positions using bracket as template',
                                        'Drill holes using appropriate bit for wall material',
                                        'Insert wall anchors flush with surface',
                                        'Position bracket and secure with bolts and washers',
                                        'Verify bracket is level and securely fastened'
                                    ],
                                    safety_notes: [
                                        'Wear safety glasses when drilling',
                                        'Use proper ladder safety procedures',
                                        'Check for electrical wires behind mounting surface'
                                    ]
                                },
                                {
                                    step_number: 2,
                                    title: 'Install Solar Panel',
                                    description: 'Mount solar panel for optimal sun exposure',
                                    orientation_guide: {
                                        northern_hemisphere: 'Face panel south at 30-45° tilt',
                                        southern_hemisphere: 'Face panel north at 30-45° tilt',
                                        equatorial_regions: 'Mount panel flat or slight tilt toward sun'
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
            {
                id: 'fish_counter_deployment',
                title: 'Fish Counter Deployment Guide',
                category: 'environmental',
                subcategory: 'aquatic_monitoring',
                difficulty_level: 'advanced',
                estimated_time: '4-8 hours',
                last_updated: new Date(),
                version: '1.0',
                product_compatibility: ['activelog_fish_counter_pro', 'activelog_fish_counter_stream'],
                description: 'Professional deployment guide for underwater fish counting systems',
                sections: [
                    {
                        id: 'site_assessment',
                        title: 'Aquatic Site Assessment',
                        order: 1,
                        content: {
                            type: 'environmental_assessment',
                            assessment_criteria: [
                                {
                                    parameter: 'Water Depth',
                                    requirements: '1-50 meters (varies by model)',
                                    measurement_method: 'Depth sounder or weighted line',
                                    documentation: 'Record depth at multiple points'
                                },
                                {
                                    parameter: 'Current Velocity',
                                    requirements: 'Less than 2 m/s for stable mounting',
                                    measurement_method: 'Flow meter or drift timing',
                                    documentation: 'Measure at different depths and times'
                                },
                                {
                                    parameter: 'Water Clarity',
                                    requirements: 'Minimum 2m visibility for optical sensors',
                                    measurement_method: 'Secchi disk or turbidimeter',
                                    documentation: 'Record seasonal variations'
                                },
                                {
                                    parameter: 'Bottom Composition',
                                    requirements: 'Stable substrate for anchoring',
                                    assessment_method: 'Visual inspection or grab sample',
                                    considerations: 'Rocky, sandy, or muddy bottom affects anchoring method'
                                }
                            ]
                        }
                    }
                ]
            }
        ];

        guides.forEach(guide => {
            guide.created_at = new Date();
            guide.author = 'ActiveLog Technical Team';
            guide.language = 'en';
            guide.tags = this.generateGuideTags(guide);
            guide.popularity_score = Math.random() * 100;
            guide.completion_rate = 0.75 + Math.random() * 0.2;
            guide.average_rating = 4.2 + Math.random() * 0.7;
            guide.total_completions = Math.floor(Math.random() * 1000) + 100;
            guide.help_requests = Math.floor(Math.random() * 50) + 5;
            
            this.guides.set(guide.id, guide);
        });
    }

    generateGuideTags(guide) {
        const tags = [guide.category, guide.subcategory, guide.difficulty_level];
        
        if (guide.estimated_time) {
            if (guide.estimated_time.includes('30') || guide.estimated_time.includes('45')) {
                tags.push('quick_setup');
            } else if (guide.estimated_time.includes('hour')) {
                tags.push('detailed_installation');
            }
        }

        if (guide.product_compatibility) {
            guide.product_compatibility.forEach(product => {
                tags.push(product);
            });
        }

        return tags;
    }

    async createGuide(guideRequest) {
        try {
            const guide = {
                id: this.generateGuideId(),
                title: guideRequest.title,
                category: guideRequest.category,
                subcategory: guideRequest.subcategory,
                difficulty_level: guideRequest.difficulty_level,
                estimated_time: guideRequest.estimated_time,
                description: guideRequest.description,
                author: guideRequest.author,
                created_at: new Date(),
                last_updated: new Date(),
                version: '1.0',
                language: guideRequest.language || 'en',
                product_compatibility: guideRequest.product_compatibility || [],
                sections: guideRequest.sections || [],
                tags: guideRequest.tags || [],
                status: 'draft',
                review_status: 'pending',
                visibility: 'private'
            };

            if (guideRequest.template_id && this.guideTemplates.has(guideRequest.template_id)) {
                await this.applyTemplate(guide, guideRequest.template_id);
            }

            this.guides.set(guide.id, guide);
            this.emit('guideCreated', guide);

            return guide;
        } catch (error) {
            this.emit('guideError', { error: error.message, guideRequest });
            throw error;
        }
    }

    async applyTemplate(guide, templateId) {
        const template = this.guideTemplates.get(templateId);
        if (!template) {
            throw new Error('Template not found');
        }

        guide.template_id = templateId;
        guide.sections = template.sections.map(section => ({
            id: this.generateSectionId(),
            title: section.name,
            order: guide.sections.length + 1,
            required: section.required,
            content_types: section.content_types,
            content: {},
            media: [],
            interactive_elements: {},
            completion_required: section.required
        }));

        return guide;
    }

    async startGuideSession(guideId, userId) {
        const guide = this.guides.get(guideId);
        if (!guide) {
            throw new Error('Guide not found');
        }

        const session = {
            id: this.generateSessionId(),
            guide_id: guideId,
            user_id: userId,
            started_at: new Date(),
            current_section: 0,
            completed_sections: [],
            progress_percentage: 0,
            time_spent_minutes: 0,
            notes: [],
            help_requests: [],
            feedback: null,
            status: 'in_progress'
        };

        if (!this.userProgress.has(guideId)) {
            this.userProgress.set(guideId, new Map());
        }
        
        this.userProgress.get(guideId).set(userId, session);
        this.emit('guideSessionStarted', session);

        return session;
    }

    async updateProgress(sessionId, progressUpdate) {
        const session = this.findSession(sessionId);
        if (!session) {
            throw new Error('Session not found');
        }

        const guide = this.guides.get(session.guide_id);
        if (!guide) {
            throw new Error('Guide not found');
        }

        if (progressUpdate.section_completed) {
            const sectionIndex = progressUpdate.section_completed;
            if (!session.completed_sections.includes(sectionIndex)) {
                session.completed_sections.push(sectionIndex);
                session.completed_sections.sort();
            }
            
            if (sectionIndex === session.current_section) {
                session.current_section = Math.min(sectionIndex + 1, guide.sections.length);
            }
        }

        if (progressUpdate.current_section !== undefined) {
            session.current_section = progressUpdate.current_section;
        }

        if (progressUpdate.time_spent_minutes) {
            session.time_spent_minutes += progressUpdate.time_spent_minutes;
        }

        if (progressUpdate.note) {
            session.notes.push({
                timestamp: new Date(),
                section: session.current_section,
                note: progressUpdate.note
            });
        }

        session.progress_percentage = this.calculateProgressPercentage(session, guide);
        session.last_updated = new Date();

        if (session.progress_percentage >= 100) {
            session.status = 'completed';
            session.completed_at = new Date();
            await this.generateCompletionCertificate(session, guide);
            this.emit('guideCompleted', session);
        }

        this.emit('progressUpdated', { session, progressUpdate });
        return session;
    }

    calculateProgressPercentage(session, guide) {
        const totalSections = guide.sections.length;
        const completedSections = session.completed_sections.length;
        
        if (totalSections === 0) return 100;
        
        return Math.round((completedSections / totalSections) * 100);
    }

    async submitHelpRequest(sessionId, helpRequest) {
        const session = this.findSession(sessionId);
        if (!session) {
            throw new Error('Session not found');
        }

        const request = {
            id: this.generateHelpRequestId(),
            session_id: sessionId,
            user_id: session.user_id,
            guide_id: session.guide_id,
            section_id: helpRequest.section_id,
            request_type: helpRequest.type,
            subject: helpRequest.subject,
            description: helpRequest.description,
            priority: helpRequest.priority || 'medium',
            submitted_at: new Date(),
            status: 'open',
            responses: []
        };

        session.help_requests.push(request);
        this.emit('helpRequestSubmitted', request);

        return request;
    }

    async respondToHelpRequest(requestId, response) {
        const session = this.findSessionByHelpRequest(requestId);
        if (!session) {
            throw new Error('Help request not found');
        }

        const helpRequest = session.help_requests.find(req => req.id === requestId);
        const helpResponse = {
            id: this.generateResponseId(),
            responder_type: response.responder_type,
            responder_id: response.responder_id,
            response_text: response.response_text,
            helpful_links: response.helpful_links || [],
            attachments: response.attachments || [],
            responded_at: new Date()
        };

        helpRequest.responses.push(helpResponse);
        
        if (response.resolve_request) {
            helpRequest.status = 'resolved';
            helpRequest.resolved_at = new Date();
        }

        this.emit('helpResponseProvided', { helpRequest, response: helpResponse });
        return helpResponse;
    }

    async addInteractiveElement(guideId, sectionId, element) {
        const guide = this.guides.get(guideId);
        if (!guide) {
            throw new Error('Guide not found');
        }

        const section = guide.sections.find(s => s.id === sectionId);
        if (!section) {
            throw new Error('Section not found');
        }

        const interactiveElement = {
            id: this.generateElementId(),
            type: element.type,
            title: element.title,
            description: element.description,
            configuration: element.configuration || {},
            created_at: new Date()
        };

        switch (element.type) {
            case 'checklist':
                interactiveElement.items = element.items || [];
                interactiveElement.allow_partial = element.allow_partial || false;
                break;
            case 'quiz':
                interactiveElement.questions = element.questions || [];
                interactiveElement.passing_score = element.passing_score || 70;
                break;
            case 'simulator':
                interactiveElement.simulator_config = element.simulator_config || {};
                interactiveElement.success_criteria = element.success_criteria || [];
                break;
            case 'calculator':
                interactiveElement.formula = element.formula || '';
                interactiveElement.variables = element.variables || [];
                break;
        }

        section.interactive_elements[interactiveElement.id] = interactiveElement;
        this.interactiveSteps.set(interactiveElement.id, interactiveElement);

        this.emit('interactiveElementAdded', { guide, section, element: interactiveElement });
        return interactiveElement;
    }

    async submitFeedback(sessionId, feedback) {
        const session = this.findSession(sessionId);
        if (!session) {
            throw new Error('Session not found');
        }

        const feedbackRecord = {
            id: this.generateFeedbackId(),
            session_id: sessionId,
            user_id: session.user_id,
            guide_id: session.guide_id,
            overall_rating: feedback.overall_rating,
            clarity_rating: feedback.clarity_rating,
            completeness_rating: feedback.completeness_rating,
            usefulness_rating: feedback.usefulness_rating,
            comments: feedback.comments || '',
            suggestions: feedback.suggestions || '',
            reported_issues: feedback.reported_issues || [],
            would_recommend: feedback.would_recommend,
            submitted_at: new Date()
        };

        session.feedback = feedbackRecord;
        
        if (!this.guideFeedback.has(session.guide_id)) {
            this.guideFeedback.set(session.guide_id, []);
        }
        this.guideFeedback.get(session.guide_id).push(feedbackRecord);

        await this.updateGuideMetrics(session.guide_id);
        this.emit('feedbackSubmitted', feedbackRecord);

        return feedbackRecord;
    }

    async updateGuideMetrics(guideId) {
        const guide = this.guides.get(guideId);
        const feedback = this.guideFeedback.get(guideId) || [];
        
        if (feedback.length > 0) {
            const totalRating = feedback.reduce((sum, fb) => sum + fb.overall_rating, 0);
            guide.average_rating = Math.round((totalRating / feedback.length) * 10) / 10;
            guide.total_feedback = feedback.length;
        }

        const userSessions = this.userProgress.get(guideId);
        if (userSessions) {
            const completedSessions = Array.from(userSessions.values())
                .filter(session => session.status === 'completed');
            
            guide.total_completions = completedSessions.length;
            guide.completion_rate = userSessions.size > 0 ? 
                completedSessions.length / userSessions.size : 0;
        }
    }

    async generateCompletionCertificate(session, guide) {
        const certificate = {
            id: this.generateCertificateId(),
            session_id: session.id,
            user_id: session.user_id,
            guide_id: guide.id,
            guide_title: guide.title,
            completion_date: session.completed_at,
            time_spent_minutes: session.time_spent_minutes,
            certificate_url: `/certificates/installation/${session.user_id}/${session.id}.pdf`,
            verification_code: this.generateVerificationCode(),
            issued_by: 'ActiveLog Installation Guides',
            valid_until: this.addMonths(new Date(), 12) // Valid for 1 year
        };

        session.completion_certificate = certificate;
        this.emit('certificateGenerated', certificate);

        return certificate;
    }

    async searchGuides(searchCriteria) {
        const {
            query = '',
            category = '',
            subcategory = '',
            difficulty_level = '',
            product_compatibility = [],
            estimated_time_max = null,
            language = '',
            tags = [],
            sort_by = 'popularity',
            sort_order = 'desc',
            page = 1,
            limit = 20
        } = searchCriteria;

        let guides = Array.from(this.guides.values()).filter(guide => 
            guide.visibility === 'public' || guide.status === 'published'
        );

        if (query) {
            const searchLower = query.toLowerCase();
            guides = guides.filter(guide => 
                guide.title.toLowerCase().includes(searchLower) ||
                guide.description.toLowerCase().includes(searchLower) ||
                guide.tags.some(tag => tag.toLowerCase().includes(searchLower))
            );
        }

        if (category) guides = guides.filter(guide => guide.category === category);
        if (subcategory) guides = guides.filter(guide => guide.subcategory === subcategory);
        if (difficulty_level) guides = guides.filter(guide => guide.difficulty_level === difficulty_level);
        if (language) guides = guides.filter(guide => guide.language === language);

        if (product_compatibility.length > 0) {
            guides = guides.filter(guide => 
                guide.product_compatibility.some(product => 
                    product_compatibility.includes(product)
                )
            );
        }

        if (tags.length > 0) {
            guides = guides.filter(guide =>
                tags.some(tag => guide.tags.includes(tag))
            );
        }

        if (estimated_time_max) {
            guides = guides.filter(guide => {
                const timeMatch = guide.estimated_time.match(/(\d+)/);
                const timeValue = timeMatch ? parseInt(timeMatch[1]) : 0;
                return timeValue <= estimated_time_max;
            });
        }

        guides.sort((a, b) => {
            let aValue, bValue;
            
            switch (sort_by) {
                case 'rating':
                    aValue = a.average_rating || 0;
                    bValue = b.average_rating || 0;
                    break;
                case 'completion_rate':
                    aValue = a.completion_rate || 0;
                    bValue = b.completion_rate || 0;
                    break;
                case 'recent':
                    aValue = new Date(a.last_updated);
                    bValue = new Date(b.last_updated);
                    break;
                case 'difficulty':
                    const difficultyOrder = ['beginner', 'intermediate', 'advanced', 'expert'];
                    aValue = difficultyOrder.indexOf(a.difficulty_level);
                    bValue = difficultyOrder.indexOf(b.difficulty_level);
                    break;
                case 'popularity':
                default:
                    aValue = a.popularity_score || 0;
                    bValue = b.popularity_score || 0;
            }

            if (sort_order === 'desc') {
                return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
            } else {
                return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
            }
        });

        const startIndex = (page - 1) * limit;
        const endIndex = startIndex + limit;
        const paginatedGuides = guides.slice(startIndex, endIndex);

        return {
            guides: paginatedGuides,
            pagination: {
                current_page: page,
                total_pages: Math.ceil(guides.length / limit),
                total_guides: guides.length,
                has_next: endIndex < guides.length,
                has_prev: page > 1
            },
            facets: {
                categories: this.calculateFacets(guides, 'category'),
                difficulty_levels: this.calculateFacets(guides, 'difficulty_level'),
                languages: this.calculateFacets(guides, 'language'),
                tags: this.calculateTagFacets(guides)
            }
        };
    }

    findSession(sessionId) {
        for (const [guideId, userSessions] of this.userProgress) {
            for (const [userId, session] of userSessions) {
                if (session.id === sessionId) {
                    return session;
                }
            }
        }
        return null;
    }

    findSessionByHelpRequest(requestId) {
        for (const [guideId, userSessions] of this.userProgress) {
            for (const [userId, session] of userSessions) {
                if (session.help_requests.some(req => req.id === requestId)) {
                    return session;
                }
            }
        }
        return null;
    }

    calculateFacets(items, field) {
        const counts = {};
        items.forEach(item => {
            const value = item[field];
            if (value) {
                counts[value] = (counts[value] || 0) + 1;
            }
        });
        return counts;
    }

    calculateTagFacets(guides) {
        const tagCounts = {};
        guides.forEach(guide => {
            guide.tags.forEach(tag => {
                tagCounts[tag] = (tagCounts[tag] || 0) + 1;
            });
        });
        return tagCounts;
    }

    addMonths(date, months) {
        const result = new Date(date);
        result.setMonth(result.getMonth() + months);
        return result;
    }

    generateGuideId() {
        return `guide_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateSectionId() {
        return `section_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateSessionId() {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateHelpRequestId() {
        return `help_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateResponseId() {
        return `response_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateElementId() {
        return `element_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateFeedbackId() {
        return `feedback_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateCertificateId() {
        return `cert_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    generateVerificationCode() {
        return Math.random().toString(36).substr(2, 16).toUpperCase();
    }

    getSystemStats() {
        const totalSessions = Array.from(this.userProgress.values()).reduce((total, userSessions) => 
            total + userSessions.size, 0
        );

        const completedSessions = Array.from(this.userProgress.values()).reduce((total, userSessions) => {
            let completed = 0;
            userSessions.forEach(session => {
                if (session.status === 'completed') completed++;
            });
            return total + completed;
        }, 0);

        return {
            total_guides: this.guides.size,
            guide_templates: this.guideTemplates.size,
            total_sessions: totalSessions,
            completed_sessions: completedSessions,
            completion_rate: totalSessions > 0 ? completedSessions / totalSessions : 0,
            interactive_elements: this.interactiveSteps.size,
            metrics: this.guideMetrics
        };
    }
}

export default InstallationGuidesSystem;