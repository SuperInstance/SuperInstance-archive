import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';

export interface Student {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  grade: string;
  dateOfBirth: Date;
  parentEmails: string[];
  emergencyContacts: EmergencyContact[];
  allergies: string[];
  medicalConditions: string[];
  learningAccommodations: string[];
  iepStatus: boolean;
  enrollmentDate: Date;
  status: 'active' | 'inactive' | 'transferred';
  profilePicture?: string;
  studentId: string;
}

export interface EmergencyContact {
  name: string;
  relationship: string;
  phone: string;
  email?: string;
  isPrimary: boolean;
}

export interface ClassRoom {
  id: string;
  name: string;
  subject: string;
  grade: string;
  academicYear: string;
  semester: string;
  teacherId: string;
  coTeachers: string[];
  students: Student[];
  capacity: number;
  room: string;
  schedule: ClassSchedule[];
  description: string;
  syllabus?: string;
  createdDate: Date;
  status: 'active' | 'archived' | 'draft';
}

export interface ClassSchedule {
  dayOfWeek: number;
  startTime: string;
  endTime: string;
  location: string;
}

export interface AttendanceRecord {
  id: string;
  classId: string;
  studentId: string;
  date: Date;
  status: 'present' | 'absent' | 'late' | 'excused';
  notes?: string;
  recordedBy: string;
  recordedAt: Date;
}

export interface SeatingChart {
  id: string;
  classId: string;
  name: string;
  layout: SeatingPosition[];
  isActive: boolean;
  createdDate: Date;
}

export interface SeatingPosition {
  row: number;
  column: number;
  studentId?: string;
  isAccessible: boolean;
  notes?: string;
}

export interface BehaviorNote {
  id: string;
  studentId: string;
  classId: string;
  date: Date;
  type: 'positive' | 'negative' | 'neutral';
  category: string;
  description: string;
  actionTaken?: string;
  parentNotified: boolean;
  teacherId: string;
  severity: 1 | 2 | 3 | 4 | 5;
}

export class ClassManager extends EventEmitter {
  private classes: Map<string, ClassRoom> = new Map();
  private students: Map<string, Student> = new Map();
  private attendance: Map<string, AttendanceRecord[]> = new Map();
  private seatingCharts: Map<string, SeatingChart[]> = new Map();
  private behaviorNotes: Map<string, BehaviorNote[]> = new Map();

  constructor() {
    super();
  }

  public async createClass(classData: Omit<ClassRoom, 'id' | 'createdDate' | 'students'>): Promise<ClassRoom> {
    const classRoom: ClassRoom = {
      ...classData,
      id: uuidv4(),
      students: [],
      createdDate: new Date(),
    };

    this.classes.set(classRoom.id, classRoom);
    this.emit('classCreated', classRoom);
    return classRoom;
  }

  public async updateClass(classId: string, updates: Partial<ClassRoom>): Promise<ClassRoom | null> {
    const existingClass = this.classes.get(classId);
    if (!existingClass) return null;

    const updatedClass = { ...existingClass, ...updates };
    this.classes.set(classId, updatedClass);
    this.emit('classUpdated', updatedClass);
    return updatedClass;
  }

  public async addClass(classRoom: ClassRoom): Promise<void> {
    this.classes.set(classRoom.id, classRoom);
    this.emit('classAdded', classRoom);
  }

  public async removeClass(classId: string): Promise<boolean> {
    const removed = this.classes.delete(classId);
    if (removed) {
      this.emit('classRemoved', classId);
    }
    return removed;
  }

  public async getClass(classId: string): Promise<ClassRoom | null> {
    return this.classes.get(classId) || null;
  }

  public async getClassesByTeacher(teacherId: string): Promise<ClassRoom[]> {
    return Array.from(this.classes.values()).filter(
      cls => cls.teacherId === teacherId || cls.coTeachers.includes(teacherId)
    );
  }

  public async getAllClasses(): Promise<ClassRoom[]> {
    return Array.from(this.classes.values());
  }

  public async addStudent(student: Student): Promise<void> {
    this.students.set(student.id, student);
    this.emit('studentAdded', student);
  }

  public async updateStudent(studentId: string, updates: Partial<Student>): Promise<Student | null> {
    const existingStudent = this.students.get(studentId);
    if (!existingStudent) return null;

    const updatedStudent = { ...existingStudent, ...updates };
    this.students.set(studentId, updatedStudent);
    this.emit('studentUpdated', updatedStudent);
    return updatedStudent;
  }

  public async enrollStudent(classId: string, studentId: string): Promise<boolean> {
    const classRoom = this.classes.get(classId);
    const student = this.students.get(studentId);

    if (!classRoom || !student) return false;
    if (classRoom.students.find(s => s.id === studentId)) return false;
    if (classRoom.students.length >= classRoom.capacity) return false;

    classRoom.students.push(student);
    this.classes.set(classId, classRoom);
    this.emit('studentEnrolled', { classId, studentId });
    return true;
  }

  public async unenrollStudent(classId: string, studentId: string): Promise<boolean> {
    const classRoom = this.classes.get(classId);
    if (!classRoom) return false;

    const studentIndex = classRoom.students.findIndex(s => s.id === studentId);
    if (studentIndex === -1) return false;

    classRoom.students.splice(studentIndex, 1);
    this.classes.set(classId, classRoom);
    this.emit('studentUnenrolled', { classId, studentId });
    return true;
  }

  public async getStudent(studentId: string): Promise<Student | null> {
    return this.students.get(studentId) || null;
  }

  public async getClassStudents(classId: string): Promise<Student[]> {
    const classRoom = this.classes.get(classId);
    return classRoom?.students || [];
  }

  public async recordAttendance(attendance: Omit<AttendanceRecord, 'id' | 'recordedAt'>): Promise<AttendanceRecord> {
    const record: AttendanceRecord = {
      ...attendance,
      id: uuidv4(),
      recordedAt: new Date(),
    };

    const classAttendance = this.attendance.get(attendance.classId) || [];
    classAttendance.push(record);
    this.attendance.set(attendance.classId, classAttendance);
    
    this.emit('attendanceRecorded', record);
    return record;
  }

  public async getAttendance(classId: string, date?: Date): Promise<AttendanceRecord[]> {
    const classAttendance = this.attendance.get(classId) || [];
    
    if (date) {
      const targetDate = new Date(date);
      return classAttendance.filter(record => 
        record.date.toDateString() === targetDate.toDateString()
      );
    }
    
    return classAttendance;
  }

  public async getStudentAttendance(studentId: string, startDate?: Date, endDate?: Date): Promise<AttendanceRecord[]> {
    let allAttendance: AttendanceRecord[] = [];
    
    for (const classAttendance of this.attendance.values()) {
      allAttendance = allAttendance.concat(classAttendance.filter(record => record.studentId === studentId));
    }

    if (startDate && endDate) {
      return allAttendance.filter(record => 
        record.date >= startDate && record.date <= endDate
      );
    }

    return allAttendance;
  }

  public async createSeatingChart(seatingChart: Omit<SeatingChart, 'id' | 'createdDate'>): Promise<SeatingChart> {
    const chart: SeatingChart = {
      ...seatingChart,
      id: uuidv4(),
      createdDate: new Date(),
    };

    const classCharts = this.seatingCharts.get(seatingChart.classId) || [];
    
    if (chart.isActive) {
      classCharts.forEach(c => c.isActive = false);
    }
    
    classCharts.push(chart);
    this.seatingCharts.set(seatingChart.classId, classCharts);
    
    this.emit('seatingChartCreated', chart);
    return chart;
  }

  public async getSeatingCharts(classId: string): Promise<SeatingChart[]> {
    return this.seatingCharts.get(classId) || [];
  }

  public async getActiveSeatingChart(classId: string): Promise<SeatingChart | null> {
    const charts = this.seatingCharts.get(classId) || [];
    return charts.find(chart => chart.isActive) || null;
  }

  public async updateSeatingChart(chartId: string, updates: Partial<SeatingChart>): Promise<SeatingChart | null> {
    for (const [classId, charts] of this.seatingCharts.entries()) {
      const chartIndex = charts.findIndex(c => c.id === chartId);
      if (chartIndex !== -1) {
        const updatedChart = { ...charts[chartIndex], ...updates };
        charts[chartIndex] = updatedChart;
        this.seatingCharts.set(classId, charts);
        this.emit('seatingChartUpdated', updatedChart);
        return updatedChart;
      }
    }
    return null;
  }

  public async addBehaviorNote(note: Omit<BehaviorNote, 'id'>): Promise<BehaviorNote> {
    const behaviorNote: BehaviorNote = {
      ...note,
      id: uuidv4(),
    };

    const studentNotes = this.behaviorNotes.get(note.studentId) || [];
    studentNotes.push(behaviorNote);
    this.behaviorNotes.set(note.studentId, studentNotes);
    
    this.emit('behaviorNoteAdded', behaviorNote);
    return behaviorNote;
  }

  public async getBehaviorNotes(studentId: string, startDate?: Date, endDate?: Date): Promise<BehaviorNote[]> {
    const notes = this.behaviorNotes.get(studentId) || [];
    
    if (startDate && endDate) {
      return notes.filter(note => 
        note.date >= startDate && note.date <= endDate
      );
    }
    
    return notes;
  }

  public async getClassBehaviorNotes(classId: string, startDate?: Date, endDate?: Date): Promise<BehaviorNote[]> {
    let allNotes: BehaviorNote[] = [];
    
    for (const notes of this.behaviorNotes.values()) {
      allNotes = allNotes.concat(notes.filter(note => note.classId === classId));
    }

    if (startDate && endDate) {
      return allNotes.filter(note => 
        note.date >= startDate && note.date <= endDate
      );
    }

    return allNotes;
  }

  public async generateClassRoster(classId: string): Promise<any> {
    const classRoom = this.classes.get(classId);
    if (!classRoom) return null;

    return {
      class: {
        name: classRoom.name,
        subject: classRoom.subject,
        grade: classRoom.grade,
        teacher: classRoom.teacherId,
        room: classRoom.room,
      },
      students: classRoom.students.map(student => ({
        name: `${student.firstName} ${student.lastName}`,
        studentId: student.studentId,
        email: student.email,
        parentEmails: student.parentEmails,
        iepStatus: student.iepStatus,
        accommodations: student.learningAccommodations,
      })),
      totalStudents: classRoom.students.length,
      capacity: classRoom.capacity,
      generatedAt: new Date(),
    };
  }

  public async getAttendanceStatistics(classId: string, startDate: Date, endDate: Date): Promise<any> {
    const attendance = await this.getAttendance(classId);
    const filteredAttendance = attendance.filter(record => 
      record.date >= startDate && record.date <= endDate
    );

    const stats = filteredAttendance.reduce((acc, record) => {
      if (!acc[record.studentId]) {
        acc[record.studentId] = { present: 0, absent: 0, late: 0, excused: 0, total: 0 };
      }
      acc[record.studentId][record.status]++;
      acc[record.studentId].total++;
      return acc;
    }, {} as any);

    return {
      period: { startDate, endDate },
      studentStats: stats,
      classStats: {
        totalRecords: filteredAttendance.length,
        averageAttendanceRate: Object.values(stats).reduce((sum: number, student: any) => 
          sum + (student.present / student.total), 0
        ) / Object.keys(stats).length,
      },
    };
  }
}