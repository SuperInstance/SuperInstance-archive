import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';

export interface Conference {
  id: string;
  title: string;
  type: 'parent-teacher' | 'student-teacher' | 'iep-meeting' | 'disciplinary' | 'college-counseling' | 'group-conference';
  studentId?: string;
  teacherId: string;
  participants: ConferenceParticipant[];
  scheduledTime: Date;
  duration: number; // in minutes
  timeZone: string;
  status: 'scheduled' | 'in-progress' | 'completed' | 'cancelled' | 'no-show' | 'rescheduled';
  meetingLink: string;
  meetingId: string;
  roomId: string;
  agenda: AgendaItem[];
  documents: ConferenceDocument[];
  notes: ConferenceNote[];
  outcomes: ConferenceOutcome[];
  followUpActions: FollowUpAction[];
  recordingEnabled: boolean;
  recordingUrl?: string;
  transcriptUrl?: string;
  waitingRoom: boolean;
  requiresAuthentication: boolean;
  maxParticipants: number;
  language: string;
  interpreterNeeded: boolean;
  interpreterLanguage?: string;
  accessibilityFeatures: AccessibilityFeature[];
  reminders: ReminderSettings[];
  createdBy: string;
  createdDate: Date;
  lastModified: Date;
  actualStartTime?: Date;
  actualEndTime?: Date;
  actualDuration?: number;
  attendanceTracked: boolean;
  qualityMetrics?: QualityMetrics;
}

export interface ConferenceParticipant {
  id: string;
  userId: string;
  name: string;
  email: string;
  role: 'teacher' | 'parent' | 'student' | 'administrator' | 'counselor' | 'specialist' | 'interpreter' | 'observer';
  relationship?: string; // e.g., "mother", "father", "guardian"
  isRequired: boolean;
  canJoinEarly: boolean;
  canRecord: boolean;
  canShare: boolean;
  canMute: boolean;
  joinTime?: Date;
  leaveTime?: Date;
  attendanceStatus: 'pending' | 'joined' | 'left' | 'no-show' | 'technical-issues';
  connectionQuality?: 'excellent' | 'good' | 'poor' | 'unstable';
  deviceType: 'desktop' | 'mobile' | 'tablet' | 'phone';
  browserInfo?: string;
  ipAddress?: string;
  microphoneEnabled: boolean;
  cameraEnabled: boolean;
  notificationPreferences: ParticipantNotifications;
}

export interface ParticipantNotifications {
  email: boolean;
  sms: boolean;
  push: boolean;
  reminderTimes: number[]; // minutes before meeting
  language: string;
  method: 'email' | 'sms' | 'both';
}

export interface AgendaItem {
  id: string;
  order: number;
  topic: string;
  description: string;
  presenter: string;
  estimatedTime: number;
  actualTime?: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
  category: 'academic' | 'behavioral' | 'social' | 'administrative' | 'planning' | 'other';
  relatedDocuments: string[];
  discussionPoints: string[];
  decisions: string[];
  actionItems: string[];
  completed: boolean;
}

export interface ConferenceDocument {
  id: string;
  name: string;
  type: 'report-card' | 'progress-report' | 'iep' | '504-plan' | 'behavior-plan' | 'portfolio' | 'assessment' | 'other';
  url: string;
  uploadedBy: string;
  uploadedDate: Date;
  isConfidential: boolean;
  accessPermissions: string[];
  viewedBy: DocumentViewer[];
  fileSize: number;
  mimeType: string;
  description?: string;
}

export interface DocumentViewer {
  userId: string;
  viewedDate: Date;
  viewDuration: number;
  downloaded: boolean;
}

export interface ConferenceNote {
  id: string;
  author: string;
  timestamp: Date;
  content: string;
  isPrivate: boolean;
  tags: string[];
  category: 'observation' | 'decision' | 'action-item' | 'concern' | 'success' | 'question';
  relatedAgendaItem?: string;
  attachments: string[];
  mentions: string[]; // user IDs mentioned in the note
}

export interface ConferenceOutcome {
  id: string;
  category: 'academic' | 'behavioral' | 'social-emotional' | 'attendance' | 'family' | 'placement' | 'services';
  description: string;
  decision: string;
  rationale: string;
  agreedUpon: boolean;
  disagreements?: string[];
  votingRecord?: VotingRecord;
  effectiveDate: Date;
  reviewDate?: Date;
  responsibleParty: string;
  successCriteria: string[];
  measurementMethod: string;
}

export interface VotingRecord {
  inFavor: string[];
  against: string[];
  abstained: string[];
  consensus: boolean;
}

export interface FollowUpAction {
  id: string;
  description: string;
  assignedTo: string;
  dueDate: Date;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'pending' | 'in-progress' | 'completed' | 'overdue' | 'cancelled';
  category: 'communication' | 'assessment' | 'intervention' | 'documentation' | 'meeting' | 'referral';
  completionDate?: Date;
  notes: string;
  reminders: Date[];
  parentNotification: boolean;
  dependencies: string[];
}

export interface AccessibilityFeature {
  type: 'closed-captions' | 'screen-reader' | 'high-contrast' | 'large-text' | 'keyboard-navigation' | 'audio-description';
  enabled: boolean;
  settings: any;
}

export interface ReminderSettings {
  type: 'email' | 'sms' | 'push' | 'phone-call';
  timing: number; // minutes before meeting
  recipients: string[];
  customMessage?: string;
  sent: boolean;
  sentDate?: Date;
}

export interface QualityMetrics {
  overallRating: number;
  audioQuality: number;
  videoQuality: number;
  connectionStability: number;
  userExperience: number;
  technicalIssues: TechnicalIssue[];
  participantFeedback: ParticipantFeedback[];
  meetingEffectiveness: number;
  goalAchievement: number;
}

export interface TechnicalIssue {
  timestamp: Date;
  type: 'audio' | 'video' | 'connection' | 'sharing' | 'recording' | 'authentication';
  description: string;
  affectedParticipants: string[];
  severity: 'low' | 'medium' | 'high' | 'critical';
  resolved: boolean;
  resolutionTime?: number;
  resolutionMethod?: string;
}

export interface ParticipantFeedback {
  participantId: string;
  overallRating: number;
  audioQuality: number;
  videoQuality: number;
  easeOfUse: number;
  meetingValue: number;
  wouldRecommend: boolean;
  comments?: string;
  improvementSuggestions: string[];
  submittedDate: Date;
}

export interface ConferenceTemplate {
  id: string;
  name: string;
  type: Conference['type'];
  description: string;
  defaultDuration: number;
  defaultAgenda: Omit<AgendaItem, 'id' | 'completed' | 'actualTime' | 'decisions' | 'actionItems'>[];
  requiredParticipants: string[];
  recommendedDocuments: string[];
  settings: ConferenceSettings;
  isPublic: boolean;
  createdBy: string;
  usageCount: number;
  rating: number;
  tags: string[];
}

export interface ConferenceSettings {
  recordingEnabled: boolean;
  waitingRoom: boolean;
  requireAuthentication: boolean;
  allowEarlyJoin: boolean;
  autoAdmit: boolean;
  maxParticipants: number;
  muteOnJoin: boolean;
  videoOnJoin: boolean;
  chatEnabled: boolean;
  screenShareEnabled: boolean;
  fileShareEnabled: boolean;
  breakoutRoomsEnabled: boolean;
  pollsEnabled: boolean;
  whiteboardEnabled: boolean;
  closedCaptionsEnabled: boolean;
  recordingAutoStart: boolean;
  endMeetingForAll: boolean;
}

export interface ConferenceRoom {
  id: string;
  name: string;
  capacity: number;
  features: string[];
  isActive: boolean;
  currentMeeting?: string;
  upcomingMeetings: string[];
  waitingQueue: WaitingParticipant[];
  settings: ConferenceSettings;
  securityLevel: 'low' | 'medium' | 'high';
  recordingStorage: string;
  lastUsed?: Date;
}

export interface WaitingParticipant {
  participantId: string;
  name: string;
  joinTime: Date;
  deviceInfo: string;
  approved: boolean;
  approvedBy?: string;
  approvalTime?: Date;
}

export interface ConferenceInvitation {
  id: string;
  conferenceId: string;
  recipientId: string;
  recipientEmail: string;
  recipientName: string;
  invitedBy: string;
  invitationDate: Date;
  status: 'sent' | 'delivered' | 'opened' | 'accepted' | 'declined' | 'expired';
  responseDate?: Date;
  customMessage?: string;
  accessCode?: string;
  expirationDate: Date;
  remindersSent: number;
  lastReminderDate?: Date;
}

export interface ConferenceSeries {
  id: string;
  name: string;
  description: string;
  type: Conference['type'];
  studentId?: string;
  teacherId: string;
  frequency: 'weekly' | 'biweekly' | 'monthly' | 'quarterly' | 'semester' | 'yearly';
  recurrence: RecurrencePattern;
  participants: string[];
  template: string;
  settings: ConferenceSettings;
  startDate: Date;
  endDate?: Date;
  conferences: string[];
  isActive: boolean;
  nextConference?: Date;
  exceptions: SeriesException[];
}

export interface RecurrencePattern {
  type: 'daily' | 'weekly' | 'monthly' | 'yearly';
  interval: number;
  daysOfWeek?: number[];
  dayOfMonth?: number;
  weekOfMonth?: number;
  monthOfYear?: number;
  endDate?: Date;
  maxOccurrences?: number;
}

export interface SeriesException {
  originalDate: Date;
  action: 'cancel' | 'reschedule' | 'modify';
  newDate?: Date;
  reason: string;
  notificationSent: boolean;
}

export interface ConferenceAnalytics {
  totalConferences: number;
  completedConferences: number;
  cancelledConferences: number;
  noShowRate: number;
  averageDuration: number;
  participantSatisfaction: number;
  technicalIssueRate: number;
  attendanceRate: number;
  followUpCompletionRate: number;
  popularTimeSlots: TimeSlot[];
  deviceUsage: DeviceUsage[];
  languageDistribution: LanguageDistribution[];
  conferenceTypeBreakdown: ConferenceTypeStats[];
  monthlyTrends: MonthlyTrend[];
  qualityTrends: QualityTrend[];
  recommendations: AnalyticsRecommendation[];
}

export interface TimeSlot {
  time: string;
  count: number;
  successRate: number;
}

export interface DeviceUsage {
  deviceType: string;
  count: number;
  percentage: number;
  averageIssues: number;
}

export interface LanguageDistribution {
  language: string;
  count: number;
  percentage: number;
}

export interface ConferenceTypeStats {
  type: string;
  count: number;
  averageDuration: number;
  satisfactionScore: number;
}

export interface MonthlyTrend {
  month: string;
  conferences: number;
  completion: number;
  satisfaction: number;
}

export interface QualityTrend {
  date: string;
  audioQuality: number;
  videoQuality: number;
  connectionStability: number;
}

export interface AnalyticsRecommendation {
  category: 'scheduling' | 'technology' | 'engagement' | 'accessibility';
  recommendation: string;
  priority: 'low' | 'medium' | 'high';
  expectedImpact: string;
  implementationSteps: string[];
}

export class VirtualConferences extends EventEmitter {
  private conferences: Map<string, Conference> = new Map();
  private conferenceRooms: Map<string, ConferenceRoom> = new Map();
  private templates: Map<string, ConferenceTemplate> = new Map();
  private invitations: Map<string, ConferenceInvitation[]> = new Map();
  private conferenceSeries: Map<string, ConferenceSeries> = new Map();

  constructor() {
    super();
    this.initializeRooms();
    this.initializeTemplates();
  }

  private initializeRooms(): void {
    const defaultRooms = [
      {
        id: 'room-general-1',
        name: 'General Conference Room 1',
        capacity: 10,
        features: ['recording', 'screen-share', 'chat', 'whiteboard'],
        isActive: true,
        upcomingMeetings: [],
        waitingQueue: [],
        settings: {
          recordingEnabled: true,
          waitingRoom: true,
          requireAuthentication: false,
          allowEarlyJoin: true,
          autoAdmit: false,
          maxParticipants: 10,
          muteOnJoin: true,
          videoOnJoin: false,
          chatEnabled: true,
          screenShareEnabled: true,
          fileShareEnabled: true,
          breakoutRoomsEnabled: false,
          pollsEnabled: true,
          whiteboardEnabled: true,
          closedCaptionsEnabled: true,
          recordingAutoStart: false,
          endMeetingForAll: true,
        },
        securityLevel: 'medium' as const,
        recordingStorage: '/recordings/general/',
      },
      {
        id: 'room-iep-secure',
        name: 'Secure IEP Meeting Room',
        capacity: 15,
        features: ['recording', 'screen-share', 'chat', 'document-sharing', 'high-security'],
        isActive: true,
        upcomingMeetings: [],
        waitingQueue: [],
        settings: {
          recordingEnabled: true,
          waitingRoom: true,
          requireAuthentication: true,
          allowEarlyJoin: false,
          autoAdmit: false,
          maxParticipants: 15,
          muteOnJoin: true,
          videoOnJoin: true,
          chatEnabled: true,
          screenShareEnabled: true,
          fileShareEnabled: true,
          breakoutRoomsEnabled: true,
          pollsEnabled: false,
          whiteboardEnabled: true,
          closedCaptionsEnabled: true,
          recordingAutoStart: true,
          endMeetingForAll: true,
        },
        securityLevel: 'high' as const,
        recordingStorage: '/recordings/secure/',
      },
    ] as ConferenceRoom[];

    defaultRooms.forEach(room => {
      this.conferenceRooms.set(room.id, room);
    });
  }

  private initializeTemplates(): void {
    const templates = [
      {
        id: 'parent-teacher-standard',
        name: 'Standard Parent-Teacher Conference',
        type: 'parent-teacher' as const,
        description: 'Regular parent-teacher conference for discussing student progress',
        defaultDuration: 30,
        defaultAgenda: [
          {
            order: 1,
            topic: 'Welcome and Introductions',
            description: 'Brief welcome and introductions of all participants',
            presenter: 'teacher',
            estimatedTime: 3,
            priority: 'low' as const,
            category: 'administrative' as const,
            relatedDocuments: [],
            discussionPoints: ['Participant introductions', 'Meeting objectives'],
          },
          {
            order: 2,
            topic: 'Academic Progress Review',
            description: 'Review of student academic performance and progress',
            presenter: 'teacher',
            estimatedTime: 15,
            priority: 'high' as const,
            category: 'academic' as const,
            relatedDocuments: ['progress-report', 'report-card'],
            discussionPoints: ['Current grades', 'Strengths', 'Areas for improvement', 'Goal progress'],
          },
          {
            order: 3,
            topic: 'Behavioral and Social Development',
            description: 'Discussion of student behavior and social interactions',
            presenter: 'teacher',
            estimatedTime: 8,
            priority: 'medium' as const,
            category: 'behavioral' as const,
            relatedDocuments: ['behavior-reports'],
            discussionPoints: ['Classroom behavior', 'Peer interactions', 'Social skills'],
          },
          {
            order: 4,
            topic: 'Goals and Action Plans',
            description: 'Setting goals and creating action plans for continued growth',
            presenter: 'teacher',
            estimatedTime: 10,
            priority: 'high' as const,
            category: 'planning' as const,
            relatedDocuments: [],
            discussionPoints: ['Short-term goals', 'Long-term goals', 'Support needed', 'Home-school collaboration'],
          },
          {
            order: 5,
            topic: 'Questions and Next Steps',
            description: 'Address parent questions and determine next steps',
            presenter: 'teacher',
            estimatedTime: 4,
            priority: 'medium' as const,
            category: 'other' as const,
            relatedDocuments: [],
            discussionPoints: ['Parent questions', 'Follow-up actions', 'Next meeting date'],
          },
        ],
        requiredParticipants: ['teacher', 'parent'],
        recommendedDocuments: ['progress-report', 'portfolio-samples', 'assessment-results'],
        settings: {
          recordingEnabled: true,
          waitingRoom: true,
          requireAuthentication: false,
          allowEarlyJoin: true,
          autoAdmit: false,
          maxParticipants: 6,
          muteOnJoin: true,
          videoOnJoin: true,
          chatEnabled: true,
          screenShareEnabled: true,
          fileShareEnabled: true,
          breakoutRoomsEnabled: false,
          pollsEnabled: false,
          whiteboardEnabled: false,
          closedCaptionsEnabled: true,
          recordingAutoStart: false,
          endMeetingForAll: true,
        },
        isPublic: true,
        createdBy: 'system',
        usageCount: 0,
        rating: 0,
        tags: ['parent-teacher', 'progress', 'standard'],
      },
      {
        id: 'iep-meeting-template',
        name: 'IEP Team Meeting',
        type: 'iep-meeting' as const,
        description: 'Structured template for IEP team meetings',
        defaultDuration: 90,
        defaultAgenda: [
          {
            order: 1,
            topic: 'Meeting Opening and Introductions',
            description: 'Welcome participants and review meeting purpose',
            presenter: 'administrator',
            estimatedTime: 5,
            priority: 'medium' as const,
            category: 'administrative' as const,
            relatedDocuments: [],
            discussionPoints: ['Introductions', 'Meeting purpose', 'Procedural safeguards'],
          },
          {
            order: 2,
            topic: 'Review of Current IEP',
            description: 'Review existing IEP goals, services, and progress',
            presenter: 'case-manager',
            estimatedTime: 20,
            priority: 'high' as const,
            category: 'academic' as const,
            relatedDocuments: ['current-iep', 'progress-reports'],
            discussionPoints: ['Goal progress', 'Service effectiveness', 'Data review'],
          },
          {
            order: 3,
            topic: 'Present Levels of Performance',
            description: 'Discussion of student current performance levels',
            presenter: 'teacher',
            estimatedTime: 15,
            priority: 'high' as const,
            category: 'academic' as const,
            relatedDocuments: ['assessments', 'evaluations'],
            discussionPoints: ['Academic performance', 'Functional performance', 'Strengths and needs'],
          },
          {
            order: 4,
            topic: 'Goal Development',
            description: 'Develop or revise IEP goals',
            presenter: 'case-manager',
            estimatedTime: 30,
            priority: 'critical' as const,
            category: 'planning' as const,
            relatedDocuments: ['draft-goals'],
            discussionPoints: ['Annual goals', 'Short-term objectives', 'Measurability', 'Progress monitoring'],
          },
          {
            order: 5,
            topic: 'Services and Placement',
            description: 'Determine appropriate services and placement',
            presenter: 'case-manager',
            estimatedTime: 15,
            priority: 'critical' as const,
            category: 'administrative' as const,
            relatedDocuments: [],
            discussionPoints: ['Service needs', 'LRE determination', 'Related services', 'Accommodations'],
          },
          {
            order: 6,
            topic: 'Finalization and Signatures',
            description: 'Finalize IEP and obtain signatures',
            presenter: 'administrator',
            estimatedTime: 5,
            priority: 'high' as const,
            category: 'administrative' as const,
            relatedDocuments: ['final-iep'],
            discussionPoints: ['Agreement confirmation', 'Signature collection', 'Implementation timeline'],
          },
        ],
        requiredParticipants: ['parent', 'teacher', 'special-ed-teacher', 'administrator'],
        recommendedDocuments: ['current-iep', 'evaluations', 'progress-data', 'draft-iep'],
        settings: {
          recordingEnabled: true,
          waitingRoom: true,
          requireAuthentication: true,
          allowEarlyJoin: false,
          autoAdmit: false,
          maxParticipants: 12,
          muteOnJoin: true,
          videoOnJoin: true,
          chatEnabled: false,
          screenShareEnabled: true,
          fileShareEnabled: true,
          breakoutRoomsEnabled: false,
          pollsEnabled: false,
          whiteboardEnabled: false,
          closedCaptionsEnabled: true,
          recordingAutoStart: true,
          endMeetingForAll: true,
        },
        isPublic: true,
        createdBy: 'system',
        usageCount: 0,
        rating: 0,
        tags: ['iep', 'special-education', 'team-meeting'],
      },
    ] as ConferenceTemplate[];

    templates.forEach(template => {
      this.templates.set(template.id, template);
    });
  }

  public async scheduleConference(conferenceData: Omit<Conference, 'id' | 'createdDate' | 'lastModified' | 'meetingLink' | 'meetingId' | 'roomId'>): Promise<Conference> {
    const room = await this.findAvailableRoom(conferenceData.scheduledTime, conferenceData.duration, conferenceData.maxParticipants);
    
    const conference: Conference = {
      ...conferenceData,
      id: uuidv4(),
      meetingLink: `https://meetings.activelog.com/join/${uuidv4()}`,
      meetingId: uuidv4().substring(0, 10),
      roomId: room.id,
      createdDate: new Date(),
      lastModified: new Date(),
    };

    this.conferences.set(conference.id, conference);
    
    // Update room bookings
    room.upcomingMeetings.push(conference.id);
    this.conferenceRooms.set(room.id, room);

    // Send invitations
    await this.sendInvitations(conference);

    this.emit('conferenceScheduled', conference);
    return conference;
  }

  private async findAvailableRoom(scheduledTime: Date, duration: number, maxParticipants: number): Promise<ConferenceRoom> {
    const availableRooms = Array.from(this.conferenceRooms.values()).filter(room => 
      room.isActive && 
      room.capacity >= maxParticipants &&
      this.isRoomAvailable(room, scheduledTime, duration)
    );

    if (availableRooms.length === 0) {
      throw new Error('No available rooms for the requested time slot');
    }

    // Return the room with the most appropriate capacity (not too large)
    return availableRooms.sort((a, b) => a.capacity - b.capacity)[0];
  }

  private isRoomAvailable(room: ConferenceRoom, scheduledTime: Date, duration: number): boolean {
    // This would check against actual bookings
    // For now, assuming room is available
    return true;
  }

  public async updateConference(conferenceId: string, updates: Partial<Conference>): Promise<Conference | null> {
    const existing = this.conferences.get(conferenceId);
    if (!existing) return null;

    const updated = {
      ...existing,
      ...updates,
      lastModified: new Date(),
    };

    this.conferences.set(conferenceId, updated);

    // If time changed, update room bookings
    if (updates.scheduledTime && updates.scheduledTime !== existing.scheduledTime) {
      await this.handleReschedule(conferenceId, updates.scheduledTime, existing.scheduledTime);
    }

    this.emit('conferenceUpdated', updated);
    return updated;
  }

  private async handleReschedule(conferenceId: string, newTime: Date, oldTime: Date): Promise<void> {
    // Notify participants about reschedule
    const conference = this.conferences.get(conferenceId);
    if (conference) {
      const notifications = conference.participants.map(p => ({
        recipientId: p.userId,
        message: `Conference "${conference.title}" has been rescheduled from ${oldTime.toLocaleString()} to ${newTime.toLocaleString()}`,
      }));

      this.emit('conferenceRescheduled', { conferenceId, notifications });
    }
  }

  public async cancelConference(conferenceId: string, reason: string): Promise<boolean> {
    const conference = this.conferences.get(conferenceId);
    if (!conference) return false;

    conference.status = 'cancelled';
    conference.lastModified = new Date();

    // Free up the room
    const room = this.conferenceRooms.get(conference.roomId);
    if (room) {
      room.upcomingMeetings = room.upcomingMeetings.filter(id => id !== conferenceId);
      this.conferenceRooms.set(conference.roomId, room);
    }

    // Notify participants
    const notifications = conference.participants.map(p => ({
      recipientId: p.userId,
      message: `Conference "${conference.title}" scheduled for ${conference.scheduledTime.toLocaleString()} has been cancelled. Reason: ${reason}`,
    }));

    this.conferences.set(conferenceId, conference);
    this.emit('conferenceCancelled', { conference, reason, notifications });
    return true;
  }

  public async startConference(conferenceId: string, hostId: string): Promise<Conference | null> {
    const conference = this.conferences.get(conferenceId);
    if (!conference || conference.status !== 'scheduled') return null;

    conference.status = 'in-progress';
    conference.actualStartTime = new Date();
    conference.lastModified = new Date();

    // Initialize room
    const room = this.conferenceRooms.get(conference.roomId);
    if (room) {
      room.currentMeeting = conferenceId;
      this.conferenceRooms.set(conference.roomId, room);
    }

    this.conferences.set(conferenceId, conference);
    this.emit('conferenceStarted', { conference, hostId });
    return conference;
  }

  public async endConference(conferenceId: string, hostId: string): Promise<Conference | null> {
    const conference = this.conferences.get(conferenceId);
    if (!conference || conference.status !== 'in-progress') return null;

    conference.status = 'completed';
    conference.actualEndTime = new Date();
    conference.actualDuration = conference.actualEndTime.getTime() - (conference.actualStartTime?.getTime() || 0);
    conference.lastModified = new Date();

    // Free up the room
    const room = this.conferenceRooms.get(conference.roomId);
    if (room) {
      room.currentMeeting = undefined;
      room.upcomingMeetings = room.upcomingMeetings.filter(id => id !== conferenceId);
      room.lastUsed = new Date();
      this.conferenceRooms.set(conference.roomId, room);
    }

    // Generate follow-up reminders
    await this.generateFollowUpReminders(conference);

    this.conferences.set(conferenceId, conference);
    this.emit('conferenceEnded', { conference, hostId });
    return conference;
  }

  public async joinConference(conferenceId: string, participantId: string, deviceInfo: any): Promise<{ success: boolean; waitingRoom?: boolean; error?: string }> {
    const conference = this.conferences.get(conferenceId);
    if (!conference) {
      return { success: false, error: 'Conference not found' };
    }

    if (conference.status !== 'scheduled' && conference.status !== 'in-progress') {
      return { success: false, error: 'Conference is not active' };
    }

    const participant = conference.participants.find(p => p.userId === participantId);
    if (!participant && conference.requiresAuthentication) {
      return { success: false, error: 'Participant not authorized' };
    }

    const room = this.conferenceRooms.get(conference.roomId);
    if (!room) {
      return { success: false, error: 'Conference room not available' };
    }

    // Check capacity
    const currentParticipants = conference.participants.filter(p => p.attendanceStatus === 'joined').length;
    if (currentParticipants >= room.capacity) {
      return { success: false, error: 'Conference room is full' };
    }

    // Handle waiting room
    if (room.settings.waitingRoom && conference.status !== 'in-progress') {
      const waitingParticipant: WaitingParticipant = {
        participantId,
        name: participant?.name || 'Unknown',
        joinTime: new Date(),
        deviceInfo: JSON.stringify(deviceInfo),
        approved: false,
      };

      room.waitingQueue.push(waitingParticipant);
      this.conferenceRooms.set(conference.roomId, room);

      return { success: true, waitingRoom: true };
    }

    // Join the conference
    if (participant) {
      participant.joinTime = new Date();
      participant.attendanceStatus = 'joined';
      participant.deviceType = deviceInfo.type || 'desktop';
      participant.browserInfo = deviceInfo.browser;
      participant.connectionQuality = 'good'; // Would be monitored in real-time
    }

    this.conferences.set(conferenceId, conference);
    this.emit('participantJoined', { conferenceId, participantId, deviceInfo });

    return { success: true };
  }

  public async leaveConference(conferenceId: string, participantId: string): Promise<boolean> {
    const conference = this.conferences.get(conferenceId);
    if (!conference) return false;

    const participant = conference.participants.find(p => p.userId === participantId);
    if (participant) {
      participant.leaveTime = new Date();
      participant.attendanceStatus = 'left';
    }

    this.conferences.set(conferenceId, conference);
    this.emit('participantLeft', { conferenceId, participantId });
    return true;
  }

  public async addParticipant(conferenceId: string, participantData: Omit<ConferenceParticipant, 'id' | 'attendanceStatus'>): Promise<ConferenceParticipant | null> {
    const conference = this.conferences.get(conferenceId);
    if (!conference) return null;

    const participant: ConferenceParticipant = {
      ...participantData,
      id: uuidv4(),
      attendanceStatus: 'pending',
    };

    conference.participants.push(participant);
    conference.lastModified = new Date();

    // Send invitation to new participant
    await this.sendInvitation(conference, participant);

    this.conferences.set(conferenceId, conference);
    this.emit('participantAdded', { conferenceId, participant });
    return participant;
  }

  public async addNote(conferenceId: string, note: Omit<ConferenceNote, 'id' | 'timestamp'>): Promise<ConferenceNote | null> {
    const conference = this.conferences.get(conferenceId);
    if (!conference) return null;

    const conferenceNote: ConferenceNote = {
      ...note,
      id: uuidv4(),
      timestamp: new Date(),
    };

    conference.notes.push(conferenceNote);
    conference.lastModified = new Date();

    this.conferences.set(conferenceId, conference);
    this.emit('noteAdded', { conferenceId, note: conferenceNote });
    return conferenceNote;
  }

  public async addOutcome(conferenceId: string, outcome: Omit<ConferenceOutcome, 'id'>): Promise<ConferenceOutcome | null> {
    const conference = this.conferences.get(conferenceId);
    if (!conference) return null;

    const conferenceOutcome: ConferenceOutcome = {
      ...outcome,
      id: uuidv4(),
    };

    conference.outcomes.push(conferenceOutcome);
    conference.lastModified = new Date();

    this.conferences.set(conferenceId, conference);
    this.emit('outcomeAdded', { conferenceId, outcome: conferenceOutcome });
    return conferenceOutcome;
  }

  public async addFollowUpAction(conferenceId: string, action: Omit<FollowUpAction, 'id'>): Promise<FollowUpAction | null> {
    const conference = this.conferences.get(conferenceId);
    if (!conference) return null;

    const followUpAction: FollowUpAction = {
      ...action,
      id: uuidv4(),
    };

    conference.followUpActions.push(followUpAction);
    conference.lastModified = new Date();

    this.conferences.set(conferenceId, conference);
    this.emit('followUpAdded', { conferenceId, action: followUpAction });
    return followUpAction;
  }

  public async uploadDocument(conferenceId: string, document: Omit<ConferenceDocument, 'id' | 'uploadedDate' | 'viewedBy'>): Promise<ConferenceDocument | null> {
    const conference = this.conferences.get(conferenceId);
    if (!conference) return null;

    const conferenceDocument: ConferenceDocument = {
      ...document,
      id: uuidv4(),
      uploadedDate: new Date(),
      viewedBy: [],
    };

    conference.documents.push(conferenceDocument);
    conference.lastModified = new Date();

    this.conferences.set(conferenceId, conference);
    this.emit('documentUploaded', { conferenceId, document: conferenceDocument });
    return conferenceDocument;
  }

  public async createTemplate(template: Omit<ConferenceTemplate, 'id' | 'usageCount' | 'rating'>): Promise<ConferenceTemplate> {
    const conferenceTemplate: ConferenceTemplate = {
      ...template,
      id: uuidv4(),
      usageCount: 0,
      rating: 0,
    };

    this.templates.set(conferenceTemplate.id, conferenceTemplate);
    this.emit('templateCreated', conferenceTemplate);
    return conferenceTemplate;
  }

  public async getTemplates(type?: Conference['type']): Promise<ConferenceTemplate[]> {
    let templates = Array.from(this.templates.values());
    
    if (type) {
      templates = templates.filter(t => t.type === type);
    }

    return templates.sort((a, b) => b.usageCount - a.usageCount);
  }

  public async useTemplate(templateId: string, customizations: Partial<Conference>): Promise<Partial<Conference> | null> {
    const template = this.templates.get(templateId);
    if (!template) return null;

    const conferenceData = {
      type: template.type,
      duration: template.defaultDuration,
      agenda: template.defaultAgenda.map(item => ({
        ...item,
        id: uuidv4(),
        actualTime: undefined,
        decisions: [],
        actionItems: [],
        completed: false,
      })),
      recordingEnabled: template.settings.recordingEnabled,
      waitingRoom: template.settings.waitingRoom,
      requiresAuthentication: template.settings.requireAuthentication,
      maxParticipants: template.settings.maxParticipants,
      accessibilityFeatures: [],
      ...customizations,
    };

    // Update template usage
    template.usageCount++;
    this.templates.set(templateId, template);

    return conferenceData;
  }

  private async sendInvitations(conference: Conference): Promise<void> {
    const invitations = conference.participants.map(participant => this.sendInvitation(conference, participant));
    await Promise.all(invitations);
  }

  private async sendInvitation(conference: Conference, participant: ConferenceParticipant): Promise<ConferenceInvitation> {
    const invitation: ConferenceInvitation = {
      id: uuidv4(),
      conferenceId: conference.id,
      recipientId: participant.userId,
      recipientEmail: participant.email,
      recipientName: participant.name,
      invitedBy: conference.createdBy,
      invitationDate: new Date(),
      status: 'sent',
      accessCode: Math.random().toString(36).substring(2, 10).toUpperCase(),
      expirationDate: new Date(conference.scheduledTime.getTime() + 24 * 60 * 60 * 1000), // 24 hours after meeting
      remindersSent: 0,
    };

    const conferenceInvitations = this.invitations.get(conference.id) || [];
    conferenceInvitations.push(invitation);
    this.invitations.set(conference.id, conferenceInvitations);

    this.emit('invitationSent', invitation);
    return invitation;
  }

  private async generateFollowUpReminders(conference: Conference): Promise<void> {
    conference.followUpActions.forEach(action => {
      if (action.status === 'pending' && action.dueDate > new Date()) {
        // Schedule reminder for follow-up action
        this.emit('followUpReminder', { conferenceId: conference.id, action });
      }
    });
  }

  public async createSeries(seriesData: Omit<ConferenceSeries, 'id' | 'conferences' | 'nextConference'>): Promise<ConferenceSeries> {
    const series: ConferenceSeries = {
      ...seriesData,
      id: uuidv4(),
      conferences: [],
      nextConference: this.calculateNextOccurrence(seriesData.startDate, seriesData.recurrence),
    };

    this.conferenceSeries.set(series.id, series);
    
    // Generate initial conferences based on recurrence
    await this.generateSeriesConferences(series);

    this.emit('seriesCreated', series);
    return series;
  }

  private calculateNextOccurrence(startDate: Date, recurrence: RecurrencePattern): Date {
    const next = new Date(startDate);
    
    switch (recurrence.type) {
      case 'daily':
        next.setDate(next.getDate() + recurrence.interval);
        break;
      case 'weekly':
        next.setDate(next.getDate() + (7 * recurrence.interval));
        break;
      case 'monthly':
        next.setMonth(next.getMonth() + recurrence.interval);
        break;
      case 'yearly':
        next.setFullYear(next.getFullYear() + recurrence.interval);
        break;
    }

    return next;
  }

  private async generateSeriesConferences(series: ConferenceSeries): Promise<void> {
    // This would generate a set of conferences based on the recurrence pattern
    // For now, just generate the next occurrence
    if (series.nextConference) {
      const template = this.templates.get(series.template);
      if (template) {
        const conferenceData = await this.useTemplate(series.template, {
          title: `${series.name} - ${series.nextConference.toDateString()}`,
          type: series.type,
          teacherId: series.teacherId,
          scheduledTime: series.nextConference,
          participants: series.participants.map(pId => ({
            id: uuidv4(),
            userId: pId,
            name: 'Participant', // Would be looked up
            email: 'participant@example.com',
            role: 'parent' as const,
            isRequired: true,
            canJoinEarly: true,
            canRecord: false,
            canShare: false,
            canMute: true,
            attendanceStatus: 'pending' as const,
            deviceType: 'desktop' as const,
            microphoneEnabled: true,
            cameraEnabled: true,
            notificationPreferences: {
              email: true,
              sms: false,
              push: true,
              reminderTimes: [60, 15],
              language: 'en',
              method: 'email' as const,
            },
          })),
        });

        if (conferenceData) {
          const conference = await this.scheduleConference({
            ...conferenceData,
            createdBy: series.teacherId,
            reminders: [],
          } as Omit<Conference, 'id' | 'createdDate' | 'lastModified' | 'meetingLink' | 'meetingId' | 'roomId'>);
          
          series.conferences.push(conference.id);
          this.conferenceSeries.set(series.id, series);
        }
      }
    }
  }

  public async getConference(conferenceId: string): Promise<Conference | null> {
    return this.conferences.get(conferenceId) || null;
  }

  public async getUpcomingConferences(userId: string, days: number = 7): Promise<Conference[]> {
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() + days);

    return Array.from(this.conferences.values()).filter(conf =>
      conf.participants.some(p => p.userId === userId) &&
      conf.status === 'scheduled' &&
      conf.scheduledTime <= cutoffDate &&
      conf.scheduledTime >= new Date()
    ).sort((a, b) => a.scheduledTime.getTime() - b.scheduledTime.getTime());
  }

  public async getConferenceHistory(userId: string, limit?: number): Promise<Conference[]> {
    let conferences = Array.from(this.conferences.values()).filter(conf =>
      conf.participants.some(p => p.userId === userId) &&
      conf.status === 'completed'
    ).sort((a, b) => (b.actualEndTime?.getTime() || 0) - (a.actualEndTime?.getTime() || 0));

    if (limit) {
      conferences = conferences.slice(0, limit);
    }

    return conferences;
  }

  public async generateAnalytics(teacherId?: string, timeframe?: { start: Date; end: Date }): Promise<ConferenceAnalytics> {
    let conferences = Array.from(this.conferences.values());

    if (teacherId) {
      conferences = conferences.filter(c => c.teacherId === teacherId);
    }

    if (timeframe) {
      conferences = conferences.filter(c =>
        c.scheduledTime >= timeframe.start && c.scheduledTime <= timeframe.end
      );
    }

    const analytics: ConferenceAnalytics = {
      totalConferences: conferences.length,
      completedConferences: conferences.filter(c => c.status === 'completed').length,
      cancelledConferences: conferences.filter(c => c.status === 'cancelled').length,
      noShowRate: this.calculateNoShowRate(conferences),
      averageDuration: this.calculateAverageDuration(conferences),
      participantSatisfaction: this.calculateSatisfactionScore(conferences),
      technicalIssueRate: this.calculateTechnicalIssueRate(conferences),
      attendanceRate: this.calculateAttendanceRate(conferences),
      followUpCompletionRate: this.calculateFollowUpCompletionRate(conferences),
      popularTimeSlots: this.getPopularTimeSlots(conferences),
      deviceUsage: this.getDeviceUsage(conferences),
      languageDistribution: this.getLanguageDistribution(conferences),
      conferenceTypeBreakdown: this.getConferenceTypeBreakdown(conferences),
      monthlyTrends: this.getMonthlyTrends(conferences),
      qualityTrends: this.getQualityTrends(conferences),
      recommendations: this.generateAnalyticsRecommendations(conferences),
    };

    this.emit('analyticsGenerated', { teacherId, timeframe, analytics });
    return analytics;
  }

  private calculateNoShowRate(conferences: Conference[]): number {
    const scheduledConferences = conferences.filter(c => c.status === 'scheduled' || c.status === 'no-show' || c.status === 'completed');
    const noShows = conferences.filter(c => c.status === 'no-show').length;
    return scheduledConferences.length > 0 ? (noShows / scheduledConferences.length) * 100 : 0;
  }

  private calculateAverageDuration(conferences: Conference[]): number {
    const completedConferences = conferences.filter(c => c.actualDuration);
    return completedConferences.length > 0
      ? completedConferences.reduce((sum, c) => sum + (c.actualDuration || 0), 0) / completedConferences.length / (1000 * 60) // Convert to minutes
      : 0;
  }

  private calculateSatisfactionScore(conferences: Conference[]): number {
    let totalRatings = 0;
    let ratingCount = 0;

    conferences.forEach(conf => {
      conf.qualityMetrics?.participantFeedback.forEach(feedback => {
        totalRatings += feedback.overallRating;
        ratingCount++;
      });
    });

    return ratingCount > 0 ? totalRatings / ratingCount : 0;
  }

  private calculateTechnicalIssueRate(conferences: Conference[]): number {
    const conferencesWithIssues = conferences.filter(c =>
      c.qualityMetrics?.technicalIssues && c.qualityMetrics.technicalIssues.length > 0
    ).length;

    return conferences.length > 0 ? (conferencesWithIssues / conferences.length) * 100 : 0;
  }

  private calculateAttendanceRate(conferences: Conference[]): number {
    let totalExpected = 0;
    let totalAttended = 0;

    conferences.forEach(conf => {
      totalExpected += conf.participants.length;
      totalAttended += conf.participants.filter(p => p.attendanceStatus === 'joined').length;
    });

    return totalExpected > 0 ? (totalAttended / totalExpected) * 100 : 0;
  }

  private calculateFollowUpCompletionRate(conferences: Conference[]): number {
    let totalActions = 0;
    let completedActions = 0;

    conferences.forEach(conf => {
      totalActions += conf.followUpActions.length;
      completedActions += conf.followUpActions.filter(a => a.status === 'completed').length;
    });

    return totalActions > 0 ? (completedActions / totalActions) * 100 : 0;
  }

  private getPopularTimeSlots(conferences: Conference[]): TimeSlot[] {
    const timeSlots = new Map<string, { count: number; successful: number }>();

    conferences.forEach(conf => {
      const hour = conf.scheduledTime.getHours();
      const timeSlot = `${hour}:00-${hour + 1}:00`;
      
      const existing = timeSlots.get(timeSlot) || { count: 0, successful: 0 };
      existing.count++;
      
      if (conf.status === 'completed') {
        existing.successful++;
      }

      timeSlots.set(timeSlot, existing);
    });

    return Array.from(timeSlots.entries()).map(([time, data]) => ({
      time,
      count: data.count,
      successRate: data.count > 0 ? (data.successful / data.count) * 100 : 0,
    })).sort((a, b) => b.count - a.count);
  }

  private getDeviceUsage(conferences: Conference[]): DeviceUsage[] {
    const deviceCounts = new Map<string, { count: number; issues: number }>();

    conferences.forEach(conf => {
      conf.participants.forEach(participant => {
        const device = participant.deviceType;
        const existing = deviceCounts.get(device) || { count: 0, issues: 0 };
        existing.count++;

        if (participant.connectionQuality === 'poor' || participant.connectionQuality === 'unstable') {
          existing.issues++;
        }

        deviceCounts.set(device, existing);
      });
    });

    const total = Array.from(deviceCounts.values()).reduce((sum, data) => sum + data.count, 0);

    return Array.from(deviceCounts.entries()).map(([deviceType, data]) => ({
      deviceType,
      count: data.count,
      percentage: total > 0 ? (data.count / total) * 100 : 0,
      averageIssues: data.count > 0 ? (data.issues / data.count) * 100 : 0,
    }));
  }

  private getLanguageDistribution(conferences: Conference[]): LanguageDistribution[] {
    const languageCounts = new Map<string, number>();

    conferences.forEach(conf => {
      const language = conf.language;
      languageCounts.set(language, (languageCounts.get(language) || 0) + 1);
    });

    const total = Array.from(languageCounts.values()).reduce((sum, count) => sum + count, 0);

    return Array.from(languageCounts.entries()).map(([language, count]) => ({
      language,
      count,
      percentage: total > 0 ? (count / total) * 100 : 0,
    }));
  }

  private getConferenceTypeBreakdown(conferences: Conference[]): ConferenceTypeStats[] {
    const typeStats = new Map<string, { count: number; totalDuration: number; totalSatisfaction: number; satisfactionCount: number }>();

    conferences.forEach(conf => {
      const type = conf.type;
      const existing = typeStats.get(type) || { count: 0, totalDuration: 0, totalSatisfaction: 0, satisfactionCount: 0 };
      
      existing.count++;
      existing.totalDuration += conf.actualDuration || conf.duration * 60000;

      if (conf.qualityMetrics?.participantFeedback) {
        conf.qualityMetrics.participantFeedback.forEach(feedback => {
          existing.totalSatisfaction += feedback.overallRating;
          existing.satisfactionCount++;
        });
      }

      typeStats.set(type, existing);
    });

    return Array.from(typeStats.entries()).map(([type, stats]) => ({
      type,
      count: stats.count,
      averageDuration: stats.count > 0 ? (stats.totalDuration / stats.count) / (1000 * 60) : 0, // Convert to minutes
      satisfactionScore: stats.satisfactionCount > 0 ? stats.totalSatisfaction / stats.satisfactionCount : 0,
    }));
  }

  private getMonthlyTrends(conferences: Conference[]): MonthlyTrend[] {
    const monthlyData = new Map<string, { conferences: number; completed: number; totalSatisfaction: number; satisfactionCount: number }>();

    conferences.forEach(conf => {
      const monthKey = `${conf.scheduledTime.getFullYear()}-${conf.scheduledTime.getMonth() + 1}`;
      const existing = monthlyData.get(monthKey) || { conferences: 0, completed: 0, totalSatisfaction: 0, satisfactionCount: 0 };
      
      existing.conferences++;
      
      if (conf.status === 'completed') {
        existing.completed++;
      }

      if (conf.qualityMetrics?.participantFeedback) {
        conf.qualityMetrics.participantFeedback.forEach(feedback => {
          existing.totalSatisfaction += feedback.overallRating;
          existing.satisfactionCount++;
        });
      }

      monthlyData.set(monthKey, existing);
    });

    return Array.from(monthlyData.entries()).map(([month, data]) => ({
      month,
      conferences: data.conferences,
      completion: data.completed,
      satisfaction: data.satisfactionCount > 0 ? data.totalSatisfaction / data.satisfactionCount : 0,
    })).sort();
  }

  private getQualityTrends(conferences: Conference[]): QualityTrend[] {
    // This would analyze quality metrics over time
    // For now, returning sample data
    return [];
  }

  private generateAnalyticsRecommendations(conferences: Conference[]): AnalyticsRecommendation[] {
    const recommendations: AnalyticsRecommendation[] = [];
    
    const noShowRate = this.calculateNoShowRate(conferences);
    if (noShowRate > 20) {
      recommendations.push({
        category: 'scheduling',
        recommendation: 'Implement additional reminder notifications to reduce no-show rate',
        priority: 'high',
        expectedImpact: 'Reduced no-show rate by 30-50%',
        implementationSteps: [
          'Add SMS reminders 2 hours before conference',
          'Implement confirmation system 24 hours prior',
          'Create automated rescheduling options'
        ],
      });
    }

    const technicalIssueRate = this.calculateTechnicalIssueRate(conferences);
    if (technicalIssueRate > 15) {
      recommendations.push({
        category: 'technology',
        recommendation: 'Improve technical support and pre-meeting testing',
        priority: 'medium',
        expectedImpact: 'Reduced technical issues by 40-60%',
        implementationSteps: [
          'Create pre-meeting system check tool',
          'Provide technical setup guides',
          'Offer practice sessions for new users'
        ],
      });
    }

    return recommendations;
  }
}