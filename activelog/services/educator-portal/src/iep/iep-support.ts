import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';

export interface IEP {
  id: string;
  studentId: string;
  studentName: string;
  dateOfBirth: Date;
  gradeLevel: string;
  schoolYear: string;
  meetingDate: Date;
  effectiveDate: Date;
  nextReviewDate: Date;
  nextTriennialDate: Date;
  status: 'draft' | 'active' | 'under-review' | 'expired' | 'archived';
  eligibilityCategory: string[];
  placementSetting: PlacementSetting;
  team: IEPTeamMember[];
  presentLevels: PresentLevel[];
  goals: IEPGoal[];
  services: RelatedService[];
  accommodations: Accommodation[];
  modifications: Modification[];
  assessmentInfo: AssessmentInformation;
  transitionServices?: TransitionServices;
  behaviorPlan?: BehaviorInterventionPlan;
  communicationPlan?: CommunicationPlan;
  emergencyProcedures: string[];
  parentConcerns: string[];
  strengthsAndNeeds: StrengthsAndNeeds;
  createdBy: string;
  createdDate: Date;
  lastModified: Date;
  lastModifiedBy: string;
  confidentialityLevel: 'high' | 'medium' | 'standard';
}

export interface PlacementSetting {
  environment: 'general-education' | 'resource-room' | 'separate-class' | 'separate-school' | 'residential' | 'homebound';
  percentageInGenEd: number;
  justification: string;
  leastRestrictive: boolean;
  rationale: string;
}

export interface IEPTeamMember {
  id: string;
  name: string;
  role: 'parent' | 'student' | 'general-ed-teacher' | 'special-ed-teacher' | 'school-psychologist' | 
        'speech-therapist' | 'occupational-therapist' | 'physical-therapist' | 'administrator' | 'other';
  email: string;
  phone?: string;
  organization: string;
  isPrimary: boolean;
  attendedMeeting: boolean;
  signature?: string;
  signatureDate?: Date;
  excusalReason?: string;
}

export interface PresentLevel {
  id: string;
  domain: 'academic' | 'functional' | 'social-emotional' | 'behavioral' | 'communication' | 'motor' | 'vocational';
  area: string;
  strengths: string[];
  needs: string[];
  currentPerformance: string;
  impactOnEducation: string;
  dataSource: string[];
  assessmentDate?: Date;
  assessedBy: string;
}

export interface IEPGoal {
  id: string;
  domain: string;
  area: string;
  timeframe: 'annual' | 'short-term' | 'quarterly' | 'semester';
  goal: string;
  measurableObjectives: MeasurableObjective[];
  baselineData: BaselineData;
  targetCriteria: TargetCriteria;
  methodology: string[];
  schedule: GoalSchedule;
  responsiblePersons: string[];
  progressReporting: ProgressReporting;
  status: 'not-started' | 'in-progress' | 'mastered' | 'discontinued' | 'modified';
  progressData: GoalProgress[];
  notes: string;
}

export interface MeasurableObjective {
  id: string;
  objective: string;
  condition: string;
  behavior: string;
  criteria: string;
  targetDate: Date;
  masteryLevel: number;
  progressMethod: string;
}

export interface BaselineData {
  description: string;
  data: string;
  date: Date;
  source: string;
  conditions: string;
}

export interface TargetCriteria {
  accuracy: string;
  frequency: string;
  duration: string;
  independence: string;
  conditions: string;
  masteryLevel: string;
}

export interface GoalSchedule {
  frequency: string;
  duration: string;
  location: string[];
  grouping: 'individual' | 'small-group' | 'large-group' | 'mixed';
}

export interface ProgressReporting {
  method: 'data-collection' | 'rubric' | 'observation' | 'portfolio' | 'assessment' | 'mixed';
  frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'as-needed';
  reportingSchedule: Date[];
  parentNotification: boolean;
}

export interface GoalProgress {
  id: string;
  date: Date;
  progress: number; // percentage
  description: string;
  dataCollected: any;
  method: string;
  recordedBy: string;
  interventionsUsed: string[];
  barriers: string[];
  successes: string[];
  nextSteps: string[];
}

export interface RelatedService {
  id: string;
  serviceType: 'speech-language' | 'occupational-therapy' | 'physical-therapy' | 'counseling' | 
               'school-psychology' | 'social-work' | 'nursing' | 'transportation' | 'assistive-tech' | 'other';
  provider: string;
  frequency: string;
  duration: string;
  location: string;
  grouping: 'individual' | 'small-group' | 'large-group';
  startDate: Date;
  endDate: Date;
  goals: string[];
  justification: string;
  progressMonitoring: ProgressMonitoring;
  status: 'active' | 'discontinued' | 'on-hold';
}

export interface ProgressMonitoring {
  method: string;
  frequency: string;
  dataSources: string[];
  reportingSchedule: Date[];
  benchmarks: Benchmark[];
}

export interface Benchmark {
  date: Date;
  description: string;
  criteria: string;
  status: 'not-met' | 'partially-met' | 'met' | 'exceeded';
}

export interface Accommodation {
  id: string;
  category: 'presentation' | 'response' | 'setting' | 'timing-scheduling';
  type: string;
  description: string;
  settings: string[];
  subjects: string[];
  frequency: 'daily' | 'as-needed' | 'testing-only' | 'specific-activities';
  provider: string;
  effectiveness: EffectivenessRating;
  implementationNotes: string[];
  reviewDate: Date;
  status: 'active' | 'trial' | 'discontinued';
}

export interface Modification {
  id: string;
  category: 'curriculum' | 'instruction' | 'assignment' | 'assessment' | 'grading';
  type: string;
  description: string;
  subjects: string[];
  rationale: string;
  implementationGuidance: string;
  effectivenessData: EffectivenessRating;
  reviewSchedule: string;
  status: 'active' | 'trial' | 'discontinued';
}

export interface EffectivenessRating {
  rating: 1 | 2 | 3 | 4 | 5;
  evidence: string[];
  lastReviewed: Date;
  reviewedBy: string;
  recommendations: string[];
}

export interface AssessmentInformation {
  stateAssessment: StateAssessmentInfo;
  alternateAssessment: AlternateAssessmentInfo[];
  accommodationsNeeded: string[];
  participationDecisions: ParticipationDecision[];
}

export interface StateAssessmentInfo {
  participates: boolean;
  accommodationsRequired: string[];
  justificationForNonParticipation?: string;
  alternativeSelected?: string;
}

export interface AlternateAssessmentInfo {
  assessmentName: string;
  subject: string;
  rationale: string;
  accommodations: string[];
}

export interface ParticipationDecision {
  assessment: string;
  decision: 'participate' | 'participate-with-accommodations' | 'alternate-assessment' | 'exempt';
  rationale: string;
}

export interface TransitionServices {
  postSecondaryGoals: PostSecondaryGoal[];
  transitionActivities: TransitionActivity[];
  agencyInvolvement: AgencyInvolvement[];
  studentPreferences: string[];
  studentInterests: string[];
  studentStrengths: string[];
  studentNeeds: string[];
}

export interface PostSecondaryGoal {
  domain: 'education' | 'employment' | 'independent-living';
  goal: string;
  timeline: string;
  supportNeeded: string[];
  measurability: string;
}

export interface TransitionActivity {
  domain: string;
  activity: string;
  timeline: string;
  responsibleParty: string;
  completionCriteria: string;
  status: 'not-started' | 'in-progress' | 'completed';
}

export interface AgencyInvolvement {
  agencyName: string;
  contactPerson: string;
  services: string[];
  timeline: string;
  consentRequired: boolean;
  consentObtained: boolean;
}

export interface BehaviorInterventionPlan {
  id: string;
  targetBehaviors: TargetBehavior[];
  functionalAssessment: FunctionalAssessment;
  interventionStrategies: InterventionStrategy[];
  preventionStrategies: PreventionStrategy[];
  responseStrategies: ResponseStrategy[];
  dataCollection: BehaviorDataCollection;
  reviewSchedule: string;
  emergencyProcedures: string[];
  teamMembers: string[];
}

export interface TargetBehavior {
  id: string;
  behavior: string;
  operationalDefinition: string;
  frequency: string;
  intensity: string;
  duration: string;
  antecedents: string[];
  consequences: string[];
  function: string;
}

export interface FunctionalAssessment {
  assessmentDate: Date;
  assessmentMethod: string[];
  assessors: string[];
  hypothesizedFunction: string;
  maintainingConsequences: string[];
  triggerEvents: string[];
  settingEvents: string[];
  recommendations: string[];
}

export interface InterventionStrategy {
  strategy: string;
  description: string;
  implementation: string;
  frequency: string;
  responsiblePerson: string;
  dataTracking: string;
  successCriteria: string;
}

export interface PreventionStrategy {
  strategy: string;
  description: string;
  triggers: string[];
  implementation: string;
  responsiblePerson: string;
}

export interface ResponseStrategy {
  behavior: string;
  response: string;
  description: string;
  responsiblePerson: string;
  followUpRequired: boolean;
  documentationRequired: boolean;
}

export interface BehaviorDataCollection {
  methods: string[];
  frequency: string;
  duration: string;
  responsiblePersons: string[];
  dataAnalysisSchedule: string;
  reportingSchedule: string;
}

export interface CommunicationPlan {
  preferredLanguage: string;
  interpreterNeeded: boolean;
  communicationMethods: string[];
  frequency: string;
  responsiblePersons: string[];
  emergencyContacts: EmergencyContact[];
  culturalConsiderations: string[];
}

export interface EmergencyContact {
  name: string;
  relationship: string;
  phone: string;
  alternatePhone?: string;
  email?: string;
  isPrimary: boolean;
  languages: string[];
}

export interface StrengthsAndNeeds {
  academicStrengths: string[];
  academicNeeds: string[];
  functionalStrengths: string[];
  functionalNeeds: string[];
  socialEmotionalStrengths: string[];
  socialEmotionalNeeds: string[];
  physicalStrengths: string[];
  physicalNeeds: string[];
  communicationStrengths: string[];
  communicationNeeds: string[];
}

export interface IEPMeeting {
  id: string;
  iepId: string;
  meetingType: 'initial' | 'annual' | 'amendment' | 'triennial' | 'transition' | 'manifestation' | 'other';
  scheduledDate: Date;
  actualDate?: Date;
  duration: number;
  location: string;
  attendees: MeetingAttendee[];
  agenda: AgendaItem[];
  decisions: MeetingDecision[];
  actionItems: ActionItem[];
  nextMeetingDate?: Date;
  parentParticipation: ParentParticipation;
  meetingNotes: string;
  materials: MeetingMaterial[];
  status: 'scheduled' | 'completed' | 'cancelled' | 'rescheduled';
  conductedBy: string;
}

export interface MeetingAttendee {
  personId: string;
  name: string;
  role: string;
  attended: boolean;
  participationMethod: 'in-person' | 'phone' | 'video' | 'excused';
  excusedReason?: string;
  contributionsProvided: boolean;
}

export interface AgendaItem {
  order: number;
  topic: string;
  presenter: string;
  timeAllocated: number;
  materials: string[];
  discussionPoints: string[];
  outcomes: string[];
}

export interface MeetingDecision {
  topic: string;
  decision: string;
  rationale: string;
  votingRecord?: VotingRecord;
  effectiveDate: Date;
  responsibleParty: string;
  followUpRequired: boolean;
}

export interface VotingRecord {
  inFavor: string[];
  against: string[];
  abstained: string[];
  consensus: boolean;
}

export interface ActionItem {
  id: string;
  description: string;
  responsibleParty: string;
  dueDate: Date;
  status: 'pending' | 'in-progress' | 'completed' | 'overdue';
  completionDate?: Date;
  notes: string;
}

export interface ParentParticipation {
  parentAttended: boolean;
  participationLevel: 'active' | 'moderate' | 'minimal' | 'observer';
  concernsRaised: string[];
  inputProvided: string[];
  agreementLevel: 'full-agreement' | 'partial-agreement' | 'disagreement';
  followUpRequested: boolean;
}

export interface MeetingMaterial {
  title: string;
  type: 'assessment' | 'progress-report' | 'data' | 'draft-iep' | 'other';
  url?: string;
  providedBy: string;
  confidential: boolean;
}

export interface ComplianceCheck {
  id: string;
  iepId: string;
  checkType: 'timeline' | 'content' | 'implementation' | 'procedural';
  checkDate: Date;
  checkedBy: string;
  status: 'compliant' | 'non-compliant' | 'needs-attention';
  findings: ComplianceFinding[];
  correctiveActions: CorrectiveAction[];
  nextCheckDate: Date;
}

export interface ComplianceFinding {
  regulation: string;
  requirement: string;
  finding: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  evidence: string[];
  impact: string;
}

export interface CorrectiveAction {
  id: string;
  finding: string;
  action: string;
  responsibleParty: string;
  dueDate: Date;
  status: 'pending' | 'in-progress' | 'completed';
  completionDate?: Date;
  verification: string[];
}

export class IEPSupport extends EventEmitter {
  private ieps: Map<string, IEP> = new Map();
  private meetings: Map<string, IEPMeeting[]> = new Map();
  private complianceChecks: Map<string, ComplianceCheck[]> = new Map();

  constructor() {
    super();
  }

  public async createIEP(iepData: Omit<IEP, 'id' | 'createdDate' | 'lastModified'>): Promise<IEP> {
    const iep: IEP = {
      ...iepData,
      id: uuidv4(),
      createdDate: new Date(),
      lastModified: new Date(),
    };

    this.ieps.set(iep.id, iep);
    this.emit('iepCreated', iep);
    return iep;
  }

  public async updateIEP(iepId: string, updates: Partial<IEP>, updatedBy: string): Promise<IEP | null> {
    const existing = this.ieps.get(iepId);
    if (!existing) return null;

    const updated = {
      ...existing,
      ...updates,
      lastModified: new Date(),
      lastModifiedBy: updatedBy,
    };

    this.ieps.set(iepId, updated);
    this.emit('iepUpdated', { iep: updated, updatedBy });
    return updated;
  }

  public async getIEP(iepId: string): Promise<IEP | null> {
    return this.ieps.get(iepId) || null;
  }

  public async getStudentIEPs(studentId: string): Promise<IEP[]> {
    return Array.from(this.ieps.values()).filter(iep => iep.studentId === studentId);
  }

  public async getCurrentIEP(studentId: string): Promise<IEP | null> {
    const ieps = await this.getStudentIEPs(studentId);
    return ieps.find(iep => iep.status === 'active') || null;
  }

  public async addGoal(iepId: string, goal: Omit<IEPGoal, 'id'>): Promise<IEPGoal | null> {
    const iep = this.ieps.get(iepId);
    if (!iep) return null;

    const iepGoal: IEPGoal = {
      ...goal,
      id: uuidv4(),
    };

    iep.goals.push(iepGoal);
    iep.lastModified = new Date();
    
    this.ieps.set(iepId, iep);
    this.emit('goalAdded', { iepId, goal: iepGoal });
    return iepGoal;
  }

  public async updateGoal(iepId: string, goalId: string, updates: Partial<IEPGoal>): Promise<IEPGoal | null> {
    const iep = this.ieps.get(iepId);
    if (!iep) return null;

    const goalIndex = iep.goals.findIndex(g => g.id === goalId);
    if (goalIndex === -1) return null;

    const updatedGoal = { ...iep.goals[goalIndex], ...updates };
    iep.goals[goalIndex] = updatedGoal;
    iep.lastModified = new Date();
    
    this.ieps.set(iepId, iep);
    this.emit('goalUpdated', { iepId, goal: updatedGoal });
    return updatedGoal;
  }

  public async recordGoalProgress(iepId: string, goalId: string, progress: Omit<GoalProgress, 'id'>): Promise<GoalProgress | null> {
    const iep = this.ieps.get(iepId);
    if (!iep) return null;

    const goal = iep.goals.find(g => g.id === goalId);
    if (!goal) return null;

    const goalProgress: GoalProgress = {
      ...progress,
      id: uuidv4(),
    };

    goal.progressData.push(goalProgress);
    iep.lastModified = new Date();
    
    this.ieps.set(iepId, iep);
    this.emit('progressRecorded', { iepId, goalId, progress: goalProgress });
    return goalProgress;
  }

  public async addService(iepId: string, service: Omit<RelatedService, 'id'>): Promise<RelatedService | null> {
    const iep = this.ieps.get(iepId);
    if (!iep) return null;

    const relatedService: RelatedService = {
      ...service,
      id: uuidv4(),
    };

    iep.services.push(relatedService);
    iep.lastModified = new Date();
    
    this.ieps.set(iepId, iep);
    this.emit('serviceAdded', { iepId, service: relatedService });
    return relatedService;
  }

  public async addAccommodation(iepId: string, accommodation: Omit<Accommodation, 'id'>): Promise<Accommodation | null> {
    const iep = this.ieps.get(iepId);
    if (!iep) return null;

    const iepAccommodation: Accommodation = {
      ...accommodation,
      id: uuidv4(),
    };

    iep.accommodations.push(iepAccommodation);
    iep.lastModified = new Date();
    
    this.ieps.set(iepId, iep);
    this.emit('accommodationAdded', { iepId, accommodation: iepAccommodation });
    return iepAccommodation;
  }

  public async scheduleMeeting(meeting: Omit<IEPMeeting, 'id'>): Promise<IEPMeeting> {
    const iepMeeting: IEPMeeting = {
      ...meeting,
      id: uuidv4(),
    };

    const iepMeetings = this.meetings.get(meeting.iepId) || [];
    iepMeetings.push(iepMeeting);
    this.meetings.set(meeting.iepId, iepMeetings);

    this.emit('meetingScheduled', iepMeeting);
    return iepMeeting;
  }

  public async updateMeeting(meetingId: string, updates: Partial<IEPMeeting>): Promise<IEPMeeting | null> {
    for (const [iepId, meetings] of this.meetings.entries()) {
      const meetingIndex = meetings.findIndex(m => m.id === meetingId);
      if (meetingIndex !== -1) {
        const updated = { ...meetings[meetingIndex], ...updates };
        meetings[meetingIndex] = updated;
        this.meetings.set(iepId, meetings);
        this.emit('meetingUpdated', updated);
        return updated;
      }
    }
    return null;
  }

  public async getMeetings(iepId: string): Promise<IEPMeeting[]> {
    return this.meetings.get(iepId) || [];
  }

  public async getUpcomingMeetings(days: number = 30): Promise<IEPMeeting[]> {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() + days);

    const upcomingMeetings: IEPMeeting[] = [];
    
    for (const meetings of this.meetings.values()) {
      upcomingMeetings.push(...meetings.filter(m => 
        m.status === 'scheduled' && m.scheduledDate <= cutoffDate
      ));
    }

    return upcomingMeetings.sort((a, b) => a.scheduledDate.getTime() - b.scheduledDate.getTime());
  }

  public async runComplianceCheck(iepId: string, checkType: ComplianceCheck['checkType'], checkedBy: string): Promise<ComplianceCheck> {
    const iep = this.ieps.get(iepId);
    if (!iep) throw new Error('IEP not found');

    const check: ComplianceCheck = {
      id: uuidv4(),
      iepId,
      checkType,
      checkDate: new Date(),
      checkedBy,
      status: 'compliant',
      findings: [],
      correctiveActions: [],
      nextCheckDate: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000), // 90 days
    };

    // Run different compliance checks based on type
    switch (checkType) {
      case 'timeline':
        check.findings = await this.checkTimelines(iep);
        break;
      case 'content':
        check.findings = await this.checkContent(iep);
        break;
      case 'implementation':
        check.findings = await this.checkImplementation(iep);
        break;
      case 'procedural':
        check.findings = await this.checkProcedural(iep);
        break;
    }

    // Determine overall status
    if (check.findings.some(f => f.severity === 'critical')) {
      check.status = 'non-compliant';
    } else if (check.findings.some(f => f.severity === 'high' || f.severity === 'medium')) {
      check.status = 'needs-attention';
    }

    // Generate corrective actions for non-compliant findings
    if (check.status !== 'compliant') {
      check.correctiveActions = await this.generateCorrectiveActions(check.findings);
    }

    const iepChecks = this.complianceChecks.get(iepId) || [];
    iepChecks.push(check);
    this.complianceChecks.set(iepId, iepChecks);

    this.emit('complianceCheckCompleted', check);
    return check;
  }

  private async checkTimelines(iep: IEP): Promise<ComplianceFinding[]> {
    const findings: ComplianceFinding[] = [];
    const now = new Date();

    // Check if IEP is approaching expiration
    if (iep.nextReviewDate < now) {
      findings.push({
        regulation: '34 CFR 300.324(b)',
        requirement: 'Annual IEP Review',
        finding: 'IEP annual review is overdue',
        severity: 'critical',
        evidence: [`Next review date: ${iep.nextReviewDate.toDateString()}`],
        impact: 'Student may not be receiving appropriate services',
      });
    }

    // Check triennial evaluation
    if (iep.nextTriennialDate < now) {
      findings.push({
        regulation: '34 CFR 300.303',
        requirement: 'Triennial Evaluation',
        finding: 'Triennial evaluation is overdue',
        severity: 'high',
        evidence: [`Next triennial date: ${iep.nextTriennialDate.toDateString()}`],
        impact: 'May affect continued eligibility determination',
      });
    }

    return findings;
  }

  private async checkContent(iep: IEP): Promise<ComplianceFinding[]> {
    const findings: ComplianceFinding[] = [];

    // Check for required components
    if (iep.goals.length === 0) {
      findings.push({
        regulation: '34 CFR 300.320(a)(2)',
        requirement: 'Measurable Annual Goals',
        finding: 'IEP lacks measurable annual goals',
        severity: 'critical',
        evidence: ['No goals found in IEP'],
        impact: 'Cannot measure student progress',
      });
    }

    // Check goal measurability
    const nonMeasurableGoals = iep.goals.filter(goal => 
      !goal.targetCriteria.accuracy || !goal.targetCriteria.criteria
    );
    
    if (nonMeasurableGoals.length > 0) {
      findings.push({
        regulation: '34 CFR 300.320(a)(2)(i)',
        requirement: 'Measurable Goals',
        finding: 'Some goals lack measurable criteria',
        severity: 'medium',
        evidence: nonMeasurableGoals.map(g => `Goal: ${g.goal}`),
        impact: 'Difficult to track progress accurately',
      });
    }

    // Check present levels
    if (iep.presentLevels.length === 0) {
      findings.push({
        regulation: '34 CFR 300.320(a)(1)',
        requirement: 'Present Levels of Performance',
        finding: 'IEP lacks present levels of academic and functional performance',
        severity: 'critical',
        evidence: ['No present levels documented'],
        impact: 'Cannot establish baseline for goals',
      });
    }

    return findings;
  }

  private async checkImplementation(iep: IEP): Promise<ComplianceFinding[]> {
    const findings: ComplianceFinding[] = [];

    // Check if services are being provided as specified
    const overdueServices = iep.services.filter(service => {
      const daysSinceStart = Math.floor((new Date().getTime() - service.startDate.getTime()) / (1000 * 60 * 60 * 24));
      return daysSinceStart > 30 && service.status === 'active' && 
             service.progressMonitoring.benchmarks.length === 0;
    });

    if (overdueServices.length > 0) {
      findings.push({
        regulation: '34 CFR 300.323',
        requirement: 'IEP Implementation',
        finding: 'Services lack progress monitoring data',
        severity: 'medium',
        evidence: overdueServices.map(s => `Service: ${s.serviceType}`),
        impact: 'Cannot verify service effectiveness',
      });
    }

    // Check goal progress
    const stagnantGoals = iep.goals.filter(goal => {
      const recentProgress = goal.progressData.filter(p => 
        (new Date().getTime() - p.date.getTime()) < 90 * 24 * 60 * 60 * 1000
      );
      return recentProgress.length === 0 && goal.status !== 'mastered';
    });

    if (stagnantGoals.length > 0) {
      findings.push({
        regulation: '34 CFR 300.320(a)(3)',
        requirement: 'Progress Reporting',
        finding: 'Some goals lack recent progress data',
        severity: 'medium',
        evidence: stagnantGoals.map(g => `Goal: ${g.goal}`),
        impact: 'Cannot determine goal effectiveness',
      });
    }

    return findings;
  }

  private async checkProcedural(iep: IEP): Promise<ComplianceFinding[]> {
    const findings: ComplianceFinding[] = [];

    // Check team composition
    const requiredRoles = ['parent', 'general-ed-teacher', 'special-ed-teacher'];
    const teamRoles = iep.team.map(member => member.role);
    
    for (const role of requiredRoles) {
      if (!teamRoles.includes(role)) {
        findings.push({
          regulation: '34 CFR 300.321',
          requirement: 'IEP Team Composition',
          finding: `Missing required team member: ${role}`,
          severity: 'high',
          evidence: [`Team roles: ${teamRoles.join(', ')}`],
          impact: 'IEP team may not meet regulatory requirements',
        });
      }
    }

    // Check signatures
    const unsignedMembers = iep.team.filter(member => !member.signature && member.attendedMeeting);
    if (unsignedMembers.length > 0) {
      findings.push({
        regulation: '34 CFR 300.324',
        requirement: 'IEP Documentation',
        finding: 'IEP lacks required signatures',
        severity: 'medium',
        evidence: unsignedMembers.map(m => `Unsigned: ${m.name} (${m.role})`),
        impact: 'May affect IEP validity',
      });
    }

    return findings;
  }

  private async generateCorrectiveActions(findings: ComplianceFinding[]): Promise<CorrectiveAction[]> {
    const actions: CorrectiveAction[] = [];

    for (const finding of findings) {
      let action: CorrectiveAction;
      
      switch (finding.severity) {
        case 'critical':
          action = {
            id: uuidv4(),
            finding: finding.finding,
            action: `Immediately address critical compliance issue: ${finding.requirement}`,
            responsibleParty: 'Special Education Coordinator',
            dueDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000), // 7 days
            status: 'pending',
            verification: ['Documentation review', 'Administrative approval'],
          };
          break;
        case 'high':
          action = {
            id: uuidv4(),
            finding: finding.finding,
            action: `Develop plan to address compliance issue: ${finding.requirement}`,
            responsibleParty: 'IEP Team Leader',
            dueDate: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000), // 14 days
            status: 'pending',
            verification: ['Team meeting', 'Documentation update'],
          };
          break;
        default:
          action = {
            id: uuidv4(),
            finding: finding.finding,
            action: `Review and update IEP component: ${finding.requirement}`,
            responsibleParty: 'Case Manager',
            dueDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), // 30 days
            status: 'pending',
            verification: ['IEP review', 'Progress monitoring'],
          };
      }

      actions.push(action);
    }

    return actions;
  }

  public async getComplianceChecks(iepId: string): Promise<ComplianceCheck[]> {
    return this.complianceChecks.get(iepId) || [];
  }

  public async generateProgressReport(iepId: string, reportingPeriod: { start: Date; end: Date }): Promise<any> {
    const iep = this.ieps.get(iepId);
    if (!iep) return null;

    const goalProgress = iep.goals.map(goal => {
      const periodProgress = goal.progressData.filter(p => 
        p.date >= reportingPeriod.start && p.date <= reportingPeriod.end
      );

      const averageProgress = periodProgress.length > 0
        ? periodProgress.reduce((sum, p) => sum + p.progress, 0) / periodProgress.length
        : 0;

      return {
        goal: goal.goal,
        domain: goal.domain,
        status: goal.status,
        averageProgress,
        dataPoints: periodProgress.length,
        currentLevel: goal.status === 'mastered' ? 100 : averageProgress,
        nextSteps: periodProgress.length > 0 ? periodProgress[periodProgress.length - 1].nextSteps : [],
      };
    });

    const serviceProgress = iep.services.map(service => ({
      serviceType: service.serviceType,
      provider: service.provider,
      frequency: service.frequency,
      status: service.status,
      benchmarksAchieved: service.progressMonitoring.benchmarks.filter(b => b.status === 'met' || b.status === 'exceeded').length,
      totalBenchmarks: service.progressMonitoring.benchmarks.length,
    }));

    return {
      student: {
        id: iep.studentId,
        name: iep.studentName,
        grade: iep.gradeLevel,
      },
      reportingPeriod,
      overallProgress: {
        goalsMastered: goalProgress.filter(g => g.status === 'mastered').length,
        goalsInProgress: goalProgress.filter(g => g.status === 'in-progress').length,
        averageProgress: goalProgress.reduce((sum, g) => sum + g.averageProgress, 0) / goalProgress.length,
      },
      goalProgress,
      serviceProgress,
      accommodations: iep.accommodations.filter(acc => acc.status === 'active').length,
      modifications: iep.modifications.filter(mod => mod.status === 'active').length,
      recommendations: this.generateProgressRecommendations(goalProgress, serviceProgress),
      nextReviewDate: iep.nextReviewDate,
      generatedDate: new Date(),
    };
  }

  private generateProgressRecommendations(goalProgress: any[], serviceProgress: any[]): string[] {
    const recommendations: string[] = [];

    const strugglingGoals = goalProgress.filter(g => g.averageProgress < 50 && g.status === 'in-progress');
    if (strugglingGoals.length > 0) {
      recommendations.push('Consider modifying instructional strategies for goals showing limited progress');
    }

    const masteredGoals = goalProgress.filter(g => g.status === 'mastered');
    if (masteredGoals.length > goalProgress.length * 0.8) {
      recommendations.push('Student showing excellent progress; consider developing more challenging goals');
    }

    const underperformingServices = serviceProgress.filter(s => 
      s.benchmarksAchieved / s.totalBenchmarks < 0.6 && s.totalBenchmarks > 0
    );
    if (underperformingServices.length > 0) {
      recommendations.push('Review effectiveness of services with limited benchmark achievement');
    }

    return recommendations;
  }

  public async exportIEP(iepId: string, format: 'pdf' | 'json' | 'xml'): Promise<any> {
    const iep = this.ieps.get(iepId);
    if (!iep) return null;

    return {
      iep,
      exportDate: new Date(),
      format,
      confidentialityNotice: 'This document contains confidential student information protected by FERPA and IDEA',
    };
  }

  public async getDueDates(days: number = 30): Promise<{ iepId: string; studentName: string; type: string; dueDate: Date }[]> {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() + days);

    const dueDates: { iepId: string; studentName: string; type: string; dueDate: Date }[] = [];

    for (const iep of this.ieps.values()) {
      if (iep.nextReviewDate <= cutoffDate) {
        dueDates.push({
          iepId: iep.id,
          studentName: iep.studentName,
          type: 'Annual Review',
          dueDate: iep.nextReviewDate,
        });
      }

      if (iep.nextTriennialDate <= cutoffDate) {
        dueDates.push({
          iepId: iep.id,
          studentName: iep.studentName,
          type: 'Triennial Evaluation',
          dueDate: iep.nextTriennialDate,
        });
      }
    }

    return dueDates.sort((a, b) => a.dueDate.getTime() - b.dueDate.getTime());
  }
}