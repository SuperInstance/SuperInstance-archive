import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';

export interface Assignment {
  id: string;
  title: string;
  description: string;
  classId: string;
  teacherId: string;
  type: 'homework' | 'quiz' | 'test' | 'project' | 'essay' | 'presentation' | 'lab';
  subject: string;
  instructions: string;
  attachments: AssignmentAttachment[];
  dueDate: Date;
  assignedDate: Date;
  totalPoints: number;
  rubric?: Rubric;
  learningObjectives: string[];
  standardsAlignment: string[];
  estimatedTime: number;
  difficultyLevel: 1 | 2 | 3 | 4 | 5;
  allowLateSubmission: boolean;
  lateSubmissionPenalty: number;
  groupAssignment: boolean;
  maxGroupSize?: number;
  requiresPeerReview: boolean;
  status: 'draft' | 'published' | 'archived';
  visibility: 'all' | 'selected';
  selectedStudents?: string[];
  createdDate: Date;
  lastModified: Date;
}

export interface AssignmentAttachment {
  id: string;
  name: string;
  type: 'document' | 'image' | 'video' | 'audio' | 'link' | 'file';
  url: string;
  size?: number;
  description?: string;
}

export interface Submission {
  id: string;
  assignmentId: string;
  studentId: string;
  groupId?: string;
  content: string;
  attachments: SubmissionAttachment[];
  submittedDate: Date;
  isLate: boolean;
  attempt: number;
  status: 'submitted' | 'graded' | 'returned' | 'resubmitted';
  grade?: Grade;
  feedback?: string;
  rubricScores?: RubricScore[];
  plagiarismCheck?: PlagiarismResult;
  timeSpent?: number;
  lastSaved?: Date;
}

export interface SubmissionAttachment {
  id: string;
  name: string;
  type: 'document' | 'image' | 'video' | 'audio' | 'file';
  url: string;
  size: number;
}

export interface Grade {
  points: number;
  percentage: number;
  letterGrade: string;
  gradedDate: Date;
  gradedBy: string;
  comments: string;
  breakdown?: GradeBreakdown[];
}

export interface GradeBreakdown {
  criteria: string;
  points: number;
  maxPoints: number;
  comments?: string;
}

export interface Rubric {
  id: string;
  name: string;
  criteria: RubricCriterion[];
  totalPoints: number;
}

export interface RubricCriterion {
  id: string;
  name: string;
  description: string;
  levels: RubricLevel[];
  weight: number;
}

export interface RubricLevel {
  id: string;
  name: string;
  description: string;
  points: number;
}

export interface RubricScore {
  criterionId: string;
  levelId: string;
  points: number;
  comments?: string;
}

export interface PlagiarismResult {
  similarity: number;
  sources: string[];
  flagged: boolean;
  checkedDate: Date;
  service: string;
}

export interface AssignmentTemplate {
  id: string;
  name: string;
  description: string;
  type: string;
  subject: string;
  gradeLevel: string;
  template: Partial<Assignment>;
  isPublic: boolean;
  createdBy: string;
  tags: string[];
}

export interface BatchOperation {
  id: string;
  type: 'grade' | 'feedback' | 'return' | 'extend';
  assignmentId: string;
  submissions: string[];
  data: any;
  processedCount: number;
  totalCount: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  createdDate: Date;
  completedDate?: Date;
  errors?: string[];
}

export class AssignmentManager extends EventEmitter {
  private assignments: Map<string, Assignment> = new Map();
  private submissions: Map<string, Submission[]> = new Map();
  private templates: Map<string, AssignmentTemplate> = new Map();
  private batchOperations: Map<string, BatchOperation> = new Map();

  constructor() {
    super();
  }

  public async createAssignment(assignmentData: Omit<Assignment, 'id' | 'createdDate' | 'lastModified'>): Promise<Assignment> {
    const assignment: Assignment = {
      ...assignmentData,
      id: uuidv4(),
      createdDate: new Date(),
      lastModified: new Date(),
    };

    this.assignments.set(assignment.id, assignment);
    this.submissions.set(assignment.id, []);
    this.emit('assignmentCreated', assignment);
    return assignment;
  }

  public async updateAssignment(assignmentId: string, updates: Partial<Assignment>): Promise<Assignment | null> {
    const existing = this.assignments.get(assignmentId);
    if (!existing) return null;

    const updated = { 
      ...existing, 
      ...updates, 
      lastModified: new Date() 
    };
    
    this.assignments.set(assignmentId, updated);
    this.emit('assignmentUpdated', updated);
    return updated;
  }

  public async deleteAssignment(assignmentId: string): Promise<boolean> {
    const removed = this.assignments.delete(assignmentId);
    if (removed) {
      this.submissions.delete(assignmentId);
      this.emit('assignmentDeleted', assignmentId);
    }
    return removed;
  }

  public async getAssignment(assignmentId: string): Promise<Assignment | null> {
    return this.assignments.get(assignmentId) || null;
  }

  public async getClassAssignments(classId: string): Promise<Assignment[]> {
    return Array.from(this.assignments.values()).filter(
      assignment => assignment.classId === classId
    );
  }

  public async getTeacherAssignments(teacherId: string): Promise<Assignment[]> {
    return Array.from(this.assignments.values()).filter(
      assignment => assignment.teacherId === teacherId
    );
  }

  public async publishAssignment(assignmentId: string): Promise<boolean> {
    const assignment = this.assignments.get(assignmentId);
    if (!assignment) return false;

    assignment.status = 'published';
    assignment.lastModified = new Date();
    
    this.assignments.set(assignmentId, assignment);
    this.emit('assignmentPublished', assignment);
    return true;
  }

  public async distributeAssignment(assignmentId: string, distribution: {
    method: 'email' | 'platform' | 'both';
    includeParents?: boolean;
    customMessage?: string;
  }): Promise<boolean> {
    const assignment = this.assignments.get(assignmentId);
    if (!assignment || assignment.status !== 'published') return false;

    this.emit('assignmentDistributed', { assignment, distribution });
    return true;
  }

  public async createSubmission(submissionData: Omit<Submission, 'id' | 'submittedDate' | 'attempt' | 'status'>): Promise<Submission> {
    const assignmentSubmissions = this.submissions.get(submissionData.assignmentId) || [];
    const existingSubmissions = assignmentSubmissions.filter(s => s.studentId === submissionData.studentId);
    
    const submission: Submission = {
      ...submissionData,
      id: uuidv4(),
      submittedDate: new Date(),
      attempt: existingSubmissions.length + 1,
      status: 'submitted',
      isLate: await this.checkIfLate(submissionData.assignmentId),
    };

    assignmentSubmissions.push(submission);
    this.submissions.set(submissionData.assignmentId, assignmentSubmissions);
    
    this.emit('submissionCreated', submission);
    return submission;
  }

  public async updateSubmission(submissionId: string, updates: Partial<Submission>): Promise<Submission | null> {
    for (const [assignmentId, submissions] of this.submissions.entries()) {
      const index = submissions.findIndex(s => s.id === submissionId);
      if (index !== -1) {
        const updated = { ...submissions[index], ...updates };
        submissions[index] = updated;
        this.submissions.set(assignmentId, submissions);
        this.emit('submissionUpdated', updated);
        return updated;
      }
    }
    return null;
  }

  public async getSubmission(submissionId: string): Promise<Submission | null> {
    for (const submissions of this.submissions.values()) {
      const submission = submissions.find(s => s.id === submissionId);
      if (submission) return submission;
    }
    return null;
  }

  public async getAssignmentSubmissions(assignmentId: string): Promise<Submission[]> {
    return this.submissions.get(assignmentId) || [];
  }

  public async getStudentSubmissions(studentId: string): Promise<Submission[]> {
    const allSubmissions: Submission[] = [];
    for (const submissions of this.submissions.values()) {
      allSubmissions.push(...submissions.filter(s => s.studentId === studentId));
    }
    return allSubmissions;
  }

  public async gradeSubmission(submissionId: string, grade: Grade): Promise<boolean> {
    const submission = await this.getSubmission(submissionId);
    if (!submission) return false;

    submission.grade = grade;
    submission.status = 'graded';
    
    await this.updateSubmission(submissionId, submission);
    this.emit('submissionGraded', { submission, grade });
    return true;
  }

  public async provideFeedback(submissionId: string, feedback: string): Promise<boolean> {
    const submission = await this.getSubmission(submissionId);
    if (!submission) return false;

    submission.feedback = feedback;
    
    await this.updateSubmission(submissionId, submission);
    this.emit('feedbackProvided', { submissionId, feedback });
    return true;
  }

  public async returnSubmission(submissionId: string): Promise<boolean> {
    const submission = await this.getSubmission(submissionId);
    if (!submission || submission.status !== 'graded') return false;

    submission.status = 'returned';
    
    await this.updateSubmission(submissionId, submission);
    this.emit('submissionReturned', submission);
    return true;
  }

  public async createTemplate(template: Omit<AssignmentTemplate, 'id'>): Promise<AssignmentTemplate> {
    const assignmentTemplate: AssignmentTemplate = {
      ...template,
      id: uuidv4(),
    };

    this.templates.set(assignmentTemplate.id, assignmentTemplate);
    this.emit('templateCreated', assignmentTemplate);
    return assignmentTemplate;
  }

  public async getTemplates(teacherId?: string, subject?: string, gradeLevel?: string): Promise<AssignmentTemplate[]> {
    let templates = Array.from(this.templates.values());

    if (teacherId) {
      templates = templates.filter(t => t.createdBy === teacherId || t.isPublic);
    }
    if (subject) {
      templates = templates.filter(t => t.subject === subject);
    }
    if (gradeLevel) {
      templates = templates.filter(t => t.gradeLevel === gradeLevel);
    }

    return templates;
  }

  public async createFromTemplate(templateId: string, overrides: Partial<Assignment>): Promise<Assignment | null> {
    const template = this.templates.get(templateId);
    if (!template) return null;

    const assignmentData = {
      ...template.template,
      ...overrides,
    } as Omit<Assignment, 'id' | 'createdDate' | 'lastModified'>;

    return await this.createAssignment(assignmentData);
  }

  public async startBatchOperation(operation: Omit<BatchOperation, 'id' | 'processedCount' | 'status' | 'createdDate'>): Promise<BatchOperation> {
    const batchOp: BatchOperation = {
      ...operation,
      id: uuidv4(),
      processedCount: 0,
      status: 'pending',
      createdDate: new Date(),
    };

    this.batchOperations.set(batchOp.id, batchOp);
    this.processBatchOperation(batchOp.id);
    return batchOp;
  }

  private async processBatchOperation(operationId: string): Promise<void> {
    const operation = this.batchOperations.get(operationId);
    if (!operation) return;

    operation.status = 'processing';
    this.emit('batchOperationStarted', operation);

    try {
      for (const submissionId of operation.submissions) {
        switch (operation.type) {
          case 'grade':
            await this.gradeSubmission(submissionId, operation.data);
            break;
          case 'feedback':
            await this.provideFeedback(submissionId, operation.data);
            break;
          case 'return':
            await this.returnSubmission(submissionId);
            break;
        }
        operation.processedCount++;
        this.emit('batchOperationProgress', operation);
      }

      operation.status = 'completed';
      operation.completedDate = new Date();
      this.emit('batchOperationCompleted', operation);

    } catch (error) {
      operation.status = 'failed';
      operation.errors = operation.errors || [];
      operation.errors.push(error instanceof Error ? error.message : 'Unknown error');
      this.emit('batchOperationFailed', operation);
    }

    this.batchOperations.set(operationId, operation);
  }

  public async getBatchOperation(operationId: string): Promise<BatchOperation | null> {
    return this.batchOperations.get(operationId) || null;
  }

  private async checkIfLate(assignmentId: string): Promise<boolean> {
    const assignment = this.assignments.get(assignmentId);
    if (!assignment) return false;
    return new Date() > assignment.dueDate;
  }

  public async getAssignmentAnalytics(assignmentId: string): Promise<any> {
    const assignment = this.assignments.get(assignmentId);
    const submissions = this.submissions.get(assignmentId) || [];

    if (!assignment) return null;

    const gradedSubmissions = submissions.filter(s => s.grade);
    const avgScore = gradedSubmissions.length > 0 
      ? gradedSubmissions.reduce((sum, s) => sum + (s.grade?.points || 0), 0) / gradedSubmissions.length
      : 0;

    return {
      assignment: {
        title: assignment.title,
        totalPoints: assignment.totalPoints,
        dueDate: assignment.dueDate,
      },
      submissions: {
        total: submissions.length,
        submitted: submissions.filter(s => s.status !== 'draft').length,
        graded: gradedSubmissions.length,
        late: submissions.filter(s => s.isLate).length,
      },
      grades: {
        average: avgScore,
        averagePercentage: (avgScore / assignment.totalPoints) * 100,
        distribution: this.calculateGradeDistribution(gradedSubmissions),
      },
      timeSpent: {
        average: submissions.reduce((sum, s) => sum + (s.timeSpent || 0), 0) / submissions.length,
      },
    };
  }

  private calculateGradeDistribution(submissions: Submission[]): any {
    const distribution = { A: 0, B: 0, C: 0, D: 0, F: 0 };
    
    submissions.forEach(submission => {
      if (submission.grade) {
        const letter = submission.grade.letterGrade;
        if (letter in distribution) {
          distribution[letter as keyof typeof distribution]++;
        }
      }
    });

    return distribution;
  }

  public async exportGrades(assignmentId: string, format: 'csv' | 'excel' | 'json'): Promise<any> {
    const assignment = this.assignments.get(assignmentId);
    const submissions = this.submissions.get(assignmentId) || [];

    if (!assignment) return null;

    const data = submissions.map(submission => ({
      studentId: submission.studentId,
      submittedDate: submission.submittedDate,
      grade: submission.grade?.points || '',
      percentage: submission.grade?.percentage || '',
      letterGrade: submission.grade?.letterGrade || '',
      isLate: submission.isLate,
      attempt: submission.attempt,
      feedback: submission.feedback || '',
    }));

    return {
      assignment: assignment.title,
      exportDate: new Date(),
      format,
      data,
    };
  }
}