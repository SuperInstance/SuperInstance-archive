const EventEmitter = require('events');
const { v4: uuidv4 } = require('uuid');
const moment = require('moment');

class InterestEvolutionMapper extends EventEmitter {
    constructor() {
        super();
        this.profiles = new Map();
        this.interestData = new Map();
        this.interestCategories = this.initializeInterestCategories();
        this.developmentalStages = this.initializeDevelopmentalStages();
        this.interestMeasurementMethods = this.initializeInterestMeasurementMethods();
        this.evolutionPatterns = this.initializeEvolutionPatterns();
        this.interestSupportStrategies = this.initializeInterestSupportStrategies();
        this.careerConnections = this.initializeCareerConnections();
    }

    initializeInterestCategories() {
        return {
            stem_interests: {
                description: 'Science, Technology, Engineering, and Mathematics',
                subcategories: {
                    life_sciences: {
                        areas: [
                            'Biology and living organisms',
                            'Environmental science',
                            'Health and medicine',
                            'Agriculture and food science',
                            'Genetics and biotechnology',
                            'Marine biology',
                            'Botany and plant science',
                            'Zoology and animal behavior'
                        ],
                        indicators: [
                            'Curiosity about how living things work',
                            'Interest in nature and outdoor exploration',
                            'Questions about health and body functions',
                            'Fascination with plants and animals',
                            'Environmental awareness and concern'
                        ]
                    },
                    physical_sciences: {
                        areas: [
                            'Physics and mechanics',
                            'Chemistry and chemical reactions',
                            'Astronomy and space science',
                            'Earth sciences and geology',
                            'Materials science',
                            'Energy and renewable resources',
                            'Weather and climate science',
                            'Nanotechnology'
                        ],
                        indicators: [
                            'Interest in how things work mechanically',
                            'Curiosity about chemical changes',
                            'Fascination with space and planets',
                            'Questions about natural phenomena',
                            'Enjoyment of physics experiments'
                        ]
                    },
                    mathematics: {
                        areas: [
                            'Pure mathematics',
                            'Applied mathematics',
                            'Statistics and probability',
                            'Mathematical modeling',
                            'Computational mathematics',
                            'Financial mathematics',
                            'Game theory',
                            'Cryptography'
                        ],
                        indicators: [
                            'Enjoyment of number puzzles',
                            'Pattern recognition abilities',
                            'Logic and reasoning interest',
                            'Problem-solving persistence',
                            'Abstract thinking preference'
                        ]
                    },
                    technology_engineering: {
                        areas: [
                            'Computer science and programming',
                            'Robotics and automation',
                            'Electrical and electronic engineering',
                            'Mechanical engineering',
                            'Civil and structural engineering',
                            'Aerospace engineering',
                            'Biomedical engineering',
                            'Environmental engineering'
                        ],
                        indicators: [
                            'Interest in building and construction',
                            'Curiosity about how devices work',
                            'Enjoyment of coding and programming',
                            'Problem-solving through design',
                            'Innovation and invention interest'
                        ]
                    }
                }
            },
            creative_arts: {
                description: 'Artistic and creative expression',
                subcategories: {
                    visual_arts: {
                        areas: [
                            'Drawing and illustration',
                            'Painting and color theory',
                            'Sculpture and 3D art',
                            'Photography and visual storytelling',
                            'Graphic design and digital art',
                            'Fashion and textile design',
                            'Architecture and spatial design',
                            'Animation and motion graphics'
                        ],
                        indicators: [
                            'Regular drawing or sketching',
                            'Interest in colors and composition',
                            'Creative use of materials',
                            'Visual observation skills',
                            'Aesthetic appreciation'
                        ]
                    },
                    performing_arts: {
                        areas: [
                            'Music composition and performance',
                            'Dance and choreography',
                            'Theater and acting',
                            'Public speaking and oratory',
                            'Comedy and entertainment',
                            'Opera and classical performance',
                            'Contemporary and popular music',
                            'Movement and physical expression'
                        ],
                        indicators: [
                            'Musical instrument interest',
                            'Rhythmic movement and dance',
                            'Dramatic play and storytelling',
                            'Performance confidence',
                            'Audience engagement skills'
                        ]
                    },
                    literary_arts: {
                        areas: [
                            'Creative writing and fiction',
                            'Poetry and verse',
                            'Journalism and non-fiction',
                            'Screenwriting and scripts',
                            'Children\'s literature',
                            'Technical and educational writing',
                            'Blog writing and digital content',
                            'Translation and interpretation'
                        ],
                        indicators: [
                            'Enjoyment of reading',
                            'Creative storytelling',
                            'Written expression preference',
                            'Language play and wordplay',
                            'Communication through writing'
                        ]
                    },
                    multimedia_arts: {
                        areas: [
                            'Film and video production',
                            'Interactive media design',
                            'Game design and development',
                            'Virtual reality experiences',
                            'Social media content creation',
                            'Podcasting and audio production',
                            'Web design and development',
                            'Cross-media storytelling'
                        ],
                        indicators: [
                            'Interest in video creation',
                            'Gaming and interactive experiences',
                            'Technology-mediated creativity',
                            'Cross-platform thinking',
                            'Digital storytelling skills'
                        ]
                    }
                }
            },
            social_humanities: {
                description: 'Human society, culture, and relationships',
                subcategories: {
                    social_sciences: {
                        areas: [
                            'Psychology and human behavior',
                            'Sociology and social systems',
                            'Anthropology and culture',
                            'Political science and governance',
                            'Economics and financial systems',
                            'Geography and human-environment interaction',
                            'Criminology and justice systems',
                            'Social work and community service'
                        ],
                        indicators: [
                            'Interest in human behavior',
                            'Questions about society and fairness',
                            'Concern for social issues',
                            'Leadership and organization skills',
                            'Empathy and helping orientation'
                        ]
                    },
                    humanities: {
                        areas: [
                            'History and historical research',
                            'Philosophy and ethical thinking',
                            'Religious and spiritual studies',
                            'Languages and linguistics',
                            'Cultural studies',
                            'Literature and literary analysis',
                            'Art history and criticism',
                            'Museum studies and preservation'
                        ],
                        indicators: [
                            'Interest in past events and stories',
                            'Philosophical questioning',
                            'Cultural curiosity',
                            'Language learning enjoyment',
                            'Historical context appreciation'
                        ]
                    },
                    communication_media: {
                        areas: [
                            'Journalism and news reporting',
                            'Public relations and marketing',
                            'Broadcasting and media production',
                            'Social media management',
                            'Advertising and creative campaigns',
                            'Documentary production',
                            'Corporate communication',
                            'Community outreach and engagement'
                        ],
                        indicators: [
                            'Interest in current events',
                            'Communication skills',
                            'Media consumption and analysis',
                            'Storytelling for audiences',
                            'Information sharing enthusiasm'
                        ]
                    },
                    education_development: {
                        areas: [
                            'Teaching and instruction',
                            'Curriculum development',
                            'Educational technology',
                            'Adult education and training',
                            'Special needs education',
                            'Educational administration',
                            'Learning research',
                            'Community education programs'
                        ],
                        indicators: [
                            'Enjoyment of explaining concepts',
                            'Patience with learning processes',
                            'Interest in how people learn',
                            'Helping others succeed',
                            'Educational innovation ideas'
                        ]
                    }
                }
            },
            business_entrepreneurship: {
                description: 'Business creation, management, and innovation',
                subcategories: {
                    business_management: {
                        areas: [
                            'Strategic planning and leadership',
                            'Operations and process management',
                            'Human resources and team building',
                            'Financial management and analysis',
                            'Marketing and brand development',
                            'Sales and customer relations',
                            'Supply chain and logistics',
                            'Quality management and improvement'
                        ],
                        indicators: [
                            'Natural leadership abilities',
                            'Interest in organizing and planning',
                            'People management skills',
                            'Strategic thinking orientation',
                            'Results and efficiency focus'
                        ]
                    },
                    entrepreneurship: {
                        areas: [
                            'Startup creation and development',
                            'Innovation and product development',
                            'Business model design',
                            'Investment and funding strategies',
                            'Market analysis and research',
                            'Risk assessment and management',
                            'Networking and partnership building',
                            'Social entrepreneurship and impact'
                        ],
                        indicators: [
                            'Innovation and idea generation',
                            'Risk-taking comfort',
                            'Problem-solving orientation',
                            'Independence and self-direction',
                            'Opportunity recognition skills'
                        ]
                    },
                    finance_economics: {
                        areas: [
                            'Investment and portfolio management',
                            'Banking and financial services',
                            'Insurance and risk management',
                            'Economic analysis and forecasting',
                            'International trade and finance',
                            'Real estate and property development',
                            'Cryptocurrency and fintech',
                            'Sustainable finance and ESG investing'
                        ],
                        indicators: [
                            'Interest in money and investing',
                            'Mathematical and analytical thinking',
                            'Market trends awareness',
                            'Future planning orientation',
                            'Economic systems understanding'
                        ]
                    },
                    consulting_advisory: {
                        areas: [
                            'Management consulting',
                            'Strategy and operations consulting',
                            'Technology consulting',
                            'Financial advisory services',
                            'Legal and compliance consulting',
                            'Specialized industry consulting',
                            'Change management consulting',
                            'Sustainability and social impact consulting'
                        ],
                        indicators: [
                            'Problem-solving expertise',
                            'Analysis and research skills',
                            'Communication and presentation abilities',
                            'Industry knowledge interest',
                            'Client service orientation'
                        ]
                    }
                }
            },
            physical_outdoor: {
                description: 'Physical activity, sports, and outdoor pursuits',
                subcategories: {
                    sports_athletics: {
                        areas: [
                            'Team sports and competition',
                            'Individual sports and personal records',
                            'Coaching and athletic development',
                            'Sports medicine and rehabilitation',
                            'Sports psychology and performance',
                            'Athletic training and fitness',
                            'Sports journalism and broadcasting',
                            'Sports management and administration'
                        ],
                        indicators: [
                            'Active participation in sports',
                            'Competitive spirit and drive',
                            'Physical coordination and skills',
                            'Team collaboration abilities',
                            'Performance improvement focus'
                        ]
                    },
                    outdoor_adventure: {
                        areas: [
                            'Hiking and mountaineering',
                            'Water sports and marine activities',
                            'Camping and wilderness survival',
                            'Rock climbing and extreme sports',
                            'Wildlife observation and photography',
                            'Environmental conservation',
                            'Outdoor education and guiding',
                            'Adventure tourism and travel'
                        ],
                        indicators: [
                            'Love of nature and outdoors',
                            'Adventure seeking behavior',
                            'Environmental awareness',
                            'Physical challenge enjoyment',
                            'Exploration and discovery interest'
                        ]
                    },
                    health_fitness: {
                        areas: [
                            'Personal training and fitness coaching',
                            'Nutrition and dietary planning',
                            'Wellness and lifestyle coaching',
                            'Rehabilitation and physical therapy',
                            'Yoga and mindfulness instruction',
                            'Group fitness and exercise classes',
                            'Health education and promotion',
                            'Sports nutrition and supplementation'
                        ],
                        indicators: [
                            'Interest in physical wellness',
                            'Health and nutrition awareness',
                            'Helping others with fitness',
                            'Body movement understanding',
                            'Holistic wellness perspective'
                        ]
                    },
                    recreation_leisure: {
                        areas: [
                            'Recreation program development',
                            'Community sports organization',
                            'Leisure activity instruction',
                            'Tourism and hospitality',
                            'Event planning and coordination',
                            'Theme park and entertainment design',
                            'Resort and vacation planning',
                            'Active lifestyle promotion'
                        ],
                        indicators: [
                            'Event organization abilities',
                            'People engagement skills',
                            'Activity planning interest',
                            'Community service orientation',
                            'Fun and enjoyment focus'
                        ]
                    }
                }
            },
            service_helping: {
                description: 'Helping others and serving community needs',
                subcategories: {
                    healthcare_medical: {
                        areas: [
                            'Medical practice and patient care',
                            'Nursing and health support',
                            'Mental health and counseling',
                            'Public health and epidemiology',
                            'Veterinary medicine',
                            'Pharmacy and pharmaceutical science',
                            'Medical research and development',
                            'Healthcare administration and policy'
                        ],
                        indicators: [
                            'Caring for others orientation',
                            'Interest in health and healing',
                            'Scientific curiosity about medicine',
                            'Empathy and compassion',
                            'Helping behavior in health contexts'
                        ]
                    },
                    social_services: {
                        areas: [
                            'Social work and case management',
                            'Child and family services',
                            'Elder care and gerontology',
                            'Disability support and advocacy',
                            'Community development and organizing',
                            'Non-profit management and fundraising',
                            'Volunteer coordination and management',
                            'Crisis intervention and support'
                        ],
                        indicators: [
                            'Strong helping orientation',
                            'Social justice concerns',
                            'Community involvement',
                            'Advocacy and support behaviors',
                            'Empathy for vulnerable populations'
                        ]
                    },
                    public_safety: {
                        areas: [
                            'Law enforcement and policing',
                            'Fire fighting and emergency response',
                            'Emergency medical services',
                            'Disaster relief and emergency management',
                            'Security and protection services',
                            'Military and defense',
                            'Border and immigration services',
                            'Public safety policy and administration'
                        ],
                        indicators: [
                            'Protecting others orientation',
                            'Physical courage and bravery',
                            'Emergency response interest',
                            'Rule enforcement comfort',
                            'Community safety concerns'
                        ]
                    },
                    legal_justice: {
                        areas: [
                            'Legal practice and advocacy',
                            'Judicial and court services',
                            'Criminal justice and corrections',
                            'Legal research and analysis',
                            'Mediation and conflict resolution',
                            'Legal education and policy',
                            'International law and human rights',
                            'Corporate and business law'
                        ],
                        indicators: [
                            'Interest in fairness and justice',
                            'Analytical and reasoning skills',
                            'Advocacy and argument abilities',
                            'Rule and regulation interest',
                            'Problem-solving through legal means'
                        ]
                    }
                }
            }
        };
    }

    initializeDevelopmentalStages() {
        return {
            ages_2_4: {
                interest_characteristics: [
                    'Concrete and immediate interests',
                    'Sensory-based preferences',
                    'Imitation and modeling',
                    'Short attention spans',
                    'Play-based exploration'
                ],
                typical_interests: [
                    'Animals and nature',
                    'Vehicles and transportation',
                    'Music and movement',
                    'Building and construction',
                    'Pretend play and stories'
                ],
                measurement_approaches: [
                    'Observational assessment',
                    'Play-based evaluation',
                    'Parent/caregiver reports',
                    'Activity preference tracking',
                    'Engagement time measurement'
                ],
                support_strategies: [
                    'Rich sensory experiences',
                    'Variety of materials and activities',
                    'Responsive interaction',
                    'Following child\'s lead',
                    'Celebrating exploration'
                ]
            },
            ages_5_7: {
                interest_characteristics: [
                    'Expanding attention spans',
                    'Beginning skill development',
                    'Peer influence emergence',
                    'Rule-based activities',
                    'Achievement motivation'
                ],
                typical_interests: [
                    'Sports and physical activities',
                    'Art and creative projects',
                    'Simple science experiments',
                    'Reading and storytelling',
                    'Collecting and organizing'
                ],
                measurement_approaches: [
                    'Interest inventories',
                    'Activity choice observations',
                    'Skill demonstration assessments',
                    'Portfolio collection',
                    'Self-report measures'
                ],
                support_strategies: [
                    'Skill building opportunities',
                    'Structured learning experiences',
                    'Peer group activities',
                    'Achievement recognition',
                    'Progressive challenges'
                ]
            },
            ages_8_10: {
                interest_characteristics: [
                    'Sustained engagement capacity',
                    'Skill refinement focus',
                    'Peer comparison awareness',
                    'Performance standards',
                    'Identity exploration beginning'
                ],
                typical_interests: [
                    'Specialized hobbies',
                    'Team sports and activities',
                    'Academic subject preferences',
                    'Technology and gaming',
                    'Social causes and helping'
                ],
                measurement_approaches: [
                    'Comprehensive interest surveys',
                    'Performance-based assessments',
                    'Peer and teacher nominations',
                    'Self-evaluation tools',
                    'Interest stability tracking'
                ],
                support_strategies: [
                    'Specialized instruction',
                    'Mentorship opportunities',
                    'Competition and challenges',
                    'Peer learning groups',
                    'Interest-based projects'
                ]
            },
            ages_11_13: {
                interest_characteristics: [
                    'Identity formation influence',
                    'Peer group importance',
                    'Future orientation emergence',
                    'Value system development',
                    'Independence seeking'
                ],
                typical_interests: [
                    'Social relationships and communication',
                    'Identity-related activities',
                    'Popular culture and trends',
                    'Academic and career exploration',
                    'Social justice and activism'
                ],
                measurement_approaches: [
                    'Multi-dimensional interest assessments',
                    'Career exploration tools',
                    'Value clarification exercises',
                    'Peer influence evaluations',
                    'Future planning discussions'
                ],
                support_strategies: [
                    'Identity exploration support',
                    'Career awareness programs',
                    'Peer mentoring',
                    'Value-based activities',
                    'Independence-building opportunities'
                ]
            },
            ages_14_plus: {
                interest_characteristics: [
                    'Career relevance consideration',
                    'Value-interest integration',
                    'Long-term commitment capacity',
                    'Specialized expertise development',
                    'Social impact awareness'
                ],
                typical_interests: [
                    'Career-related subjects',
                    'Specialized skill development',
                    'Leadership and service',
                    'Creative and artistic pursuits',
                    'Social and global issues'
                ],
                measurement_approaches: [
                    'Comprehensive career assessments',
                    'Interest-aptitude batteries',
                    'Work-based learning evaluations',
                    'Portfolio assessments',
                    'Future planning tools'
                ],
                support_strategies: [
                    'Career exploration experiences',
                    'Specialized training opportunities',
                    'Mentorship and internships',
                    'Leadership development',
                    'College and career planning'
                ]
            }
        };
    }

    initializeInterestMeasurementMethods() {
        return {
            observational_methods: {
                description: 'Systematic observation of interest behaviors',
                techniques: [
                    {
                        name: 'time_sampling',
                        description: 'Recording engagement at regular intervals',
                        age_range: '2-18',
                        procedure: [
                            'Define observation periods',
                            'Create coding system',
                            'Train observers',
                            'Collect systematic data',
                            'Analyze engagement patterns'
                        ]
                    },
                    {
                        name: 'event_sampling',
                        description: 'Recording specific interest-related events',
                        age_range: '3-18',
                        procedure: [
                            'Define target behaviors',
                            'Create event recording system',
                            'Document context and triggers',
                            'Record duration and intensity',
                            'Analyze frequency and patterns'
                        ]
                    },
                    {
                        name: 'activity_preference_assessment',
                        description: 'Measuring choices among activities',
                        age_range: '2-18',
                        procedure: [
                            'Present activity options',
                            'Record choice patterns',
                            'Measure engagement time',
                            'Document persistence',
                            'Analyze preference hierarchies'
                        ]
                    }
                ]
            },
            self_report_methods: {
                description: 'Individual reporting of interests and preferences',
                techniques: [
                    {
                        name: 'interest_inventories',
                        description: 'Structured questionnaires about interests',
                        age_range: '8-18',
                        examples: [
                            'Strong Interest Inventory',
                            'Kuder Career Search',
                            'Self-Directed Search',
                            'Career Assessment Inventory',
                            'Interest Profiler'
                        ]
                    },
                    {
                        name: 'activity_rating_scales',
                        description: 'Rating enjoyment and interest levels',
                        age_range: '6-18',
                        components: [
                            'Activity lists with rating scales',
                            'Enjoyment level indicators',
                            'Participation frequency measures',
                            'Skill development interest',
                            'Future engagement intentions'
                        ]
                    },
                    {
                        name: 'interest_interviews',
                        description: 'In-depth discussions about interests',
                        age_range: '5-18',
                        structure: [
                            'Current interest exploration',
                            'Interest development history',
                            'Motivation and value discussion',
                            'Future interest aspirations',
                            'Barrier and support identification'
                        ]
                    }
                ]
            },
            performance_based_methods: {
                description: 'Measuring interest through performance and engagement',
                techniques: [
                    {
                        name: 'portfolio_assessment',
                        description: 'Collection of interest-related work and artifacts',
                        age_range: '4-18',
                        components: [
                            'Work samples and projects',
                            'Reflection documents',
                            'Progress documentation',
                            'Interest exploration records',
                            'Achievement evidence'
                        ]
                    },
                    {
                        name: 'task_engagement_measures',
                        description: 'Measuring involvement in specific tasks',
                        age_range: '3-18',
                        indicators: [
                            'Time on task',
                            'Effort and persistence',
                            'Quality of work',
                            'Self-initiated exploration',
                            'Help-seeking behavior'
                        ]
                    },
                    {
                        name: 'choice_making_assessments',
                        description: 'Evaluating decisions in interest contexts',
                        age_range: '5-18',
                        measures: [
                            'Free choice situations',
                            'Forced choice scenarios',
                            'Resource allocation decisions',
                            'Time investment choices',
                            'Effort distribution patterns'
                        ]
                    }
                ]
            },
            multi_informant_methods: {
                description: 'Gathering information from multiple sources',
                techniques: [
                    {
                        name: 'parent_teacher_ratings',
                        description: 'Adult observations of interest behaviors',
                        age_range: '2-18',
                        components: [
                            'Interest behavior checklists',
                            'Engagement level ratings',
                            'Skill development observations',
                            'Motivation indicators',
                            'Support needs identification'
                        ]
                    },
                    {
                        name: 'peer_nominations',
                        description: 'Peer recognition of interests and talents',
                        age_range: '6-18',
                        procedures: [
                            'Interest area nominations',
                            'Talent recognition activities',
                            'Collaboration preference assessment',
                            'Leadership identification',
                            'Peer support network mapping'
                        ]
                    }
                ]
            }
        };
    }

    initializeEvolutionPatterns() {
        return {
            interest_development_trajectories: {
                emergent_pattern: {
                    description: 'New interests that appear suddenly',
                    characteristics: [
                        'Rapid onset of engagement',
                        'High initial intensity',
                        'Exploration and discovery phase',
                        'Uncertainty about persistence',
                        'External trigger or influence'
                    ],
                    typical_causes: [
                        'Exposure to new experiences',
                        'Peer or mentor influence',
                        'Media or cultural exposure',
                        'Developmental readiness',
                        'Environmental opportunities'
                    ],
                    support_strategies: [
                        'Provide rich exploration opportunities',
                        'Connect with mentors or experts',
                        'Offer skill-building resources',
                        'Monitor engagement and progress',
                        'Allow natural development pace'
                    ]
                },
                developing_pattern: {
                    description: 'Interests growing steadily over time',
                    characteristics: [
                        'Gradual intensity increase',
                        'Skill development progression',
                        'Sustained engagement',
                        'Expanding related interests',
                        'Growing expertise'
                    ],
                    typical_causes: [
                        'Positive experiences and success',
                        'Skill mastery and competence',
                        'Social support and encouragement',
                        'Value alignment',
                        'Identity integration'
                    ],
                    support_strategies: [
                        'Provide progressive challenges',
                        'Offer specialized instruction',
                        'Create community connections',
                        'Recognize achievements',
                        'Support goal setting'
                    ]
                },
                stable_pattern: {
                    description: 'Consistent interests maintained over time',
                    characteristics: [
                        'Steady engagement levels',
                        'Established skill sets',
                        'Integrated into identity',
                        'Consistent time investment',
                        'Predictable patterns'
                    ],
                    typical_causes: [
                        'Strong value alignment',
                        'Natural talent and ability',
                        'Social identity integration',
                        'Environmental support',
                        'Personal meaning and purpose'
                    ],
                    support_strategies: [
                        'Maintain quality opportunities',
                        'Support advancement and growth',
                        'Encourage mentoring others',
                        'Provide leadership roles',
                        'Connect to future goals'
                    ]
                },
                declining_pattern: {
                    description: 'Interests losing intensity over time',
                    characteristics: [
                        'Decreasing engagement',
                        'Reduced time investment',
                        'Shifting priorities',
                        'Boredom or frustration',
                        'Alternative interest development'
                    ],
                    typical_causes: [
                        'Lack of challenge or growth',
                        'Competing interests',
                        'Social or peer pressure',
                        'Developmental changes',
                        'External barriers or obstacles'
                    ],
                    support_strategies: [
                        'Assess barriers and challenges',
                        'Introduce new dimensions',
                        'Respect natural evolution',
                        'Support transition processes',
                        'Maintain connection opportunities'
                    ]
                },
                cycling_pattern: {
                    description: 'Interests that return after periods of dormancy',
                    characteristics: [
                        'Periodic engagement waves',
                        'Variable intensity levels',
                        'Contextual activation',
                        'Maintained underlying connection',
                        'Responsive to triggers'
                    ],
                    typical_causes: [
                        'Seasonal or contextual factors',
                        'Life stage transitions',
                        'External opportunities',
                        'Social or cultural events',
                        'Personal readiness changes'
                    ],
                    support_strategies: [
                        'Recognize cyclical patterns',
                        'Maintain flexible access',
                        'Support re-engagement',
                        'Understand triggering factors',
                        'Provide patient encouragement'
                    ]
                }
            },
            interest_relationship_patterns: {
                branching_interests: {
                    description: 'One interest leading to related interests',
                    examples: [
                        'Music leading to sound engineering',
                        'Sports leading to sports medicine',
                        'Art leading to graphic design',
                        'Cooking leading to nutrition science',
                        'Gaming leading to programming'
                    ]
                },
                converging_interests: {
                    description: 'Multiple interests combining into new areas',
                    examples: [
                        'Art + technology = digital design',
                        'Science + communication = science writing',
                        'Business + environment = sustainable entrepreneurship',
                        'Sports + psychology = sport psychology',
                        'Music + technology = audio engineering'
                    ]
                },
                competing_interests: {
                    description: 'Interests that compete for time and attention',
                    management_strategies: [
                        'Time scheduling and allocation',
                        'Season or phase rotation',
                        'Integration opportunities',
                        'Priority clarification',
                        'Balance and moderation'
                    ]
                },
                complementary_interests: {
                    description: 'Interests that enhance and support each other',
                    examples: [
                        'Reading supporting writing',
                        'Mathematics supporting science',
                        'Physical fitness supporting sports',
                        'History supporting cultural arts',
                        'Psychology supporting education'
                    ]
                }
            }
        };
    }

    initializeInterestSupportStrategies() {
        return {
            exploration_support: {
                description: 'Helping individuals discover and explore interests',
                strategies: [
                    {
                        name: 'exposure_experiences',
                        description: 'Providing diverse activity exposure',
                        methods: [
                            'Field trips and site visits',
                            'Guest speaker presentations',
                            'Workshop and class offerings',
                            'Media and virtual experiences',
                            'Hands-on demonstration sessions'
                        ]
                    },
                    {
                        name: 'try_it_opportunities',
                        description: 'Low-commitment trial experiences',
                        methods: [
                            'Sample classes and workshops',
                            'Club and organization visits',
                            'Shadowing and observation',
                            'Short-term projects',
                            'Interest fairs and exhibitions'
                        ]
                    },
                    {
                        name: 'guided_exploration',
                        description: 'Structured interest discovery processes',
                        methods: [
                            'Interest assessment discussions',
                            'Reflection and journaling',
                            'Goal setting and planning',
                            'Progress monitoring and review',
                            'Interest mapping and connection making'
                        ]
                    }
                ]
            },
            development_support: {
                description: 'Supporting growth and advancement in interests',
                strategies: [
                    {
                        name: 'skill_building',
                        description: 'Progressive skill development opportunities',
                        methods: [
                            'Sequential instruction programs',
                            'Mentorship and coaching',
                            'Practice and repetition support',
                            'Feedback and improvement guidance',
                            'Challenge and advancement pathways'
                        ]
                    },
                    {
                        name: 'resource_provision',
                        description: 'Access to materials and tools',
                        methods: [
                            'Equipment and material access',
                            'Information and learning resources',
                            'Technology and software access',
                            'Space and facility availability',
                            'Financial and scholarship support'
                        ]
                    },
                    {
                        name: 'community_connection',
                        description: 'Linking to interest communities',
                        methods: [
                            'Club and organization membership',
                            'Peer group formation',
                            'Mentor and expert connection',
                            'Online community participation',
                            'Event and gathering attendance'
                        ]
                    }
                ]
            },
            sustaining_support: {
                description: 'Maintaining interest engagement over time',
                strategies: [
                    {
                        name: 'motivation_maintenance',
                        description: 'Keeping interest and engagement high',
                        methods: [
                            'Achievement recognition and celebration',
                            'Goal setting and progress tracking',
                            'Challenge and novelty introduction',
                            'Autonomy and choice provision',
                            'Purpose and meaning connection'
                        ]
                    },
                    {
                        name: 'obstacle_removal',
                        description: 'Addressing barriers to continued engagement',
                        methods: [
                            'Time and scheduling support',
                            'Transportation and access assistance',
                            'Financial barrier reduction',
                            'Social and family support',
                            'Skill gap identification and support'
                        ]
                    },
                    {
                        name: 'evolution_support',
                        description: 'Adapting to changing interests and needs',
                        methods: [
                            'Flexible programming and options',
                            'Transition and pathway planning',
                            'Advanced and specialized opportunities',
                            'Leadership and teaching roles',
                            'Career and future connection'
                        ]
                    }
                ]
            }
        };
    }

    initializeCareerConnections() {
        return {
            interest_to_career_pathways: {
                stem_pathways: [
                    { interest: 'life_sciences', careers: ['Biologist', 'Doctor', 'Veterinarian', 'Environmental Scientist', 'Geneticist'] },
                    { interest: 'physical_sciences', careers: ['Physicist', 'Chemist', 'Astronomer', 'Geologist', 'Materials Scientist'] },
                    { interest: 'mathematics', careers: ['Mathematician', 'Statistician', 'Actuary', 'Data Scientist', 'Cryptographer'] },
                    { interest: 'technology_engineering', careers: ['Software Engineer', 'Robotics Engineer', 'Electrical Engineer', 'Aerospace Engineer'] }
                ],
                creative_pathways: [
                    { interest: 'visual_arts', careers: ['Graphic Designer', 'Illustrator', 'Photographer', 'Art Director', 'Animator'] },
                    { interest: 'performing_arts', careers: ['Musician', 'Actor', 'Dancer', 'Director', 'Music Therapist'] },
                    { interest: 'literary_arts', careers: ['Writer', 'Editor', 'Journalist', 'Screenwriter', 'Literary Agent'] },
                    { interest: 'multimedia_arts', careers: ['Film Director', 'Game Designer', 'Web Developer', 'Content Creator'] }
                ],
                social_pathways: [
                    { interest: 'social_sciences', careers: ['Psychologist', 'Sociologist', 'Political Scientist', 'Social Worker', 'Anthropologist'] },
                    { interest: 'humanities', careers: ['Historian', 'Philosopher', 'Linguist', 'Museum Curator', 'Archivist'] },
                    { interest: 'communication_media', careers: ['Journalist', 'PR Specialist', 'Broadcaster', 'Marketing Manager'] },
                    { interest: 'education_development', careers: ['Teacher', 'Principal', 'Curriculum Developer', 'Educational Consultant'] }
                ],
                business_pathways: [
                    { interest: 'business_management', careers: ['CEO', 'Operations Manager', 'HR Director', 'Marketing Manager', 'Sales Manager'] },
                    { interest: 'entrepreneurship', careers: ['Startup Founder', 'Business Owner', 'Venture Capitalist', 'Innovation Manager'] },
                    { interest: 'finance_economics', careers: ['Financial Analyst', 'Investment Banker', 'Economist', 'Real Estate Developer'] },
                    { interest: 'consulting_advisory', careers: ['Management Consultant', 'Strategy Consultant', 'Financial Advisor'] }
                ],
                service_pathways: [
                    { interest: 'healthcare_medical', careers: ['Doctor', 'Nurse', 'Therapist', 'Pharmacist', 'Public Health Officer'] },
                    { interest: 'social_services', careers: ['Social Worker', 'Community Organizer', 'Non-profit Director', 'Counselor'] },
                    { interest: 'public_safety', careers: ['Police Officer', 'Firefighter', 'EMT', 'Military Officer', 'Security Specialist'] },
                    { interest: 'legal_justice', careers: ['Lawyer', 'Judge', 'Paralegal', 'Mediator', 'Legal Researcher'] }
                ]
            },
            career_exploration_activities: {
                informational_interviews: {
                    description: 'Conversations with professionals in interest areas',
                    age_appropriate: '12+',
                    structure: [
                        'Identify professionals to interview',
                        'Prepare thoughtful questions',
                        'Conduct respectful interviews',
                        'Follow up with thank you notes',
                        'Reflect on learning and insights'
                    ]
                },
                job_shadowing: {
                    description: 'Observing professionals at work',
                    age_appropriate: '14+',
                    components: [
                        'Workplace observation',
                        'Daily routine understanding',
                        'Skill requirement awareness',
                        'Work environment exposure',
                        'Career reality assessment'
                    ]
                },
                internships_work_experience: {
                    description: 'Hands-on work experience in interest areas',
                    age_appropriate: '16+',
                    benefits: [
                        'Real work experience',
                        'Skill development opportunities',
                        'Professional network building',
                        'Career decision information',
                        'Resume and portfolio development'
                    ]
                },
                career_fairs_events: {
                    description: 'Events showcasing various career options',
                    age_appropriate: '10+',
                    activities: [
                        'Career booth exploration',
                        'Professional presentations',
                        'Interactive demonstrations',
                        'Information collection',
                        'Network connection building'
                    ]
                }
            }
        };
    }

    createProfile(studentId, age, initialInterests = []) {
        const profile = {
            id: uuidv4(),
            studentId,
            age,
            interestProfile: this.initializeInterestProfile(initialInterests),
            evolutionHistory: [],
            assessmentHistory: [],
            developmentalStage: this.determineStage(age),
            strengthAreas: [],
            emergingInterests: [],
            supportNeeds: [],
            careerConnections: [],
            createdAt: moment().toISOString(),
            updatedAt: moment().toISOString()
        };

        this.profiles.set(profile.id, profile);
        this.emit('profileCreated', { profileId: profile.id, studentId });

        return profile.id;
    }

    initializeInterestProfile(initialInterests = []) {
        const profile = {
            current_interests: {},
            interest_strengths: {},
            engagement_patterns: {},
            evolution_tracking: {}
        };

        Object.keys(this.interestCategories).forEach(category => {
            profile.current_interests[category] = {
                level: 'none',
                intensity: 0,
                duration: 0,
                subcategories: {}
            };

            Object.keys(this.interestCategories[category].subcategories || {}).forEach(subcategory => {
                profile.current_interests[category].subcategories[subcategory] = {
                    level: 'none',
                    intensity: 0,
                    engagement_history: []
                };
            });
        });

        initialInterests.forEach(interest => {
            if (profile.current_interests[interest.category]) {
                profile.current_interests[interest.category].level = interest.level || 'emerging';
                profile.current_interests[interest.category].intensity = interest.intensity || 50;
            }
        });

        return profile;
    }

    recordInterestAssessment(profileId, assessmentData) {
        const profile = this.profiles.get(profileId);
        if (!profile) {
            throw new Error('Profile not found');
        }

        const assessment = {
            id: uuidv4(),
            timestamp: moment().toISOString(),
            method: assessmentData.method,
            results: assessmentData.results,
            context: assessmentData.context || {},
            changes_identified: []
        };

        assessment.changes_identified = this.identifyInterestChanges(
            profile.interestProfile,
            assessment.results
        );

        this.updateInterestProfile(profile, assessment.results);
        profile.assessmentHistory.push(assessment);
        profile.updatedAt = moment().toISOString();

        this.emit('interestAssessmentCompleted', { 
            profileId, 
            assessmentId: assessment.id,
            changes: assessment.changes_identified 
        });

        return assessment.id;
    }

    identifyInterestChanges(currentProfile, newResults) {
        const changes = [];
        
        Object.keys(newResults.interests || {}).forEach(category => {
            const current = currentProfile.current_interests[category];
            const newData = newResults.interests[category];
            
            if (!current) return;
            
            if (newData.intensity > current.intensity + 10) {
                changes.push({
                    type: 'increase',
                    category,
                    change: newData.intensity - current.intensity,
                    significance: this.assessChangeSignificance(newData.intensity - current.intensity)
                });
            } else if (newData.intensity < current.intensity - 10) {
                changes.push({
                    type: 'decrease',
                    category,
                    change: current.intensity - newData.intensity,
                    significance: this.assessChangeSignificance(current.intensity - newData.intensity)
                });
            }
            
            if (newData.level !== current.level) {
                changes.push({
                    type: 'level_change',
                    category,
                    from: current.level,
                    to: newData.level,
                    direction: this.compareLevels(current.level, newData.level)
                });
            }
        });
        
        return changes;
    }

    assessChangeSignificance(magnitude) {
        if (magnitude >= 30) return 'major';
        if (magnitude >= 15) return 'moderate';
        return 'minor';
    }

    compareLevels(oldLevel, newLevel) {
        const levels = ['none', 'emerging', 'developing', 'strong', 'passionate'];
        const oldIndex = levels.indexOf(oldLevel);
        const newIndex = levels.indexOf(newLevel);
        
        if (newIndex > oldIndex) return 'increase';
        if (newIndex < oldIndex) return 'decrease';
        return 'stable';
    }

    updateInterestProfile(profile, assessmentResults) {
        Object.keys(assessmentResults.interests || {}).forEach(category => {
            const newData = assessmentResults.interests[category];
            const current = profile.interestProfile.current_interests[category];
            
            if (current) {
                current.level = newData.level || current.level;
                current.intensity = newData.intensity || current.intensity;
                current.duration = this.calculateDuration(current, newData);
                
                if (newData.subcategories) {
                    Object.keys(newData.subcategories).forEach(subcategory => {
                        if (current.subcategories[subcategory]) {
                            current.subcategories[subcategory].level = newData.subcategories[subcategory].level;
                            current.subcategories[subcategory].intensity = newData.subcategories[subcategory].intensity;
                            current.subcategories[subcategory].engagement_history.push({
                                timestamp: moment().toISOString(),
                                level: newData.subcategories[subcategory].level,
                                intensity: newData.subcategories[subcategory].intensity
                            });
                        }
                    });
                }
            }
        });
    }

    trackInterestEvolution(profileId, timeframe = 'all') {
        const profile = this.profiles.get(profileId);
        if (!profile) {
            throw new Error('Profile not found');
        }

        const evolutionData = {
            timeframe,
            patterns_identified: [],
            trajectory_analysis: {},
            stability_assessment: {},
            prediction_indicators: {}
        };

        const assessmentHistory = this.filterByTimeframe(profile.assessmentHistory, timeframe);
        
        if (assessmentHistory.length < 2) {
            evolutionData.patterns_identified.push('insufficient_data');
            return evolutionData;
        }

        evolutionData.patterns_identified = this.identifyEvolutionPatterns(assessmentHistory);
        evolutionData.trajectory_analysis = this.analyzeTrajectories(assessmentHistory);
        evolutionData.stability_assessment = this.assessInterestStability(assessmentHistory);
        evolutionData.prediction_indicators = this.generatePredictionIndicators(assessmentHistory, profile);

        profile.evolutionHistory.push({
            timestamp: moment().toISOString(),
            analysis: evolutionData
        });

        this.emit('evolutionAnalysisCompleted', { profileId, analysis: evolutionData });

        return evolutionData;
    }

    identifyEvolutionPatterns(assessmentHistory) {
        const patterns = [];
        const categories = Object.keys(this.interestCategories);
        
        categories.forEach(category => {
            const categoryData = this.extractCategoryData(assessmentHistory, category);
            const pattern = this.classifyEvolutionPattern(categoryData);
            
            if (pattern !== 'insufficient_data') {
                patterns.push({
                    category,
                    pattern,
                    confidence: this.calculatePatternConfidence(categoryData),
                    description: this.getPatternDescription(pattern)
                });
            }
        });
        
        return patterns;
    }

    extractCategoryData(assessmentHistory, category) {
        return assessmentHistory.map(assessment => ({
            timestamp: assessment.timestamp,
            level: assessment.results.interests?.[category]?.level || 'none',
            intensity: assessment.results.interests?.[category]?.intensity || 0
        })).filter(data => data.level !== 'none' || data.intensity > 0);
    }

    classifyEvolutionPattern(categoryData) {
        if (categoryData.length < 2) return 'insufficient_data';
        
        const intensities = categoryData.map(d => d.intensity);
        const trend = this.calculateTrend(intensities);
        const variance = this.calculateVariance(intensities);
        
        if (Math.abs(trend) < 2 && variance < 10) return 'stable';
        if (trend > 5) return 'developing';
        if (trend < -5) return 'declining';
        if (variance > 20) return 'cycling';
        
        return 'emergent';
    }

    calculateTrend(values) {
        if (values.length < 2) return 0;
        
        const n = values.length;
        const sumX = (n * (n - 1)) / 2;
        const sumY = values.reduce((sum, val) => sum + val, 0);
        const sumXY = values.reduce((sum, val, index) => sum + (val * index), 0);
        const sumXX = (n * (n - 1) * (2 * n - 1)) / 6;
        
        return (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    }

    calculateVariance(values) {
        if (values.length < 2) return 0;
        
        const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
        const squaredDiffs = values.map(val => Math.pow(val - mean, 2));
        return squaredDiffs.reduce((sum, val) => sum + val, 0) / values.length;
    }

    generateInterestReport(profileId) {
        const profile = this.profiles.get(profileId);
        if (!profile) return null;

        const evolutionAnalysis = this.trackInterestEvolution(profileId);
        const strengthAnalysis = this.analyzeInterestStrengths(profile);
        const careerConnections = this.generateCareerConnections(profile);
        const supportRecommendations = this.generateSupportRecommendations(profile);

        return {
            studentId: profile.studentId,
            age: profile.age,
            developmentalStage: profile.developmentalStage,
            reportDate: moment().toISOString(),
            currentInterests: this.formatCurrentInterests(profile.interestProfile),
            strengthAreas: strengthAnalysis.strengths,
            emergingInterests: strengthAnalysis.emerging,
            evolutionPatterns: evolutionAnalysis.patterns_identified,
            stabilityAssessment: evolutionAnalysis.stability_assessment,
            careerConnections: careerConnections,
            supportRecommendations: supportRecommendations,
            nextSteps: this.generateNextSteps(profile),
            nextAssessmentDate: moment().add(6, 'months').toISOString()
        };
    }

    formatCurrentInterests(interestProfile) {
        const formatted = {};
        
        Object.keys(interestProfile.current_interests).forEach(category => {
            const categoryData = interestProfile.current_interests[category];
            
            if (categoryData.level !== 'none' && categoryData.intensity > 0) {
                formatted[category] = {
                    level: categoryData.level,
                    intensity: categoryData.intensity,
                    duration_months: categoryData.duration,
                    strongestSubcategories: this.identifyStrongSubcategories(categoryData.subcategories)
                };
            }
        });
        
        return formatted;
    }

    identifyStrongSubcategories(subcategories) {
        return Object.entries(subcategories || {})
            .filter(([_, data]) => data.level !== 'none' && data.intensity > 60)
            .map(([name, data]) => ({ name, level: data.level, intensity: data.intensity }))
            .sort((a, b) => b.intensity - a.intensity)
            .slice(0, 3);
    }

    analyzeInterestStrengths(profile) {
        const strengths = [];
        const emerging = [];
        
        Object.entries(profile.interestProfile.current_interests).forEach(([category, data]) => {
            if (data.intensity >= 70 && data.level === 'strong' || data.level === 'passionate') {
                strengths.push({
                    category,
                    intensity: data.intensity,
                    level: data.level,
                    stability: this.assessCategoryStability(profile.assessmentHistory, category)
                });
            } else if (data.intensity >= 40 && data.level === 'developing') {
                emerging.push({
                    category,
                    intensity: data.intensity,
                    level: data.level,
                    growth_potential: this.assessGrowthPotential(profile.assessmentHistory, category)
                });
            }
        });
        
        return { strengths: strengths.slice(0, 5), emerging: emerging.slice(0, 3) };
    }

    generateCareerConnections(profile) {
        const connections = [];
        const strongInterests = Object.entries(profile.interestProfile.current_interests)
            .filter(([_, data]) => data.intensity >= 60)
            .map(([category, _]) => category);
        
        strongInterests.forEach(interest => {
            const pathways = this.findCareerPathways(interest);
            if (pathways.length > 0) {
                connections.push({
                    interest,
                    pathways: pathways.slice(0, 5),
                    exploration_activities: this.suggestExplorationActivities(interest, profile.age)
                });
            }
        });
        
        return connections;
    }

    findCareerPathways(interest) {
        const allPathways = Object.values(this.careerConnections.interest_to_career_pathways).flat();
        return allPathways
            .filter(pathway => pathway.interest === interest || 
                   pathway.interest.includes(interest.split('_')[0]))
            .map(pathway => pathway.careers)
            .flat()
            .slice(0, 8);
    }

    suggestExplorationActivities(interest, age) {
        const activities = [];
        const ageAppropriate = this.careerConnections.career_exploration_activities;
        
        Object.entries(ageAppropriate).forEach(([activity, details]) => {
            const minAge = parseInt(details.age_appropriate.split('+')[0]);
            if (age >= minAge) {
                activities.push({
                    activity,
                    description: details.description,
                    suitability: age >= minAge + 2 ? 'highly_suitable' : 'suitable'
                });
            }
        });
        
        return activities;
    }

    generateSupportRecommendations(profile) {
        const recommendations = [];
        const currentInterests = profile.interestProfile.current_interests;
        
        Object.entries(currentInterests).forEach(([category, data]) => {
            if (data.level !== 'none') {
                const support = this.determineOptimalSupport(category, data.level, data.intensity, profile.age);
                if (support) {
                    recommendations.push({
                        category,
                        support_type: support.type,
                        strategies: support.strategies,
                        priority: support.priority,
                        timeline: support.timeline
                    });
                }
            }
        });
        
        return recommendations.sort((a, b) => this.priorityOrder(a.priority) - this.priorityOrder(b.priority));
    }

    determineOptimalSupport(category, level, intensity, age) {
        const stage = this.determineStage(age);
        const stageData = this.developmentalStages[stage];
        
        if (intensity >= 70) {
            return {
                type: 'advancement',
                strategies: this.interestSupportStrategies.development_support.strategies,
                priority: 'high',
                timeline: '3-6 months'
            };
        } else if (level === 'emerging') {
            return {
                type: 'exploration',
                strategies: this.interestSupportStrategies.exploration_support.strategies,
                priority: 'medium',
                timeline: '1-3 months'
            };
        } else if (intensity < 40) {
            return {
                type: 'sustaining',
                strategies: this.interestSupportStrategies.sustaining_support.strategies,
                priority: 'low',
                timeline: 'ongoing'
            };
        }
        
        return null;
    }

    priorityOrder(priority) {
        const order = { 'high': 1, 'medium': 2, 'low': 3 };
        return order[priority] || 4;
    }

    generateNextSteps(profile) {
        const steps = [];
        const recentAssessment = profile.assessmentHistory[profile.assessmentHistory.length - 1];
        
        steps.push('Continue regular interest monitoring and assessment');
        
        if (recentAssessment && recentAssessment.changes_identified.length > 0) {
            steps.push('Follow up on identified interest changes');
        }
        
        const strongInterests = Object.entries(profile.interestProfile.current_interests)
            .filter(([_, data]) => data.intensity >= 60).length;
        
        if (strongInterests === 0) {
            steps.push('Focus on interest exploration and discovery activities');
        } else if (strongInterests >= 3) {
            steps.push('Consider interest integration and career connection activities');
        }
        
        if (profile.age >= 14) {
            steps.push('Begin formal career exploration and planning processes');
        }
        
        return steps;
    }

    determineStage(age) {
        if (age <= 4) return 'ages_2_4';
        if (age <= 7) return 'ages_5_7';
        if (age <= 10) return 'ages_8_10';
        if (age <= 13) return 'ages_11_13';
        return 'ages_14_plus';
    }

    filterByTimeframe(history, timeframe) {
        if (timeframe === 'all') return history;
        
        const cutoffDate = moment().subtract(1, timeframe);
        return history.filter(item => moment(item.timestamp).isAfter(cutoffDate));
    }

    calculateDuration(current, newData) {
        if (!current.start_date && (newData.level !== 'none' || newData.intensity > 0)) {
            current.start_date = moment().toISOString();
            return 0;
        }
        
        if (current.start_date) {
            return moment().diff(moment(current.start_date), 'months');
        }
        
        return current.duration || 0;
    }
}

module.exports = InterestEvolutionMapper;