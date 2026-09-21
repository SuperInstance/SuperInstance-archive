/**
 * Employee Management System
 * Handles employee onboarding, scheduling, time tracking, and HR processes
 */

import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import winston from 'winston';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'logs/employee.log' })
  ]
});

export class EmployeeManager extends EventEmitter {
  constructor() {
    super();
    this.employees = new Map();
    this.schedules = new Map();
    this.timeEntries = new Map();
    this.departments = new Map();
    this.positions = new Map();
    this.payrollPeriods = new Map();
    this.benefits = new Map();
    this.evaluations = new Map();
    
    this.initializeDepartments();
    this.initializePositions();
    this.initializeBenefitsPackages();
  }

  /**
   * Initialize default departments
   */
  initializeDepartments() {
    const departments = [
      {
        id: 'front_of_house',
        name: 'Front of House',
        description: 'Customer-facing roles',
        industries: ['Restaurant', 'Retail Store', 'Healthcare']
      },
      {
        id: 'back_of_house',
        name: 'Back of House',
        description: 'Operations and support roles',
        industries: ['Restaurant', 'Manufacturing']
      },
      {
        id: 'sales',
        name: 'Sales',
        description: 'Sales and customer acquisition',
        industries: ['Retail Store', 'Real Estate', 'Professional Services']
      },
      {
        id: 'administration',
        name: 'Administration',
        description: 'Administrative and office support',
        industries: ['all']
      },
      {
        id: 'management',
        name: 'Management',
        description: 'Leadership and supervisory roles',
        industries: ['all']
      },
      {
        id: 'production',
        name: 'Production',
        description: 'Manufacturing and production',
        industries: ['Manufacturing', 'Agriculture']
      },
      {
        id: 'technical',
        name: 'Technical',
        description: 'IT and technical support',
        industries: ['Technology', 'Professional Services']
      },
      {
        id: 'maintenance',
        name: 'Maintenance',
        description: 'Facility and equipment maintenance',
        industries: ['Manufacturing', 'Healthcare', 'Education']
      }
    ];

    departments.forEach(dept => {
      this.departments.set(dept.id, dept);
    });
  }

  /**
   * Initialize default positions
   */
  initializePositions() {
    const positions = [
      // Restaurant positions
      {
        id: 'server',
        title: 'Server',
        department: 'front_of_house',
        hourlyRate: { min: 15, max: 25 },
        requirements: ['Customer service skills', 'Communication'],
        responsibilities: ['Take orders', 'Serve food', 'Handle payments'],
        industries: ['Restaurant']
      },
      {
        id: 'cook',
        title: 'Cook',
        department: 'back_of_house',
        hourlyRate: { min: 18, max: 28 },
        requirements: ['Food preparation experience', 'Food safety certification'],
        responsibilities: ['Prepare meals', 'Maintain kitchen cleanliness', 'Follow recipes'],
        industries: ['Restaurant']
      },
      {
        id: 'host',
        title: 'Host/Hostess',
        department: 'front_of_house',
        hourlyRate: { min: 14, max: 18 },
        requirements: ['Customer service', 'Organization'],
        responsibilities: ['Greet customers', 'Manage seating', 'Answer phones'],
        industries: ['Restaurant']
      },

      // Retail positions
      {
        id: 'sales_associate',
        title: 'Sales Associate',
        department: 'sales',
        hourlyRate: { min: 16, max: 22 },
        requirements: ['Sales experience', 'Product knowledge'],
        responsibilities: ['Assist customers', 'Process transactions', 'Stock shelves'],
        industries: ['Retail Store']
      },
      {
        id: 'cashier',
        title: 'Cashier',
        department: 'front_of_house',
        hourlyRate: { min: 15, max: 20 },
        requirements: ['Math skills', 'Attention to detail'],
        responsibilities: ['Process payments', 'Handle returns', 'Maintain register'],
        industries: ['Retail Store']
      },
      {
        id: 'stock_clerk',
        title: 'Stock Clerk',
        department: 'back_of_house',
        hourlyRate: { min: 14, max: 18 },
        requirements: ['Physical ability', 'Organization'],
        responsibilities: ['Receive inventory', 'Stock shelves', 'Organize storage'],
        industries: ['Retail Store']
      },

      // General positions
      {
        id: 'manager',
        title: 'Manager',
        department: 'management',
        hourlyRate: { min: 25, max: 45 },
        requirements: ['Leadership experience', 'Management skills'],
        responsibilities: ['Supervise staff', 'Handle operations', 'Customer escalations'],
        industries: ['all']
      },
      {
        id: 'assistant_manager',
        title: 'Assistant Manager',
        department: 'management',
        hourlyRate: { min: 20, max: 32 },
        requirements: ['Supervisory experience', 'Communication'],
        responsibilities: ['Support manager', 'Train staff', 'Handle scheduling'],
        industries: ['all']
      },
      {
        id: 'receptionist',
        title: 'Receptionist',
        department: 'administration',
        hourlyRate: { min: 16, max: 22 },
        requirements: ['Communication skills', 'Computer proficiency'],
        responsibilities: ['Answer phones', 'Greet visitors', 'Administrative tasks'],
        industries: ['Professional Services', 'Healthcare']
      }
    ];

    positions.forEach(position => {
      this.positions.set(position.id, position);
    });
  }

  /**
   * Initialize benefits packages
   */
  initializeBenefitsPackages() {
    const packages = [
      {
        id: 'basic',
        name: 'Basic Package',
        description: 'Essential benefits for part-time employees',
        benefits: [
          { type: 'paid_time_off', value: 5, unit: 'days' },
          { type: 'employee_discount', value: 10, unit: 'percent' }
        ],
        eligibility: { minHours: 20, minTenure: 90 },
        cost: 50 // monthly cost to employer
      },
      {
        id: 'standard',
        name: 'Standard Package',
        description: 'Comprehensive benefits for full-time employees',
        benefits: [
          { type: 'health_insurance', value: 80, unit: 'percent_covered' },
          { type: 'paid_time_off', value: 15, unit: 'days' },
          { type: 'sick_leave', value: 8, unit: 'days' },
          { type: 'employee_discount', value: 15, unit: 'percent' },
          { type: 'retirement_match', value: 3, unit: 'percent' }
        ],
        eligibility: { minHours: 32, minTenure: 90 },
        cost: 400
      },
      {
        id: 'premium',
        name: 'Premium Package',
        description: 'Enhanced benefits for management and senior staff',
        benefits: [
          { type: 'health_insurance', value: 90, unit: 'percent_covered' },
          { type: 'dental_insurance', value: 100, unit: 'percent_covered' },
          { type: 'vision_insurance', value: 100, unit: 'percent_covered' },
          { type: 'paid_time_off', value: 25, unit: 'days' },
          { type: 'sick_leave', value: 12, unit: 'days' },
          { type: 'personal_days', value: 3, unit: 'days' },
          { type: 'employee_discount', value: 20, unit: 'percent' },
          { type: 'retirement_match', value: 6, unit: 'percent' },
          { type: 'life_insurance', value: 50000, unit: 'dollars' }
        ],
        eligibility: { minHours: 40, minTenure: 180 },
        cost: 650
      }
    ];

    packages.forEach(pkg => {
      this.benefits.set(pkg.id, pkg);
    });
  }

  /**
   * Add new employee to the system
   */
  async addEmployee(employeeData) {
    try {
      const employeeId = uuidv4();
      
      // Validate required fields
      this.validateEmployeeData(employeeData);

      // Hash password if provided
      let hashedPassword = null;
      if (employeeData.password) {
        hashedPassword = await bcrypt.hash(employeeData.password, 10);
      }

      // Get position details
      const position = this.positions.get(employeeData.positionId);
      if (!position) {
        throw new Error(`Position not found: ${employeeData.positionId}`);
      }

      const employee = {
        id: employeeId,
        businessId: employeeData.businessId,
        personalInfo: {
          firstName: employeeData.firstName,
          lastName: employeeData.lastName,
          email: employeeData.email,
          phone: employeeData.phone,
          address: employeeData.address || {},
          dateOfBirth: employeeData.dateOfBirth,
          emergencyContact: employeeData.emergencyContact || {},
          socialSecurityNumber: this.encryptSSN(employeeData.ssn) // Encrypted
        },
        employment: {
          employeeNumber: this.generateEmployeeNumber(employeeData.businessId),
          startDate: employeeData.startDate || Date.now(),
          endDate: null,
          status: 'active', // active, inactive, terminated
          positionId: employeeData.positionId,
          position: position.title,
          department: position.department,
          manager: employeeData.managerId || null,
          employmentType: employeeData.employmentType || 'full_time', // full_time, part_time, contract, intern
          workLocation: employeeData.workLocation || 'on_site' // on_site, remote, hybrid
        },
        compensation: {
          payType: employeeData.payType || 'hourly', // hourly, salary, commission
          rate: employeeData.rate || position.hourlyRate.min,
          currency: 'USD',
          paySchedule: employeeData.paySchedule || 'bi_weekly',
          overtimeEligible: employeeData.overtimeEligible !== false,
          benefitsPackage: employeeData.benefitsPackage || 'basic'
        },
        access: {
          username: employeeData.username || this.generateUsername(employeeData.firstName, employeeData.lastName),
          password: hashedPassword,
          permissions: employeeData.permissions || this.getDefaultPermissions(employeeData.positionId),
          lastLogin: null,
          loginAttempts: 0,
          accountLocked: false
        },
        schedule: {
          defaultHours: employeeData.defaultHours || 40,
          preferredShifts: employeeData.preferredShifts || [],
          availability: employeeData.availability || this.getDefaultAvailability(),
          timeOffBalance: this.calculateInitialTimeOff(employeeData.benefitsPackage)
        },
        documents: {
          i9Form: { completed: false, expirationDate: null },
          w4Form: { completed: false },
          handbook: { acknowledged: false, date: null },
          policies: [],
          certifications: employeeData.certifications || [],
          training: []
        },
        performance: {
          evaluations: [],
          goals: [],
          achievements: [],
          disciplinaryActions: [],
          commendations: []
        },
        createdAt: Date.now(),
        updatedAt: Date.now(),
        createdBy: employeeData.createdBy
      };

      this.employees.set(employeeId, employee);

      // Create initial schedule if provided
      if (employeeData.initialSchedule) {
        await this.createSchedule(employeeId, employeeData.initialSchedule);
      }

      // Send welcome email/notification
      this.sendWelcomeNotification(employee);

      this.emit('employee:added', {
        employeeId,
        businessId: employeeData.businessId,
        employee: this.sanitizeEmployeeData(employee)
      });

      logger.info(`Added employee: ${employee.personalInfo.firstName} ${employee.personalInfo.lastName}`);

      return this.sanitizeEmployeeData(employee);

    } catch (error) {
      logger.error('Failed to add employee:', error);
      throw error;
    }
  }

  /**
   * Get employees for a business
   */
  async getEmployees(businessId, filters = {}) {
    const businessEmployees = Array.from(this.employees.values())
      .filter(emp => emp.businessId === businessId);

    let filteredEmployees = businessEmployees;

    // Apply filters
    if (filters.status) {
      filteredEmployees = filteredEmployees.filter(emp => 
        emp.employment.status === filters.status
      );
    }

    if (filters.department) {
      filteredEmployees = filteredEmployees.filter(emp => 
        emp.employment.department === filters.department
      );
    }

    if (filters.position) {
      filteredEmployees = filteredEmployees.filter(emp => 
        emp.employment.positionId === filters.position
      );
    }

    if (filters.search) {
      const searchTerm = filters.search.toLowerCase();
      filteredEmployees = filteredEmployees.filter(emp => 
        emp.personalInfo.firstName.toLowerCase().includes(searchTerm) ||
        emp.personalInfo.lastName.toLowerCase().includes(searchTerm) ||
        emp.personalInfo.email.toLowerCase().includes(searchTerm) ||
        emp.employment.employeeNumber.includes(searchTerm)
      );
    }

    // Sort employees
    const sortField = filters.sortBy || 'personalInfo.lastName';
    const sortOrder = filters.sortOrder || 'asc';
    
    filteredEmployees.sort((a, b) => {
      const aValue = this.getNestedValue(a, sortField);
      const bValue = this.getNestedValue(b, sortField);
      
      if (sortOrder === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    return filteredEmployees.map(emp => this.sanitizeEmployeeData(emp));
  }

  /**
   * Update employee information
   */
  async updateEmployee(employeeId, updates) {
    const employee = this.employees.get(employeeId);
    if (!employee) {
      throw new Error('Employee not found');
    }

    try {
      // Deep merge updates
      const updatedEmployee = this.deepMerge(employee, updates);
      updatedEmployee.updatedAt = Date.now();

      // Validate critical updates
      if (updates.employment && updates.employment.positionId) {
        const position = this.positions.get(updates.employment.positionId);
        if (!position) {
          throw new Error(`Position not found: ${updates.employment.positionId}`);
        }
        updatedEmployee.employment.position = position.title;
        updatedEmployee.employment.department = position.department;
      }

      // Hash new password if provided
      if (updates.access && updates.access.password) {
        updatedEmployee.access.password = await bcrypt.hash(updates.access.password, 10);
      }

      this.employees.set(employeeId, updatedEmployee);

      this.emit('employee:updated', {
        employeeId,
        updates,
        employee: this.sanitizeEmployeeData(updatedEmployee)
      });

      logger.info(`Updated employee: ${employeeId}`);

      return this.sanitizeEmployeeData(updatedEmployee);

    } catch (error) {
      logger.error('Failed to update employee:', error);
      throw error;
    }
  }

  /**
   * Create employee schedule
   */
  async createSchedule(employeeId, scheduleData) {
    const employee = this.employees.get(employeeId);
    if (!employee) {
      throw new Error('Employee not found');
    }

    const scheduleId = uuidv4();
    
    const schedule = {
      id: scheduleId,
      employeeId,
      businessId: employee.businessId,
      weekOf: scheduleData.weekOf || this.getStartOfWeek(Date.now()),
      shifts: this.validateAndProcessShifts(scheduleData.shifts || []),
      totalHours: 0,
      status: 'draft', // draft, published, confirmed
      notes: scheduleData.notes || '',
      createdAt: Date.now(),
      createdBy: scheduleData.createdBy,
      approvedBy: null,
      approvedAt: null
    };

    // Calculate total hours
    schedule.totalHours = this.calculateTotalHours(schedule.shifts);

    // Check for conflicts
    const conflicts = await this.checkScheduleConflicts(employeeId, schedule);
    if (conflicts.length > 0) {
      schedule.conflicts = conflicts;
      schedule.status = 'needs_review';
    }

    this.schedules.set(scheduleId, schedule);

    this.emit('schedule:created', {
      scheduleId,
      employeeId,
      schedule
    });

    return schedule;
  }

  /**
   * Update employee schedule
   */
  async updateSchedule(employeeId, scheduleData) {
    // Find existing schedule for the week
    const existingSchedule = Array.from(this.schedules.values()).find(
      schedule => schedule.employeeId === employeeId && 
                 schedule.weekOf === scheduleData.weekOf
    );

    if (existingSchedule) {
      // Update existing schedule
      existingSchedule.shifts = this.validateAndProcessShifts(scheduleData.shifts);
      existingSchedule.totalHours = this.calculateTotalHours(existingSchedule.shifts);
      existingSchedule.updatedAt = Date.now();
      
      // Recheck conflicts
      const conflicts = await this.checkScheduleConflicts(employeeId, existingSchedule);
      existingSchedule.conflicts = conflicts;
      
      this.emit('schedule:updated', {
        scheduleId: existingSchedule.id,
        employeeId,
        schedule: existingSchedule
      });

      return existingSchedule;
    } else {
      // Create new schedule
      return await this.createSchedule(employeeId, scheduleData);
    }
  }

  /**
   * Clock in/out functionality
   */
  async clockIn(employeeId, location = null, notes = '') {
    const employee = this.employees.get(employeeId);
    if (!employee) {
      throw new Error('Employee not found');
    }

    // Check if already clocked in
    const activeEntry = Array.from(this.timeEntries.values()).find(
      entry => entry.employeeId === employeeId && !entry.clockOut
    );

    if (activeEntry) {
      throw new Error('Employee is already clocked in');
    }

    const timeEntryId = uuidv4();
    const timeEntry = {
      id: timeEntryId,
      employeeId,
      businessId: employee.businessId,
      clockIn: Date.now(),
      clockOut: null,
      location,
      notes,
      breakTime: 0,
      adjustments: [],
      totalHours: 0,
      status: 'active'
    };

    this.timeEntries.set(timeEntryId, timeEntry);

    this.emit('time:clock_in', {
      employeeId,
      timeEntryId,
      clockIn: timeEntry.clockIn,
      location
    });

    logger.info(`Employee ${employeeId} clocked in at ${new Date(timeEntry.clockIn)}`);

    return timeEntry;
  }

  async clockOut(employeeId, notes = '') {
    const employee = this.employees.get(employeeId);
    if (!employee) {
      throw new Error('Employee not found');
    }

    // Find active time entry
    const activeEntry = Array.from(this.timeEntries.values()).find(
      entry => entry.employeeId === employeeId && !entry.clockOut
    );

    if (!activeEntry) {
      throw new Error('Employee is not currently clocked in');
    }

    activeEntry.clockOut = Date.now();
    activeEntry.notes += (activeEntry.notes ? ' | ' : '') + notes;
    activeEntry.status = 'completed';
    
    // Calculate total hours
    const totalMinutes = (activeEntry.clockOut - activeEntry.clockIn) / (1000 * 60);
    activeEntry.totalHours = Math.round(((totalMinutes - activeEntry.breakTime) / 60) * 100) / 100;

    // Check for overtime
    const overtimeThreshold = 8; // hours per day
    if (activeEntry.totalHours > overtimeThreshold) {
      activeEntry.overtimeHours = activeEntry.totalHours - overtimeThreshold;
      activeEntry.regularHours = overtimeThreshold;
    } else {
      activeEntry.regularHours = activeEntry.totalHours;
      activeEntry.overtimeHours = 0;
    }

    this.emit('time:clock_out', {
      employeeId,
      timeEntryId: activeEntry.id,
      clockOut: activeEntry.clockOut,
      totalHours: activeEntry.totalHours,
      overtimeHours: activeEntry.overtimeHours
    });

    logger.info(`Employee ${employeeId} clocked out at ${new Date(activeEntry.clockOut)} - ${activeEntry.totalHours} hours`);

    return activeEntry;
  }

  /**
   * Start/end break
   */
  async startBreak(employeeId, breakType = 'break') {
    const activeEntry = Array.from(this.timeEntries.values()).find(
      entry => entry.employeeId === employeeId && !entry.clockOut
    );

    if (!activeEntry) {
      throw new Error('Employee is not currently clocked in');
    }

    if (activeEntry.onBreak) {
      throw new Error('Employee is already on break');
    }

    activeEntry.onBreak = true;
    activeEntry.breakStart = Date.now();
    activeEntry.breakType = breakType;

    this.emit('time:break_start', {
      employeeId,
      timeEntryId: activeEntry.id,
      breakType,
      breakStart: activeEntry.breakStart
    });

    return activeEntry;
  }

  async endBreak(employeeId) {
    const activeEntry = Array.from(this.timeEntries.values()).find(
      entry => entry.employeeId === employeeId && !entry.clockOut
    );

    if (!activeEntry) {
      throw new Error('Employee is not currently clocked in');
    }

    if (!activeEntry.onBreak) {
      throw new Error('Employee is not currently on break');
    }

    const breakDuration = (Date.now() - activeEntry.breakStart) / (1000 * 60); // minutes
    activeEntry.breakTime += breakDuration;
    activeEntry.onBreak = false;
    activeEntry.breakStart = null;

    this.emit('time:break_end', {
      employeeId,
      timeEntryId: activeEntry.id,
      breakDuration,
      totalBreakTime: activeEntry.breakTime
    });

    return activeEntry;
  }

  /**
   * Generate payroll report
   */
  async generatePayroll(businessId, startDate, endDate) {
    const businessEmployees = Array.from(this.employees.values())
      .filter(emp => emp.businessId === businessId && emp.employment.status === 'active');

    const payrollData = [];

    for (const employee of businessEmployees) {
      const timeEntries = Array.from(this.timeEntries.values()).filter(
        entry => entry.employeeId === employee.id &&
                entry.clockIn >= startDate &&
                entry.clockIn <= endDate &&
                entry.status === 'completed'
      );

      const regularHours = timeEntries.reduce((sum, entry) => sum + (entry.regularHours || 0), 0);
      const overtimeHours = timeEntries.reduce((sum, entry) => sum + (entry.overtimeHours || 0), 0);
      const totalHours = regularHours + overtimeHours;

      const regularPay = regularHours * employee.compensation.rate;
      const overtimePay = overtimeHours * employee.compensation.rate * 1.5;
      const grossPay = regularPay + overtimePay;

      // Calculate deductions (simplified)
      const federalTax = grossPay * 0.12;
      const stateTax = grossPay * 0.05;
      const socialSecurity = grossPay * 0.062;
      const medicare = grossPay * 0.0145;
      const totalDeductions = federalTax + stateTax + socialSecurity + medicare;

      const netPay = grossPay - totalDeductions;

      payrollData.push({
        employee: this.sanitizeEmployeeData(employee),
        hours: {
          regular: regularHours,
          overtime: overtimeHours,
          total: totalHours
        },
        pay: {
          regularRate: employee.compensation.rate,
          overtimeRate: employee.compensation.rate * 1.5,
          regularPay,
          overtimePay,
          grossPay,
          netPay
        },
        deductions: {
          federalTax,
          stateTax,
          socialSecurity,
          medicare,
          total: totalDeductions
        },
        timeEntries: timeEntries.length
      });
    }

    const payrollSummary = {
      businessId,
      periodStart: startDate,
      periodEnd: endDate,
      employeeCount: payrollData.length,
      totalGrossPay: payrollData.reduce((sum, emp) => sum + emp.pay.grossPay, 0),
      totalNetPay: payrollData.reduce((sum, emp) => sum + emp.pay.netPay, 0),
      totalDeductions: payrollData.reduce((sum, emp) => sum + emp.deductions.total, 0),
      totalHours: payrollData.reduce((sum, emp) => sum + emp.hours.total, 0),
      employees: payrollData,
      generatedAt: Date.now()
    };

    return payrollSummary;
  }

  /**
   * Helper methods
   */
  validateEmployeeData(data) {
    const required = ['firstName', 'lastName', 'email', 'businessId', 'positionId'];
    const missing = required.filter(field => !data[field]);
    
    if (missing.length > 0) {
      throw new Error(`Missing required fields: ${missing.join(', ')}`);
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(data.email)) {
      throw new Error('Invalid email format');
    }

    // Validate phone if provided
    if (data.phone && !/^\d{10}$/.test(data.phone.replace(/\D/g, ''))) {
      throw new Error('Invalid phone number format');
    }
  }

  generateEmployeeNumber(businessId) {
    const businessEmployees = Array.from(this.employees.values())
      .filter(emp => emp.businessId === businessId);
    
    return `EMP${businessId.slice(-4).toUpperCase()}${(businessEmployees.length + 1).toString().padStart(4, '0')}`;
  }

  generateUsername(firstName, lastName) {
    return `${firstName.toLowerCase()}.${lastName.toLowerCase()}`.replace(/[^a-z.]/g, '');
  }

  encryptSSN(ssn) {
    if (!ssn) return null;
    // In production, use proper encryption
    return `***-**-${ssn.slice(-4)}`;
  }

  getDefaultPermissions(positionId) {
    const position = this.positions.get(positionId);
    if (!position) return ['basic_access'];

    const permissionMap = {
      'manager': ['full_access', 'employee_management', 'reports', 'scheduling'],
      'assistant_manager': ['employee_management', 'scheduling', 'basic_reports'],
      'server': ['pos_access', 'customer_management'],
      'cook': ['inventory_view', 'recipe_access'],
      'sales_associate': ['pos_access', 'inventory_view', 'customer_management'],
      'cashier': ['pos_access', 'basic_reports']
    };

    return permissionMap[positionId] || ['basic_access'];
  }

  getDefaultAvailability() {
    return {
      monday: { available: true, start: '09:00', end: '17:00' },
      tuesday: { available: true, start: '09:00', end: '17:00' },
      wednesday: { available: true, start: '09:00', end: '17:00' },
      thursday: { available: true, start: '09:00', end: '17:00' },
      friday: { available: true, start: '09:00', end: '17:00' },
      saturday: { available: false, start: null, end: null },
      sunday: { available: false, start: null, end: null }
    };
  }

  calculateInitialTimeOff(benefitsPackage) {
    const pkg = this.benefits.get(benefitsPackage);
    if (!pkg) return { vacation: 0, sick: 0, personal: 0 };

    const timeOff = { vacation: 0, sick: 0, personal: 0 };
    
    pkg.benefits.forEach(benefit => {
      if (benefit.type === 'paid_time_off') {
        timeOff.vacation = benefit.value;
      } else if (benefit.type === 'sick_leave') {
        timeOff.sick = benefit.value;
      } else if (benefit.type === 'personal_days') {
        timeOff.personal = benefit.value;
      }
    });

    return timeOff;
  }

  validateAndProcessShifts(shifts) {
    return shifts.map(shift => {
      if (!shift.date || !shift.startTime || !shift.endTime) {
        throw new Error('Shift must have date, start time, and end time');
      }

      // Parse times and calculate duration
      const start = new Date(`${shift.date} ${shift.startTime}`);
      const end = new Date(`${shift.date} ${shift.endTime}`);
      
      if (end <= start) {
        throw new Error('End time must be after start time');
      }

      const hours = (end - start) / (1000 * 60 * 60);

      return {
        ...shift,
        duration: hours,
        startDateTime: start.getTime(),
        endDateTime: end.getTime()
      };
    });
  }

  calculateTotalHours(shifts) {
    return shifts.reduce((total, shift) => total + (shift.duration || 0), 0);
  }

  async checkScheduleConflicts(employeeId, schedule) {
    const conflicts = [];
    
    // Check each shift against existing schedules
    for (const shift of schedule.shifts) {
      const conflictingSchedules = Array.from(this.schedules.values()).filter(
        existingSchedule => existingSchedule.employeeId === employeeId &&
                           existingSchedule.id !== schedule.id &&
                           existingSchedule.status !== 'cancelled'
      );

      for (const existingSchedule of conflictingSchedules) {
        for (const existingShift of existingSchedule.shifts) {
          if (this.shiftsOverlap(shift, existingShift)) {
            conflicts.push({
              type: 'schedule_overlap',
              shift,
              conflictingShift: existingShift,
              conflictingScheduleId: existingSchedule.id
            });
          }
        }
      }
    }

    return conflicts;
  }

  shiftsOverlap(shift1, shift2) {
    return shift1.startDateTime < shift2.endDateTime && 
           shift2.startDateTime < shift1.endDateTime;
  }

  getStartOfWeek(date) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day;
    return new Date(d.setDate(diff)).setHours(0, 0, 0, 0);
  }

  sanitizeEmployeeData(employee) {
    // Remove sensitive data before sending to client
    const sanitized = { ...employee };
    delete sanitized.personalInfo.socialSecurityNumber;
    delete sanitized.access.password;
    return sanitized;
  }

  deepMerge(target, source) {
    const result = { ...target };
    
    for (const key in source) {
      if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
        result[key] = this.deepMerge(result[key] || {}, source[key]);
      } else {
        result[key] = source[key];
      }
    }
    
    return result;
  }

  getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) => current?.[key], obj);
  }

  sendWelcomeNotification(employee) {
    // In production, this would send actual email/SMS
    logger.info(`Welcome notification sent to ${employee.personalInfo.email}`);
  }

  /**
   * Get available positions for industry
   */
  getPositionsForIndustry(industry) {
    return Array.from(this.positions.values()).filter(
      position => position.industries.includes('all') || position.industries.includes(industry)
    );
  }

  /**
   * Get departments for industry
   */
  getDepartmentsForIndustry(industry) {
    return Array.from(this.departments.values()).filter(
      dept => dept.industries.includes('all') || dept.industries.includes(industry)
    );
  }

  /**
   * Get employee by ID
   */
  getEmployee(employeeId) {
    const employee = this.employees.get(employeeId);
    return employee ? this.sanitizeEmployeeData(employee) : null;
  }

  /**
   * Close connections (for graceful shutdown)
   */
  close() {
    // Close any database connections, clear timers, etc.
    logger.info('Employee Manager closed');
  }
}