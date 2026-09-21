"""
Integration tests for adult learning adaptations
Tests adaptive learning systems, professional development tracking, and skill assessment
"""

import pytest
import asyncio
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx
from unittest.mock import Mock, patch, MagicMock

# Test configuration
STUDYLOG_ADULTS_URL = "http://localhost:8319"
EDUCATION_AI_URL = "http://localhost:8320"
SKILL_DEVELOPMENT_URL = "http://localhost:8321"
PROFESSIONAL_CERTS_URL = "http://localhost:8322"
API_GATEWAY_URL = "http://localhost:8000"


class TestAdultLearningAdaptations:
    """Test adult learning adaptations and professional development features"""
    
    @pytest.fixture
    def adult_learner_profile(self):
        """Sample adult learner profile"""
        return {
            'learner_id': str(uuid.uuid4()),
            'name': 'Sarah Professional',
            'age': 32,
            'occupation': 'Software Developer',
            'education_level': 'bachelors_degree',
            'learning_preferences': {
                'preferred_time_slots': ['early_morning', 'evening'],
                'session_length': 45,  # minutes
                'learning_style': 'visual_kinesthetic',
                'pace_preference': 'self_paced',
                'break_frequency': 25  # Pomodoro technique
            },
            'professional_goals': [
                'machine_learning_certification',
                'cloud_architecture_skills',
                'leadership_development',
                'public_speaking_improvement'
            ],
            'constraints': {
                'time_availability': '6-8 hours per week',
                'budget': 'moderate',
                'location': 'remote_only',
                'family_commitments': True
            },
            'current_skills': {
                'programming': 'advanced',
                'data_analysis': 'intermediate',
                'project_management': 'beginner',
                'communication': 'intermediate'
            }
        }
    
    @pytest.fixture
    def professional_development_plan(self):
        """Sample professional development plan"""
        return {
            'plan_id': str(uuid.uuid4()),
            'title': 'ML Engineer Career Transition',
            'duration_weeks': 24,
            'target_role': 'Machine Learning Engineer',
            'milestones': [
                {
                    'week': 4,
                    'title': 'Python for Data Science Fundamentals',
                    'skills': ['pandas', 'numpy', 'matplotlib'],
                    'assessment_type': 'project_portfolio'
                },
                {
                    'week': 8,
                    'title': 'Machine Learning Algorithms',
                    'skills': ['supervised_learning', 'unsupervised_learning'],
                    'assessment_type': 'certification_exam'
                },
                {
                    'week': 16,
                    'title': 'Deep Learning Specialization',
                    'skills': ['neural_networks', 'tensorflow', 'pytorch'],
                    'assessment_type': 'capstone_project'
                },
                {
                    'week': 24,
                    'title': 'MLOps and Deployment',
                    'skills': ['model_deployment', 'monitoring', 'ci_cd'],
                    'assessment_type': 'practical_interview'
                }
            ],
            'learning_resources': [
                'interactive_courses',
                'peer_study_groups',
                'mentor_sessions',
                'industry_projects'
            ]
        }
    
    @pytest.fixture
    def corporate_training_program(self):
        """Sample corporate training program"""
        return {
            'program_id': str(uuid.uuid4()),
            'company': 'TechCorp Solutions',
            'title': 'Digital Leadership Transformation',
            'participants': 50,
            'duration_months': 6,
            'delivery_mode': 'blended',
            'objectives': [
                'digital_literacy',
                'remote_team_management',
                'agile_methodologies',
                'data_driven_decision_making'
            ],
            'assessment_framework': {
                'pre_assessment': True,
                'continuous_assessment': True,
                'peer_evaluation': True,
                'manager_feedback': True,
                'post_assessment': True
            },
            'compliance_requirements': [
                'accessibility_standards',
                'data_privacy',
                'industry_regulations'
            ]
        }
    
    @pytest.fixture
    async def authenticated_adult_sessions(self, adult_learner_profile):
        """Authenticated sessions for adult learners and corporate admin"""
        return {
            'learner': {
                'profile': adult_learner_profile,
                'token': 'adult.learner.token',
                'headers': {'Authorization': 'Bearer adult.learner.token'}
            },
            'corporate_admin': {
                'user_id': str(uuid.uuid4()),
                'token': 'corporate.admin.token',
                'headers': {'Authorization': 'Bearer corporate.admin.token'},
                'role': 'corporate_learning_admin'
            },
            'mentor': {
                'user_id': str(uuid.uuid4()),
                'token': 'mentor.token',
                'headers': {'Authorization': 'Bearer mentor.token'},
                'role': 'professional_mentor'
            }
        }

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_adaptive_professional_learning_path(self, authenticated_adult_sessions, professional_development_plan):
        """Test adaptive professional learning path creation and adjustment"""
        
        async with httpx.AsyncClient() as client:
            learner_session = authenticated_adult_sessions['learner']
            
            # Step 1: Initial skills assessment
            skills_assessment = {
                'assessment_type': 'comprehensive_skills_evaluation',
                'domains': [
                    'technical_skills',
                    'soft_skills',
                    'industry_knowledge',
                    'learning_agility'
                ],
                'time_limit_minutes': 90
            }
            
            assessment_response = await client.post(
                f"{SKILL_DEVELOPMENT_URL}/api/assessments/start",
                json=skills_assessment,
                headers=learner_session['headers']
            )
            assert assessment_response.status_code == 201
            
            assessment_id = assessment_response.json()['assessment_id']
            
            # Simulate assessment completion
            assessment_answers = {
                'technical_skills': {
                    'python_programming': 8,  # out of 10
                    'data_structures': 7,
                    'machine_learning_theory': 4,
                    'cloud_platforms': 3
                },
                'soft_skills': {
                    'communication': 6,
                    'leadership': 4,
                    'problem_solving': 8,
                    'time_management': 7
                },
                'learning_preferences': {
                    'practical_projects': 9,
                    'theoretical_study': 5,
                    'peer_collaboration': 7,
                    'self_directed': 8
                }
            }
            
            submit_assessment = await client.post(
                f"{SKILL_DEVELOPMENT_URL}/api/assessments/{assessment_id}/submit",
                json=assessment_answers,
                headers=learner_session['headers']
            )
            assert submit_assessment.status_code == 200
            
            # Step 2: Generate personalized learning path
            path_generation_request = {
                'assessment_results': submit_assessment.json()['results'],
                'career_goals': learner_session['profile']['professional_goals'],
                'constraints': learner_session['profile']['constraints'],
                'target_timeline': '6_months'
            }
            
            learning_path_response = await client.post(
                f"{EDUCATION_AI_URL}/api/generate-learning-path",
                json=path_generation_request,
                headers=learner_session['headers']
            )
            assert learning_path_response.status_code == 201
            
            learning_path = learning_path_response.json()
            assert 'personalized_curriculum' in learning_path
            assert 'weekly_schedule' in learning_path
            assert 'skill_progression_timeline' in learning_path
            
            # Step 3: Begin adaptive learning sessions
            first_module = learning_path['personalized_curriculum']['modules'][0]
            
            learning_session = {
                'module_id': first_module['id'],
                'session_type': 'interactive_learning',
                'expected_duration': 45,
                'learning_objectives': first_module['objectives']
            }
            
            session_response = await client.post(
                f"{STUDYLOG_ADULTS_URL}/api/sessions/start",
                json=learning_session,
                headers=learner_session['headers']
            )
            session_id = session_response.json()['session_id']
            
            # Step 4: Simulate learning interactions with adaptation
            learning_interactions = [
                {
                    'interaction_type': 'concept_explanation',
                    'concept': 'linear_regression',
                    'comprehension_rating': 8,
                    'time_spent': 180,  # 3 minutes
                    'questions_asked': 1
                },
                {
                    'interaction_type': 'practical_exercise',
                    'exercise': 'implement_linear_regression',
                    'completion_status': 'completed',
                    'accuracy': 0.85,
                    'time_spent': 900,  # 15 minutes
                    'help_requests': 2
                },
                {
                    'interaction_type': 'knowledge_check',
                    'question_type': 'multiple_choice',
                    'correct_answers': 3,
                    'total_questions': 5,
                    'time_spent': 300  # 5 minutes
                }
            ]
            
            adaptation_data = []
            for interaction in learning_interactions:
                interaction_response = await client.post(
                    f"{STUDYLOG_ADULTS_URL}/api/sessions/{session_id}/interaction",
                    json=interaction,
                    headers=learner_session['headers']
                )
                assert interaction_response.status_code == 200
                
                adaptation_info = interaction_response.json()['adaptation']
                adaptation_data.append(adaptation_info)
            
            # Step 5: Verify adaptive adjustments
            session_summary = await client.get(
                f"{STUDYLOG_ADULTS_URL}/api/sessions/{session_id}/summary",
                headers=learner_session['headers']
            )
            summary_data = session_summary.json()
            
            assert 'learning_effectiveness' in summary_data
            assert 'recommended_adjustments' in summary_data
            
            # Should recommend more practical exercises based on performance
            adjustments = summary_data['recommended_adjustments']
            assert any('practical_exercise' in adj['type'] for adj in adjustments)

    @pytest.mark.asyncio
    async def test_corporate_learning_analytics_and_roi(self, authenticated_adult_sessions, corporate_training_program):
        """Test corporate learning analytics and ROI measurement"""
        
        async with httpx.AsyncClient() as client:
            admin_session = authenticated_adult_sessions['corporate_admin']
            
            # Step 1: Deploy corporate training program
            program_deployment = await client.post(
                f"{STUDYLOG_ADULTS_URL}/api/corporate/programs/deploy",
                json=corporate_training_program,
                headers=admin_session['headers']
            )
            assert program_deployment.status_code == 201
            program_id = program_deployment.json()['program_id']
            
            # Step 2: Enroll participants
            participants = []
            for i in range(10):  # Simulate 10 participants
                participant_data = {
                    'employee_id': f'EMP{i:03d}',
                    'name': f'Employee {i+1}',
                    'department': 'Engineering' if i < 5 else 'Marketing',
                    'role': 'Senior Developer' if i < 3 else 'Team Lead',
                    'years_experience': 5 + i,
                    'baseline_skills': {
                        'digital_literacy': random.randint(3, 7),
                        'leadership': random.randint(2, 6),
                        'agile_methods': random.randint(1, 5)
                    }
                }
                
                enrollment_response = await client.post(
                    f"{STUDYLOG_ADULTS_URL}/api/corporate/programs/{program_id}/enroll",
                    json=participant_data,
                    headers=admin_session['headers']
                )
                assert enrollment_response.status_code == 201
                participants.append(enrollment_response.json()['participant_id'])
            
            # Step 3: Simulate learning progress over time
            weeks_completed = 12  # Halfway through 6-month program
            
            for week in range(1, weeks_completed + 1):
                for participant_id in participants:
                    # Simulate varying engagement and performance
                    engagement_score = random.uniform(0.6, 0.95)
                    completion_rate = random.uniform(0.7, 1.0) if engagement_score > 0.75 else random.uniform(0.4, 0.8)
                    
                    progress_data = {
                        'week': week,
                        'participant_id': participant_id,
                        'modules_completed': int(completion_rate * 3),  # 3 modules per week
                        'time_spent_minutes': int(engagement_score * 180),  # 3 hours target
                        'assessment_scores': [random.uniform(0.65, 0.95) for _ in range(2)],
                        'peer_interaction_score': random.uniform(0.5, 0.9),
                        'manager_feedback_score': random.uniform(0.6, 0.9) if week % 4 == 0 else None
                    }
                    
                    await client.post(
                        f"{STUDYLOG_ADULTS_URL}/api/corporate/progress/record",
                        json=progress_data,
                        headers=admin_session['headers']
                    )
            
            # Step 4: Generate comprehensive analytics
            analytics_response = await client.get(
                f"{STUDYLOG_ADULTS_URL}/api/corporate/programs/{program_id}/analytics",
                params={'include_roi': True, 'timeframe': 'program_to_date'},
                headers=admin_session['headers']
            )
            assert analytics_response.status_code == 200
            
            analytics_data = analytics_response.json()
            
            # Verify comprehensive metrics
            assert 'program_completion_rate' in analytics_data
            assert 'engagement_metrics' in analytics_data
            assert 'skill_improvement_metrics' in analytics_data
            assert 'roi_analysis' in analytics_data
            assert 'departmental_comparison' in analytics_data
            
            # Step 5: Verify ROI calculations
            roi_data = analytics_data['roi_analysis']
            assert 'training_investment' in roi_data
            assert 'productivity_gains' in roi_data
            assert 'retention_improvement' in roi_data
            assert 'calculated_roi_percentage' in roi_data
            
            # ROI should be measurable (positive or negative)
            assert isinstance(roi_data['calculated_roi_percentage'], (int, float))
            
            # Step 6: Test predictive analytics for program optimization
            optimization_response = await client.get(
                f"{EDUCATION_AI_URL}/api/corporate/programs/{program_id}/optimization-recommendations",
                headers=admin_session['headers']
            )
            assert optimization_response.status_code == 200
            
            optimization_data = optimization_response.json()
            assert 'at_risk_participants' in optimization_data
            assert 'content_effectiveness' in optimization_data
            assert 'engagement_improvement_suggestions' in optimization_data

    @pytest.mark.asyncio
    async def test_professional_mentoring_integration(self, authenticated_adult_sessions):
        """Test professional mentoring and coaching integration"""
        
        async with httpx.AsyncClient() as client:
            learner_session = authenticated_adult_sessions['learner']
            mentor_session = authenticated_adult_sessions['mentor']
            
            # Step 1: Learner requests mentoring
            mentoring_request = {
                'expertise_needed': ['machine_learning', 'career_advancement'],
                'commitment_level': 'high',
                'preferred_communication': ['video_calls', 'messaging'],
                'availability': {
                    'timezone': 'EST',
                    'preferred_times': ['weekday_evenings', 'saturday_mornings']
                },
                'specific_goals': [
                    'Transition from software dev to ML engineer',
                    'Build technical leadership skills',
                    'Navigate corporate advancement'
                ]
            }
            
            mentoring_response = await client.post(
                f"{SKILL_DEVELOPMENT_URL}/api/mentoring/request",
                json=mentoring_request,
                headers=learner_session['headers']
            )
            assert mentoring_response.status_code == 201
            mentoring_request_id = mentoring_response.json()['request_id']
            
            # Step 2: Mentor accepts the request
            mentor_acceptance = {
                'request_id': mentoring_request_id,
                'commitment_duration': '6_months',
                'session_frequency': 'bi_weekly',
                'additional_notes': 'Excited to help with ML transition and leadership development'
            }
            
            acceptance_response = await client.post(
                f"{SKILL_DEVELOPMENT_URL}/api/mentoring/accept",
                json=mentor_acceptance,
                headers=mentor_session['headers']
            )
            assert acceptance_response.status_code == 200
            mentoring_relationship_id = acceptance_response.json()['relationship_id']
            
            # Step 3: Conduct mentoring sessions
            mentoring_sessions = [
                {
                    'session_type': 'goal_setting',
                    'duration_minutes': 60,
                    'topics_discussed': ['career_roadmap', '90_day_goals', 'skill_gaps'],
                    'action_items': [
                        'Complete Python for ML course',
                        'Identify internal ML project to contribute to',
                        'Schedule coffee chat with ML team lead'
                    ],
                    'learner_satisfaction': 9,
                    'mentor_notes': 'Great clarity on goals, motivated learner'
                },
                {
                    'session_type': 'technical_guidance',
                    'duration_minutes': 75,
                    'topics_discussed': ['linear_regression_implementation', 'feature_engineering'],
                    'code_review': True,
                    'resources_shared': ['recommended_books', 'online_tutorials'],
                    'learner_satisfaction': 8,
                    'mentor_notes': 'Strong programming fundamentals, needs ML theory reinforcement'
                },
                {
                    'session_type': 'career_coaching',
                    'duration_minutes': 50,
                    'topics_discussed': ['networking_strategies', 'interview_preparation'],
                    'mock_interview': True,
                    'feedback_provided': 'Technical competency strong, work on explaining complex concepts simply',
                    'learner_satisfaction': 9,
                    'mentor_notes': 'Ready for informational interviews, confidence building needed'
                }
            ]
            
            session_outcomes = []
            for session_data in mentoring_sessions:
                session_response = await client.post(
                    f"{SKILL_DEVELOPMENT_URL}/api/mentoring/{mentoring_relationship_id}/sessions",
                    json=session_data,
                    headers=mentor_session['headers']
                )
                assert session_response.status_code == 201
                session_outcomes.append(session_response.json())
            
            # Step 4: Track mentoring effectiveness
            effectiveness_response = await client.get(
                f"{SKILL_DEVELOPMENT_URL}/api/mentoring/{mentoring_relationship_id}/effectiveness",
                headers=learner_session['headers']
            )
            effectiveness_data = effectiveness_response.json()
            
            assert 'goal_progress' in effectiveness_data
            assert 'skill_development_rate' in effectiveness_data
            assert 'satisfaction_trends' in effectiveness_data
            
            # Verify average satisfaction is high
            avg_satisfaction = sum(s['learner_satisfaction'] for s in mentoring_sessions) / len(mentoring_sessions)
            assert effectiveness_data['average_satisfaction'] == avg_satisfaction
            assert avg_satisfaction >= 8.0

    @pytest.mark.asyncio
    async def test_competency_based_certification_tracking(self, authenticated_adult_sessions):
        """Test competency-based certification and skill verification"""
        
        async with httpx.AsyncClient() as client:
            learner_session = authenticated_adult_sessions['learner']
            
            # Step 1: Enroll in certification program
            certification_program = {
                'certification_name': 'Certified Machine Learning Professional',
                'issuing_body': 'Tech Skills Institute',
                'competency_framework': {
                    'domains': [
                        {
                            'name': 'Data Processing and Analysis',
                            'weight': 0.25,
                            'competencies': [
                                'data_cleaning',
                                'feature_engineering',
                                'exploratory_data_analysis'
                            ]
                        },
                        {
                            'name': 'Machine Learning Algorithms',
                            'weight': 0.35,
                            'competencies': [
                                'supervised_learning',
                                'unsupervised_learning',
                                'model_evaluation'
                            ]
                        },
                        {
                            'name': 'Model Deployment and MLOps',
                            'weight': 0.25,
                            'competencies': [
                                'model_deployment',
                                'monitoring_and_maintenance',
                                'version_control'
                            ]
                        },
                        {
                            'name': 'Ethics and Governance',
                            'weight': 0.15,
                            'competencies': [
                                'bias_detection',
                                'fairness_assessment',
                                'responsible_ai'
                            ]
                        }
                    ]
                },
                'assessment_methods': [
                    'practical_projects',
                    'peer_review',
                    'expert_evaluation',
                    'industry_simulation'
                ]
            }
            
            enrollment_response = await client.post(
                f"{PROFESSIONAL_CERTS_URL}/api/certifications/enroll",
                json=certification_program,
                headers=learner_session['headers']
            )
            assert enrollment_response.status_code == 201
            certification_id = enrollment_response.json()['certification_id']
            
            # Step 2: Complete competency assessments
            competency_assessments = [
                {
                    'domain': 'Data Processing and Analysis',
                    'competency': 'data_cleaning',
                    'assessment_type': 'practical_project',
                    'project_submission': {
                        'title': 'Customer Data Cleaning Pipeline',
                        'description': 'Built automated pipeline to clean customer data',
                        'technologies_used': ['Python', 'pandas', 'numpy'],
                        'github_repo': 'https://github.com/user/data-cleaning-project',
                        'performance_metrics': {
                            'data_quality_improvement': 0.85,
                            'processing_time_reduction': 0.60
                        }
                    },
                    'self_assessment_score': 8,
                    'time_invested_hours': 15
                },
                {
                    'domain': 'Machine Learning Algorithms',
                    'competency': 'supervised_learning',
                    'assessment_type': 'expert_evaluation',
                    'submission': {
                        'algorithm_implementations': ['linear_regression', 'random_forest', 'xgboost'],
                        'model_comparison_report': 'Comprehensive analysis of model performance',
                        'cross_validation_results': [0.85, 0.87, 0.89],
                        'feature_importance_analysis': True
                    },
                    'self_assessment_score': 9,
                    'time_invested_hours': 25
                }
            ]
            
            assessment_results = []
            for assessment in competency_assessments:
                assessment_response = await client.post(
                    f"{PROFESSIONAL_CERTS_URL}/api/certifications/{certification_id}/assess-competency",
                    json=assessment,
                    headers=learner_session['headers']
                )
                assert assessment_response.status_code == 202  # Submitted for evaluation
                assessment_results.append(assessment_response.json()['assessment_id'])
            
            # Step 3: Simulate expert evaluation
            for assessment_id in assessment_results:
                expert_evaluation = {
                    'assessment_id': assessment_id,
                    'expert_score': random.uniform(7.5, 9.5),
                    'detailed_feedback': {
                        'strengths': ['Strong technical implementation', 'Good documentation'],
                        'areas_for_improvement': ['Consider edge cases', 'Add more performance metrics'],
                        'recommendations': ['Explore advanced algorithms', 'Focus on production deployment']
                    },
                    'competency_level': 'proficient'  # novice, developing, proficient, advanced, expert
                }
                
                await client.post(
                    f"{PROFESSIONAL_CERTS_URL}/api/assessments/{assessment_id}/expert-evaluation",
                    json=expert_evaluation,
                    headers={'Authorization': 'Bearer expert.evaluator.token'}
                )
            
            # Step 4: Check certification progress
            progress_response = await client.get(
                f"{PROFESSIONAL_CERTS_URL}/api/certifications/{certification_id}/progress",
                headers=learner_session['headers']
            )
            progress_data = progress_response.json()
            
            assert 'competency_progress' in progress_data
            assert 'overall_completion_percentage' in progress_data
            assert 'next_recommended_assessments' in progress_data
            
            # Verify competency tracking
            for domain in certification_program['competency_framework']['domains']:
                domain_progress = next(
                    (d for d in progress_data['competency_progress'] if d['domain'] == domain['name']),
                    None
                )
                assert domain_progress is not None

    @pytest.mark.asyncio
    async def test_workplace_skill_application_tracking(self, authenticated_adult_sessions):
        """Test tracking of skill application in workplace contexts"""
        
        async with httpx.AsyncClient() as client:
            learner_session = authenticated_adult_sessions['learner']
            
            # Step 1: Set up workplace integration
            workplace_integration = {
                'company': 'TechCorp Solutions',
                'department': 'Engineering',
                'role': 'Senior Software Developer',
                'manager_email': 'manager@techcorp.com',
                'skill_tracking_consent': True,
                'integration_tools': ['jira', 'github', 'slack', 'performance_reviews']
            }
            
            integration_response = await client.post(
                f"{SKILL_DEVELOPMENT_URL}/api/workplace/integrate",
                json=workplace_integration,
                headers=learner_session['headers']
            )
            assert integration_response.status_code == 201
            integration_id = integration_response.json()['integration_id']
            
            # Step 2: Record skill applications in workplace
            skill_applications = [
                {
                    'date': (datetime.utcnow() - timedelta(days=5)).isoformat(),
                    'skill_used': 'machine_learning',
                    'context': 'project_work',
                    'description': 'Implemented recommendation algorithm for user personalization',
                    'tools_used': ['Python', 'scikit-learn', 'pandas'],
                    'outcome': 'successful',
                    'impact_metrics': {
                        'user_engagement_increase': 0.15,
                        'click_through_rate_improvement': 0.12
                    },
                    'confidence_level': 8,
                    'peer_recognition': True
                },
                {
                    'date': (datetime.utcnow() - timedelta(days=3)).isoformat(),
                    'skill_used': 'data_visualization',
                    'context': 'presentation',
                    'description': 'Created interactive dashboard for stakeholder demo',
                    'tools_used': ['Tableau', 'Python', 'matplotlib'],
                    'outcome': 'successful',
                    'impact_metrics': {
                        'stakeholder_satisfaction': 9,
                        'decision_speed_improvement': 0.25
                    },
                    'confidence_level': 9,
                    'manager_feedback': 'Excellent visualization, really helped convey insights'
                },
                {
                    'date': (datetime.utcnow() - timedelta(days=1)).isoformat(),
                    'skill_used': 'project_leadership',
                    'context': 'team_collaboration',
                    'description': 'Led cross-functional team to resolve production issue',
                    'outcome': 'successful',
                    'impact_metrics': {
                        'issue_resolution_time': '2 hours',
                        'team_collaboration_score': 8
                    },
                    'confidence_level': 7,
                    'areas_for_improvement': 'Communication with non-technical stakeholders'
                }
            ]
            
            for application in skill_applications:
                application_response = await client.post(
                    f"{SKILL_DEVELOPMENT_URL}/api/workplace/{integration_id}/skill-application",
                    json=application,
                    headers=learner_session['headers']
                )
                assert application_response.status_code == 201
            
            # Step 3: Generate workplace skills report
            skills_report_response = await client.get(
                f"{SKILL_DEVELOPMENT_URL}/api/workplace/{integration_id}/skills-report",
                params={'timeframe': '30_days'},
                headers=learner_session['headers']
            )
            assert skills_report_response.status_code == 200
            
            skills_report = skills_report_response.json()
            
            assert 'skills_utilization' in skills_report
            assert 'confidence_trends' in skills_report
            assert 'impact_summary' in skills_report
            assert 'growth_recommendations' in skills_report
            
            # Verify skill utilization tracking
            ml_utilization = next(
                (s for s in skills_report['skills_utilization'] if s['skill'] == 'machine_learning'),
                None
            )
            assert ml_utilization is not None
            assert ml_utilization['frequency'] == 1  # Used once in timeframe
            assert ml_utilization['average_confidence'] == 8

    @pytest.mark.asyncio
    async def test_personalized_learning_recommendations(self, authenticated_adult_sessions):
        """Test AI-powered personalized learning recommendations for adults"""
        
        async with httpx.AsyncClient() as client:
            learner_session = authenticated_adult_sessions['learner']
            
            # Step 1: Gather learner behavior data
            learning_behavior_data = {
                'completed_courses': [
                    {
                        'course_name': 'Python Fundamentals',
                        'completion_rate': 1.0,
                        'time_to_complete_days': 21,
                        'final_score': 0.88,
                        'engagement_metrics': {
                            'video_watch_completion': 0.95,
                            'exercise_completion': 0.92,
                            'forum_participation': 0.3
                        }
                    },
                    {
                        'course_name': 'Statistics for Data Science',
                        'completion_rate': 0.75,
                        'time_to_complete_days': 45,  # Took longer than expected
                        'final_score': 0.72,
                        'engagement_metrics': {
                            'video_watch_completion': 0.68,
                            'exercise_completion': 0.85,
                            'forum_participation': 0.1
                        }
                    }
                ],
                'learning_patterns': {
                    'preferred_content_types': ['hands_on_projects', 'interactive_tutorials'],
                    'peak_learning_times': ['early_morning', 'late_evening'],
                    'average_session_duration': 35,  # minutes
                    'break_frequency': 25,  # minutes
                    'repetition_preference': 'moderate'
                },
                'struggle_areas': [
                    'advanced_statistics',
                    'theoretical_concepts'
                ],
                'strength_areas': [
                    'programming_implementation',
                    'practical_problem_solving'
                ]
            }
            
            behavior_response = await client.post(
                f"{EDUCATION_AI_URL}/api/learner-behavior/update",
                json=learning_behavior_data,
                headers=learner_session['headers']
            )
            assert behavior_response.status_code == 200
            
            # Step 2: Request personalized recommendations
            recommendation_request = {
                'career_goals': learner_session['profile']['professional_goals'],
                'time_constraints': learner_session['profile']['constraints']['time_availability'],
                'current_skill_gaps': ['machine_learning', 'cloud_architecture'],
                'learning_deadline': (datetime.utcnow() + timedelta(days=180)).isoformat(),
                'budget_constraints': 'moderate',
                'preferred_certification': 'industry_recognized'
            }
            
            recommendations_response = await client.post(
                f"{EDUCATION_AI_URL}/api/recommendations/generate",
                json=recommendation_request,
                headers=learner_session['headers']
            )
            assert recommendations_response.status_code == 200
            
            recommendations = recommendations_response.json()
            
            # Step 3: Verify recommendation quality and personalization
            assert 'recommended_courses' in recommendations
            assert 'learning_path_options' in recommendations
            assert 'study_schedule' in recommendations
            assert 'success_probability' in recommendations
            
            # Recommendations should account for learning patterns
            for course in recommendations['recommended_courses']:
                # Should prefer hands-on content based on behavior
                assert course['practical_component_percentage'] >= 0.6
                
                # Should account for struggle with theory
                if 'theory_heavy' in course.get('tags', []):
                    assert course['difficulty_adjustment'] == 'beginner_friendly'
            
            # Step 4: Test recommendation refinement based on feedback
            recommendation_feedback = {
                'course_recommendations': [
                    {
                        'course_id': recommendations['recommended_courses'][0]['id'],
                        'interest_level': 9,
                        'time_commitment_acceptable': True,
                        'difficulty_appropriate': True
                    },
                    {
                        'course_id': recommendations['recommended_courses'][1]['id'],
                        'interest_level': 6,
                        'time_commitment_acceptable': False,
                        'difficulty_appropriate': True,
                        'feedback': 'Too time-intensive for current schedule'
                    }
                ],
                'overall_satisfaction': 8,
                'request_modifications': [
                    'shorter_courses_preferred',
                    'more_weekend_options'
                ]
            }
            
            feedback_response = await client.post(
                f"{EDUCATION_AI_URL}/api/recommendations/feedback",
                json=recommendation_feedback,
                headers=learner_session['headers']
            )
            assert feedback_response.status_code == 200
            
            # Verify refined recommendations
            refined_recommendations = feedback_response.json()['updated_recommendations']
            
            # Should now prefer shorter courses
            avg_duration = sum(c['estimated_weeks'] for c in refined_recommendations['recommended_courses']) / len(refined_recommendations['recommended_courses'])
            original_avg_duration = sum(c['estimated_weeks'] for c in recommendations['recommended_courses']) / len(recommendations['recommended_courses'])
            
            assert avg_duration < original_avg_duration

    @pytest.mark.load
    async def test_adult_learning_platform_scalability(self, authenticated_adult_sessions):
        """Test adult learning platform under high concurrent load"""
        
        import random
        
        async def simulate_adult_learner(learner_id: int):
            async with httpx.AsyncClient() as client:
                # Simulate diverse adult learning activities
                activities = [
                    {
                        'type': 'course_enrollment',
                        'course_subject': random.choice(['data_science', 'leadership', 'digital_marketing']),
                        'time_commitment': random.randint(2, 8)  # hours per week
                    },
                    {
                        'type': 'skill_assessment',
                        'skill_domain': random.choice(['technical', 'soft_skills', 'industry_knowledge']),
                        'assessment_duration': random.randint(30, 90)  # minutes
                    },
                    {
                        'type': 'mentoring_session',
                        'session_duration': random.randint(45, 90),  # minutes
                        'session_type': random.choice(['career_guidance', 'technical_mentoring'])
                    }
                ]
                
                selected_activity = random.choice(activities)
                
                if selected_activity['type'] == 'course_enrollment':
                    return await client.post(
                        f"{STUDYLOG_ADULTS_URL}/api/courses/enroll",
                        json=selected_activity,
                        headers={'Authorization': f'Bearer learner_{learner_id}.token'}
                    )
                elif selected_activity['type'] == 'skill_assessment':
                    return await client.post(
                        f"{SKILL_DEVELOPMENT_URL}/api/assessments/start",
                        json=selected_activity,
                        headers={'Authorization': f'Bearer learner_{learner_id}.token'}
                    )
                else:  # mentoring_session
                    return await client.post(
                        f"{SKILL_DEVELOPMENT_URL}/api/mentoring/sessions/start",
                        json=selected_activity,
                        headers={'Authorization': f'Bearer learner_{learner_id}.token'}
                    )
        
        # Simulate 30 concurrent adult learners
        tasks = [simulate_adult_learner(i) for i in range(30)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify most activities completed successfully
        successful_activities = [
            r for r in responses 
            if not isinstance(r, Exception) and r.status_code in [200, 201, 202]
        ]
        assert len(successful_activities) >= 25
        
        # Test system performance under load
        performance_response = await httpx.AsyncClient().get(
            f"{STUDYLOG_ADULTS_URL}/api/system/performance"
        )
        assert performance_response.status_code == 200
        
        performance_data = performance_response.json()
        assert performance_data['response_time_avg'] < 2000  # Under 2 seconds
        assert performance_data['error_rate'] < 0.05  # Under 5% error rate
        assert performance_data['active_sessions'] >= 25