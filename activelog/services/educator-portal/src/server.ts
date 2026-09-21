import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { Server as SocketIOServer } from 'socket.io';
import { createServer } from 'http';
import rateLimit from 'express-rate-limit';

// Import all managers
import { ClassManager } from './classroom/class-manager';
import { AssignmentManager } from './assignments/assignment-manager';
import { ProgressReporter } from './reports/progress-reporter';
import { ParentTeacherCommunication } from './communication/parent-teacher-comm';
import { CurriculumAlignment } from './curriculum/curriculum-alignment';
import { LearningObjectivesTracker } from './objectives/learning-objectives';
import { IEPSupport } from './iep/iep-support';
import { HomeworkHelpSystem } from './homework/homework-help';
import { VirtualConferences } from './conferences/virtual-conferences';
import { ResourceLibrary } from './resources/resource-library';

// Initialize Express app
const app = express();
const server = createServer(app);
const io = new SocketIOServer(server, {
  cors: {
    origin: process.env.ALLOWED_ORIGINS?.split(',') || ["http://localhost:3000"],
    methods: ["GET", "POST", "PUT", "DELETE"],
    credentials: true
  }
});

// Initialize all managers
const classManager = new ClassManager();
const assignmentManager = new AssignmentManager();
const progressReporter = new ProgressReporter();
const parentTeacherComm = new ParentTeacherCommunication();
const curriculumAlignment = new CurriculumAlignment();
const learningObjectives = new LearningObjectivesTracker();
const iepSupport = new IEPSupport();
const homeworkHelp = new HomeworkHelpSystem();
const virtualConferences = new VirtualConferences();
const resourceLibrary = new ResourceLibrary();

// Configure middleware
app.use(helmet({
  contentSecurityPolicy: false, // Allow for development
  crossOriginEmbedderPolicy: false
}));

app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ["http://localhost:3000"],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
}));

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 1000, // limit each IP to 1000 requests per windowMs
  message: 'Too many requests from this IP, please try again later.',
  standardHeaders: true,
  legacyHeaders: false,
});
app.use(limiter);

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    service: 'educator-portal',
    version: '1.0.0'
  });
});

// ==================== CLASS MANAGEMENT ROUTES ====================

// Classes
app.post('/api/classes', async (req, res) => {
  try {
    const classRoom = await classManager.createClass(req.body);
    res.status(201).json(classRoom);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/classes/:id', async (req, res) => {
  try {
    const classRoom = await classManager.getClass(req.params.id);
    if (!classRoom) {
      return res.status(404).json({ error: 'Class not found' });
    }
    res.json(classRoom);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.put('/api/classes/:id', async (req, res) => {
  try {
    const classRoom = await classManager.updateClass(req.params.id, req.body);
    if (!classRoom) {
      return res.status(404).json({ error: 'Class not found' });
    }
    res.json(classRoom);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/classes/teacher/:teacherId', async (req, res) => {
  try {
    const classes = await classManager.getClassesByTeacher(req.params.teacherId);
    res.json(classes);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Students
app.post('/api/students', async (req, res) => {
  try {
    await classManager.addStudent(req.body);
    res.status(201).json({ message: 'Student added successfully' });
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/students/:id', async (req, res) => {
  try {
    const student = await classManager.getStudent(req.params.id);
    if (!student) {
      return res.status(404).json({ error: 'Student not found' });
    }
    res.json(student);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.post('/api/classes/:classId/students/:studentId/enroll', async (req, res) => {
  try {
    const success = await classManager.enrollStudent(req.params.classId, req.params.studentId);
    if (!success) {
      return res.status(400).json({ error: 'Failed to enroll student' });
    }
    res.json({ message: 'Student enrolled successfully' });
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Attendance
app.post('/api/attendance', async (req, res) => {
  try {
    const record = await classManager.recordAttendance(req.body);
    res.status(201).json(record);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/classes/:classId/attendance', async (req, res) => {
  try {
    const date = req.query.date ? new Date(req.query.date as string) : undefined;
    const attendance = await classManager.getAttendance(req.params.classId, date);
    res.json(attendance);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Behavior Notes
app.post('/api/behavior-notes', async (req, res) => {
  try {
    const note = await classManager.addBehaviorNote(req.body);
    res.status(201).json(note);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/students/:studentId/behavior-notes', async (req, res) => {
  try {
    const startDate = req.query.startDate ? new Date(req.query.startDate as string) : undefined;
    const endDate = req.query.endDate ? new Date(req.query.endDate as string) : undefined;
    const notes = await classManager.getBehaviorNotes(req.params.studentId, startDate, endDate);
    res.json(notes);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// ==================== ASSIGNMENT MANAGEMENT ROUTES ====================

// Assignments
app.post('/api/assignments', async (req, res) => {
  try {
    const assignment = await assignmentManager.createAssignment(req.body);
    res.status(201).json(assignment);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/assignments/:id', async (req, res) => {
  try {
    const assignment = await assignmentManager.getAssignment(req.params.id);
    if (!assignment) {
      return res.status(404).json({ error: 'Assignment not found' });
    }
    res.json(assignment);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.put('/api/assignments/:id', async (req, res) => {
  try {
    const assignment = await assignmentManager.updateAssignment(req.params.id, req.body);
    if (!assignment) {
      return res.status(404).json({ error: 'Assignment not found' });
    }
    res.json(assignment);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/classes/:classId/assignments', async (req, res) => {
  try {
    const assignments = await assignmentManager.getClassAssignments(req.params.classId);
    res.json(assignments);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.post('/api/assignments/:id/publish', async (req, res) => {
  try {
    const success = await assignmentManager.publishAssignment(req.params.id);
    if (!success) {
      return res.status(400).json({ error: 'Failed to publish assignment' });
    }
    res.json({ message: 'Assignment published successfully' });
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Submissions
app.post('/api/submissions', async (req, res) => {
  try {
    const submission = await assignmentManager.createSubmission(req.body);
    res.status(201).json(submission);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/assignments/:assignmentId/submissions', async (req, res) => {
  try {
    const submissions = await assignmentManager.getAssignmentSubmissions(req.params.assignmentId);
    res.json(submissions);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.post('/api/submissions/:id/grade', async (req, res) => {
  try {
    const success = await assignmentManager.gradeSubmission(req.params.id, req.body);
    if (!success) {
      return res.status(404).json({ error: 'Submission not found' });
    }
    res.json({ message: 'Submission graded successfully' });
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// ==================== PROGRESS REPORTING ROUTES ====================

app.post('/api/progress-reports', async (req, res) => {
  try {
    const report = await progressReporter.generateProgressReport(
      req.body.studentId,
      req.body.classId,
      req.body.reportType,
      req.body.options
    );
    res.status(201).json(report);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/progress-reports/:id', async (req, res) => {
  try {
    const report = await progressReporter.getProgressReport(req.params.id);
    if (!report) {
      return res.status(404).json({ error: 'Progress report not found' });
    }
    res.json(report);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/students/:studentId/progress-reports', async (req, res) => {
  try {
    const academicYear = req.query.academicYear as string;
    const reports = await progressReporter.getStudentReports(req.params.studentId, academicYear);
    res.json(reports);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.post('/api/progress-reports/:id/send', async (req, res) => {
  try {
    const success = await progressReporter.sendProgressReport(req.params.id, req.body.recipients);
    if (!success) {
      return res.status(400).json({ error: 'Failed to send progress report' });
    }
    res.json({ message: 'Progress report sent successfully' });
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// ==================== COMMUNICATION ROUTES ====================

// Messages
app.post('/api/messages', async (req, res) => {
  try {
    const message = await parentTeacherComm.sendMessage(req.body);
    res.status(201).json(message);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/messages/:id', async (req, res) => {
  try {
    const message = await parentTeacherComm.getMessage(req.params.id);
    if (!message) {
      return res.status(404).json({ error: 'Message not found' });
    }
    res.json(message);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.post('/api/messages/:id/read', async (req, res) => {
  try {
    const success = await parentTeacherComm.markMessageAsRead(req.params.id, req.body.userId);
    if (!success) {
      return res.status(404).json({ error: 'Message not found' });
    }
    res.json({ message: 'Message marked as read' });
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Conversations
app.post('/api/conversations', async (req, res) => {
  try {
    const conversation = await parentTeacherComm.createConversation(req.body);
    res.status(201).json(conversation);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/users/:userId/conversations', async (req, res) => {
  try {
    const userType = req.query.userType as string;
    const conversations = await parentTeacherComm.getUserConversations(req.params.userId, userType);
    res.json(conversations);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Templates
app.post('/api/communication-templates', async (req, res) => {
  try {
    const template = await parentTeacherComm.createTemplate(req.body);
    res.status(201).json(template);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/communication-templates', async (req, res) => {
  try {
    const category = req.query.category as string;
    const createdBy = req.query.createdBy as string;
    const templates = await parentTeacherComm.getTemplates(category, createdBy);
    res.json(templates);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// ==================== CURRICULUM ALIGNMENT ROUTES ====================

// Standards
app.post('/api/standards', async (req, res) => {
  try {
    const standard = await curriculumAlignment.addStandard(req.body);
    res.status(201).json(standard);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/standards', async (req, res) => {
  try {
    const filters = {
      subject: req.query.subject as string,
      gradeLevel: req.query.gradeLevel as string,
      domain: req.query.domain as string,
      source: req.query.source as string,
      keywords: req.query.keywords ? (req.query.keywords as string).split(',') : undefined,
    };
    const standards = await curriculumAlignment.getStandards(filters);
    res.json(standards);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Alignments
app.post('/api/alignments', async (req, res) => {
  try {
    const alignment = await curriculumAlignment.alignItemToStandards(req.body);
    res.status(201).json(alignment);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/items/:itemId/alignments', async (req, res) => {
  try {
    const alignments = await curriculumAlignment.getItemAlignments(req.params.itemId);
    res.json(alignments);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Curriculum Units
app.post('/api/curriculum-units', async (req, res) => {
  try {
    const unit = await curriculumAlignment.createCurriculumUnit(req.body);
    res.status(201).json(unit);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/curriculum-units', async (req, res) => {
  try {
    const subject = req.query.subject as string;
    const gradeLevel = req.query.gradeLevel as string;
    const units = await curriculumAlignment.getUnits(subject, gradeLevel);
    res.json(units);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// ==================== LEARNING OBJECTIVES ROUTES ====================

// Objectives
app.post('/api/learning-objectives', async (req, res) => {
  try {
    const objective = await learningObjectives.createObjective(req.body);
    res.status(201).json(objective);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/learning-objectives/:id', async (req, res) => {
  try {
    const objective = await learningObjectives.getObjective(req.params.id);
    if (!objective) {
      return res.status(404).json({ error: 'Learning objective not found' });
    }
    res.json(objective);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/classes/:classId/learning-objectives', async (req, res) => {
  try {
    const status = req.query.status as string;
    const objectives = await learningObjectives.getClassObjectives(req.params.classId, status);
    res.json(objectives);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Progress tracking
app.post('/api/student-progress', async (req, res) => {
  try {
    const progress = await learningObjectives.recordStudentProgress(req.body);
    res.status(201).json(progress);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/students/:studentId/progress', async (req, res) => {
  try {
    const objectiveId = req.query.objectiveId as string;
    const progress = await learningObjectives.getStudentProgress(req.params.studentId, objectiveId);
    res.json(progress);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Templates
app.post('/api/objective-templates', async (req, res) => {
  try {
    const template = await learningObjectives.createTemplate(req.body);
    res.status(201).json(template);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/objective-templates', async (req, res) => {
  try {
    const filters = {
      subject: req.query.subject as string,
      gradeLevel: req.query.gradeLevel as string,
      bloomsLevel: req.query.bloomsLevel as string,
      tags: req.query.tags ? (req.query.tags as string).split(',') : undefined,
    };
    const templates = await learningObjectives.getTemplates(filters);
    res.json(templates);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// ==================== IEP SUPPORT ROUTES ====================

// IEPs
app.post('/api/ieps', async (req, res) => {
  try {
    const iep = await iepSupport.createIEP(req.body);
    res.status(201).json(iep);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/ieps/:id', async (req, res) => {
  try {
    const iep = await iepSupport.getIEP(req.params.id);
    if (!iep) {
      return res.status(404).json({ error: 'IEP not found' });
    }
    res.json(iep);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/students/:studentId/ieps', async (req, res) => {
  try {
    const ieps = await iepSupport.getStudentIEPs(req.params.studentId);
    res.json(ieps);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/students/:studentId/current-iep', async (req, res) => {
  try {
    const iep = await iepSupport.getCurrentIEP(req.params.studentId);
    if (!iep) {
      return res.status(404).json({ error: 'No current IEP found' });
    }
    res.json(iep);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// IEP Goals
app.post('/api/ieps/:iepId/goals', async (req, res) => {
  try {
    const goal = await iepSupport.addGoal(req.params.iepId, req.body);
    if (!goal) {
      return res.status(404).json({ error: 'IEP not found' });
    }
    res.status(201).json(goal);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.post('/api/ieps/:iepId/goals/:goalId/progress', async (req, res) => {
  try {
    const progress = await iepSupport.recordGoalProgress(req.params.iepId, req.params.goalId, req.body);
    if (!progress) {
      return res.status(404).json({ error: 'IEP or goal not found' });
    }
    res.status(201).json(progress);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// IEP Meetings
app.post('/api/iep-meetings', async (req, res) => {
  try {
    const meeting = await iepSupport.scheduleMeeting(req.body);
    res.status(201).json(meeting);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/ieps/:iepId/meetings', async (req, res) => {
  try {
    const meetings = await iepSupport.getMeetings(req.params.iepId);
    res.json(meetings);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Compliance
app.post('/api/ieps/:iepId/compliance-check', async (req, res) => {
  try {
    const check = await iepSupport.runComplianceCheck(
      req.params.iepId,
      req.body.checkType,
      req.body.checkedBy
    );
    res.status(201).json(check);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// ==================== HOMEWORK HELP ROUTES ====================

// Homework Assignments
app.post('/api/homework-assignments', async (req, res) => {
  try {
    const assignment = await homeworkHelp.createHomeworkAssignment(req.body);
    res.status(201).json(assignment);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Help Sessions
app.post('/api/help-sessions', async (req, res) => {
  try {
    const session = await homeworkHelp.startHelpSession(req.body.studentId, req.body.assignmentId);
    res.status(201).json(session);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.post('/api/help-sessions/:sessionId/end', async (req, res) => {
  try {
    const session = await homeworkHelp.endHelpSession(req.params.sessionId);
    if (!session) {
      return res.status(404).json({ error: 'Session not found' });
    }
    res.json(session);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.post('/api/help-sessions/:sessionId/help-request', async (req, res) => {
  try {
    const request = await homeworkHelp.submitHelpRequest(req.params.sessionId, req.body);
    res.status(201).json(request);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/students/:studentId/help-sessions', async (req, res) => {
  try {
    const sessions = await homeworkHelp.getStudentSessions(req.params.studentId);
    res.json(sessions);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Study Groups
app.post('/api/study-groups', async (req, res) => {
  try {
    const group = await homeworkHelp.createStudyGroup(req.body);
    res.status(201).json(group);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.post('/api/study-groups/:groupId/join', async (req, res) => {
  try {
    const success = await homeworkHelp.joinStudyGroup(req.params.groupId, req.body.studentId);
    if (!success) {
      return res.status(400).json({ error: 'Unable to join study group' });
    }
    res.json({ message: 'Successfully joined study group' });
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/assignments/:assignmentId/study-groups', async (req, res) => {
  try {
    const groups = await homeworkHelp.getAvailableStudyGroups(req.params.assignmentId);
    res.json(groups);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Analytics
app.get('/api/assignments/:assignmentId/analytics', async (req, res) => {
  try {
    const analytics = await homeworkHelp.generateAnalytics(req.params.assignmentId);
    res.json(analytics);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// ==================== VIRTUAL CONFERENCES ROUTES ====================

// Conferences
app.post('/api/conferences', async (req, res) => {
  try {
    const conference = await virtualConferences.scheduleConference(req.body);
    res.status(201).json(conference);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/conferences/:id', async (req, res) => {
  try {
    const conference = await virtualConferences.getConference(req.params.id);
    if (!conference) {
      return res.status(404).json({ error: 'Conference not found' });
    }
    res.json(conference);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.put('/api/conferences/:id', async (req, res) => {
  try {
    const conference = await virtualConferences.updateConference(req.params.id, req.body);
    if (!conference) {
      return res.status(404).json({ error: 'Conference not found' });
    }
    res.json(conference);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.post('/api/conferences/:id/start', async (req, res) => {
  try {
    const conference = await virtualConferences.startConference(req.params.id, req.body.hostId);
    if (!conference) {
      return res.status(404).json({ error: 'Conference not found or cannot be started' });
    }
    res.json(conference);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.post('/api/conferences/:id/end', async (req, res) => {
  try {
    const conference = await virtualConferences.endConference(req.params.id, req.body.hostId);
    if (!conference) {
      return res.status(404).json({ error: 'Conference not found or cannot be ended' });
    }
    res.json(conference);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.post('/api/conferences/:id/join', async (req, res) => {
  try {
    const result = await virtualConferences.joinConference(req.params.id, req.body.participantId, req.body.deviceInfo);
    if (!result.success) {
      return res.status(400).json({ error: result.error });
    }
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/users/:userId/upcoming-conferences', async (req, res) => {
  try {
    const days = parseInt(req.query.days as string) || 7;
    const conferences = await virtualConferences.getUpcomingConferences(req.params.userId, days);
    res.json(conferences);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Conference Templates
app.post('/api/conference-templates', async (req, res) => {
  try {
    const template = await virtualConferences.createTemplate(req.body);
    res.status(201).json(template);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/conference-templates', async (req, res) => {
  try {
    const type = req.query.type as any;
    const templates = await virtualConferences.getTemplates(type);
    res.json(templates);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Conference Analytics
app.get('/api/conference-analytics', async (req, res) => {
  try {
    const teacherId = req.query.teacherId as string;
    const timeframe = req.query.start && req.query.end ? {
      start: new Date(req.query.start as string),
      end: new Date(req.query.end as string)
    } : undefined;
    
    const analytics = await virtualConferences.generateAnalytics(teacherId, timeframe);
    res.json(analytics);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// ==================== RESOURCE LIBRARY ROUTES ====================

// Resources
app.post('/api/resources', async (req, res) => {
  try {
    const resource = await resourceLibrary.addResource(req.body);
    res.status(201).json(resource);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/resources/:id', async (req, res) => {
  try {
    const resource = await resourceLibrary.getResource(req.params.id);
    if (!resource) {
      return res.status(404).json({ error: 'Resource not found' });
    }
    res.json(resource);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.put('/api/resources/:id', async (req, res) => {
  try {
    const resource = await resourceLibrary.updateResource(req.params.id, req.body);
    if (!resource) {
      return res.status(404).json({ error: 'Resource not found' });
    }
    res.json(resource);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.delete('/api/resources/:id', async (req, res) => {
  try {
    const success = await resourceLibrary.deleteResource(req.params.id);
    if (!success) {
      return res.status(404).json({ error: 'Resource not found' });
    }
    res.json({ message: 'Resource deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Search
app.get('/api/resources/search', async (req, res) => {
  try {
    const query = req.query.q as string || '';
    const filters = {
      subjects: req.query.subjects ? (req.query.subjects as string).split(',') : undefined,
      gradeLevel: req.query.gradeLevel ? (req.query.gradeLevel as string).split(',') : undefined,
      resourceType: req.query.type ? (req.query.type as string).split(',') : undefined,
      difficulty: req.query.difficulty ? (req.query.difficulty as string).split(',').map(Number) : undefined,
      rating: req.query.rating ? Number(req.query.rating) : undefined,
      isPremium: req.query.premium ? req.query.premium === 'true' : undefined,
      hasAccessibility: req.query.accessibility === 'true' ? true : undefined,
    };
    const sortBy = req.query.sort as any || 'relevance';
    const limit = parseInt(req.query.limit as string) || 20;
    const offset = parseInt(req.query.offset as string) || 0;

    const results = await resourceLibrary.searchResources(query, filters, sortBy, limit, offset);
    res.json(results);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Reviews
app.post('/api/resources/:id/reviews', async (req, res) => {
  try {
    const review = await resourceLibrary.addReview(req.params.id, req.body);
    if (!review) {
      return res.status(404).json({ error: 'Resource not found' });
    }
    res.status(201).json(review);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Bookmarks
app.post('/api/resources/:id/bookmark', async (req, res) => {
  try {
    const success = await resourceLibrary.addToBookmarks(req.params.id, req.body.userId);
    if (!success) {
      return res.status(404).json({ error: 'Resource not found' });
    }
    res.json({ message: 'Resource bookmarked successfully' });
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Downloads
app.post('/api/resources/:id/download', async (req, res) => {
  try {
    const result = await resourceLibrary.downloadResource(req.params.id, req.body.userId);
    if (!result.success) {
      return res.status(400).json({ error: result.error });
    }
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Collections
app.post('/api/resource-collections', async (req, res) => {
  try {
    const collection = await resourceLibrary.createCollection(req.body);
    res.status(201).json(collection);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/resource-collections/:id', async (req, res) => {
  try {
    const collection = await resourceLibrary.getCollection(req.params.id);
    if (!collection) {
      return res.status(404).json({ error: 'Collection not found' });
    }
    res.json(collection);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/resource-collections/:id/resources', async (req, res) => {
  try {
    const resources = await resourceLibrary.getCollectionResources(req.params.id);
    res.json(resources);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Recommendations
app.get('/api/users/:userId/recommendations', async (req, res) => {
  try {
    const limit = parseInt(req.query.limit as string) || 10;
    const recommendations = await resourceLibrary.generateRecommendations(req.params.userId, limit);
    res.json(recommendations);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// User Preferences
app.post('/api/users/:userId/preferences', async (req, res) => {
  try {
    const preferences = await resourceLibrary.setUserPreferences(req.params.userId, req.body);
    res.json(preferences);
  } catch (error) {
    res.status(400).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/users/:userId/preferences', async (req, res) => {
  try {
    const preferences = await resourceLibrary.getUserPreferences(req.params.userId);
    if (!preferences) {
      return res.status(404).json({ error: 'User preferences not found' });
    }
    res.json(preferences);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// Popular and Recent Resources
app.get('/api/resources/popular', async (req, res) => {
  try {
    const subject = req.query.subject as string;
    const gradeLevel = req.query.gradeLevel as string;
    const limit = parseInt(req.query.limit as string) || 10;
    const resources = await resourceLibrary.getPopularResources(subject, gradeLevel, limit);
    res.json(resources);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

app.get('/api/resources/recent', async (req, res) => {
  try {
    const limit = parseInt(req.query.limit as string) || 10;
    const resources = await resourceLibrary.getRecentResources(limit);
    res.json(resources);
  } catch (error) {
    res.status(500).json({ error: error instanceof Error ? error.message : 'Unknown error' });
  }
});

// ==================== WEBSOCKET EVENTS ====================

io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  // Class management events
  socket.on('join-class', (classId: string) => {
    socket.join(`class-${classId}`);
  });

  socket.on('leave-class', (classId: string) => {
    socket.leave(`class-${classId}`);
  });

  // Assignment events
  socket.on('join-assignment', (assignmentId: string) => {
    socket.join(`assignment-${assignmentId}`);
  });

  // Conference events
  socket.on('join-conference', (conferenceId: string) => {
    socket.join(`conference-${conferenceId}`);
  });

  socket.on('leave-conference', (conferenceId: string) => {
    socket.leave(`conference-${conferenceId}`);
  });

  // Help session events
  socket.on('join-help-session', (sessionId: string) => {
    socket.join(`help-session-${sessionId}`);
  });

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
  });
});

// Setup event listeners for real-time updates
classManager.on('studentEnrolled', (data) => {
  io.to(`class-${data.classId}`).emit('student-enrolled', data);
});

classManager.on('attendanceRecorded', (record) => {
  io.to(`class-${record.classId}`).emit('attendance-updated', record);
});

assignmentManager.on('assignmentPublished', (assignment) => {
  io.to(`class-${assignment.classId}`).emit('assignment-published', assignment);
});

assignmentManager.on('submissionCreated', (submission) => {
  io.to(`assignment-${submission.assignmentId}`).emit('submission-received', submission);
});

parentTeacherComm.on('messageSent', (message) => {
  message.recipientIds.forEach(recipientId => {
    io.to(`user-${recipientId}`).emit('new-message', message);
  });
});

virtualConferences.on('conferenceStarted', (data) => {
  io.to(`conference-${data.conference.id}`).emit('conference-started', data);
});

virtualConferences.on('participantJoined', (data) => {
  io.to(`conference-${data.conferenceId}`).emit('participant-joined', data);
});

homeworkHelp.on('interventionTriggered', (data) => {
  io.to(`help-session-${data.sessionId}`).emit('intervention-triggered', data);
});

homeworkHelp.on('teacherNotified', (data) => {
  io.to(`teacher-${data.notification.type}`).emit('teacher-notification', data);
});

// Error handling middleware
app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('Error:', err);
  res.status(500).json({ 
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong'
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

// Start server
const PORT = process.env.PORT || 8215;

server.listen(PORT, () => {
  console.log(`🚀 Educator Portal Server is running on port ${PORT}`);
  console.log(`📚 Class Management: http://localhost:${PORT}/api/classes`);
  console.log(`📝 Assignment Management: http://localhost:${PORT}/api/assignments`);
  console.log(`📊 Progress Reports: http://localhost:${PORT}/api/progress-reports`);
  console.log(`💬 Communication: http://localhost:${PORT}/api/messages`);
  console.log(`🎯 Curriculum Alignment: http://localhost:${PORT}/api/standards`);
  console.log(`🎓 Learning Objectives: http://localhost:${PORT}/api/learning-objectives`);
  console.log(`🏥 IEP Support: http://localhost:${PORT}/api/ieps`);
  console.log(`📚 Homework Help: http://localhost:${PORT}/api/homework-assignments`);
  console.log(`📹 Virtual Conferences: http://localhost:${PORT}/api/conferences`);
  console.log(`📁 Resource Library: http://localhost:${PORT}/api/resources`);
  console.log(`🔍 Resource Search: http://localhost:${PORT}/api/resources/search`);
  console.log(`💡 Health Check: http://localhost:${PORT}/health`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  server.close(() => {
    console.log('Process terminated');
  });
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down gracefully');
  server.close(() => {
    console.log('Process terminated');
  });
});

export default app;