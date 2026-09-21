/**
 * Custom Interface Generator
 * Dynamically creates tailored user interfaces based on business profiles and complexity levels
 */

import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import winston from 'winston';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.json(),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'logs/interface.log' })
  ]
});

export class InterfaceGenerator extends EventEmitter {
  constructor() {
    super();
    this.interfaces = new Map();
    this.componentLibrary = new Map();
    this.layoutTemplates = new Map();
    this.themeConfigs = new Map();
    
    this.initializeComponentLibrary();
    this.initializeLayoutTemplates();
    this.initializeThemes();
  }

  /**
   * Initialize component library with reusable UI components
   */
  initializeComponentLibrary() {
    const components = {
      // Navigation Components
      navbar: {
        id: 'navbar',
        type: 'navigation',
        component: 'Navbar',
        props: {
          logo: true,
          search: true,
          notifications: true,
          userProfile: true
        },
        complexity: 1,
        industries: ['all']
      },
      sidebar: {
        id: 'sidebar',
        type: 'navigation',
        component: 'Sidebar',
        props: {
          collapsible: true,
          icons: true,
          nested: false
        },
        complexity: 2,
        industries: ['all']
      },
      breadcrumbs: {
        id: 'breadcrumbs',
        type: 'navigation',
        component: 'Breadcrumbs',
        props: {
          separator: '/',
          clickable: true
        },
        complexity: 3,
        industries: ['all']
      },

      // Dashboard Components
      summary_cards: {
        id: 'summary_cards',
        type: 'dashboard',
        component: 'SummaryCards',
        props: {
          metrics: ['revenue', 'customers', 'inventory', 'employees'],
          period: 'daily',
          comparison: true
        },
        complexity: 1,
        industries: ['all']
      },
      quick_actions: {
        id: 'quick_actions',
        type: 'dashboard',
        component: 'QuickActions',
        props: {
          actions: ['add_sale', 'add_customer', 'check_inventory'],
          customizable: true
        },
        complexity: 1,
        industries: ['all']
      },
      recent_activity: {
        id: 'recent_activity',
        type: 'dashboard',
        component: 'RecentActivity',
        props: {
          limit: 10,
          filters: true,
          realTime: true
        },
        complexity: 2,
        industries: ['all']
      },
      charts_analytics: {
        id: 'charts_analytics',
        type: 'dashboard',
        component: 'ChartsAnalytics',
        props: {
          chartTypes: ['line', 'bar', 'pie'],
          customizable: true,
          exportable: true
        },
        complexity: 3,
        industries: ['all']
      },

      // Sales & POS Components
      pos_terminal: {
        id: 'pos_terminal',
        type: 'sales',
        component: 'POSTerminal',
        props: {
          barcode: true,
          calculator: true,
          discounts: true,
          taxes: true
        },
        complexity: 2,
        industries: ['Retail Store', 'Restaurant']
      },
      sales_history: {
        id: 'sales_history',
        type: 'sales',
        component: 'SalesHistory',
        props: {
          search: true,
          filters: true,
          export: true,
          refunds: true
        },
        complexity: 2,
        industries: ['all']
      },
      receipt_printer: {
        id: 'receipt_printer',
        type: 'sales',
        component: 'ReceiptPrinter',
        props: {
          templates: true,
          logo: true,
          email: true
        },
        complexity: 3,
        industries: ['Retail Store', 'Restaurant']
      },

      // Inventory Components
      inventory_list: {
        id: 'inventory_list',
        type: 'inventory',
        component: 'InventoryList',
        props: {
          search: true,
          filters: true,
          bulk_actions: true,
          low_stock_alerts: true
        },
        complexity: 1,
        industries: ['Retail Store', 'Manufacturing', 'Restaurant']
      },
      stock_alerts: {
        id: 'stock_alerts',
        type: 'inventory',
        component: 'StockAlerts',
        props: {
          thresholds: true,
          notifications: true,
          auto_reorder: false
        },
        complexity: 2,
        industries: ['Retail Store', 'Manufacturing', 'Restaurant']
      },
      barcode_scanner: {
        id: 'barcode_scanner',
        type: 'inventory',
        component: 'BarcodeScanner',
        props: {
          camera: true,
          manual_entry: true,
          batch_scan: false
        },
        complexity: 3,
        industries: ['Retail Store', 'Manufacturing']
      },

      // Employee Components
      employee_list: {
        id: 'employee_list',
        type: 'employee',
        component: 'EmployeeList',
        props: {
          search: true,
          filters: true,
          photo: true,
          contact_info: true
        },
        complexity: 1,
        industries: ['all']
      },
      schedule_calendar: {
        id: 'schedule_calendar',
        type: 'employee',
        component: 'ScheduleCalendar',
        props: {
          drag_drop: true,
          shift_templates: true,
          conflict_detection: true
        },
        complexity: 2,
        industries: ['all']
      },
      time_clock: {
        id: 'time_clock',
        type: 'employee',
        component: 'TimeClock',
        props: {
          punch_in_out: true,
          break_tracking: true,
          overtime_alerts: true
        },
        complexity: 2,
        industries: ['all']
      },
      payroll_summary: {
        id: 'payroll_summary',
        type: 'employee',
        component: 'PayrollSummary',
        props: {
          hours: true,
          rates: true,
          deductions: true,
          export: true
        },
        complexity: 3,
        industries: ['all']
      },

      // Customer Components
      customer_list: {
        id: 'customer_list',
        type: 'customer',
        component: 'CustomerList',
        props: {
          search: true,
          filters: true,
          contact_info: true,
          purchase_history: true
        },
        complexity: 2,
        industries: ['all']
      },
      loyalty_program: {
        id: 'loyalty_program',
        type: 'customer',
        component: 'LoyaltyProgram',
        props: {
          points: true,
          rewards: true,
          tiers: true
        },
        complexity: 3,
        industries: ['Retail Store', 'Restaurant']
      },

      // Security Components
      security_cameras: {
        id: 'security_cameras',
        type: 'security',
        component: 'SecurityCameras',
        props: {
          live_view: true,
          recording: true,
          alerts: true,
          multiple_cameras: true
        },
        complexity: 3,
        industries: ['all']
      },
      access_control: {
        id: 'access_control',
        type: 'security',
        component: 'AccessControl',
        props: {
          user_permissions: true,
          time_restrictions: true,
          audit_log: true
        },
        complexity: 4,
        industries: ['all']
      },

      // Reports Components
      financial_reports: {
        id: 'financial_reports',
        type: 'reports',
        component: 'FinancialReports',
        props: {
          templates: ['profit_loss', 'cash_flow', 'balance_sheet'],
          date_ranges: true,
          export: true,
          scheduling: false
        },
        complexity: 3,
        industries: ['all']
      },
      inventory_reports: {
        id: 'inventory_reports',
        type: 'reports',
        component: 'InventoryReports',
        props: {
          templates: ['stock_levels', 'valuation', 'movement'],
          filters: true,
          export: true
        },
        complexity: 3,
        industries: ['Retail Store', 'Manufacturing', 'Restaurant']
      },

      // Industry-Specific Components
      table_management: {
        id: 'table_management',
        type: 'restaurant',
        component: 'TableManagement',
        props: {
          floor_plan: true,
          reservations: true,
          wait_list: true,
          table_status: true
        },
        complexity: 3,
        industries: ['Restaurant']
      },
      menu_management: {
        id: 'menu_management',
        type: 'restaurant',
        component: 'MenuManagement',
        props: {
          categories: true,
          modifiers: true,
          pricing: true,
          seasonal_items: true
        },
        complexity: 2,
        industries: ['Restaurant']
      },
      production_planning: {
        id: 'production_planning',
        type: 'manufacturing',
        component: 'ProductionPlanning',
        props: {
          work_orders: true,
          resource_allocation: true,
          scheduling: true,
          capacity_planning: true
        },
        complexity: 4,
        industries: ['Manufacturing']
      },
      quality_control: {
        id: 'quality_control',
        type: 'manufacturing',
        component: 'QualityControl',
        props: {
          checklists: true,
          inspections: true,
          defect_tracking: true,
          corrective_actions: true
        },
        complexity: 4,
        industries: ['Manufacturing']
      }
    };

    Object.values(components).forEach(component => {
      this.componentLibrary.set(component.id, component);
    });
  }

  /**
   * Initialize layout templates for different business types
   */
  initializeLayoutTemplates() {
    const templates = {
      simple_dashboard: {
        id: 'simple_dashboard',
        name: 'Simple Dashboard',
        description: 'Clean, minimal interface for small businesses',
        complexity: 1,
        layout: {
          type: 'grid',
          columns: 12,
          rows: 'auto',
          areas: [
            { component: 'navbar', area: 'header', span: 12 },
            { component: 'summary_cards', area: 'main-top', span: 8 },
            { component: 'quick_actions', area: 'sidebar-top', span: 4 },
            { component: 'recent_activity', area: 'main-bottom', span: 12 }
          ]
        },
        theme: 'clean',
        responsive: true
      },
      sidebar_layout: {
        id: 'sidebar_layout',
        name: 'Sidebar Layout',
        description: 'Navigation sidebar with main content area',
        complexity: 2,
        layout: {
          type: 'sidebar',
          sidebar: { width: 250, collapsible: true },
          areas: [
            { component: 'sidebar', area: 'navigation' },
            { component: 'navbar', area: 'header' },
            { component: 'breadcrumbs', area: 'breadcrumb' },
            { component: 'summary_cards', area: 'content-top' },
            { component: 'charts_analytics', area: 'content-main' }
          ]
        },
        theme: 'professional',
        responsive: true
      },
      comprehensive_layout: {
        id: 'comprehensive_layout',
        name: 'Comprehensive Layout',
        description: 'Full-featured layout for advanced users',
        complexity: 4,
        layout: {
          type: 'multi-panel',
          panels: 4,
          areas: [
            { component: 'navbar', area: 'header', span: 12 },
            { component: 'sidebar', area: 'navigation', span: 2 },
            { component: 'summary_cards', area: 'main-top', span: 6 },
            { component: 'stock_alerts', area: 'alert-panel', span: 2 },
            { component: 'quick_actions', area: 'action-panel', span: 2 },
            { component: 'charts_analytics', area: 'main-center', span: 8 },
            { component: 'recent_activity', area: 'activity-panel', span: 2 },
            { component: 'financial_reports', area: 'reports', span: 10 }
          ]
        },
        theme: 'advanced',
        responsive: true
      },
      retail_pos: {
        id: 'retail_pos',
        name: 'Retail POS Layout',
        description: 'Optimized for retail point-of-sale operations',
        complexity: 2,
        layout: {
          type: 'dual-pane',
          panes: ['pos', 'management'],
          areas: [
            { component: 'pos_terminal', area: 'pos-main' },
            { component: 'inventory_list', area: 'pos-secondary' },
            { component: 'sales_history', area: 'management-main' },
            { component: 'customer_list', area: 'management-secondary' }
          ]
        },
        theme: 'retail',
        responsive: false // POS typically fixed screen
      },
      restaurant_layout: {
        id: 'restaurant_layout',
        name: 'Restaurant Management',
        description: 'Tailored for restaurant operations',
        complexity: 3,
        layout: {
          type: 'tab-based',
          tabs: ['orders', 'tables', 'menu', 'inventory'],
          areas: [
            { component: 'navbar', area: 'header' },
            { component: 'table_management', area: 'tab-tables' },
            { component: 'pos_terminal', area: 'tab-orders' },
            { component: 'menu_management', area: 'tab-menu' },
            { component: 'inventory_list', area: 'tab-inventory' }
          ]
        },
        theme: 'restaurant',
        responsive: true
      }
    };

    Object.values(templates).forEach(template => {
      this.layoutTemplates.set(template.id, template);
    });
  }

  /**
   * Initialize theme configurations
   */
  initializeThemes() {
    const themes = {
      clean: {
        id: 'clean',
        name: 'Clean & Simple',
        colors: {
          primary: '#2563eb',
          secondary: '#64748b',
          accent: '#06b6d4',
          background: '#ffffff',
          surface: '#f8fafc',
          text: '#0f172a',
          textSecondary: '#475569'
        },
        typography: {
          fontFamily: 'Inter, sans-serif',
          fontSize: { base: 14, large: 18, small: 12 }
        },
        spacing: { base: 16, compact: 8, comfortable: 24 },
        borderRadius: 6,
        shadows: 'minimal'
      },
      professional: {
        id: 'professional',
        name: 'Professional',
        colors: {
          primary: '#1e40af',
          secondary: '#374151',
          accent: '#059669',
          background: '#ffffff',
          surface: '#f9fafb',
          text: '#111827',
          textSecondary: '#6b7280'
        },
        typography: {
          fontFamily: 'Roboto, sans-serif',
          fontSize: { base: 14, large: 16, small: 12 }
        },
        spacing: { base: 16, compact: 12, comfortable: 20 },
        borderRadius: 4,
        shadows: 'subtle'
      },
      retail: {
        id: 'retail',
        name: 'Retail Optimized',
        colors: {
          primary: '#dc2626',
          secondary: '#525252',
          accent: '#ea580c',
          background: '#ffffff',
          surface: '#fafafa',
          text: '#171717',
          textSecondary: '#737373'
        },
        typography: {
          fontFamily: 'Open Sans, sans-serif',
          fontSize: { base: 15, large: 18, small: 13 }
        },
        spacing: { base: 18, compact: 12, comfortable: 24 },
        borderRadius: 8,
        shadows: 'pronounced'
      },
      restaurant: {
        id: 'restaurant',
        name: 'Restaurant Theme',
        colors: {
          primary: '#b91c1c',
          secondary: '#44403c',
          accent: '#f59e0b',
          background: '#fffbeb',
          surface: '#fef3c7',
          text: '#451a03',
          textSecondary: '#92400e'
        },
        typography: {
          fontFamily: 'Poppins, sans-serif',
          fontSize: { base: 14, large: 17, small: 12 }
        },
        spacing: { base: 16, compact: 10, comfortable: 22 },
        borderRadius: 10,
        shadows: 'warm'
      }
    };

    Object.values(themes).forEach(theme => {
      this.themeConfigs.set(theme.id, theme);
    });
  }

  /**
   * Generate custom interface based on business profile
   */
  async generateInterface(businessProfile, requestedComplexity = null) {
    const interfaceId = uuidv4();
    
    try {
      logger.info(`Generating interface for ${businessProfile.basicInfo.name}`);

      // Determine complexity level
      const complexity = requestedComplexity || this.determineOptimalComplexity(businessProfile);

      // Select appropriate layout template
      const layoutTemplate = this.selectLayoutTemplate(businessProfile, complexity);

      // Select and configure components
      const components = this.selectComponents(businessProfile, complexity);

      // Generate navigation structure
      const navigation = this.generateNavigation(businessProfile, components);

      // Select theme
      const theme = this.selectTheme(businessProfile, complexity);

      // Generate responsive breakpoints
      const responsive = this.generateResponsiveConfig(businessProfile);

      // Create interface configuration
      const interfaceConfig = {
        id: interfaceId,
        businessId: businessProfile.businessId,
        businessName: businessProfile.basicInfo.name,
        complexity,
        layout: layoutTemplate,
        components,
        navigation,
        theme,
        responsive,
        features: this.generateFeatureList(components),
        customizations: this.generateCustomizations(businessProfile),
        integrations: this.suggestIntegrations(businessProfile),
        createdAt: Date.now(),
        version: '1.0'
      };

      // Generate actual UI code/config
      const generatedUI = await this.generateUICode(interfaceConfig);
      interfaceConfig.generatedUI = generatedUI;

      // Store interface
      this.interfaces.set(interfaceId, interfaceConfig);

      this.emit('interface:generated', {
        interfaceId,
        businessId: businessProfile.businessId,
        complexity,
        componentsCount: components.length
      });

      logger.info(`Interface generated successfully: ${interfaceId}`);

      return interfaceConfig;

    } catch (error) {
      logger.error('Failed to generate interface:', error);
      throw error;
    }
  }

  /**
   * Determine optimal complexity level based on business profile
   */
  determineOptimalComplexity(businessProfile) {
    let complexity = 1;

    // Business size factors
    if (businessProfile.basicInfo.employeeCount > 5) complexity++;
    if (businessProfile.basicInfo.employeeCount > 20) complexity++;
    if (businessProfile.basicInfo.employeeCount > 50) complexity++;

    // Technology comfort
    if (businessProfile.technology.comfortLevel >= 4) complexity++;
    if (businessProfile.technology.automationInterest >= 4) complexity++;

    // Existing systems
    const systemsCount = businessProfile.operations.currentSystems?.length || 0;
    if (systemsCount > 3) complexity++;
    if (systemsCount > 6) complexity++;

    // Industry complexity
    const complexIndustries = ['Manufacturing', 'Healthcare', 'Professional Services'];
    if (complexIndustries.includes(businessProfile.basicInfo.industry)) {
      complexity++;
    }

    // Challenges requiring advanced features
    const advancedChallenges = ['Quality control', 'Compliance', 'Supply chain'];
    const hasAdvancedChallenges = businessProfile.operations.biggestChallenges?.some(
      challenge => advancedChallenges.includes(challenge)
    );
    if (hasAdvancedChallenges) complexity++;

    return Math.min(Math.max(complexity, 1), 5);
  }

  /**
   * Select appropriate layout template
   */
  selectLayoutTemplate(businessProfile, complexity) {
    const industry = businessProfile.basicInfo.industry;
    const employeeCount = businessProfile.basicInfo.employeeCount;

    // Industry-specific layouts
    if (industry === 'Retail Store' && businessProfile.operations.currentSystems?.includes('Point of Sale (POS)')) {
      return this.layoutTemplates.get('retail_pos');
    }
    
    if (industry === 'Restaurant') {
      return this.layoutTemplates.get('restaurant_layout');
    }

    // Complexity-based selection
    if (complexity <= 2 || employeeCount <= 3) {
      return this.layoutTemplates.get('simple_dashboard');
    } else if (complexity <= 3) {
      return this.layoutTemplates.get('sidebar_layout');
    } else {
      return this.layoutTemplates.get('comprehensive_layout');
    }
  }

  /**
   * Select and configure components based on business needs
   */
  selectComponents(businessProfile, complexity) {
    const selectedComponents = [];
    const industry = businessProfile.basicInfo.industry;
    const challenges = businessProfile.operations.biggestChallenges || [];
    const currentSystems = businessProfile.operations.currentSystems || [];

    // Essential components for all businesses
    selectedComponents.push(
      this.componentLibrary.get('navbar'),
      this.componentLibrary.get('summary_cards'),
      this.componentLibrary.get('quick_actions')
    );

    // Add components based on complexity
    if (complexity >= 2) {
      selectedComponents.push(
        this.componentLibrary.get('recent_activity'),
        this.componentLibrary.get('sidebar')
      );
    }

    if (complexity >= 3) {
      selectedComponents.push(
        this.componentLibrary.get('charts_analytics'),
        this.componentLibrary.get('breadcrumbs')
      );
    }

    // Industry-specific components
    if (industry === 'Retail Store') {
      if (currentSystems.includes('Point of Sale (POS)') || challenges.includes('Customer management')) {
        selectedComponents.push(this.componentLibrary.get('pos_terminal'));
      }
      selectedComponents.push(
        this.componentLibrary.get('inventory_list'),
        this.componentLibrary.get('customer_list')
      );
      if (complexity >= 3) {
        selectedComponents.push(this.componentLibrary.get('loyalty_program'));
      }
    }

    if (industry === 'Restaurant') {
      selectedComponents.push(
        this.componentLibrary.get('table_management'),
        this.componentLibrary.get('menu_management'),
        this.componentLibrary.get('pos_terminal')
      );
      if (complexity >= 3) {
        selectedComponents.push(this.componentLibrary.get('inventory_list'));
      }
    }

    if (industry === 'Manufacturing') {
      selectedComponents.push(
        this.componentLibrary.get('inventory_list'),
        this.componentLibrary.get('production_planning')
      );
      if (complexity >= 4) {
        selectedComponents.push(this.componentLibrary.get('quality_control'));
      }
    }

    // Challenge-based components
    if (challenges.includes('Managing inventory')) {
      selectedComponents.push(
        this.componentLibrary.get('inventory_list'),
        this.componentLibrary.get('stock_alerts')
      );
      if (complexity >= 3) {
        selectedComponents.push(this.componentLibrary.get('barcode_scanner'));
      }
    }

    if (challenges.includes('Employee scheduling')) {
      selectedComponents.push(
        this.componentLibrary.get('employee_list'),
        this.componentLibrary.get('schedule_calendar'),
        this.componentLibrary.get('time_clock')
      );
    }

    if (challenges.includes('Security')) {
      selectedComponents.push(this.componentLibrary.get('security_cameras'));
      if (complexity >= 4) {
        selectedComponents.push(this.componentLibrary.get('access_control'));
      }
    }

    // Employee management for businesses with staff
    if (businessProfile.basicInfo.employeeCount > 0) {
      if (!selectedComponents.find(c => c.id === 'employee_list')) {
        selectedComponents.push(this.componentLibrary.get('employee_list'));
      }
      if (businessProfile.basicInfo.employeeCount > 5 && complexity >= 2) {
        selectedComponents.push(this.componentLibrary.get('schedule_calendar'));
      }
    }

    // Financial reporting for established businesses
    if (businessProfile.basicInfo.stage !== 'Planning/Startup' && complexity >= 3) {
      selectedComponents.push(this.componentLibrary.get('financial_reports'));
    }

    // Remove duplicates and filter by complexity
    return this.filterAndValidateComponents(selectedComponents, complexity, industry);
  }

  /**
   * Filter and validate component selection
   */
  filterAndValidateComponents(components, complexity, industry) {
    const uniqueComponents = [];
    const seen = new Set();

    components.forEach(component => {
      if (!component) return;
      
      if (!seen.has(component.id) && 
          component.complexity <= complexity &&
          (component.industries.includes('all') || component.industries.includes(industry))) {
        uniqueComponents.push(component);
        seen.add(component.id);
      }
    });

    return uniqueComponents;
  }

  /**
   * Generate navigation structure
   */
  generateNavigation(businessProfile, components) {
    const navigation = {
      type: 'hierarchical',
      items: []
    };

    // Dashboard (always first)
    navigation.items.push({
      id: 'dashboard',
      label: 'Dashboard',
      icon: 'dashboard',
      path: '/',
      order: 0
    });

    // Sales section
    const salesComponents = components.filter(c => c.type === 'sales');
    if (salesComponents.length > 0) {
      navigation.items.push({
        id: 'sales',
        label: 'Sales',
        icon: 'shopping_cart',
        path: '/sales',
        order: 1,
        children: salesComponents.map(c => ({
          id: c.id,
          label: c.component.replace(/([A-Z])/g, ' $1').trim(),
          path: `/sales/${c.id}`,
          component: c.id
        }))
      });
    }

    // Inventory section
    const inventoryComponents = components.filter(c => c.type === 'inventory');
    if (inventoryComponents.length > 0) {
      navigation.items.push({
        id: 'inventory',
        label: 'Inventory',
        icon: 'inventory',
        path: '/inventory',
        order: 2,
        children: inventoryComponents.map(c => ({
          id: c.id,
          label: c.component.replace(/([A-Z])/g, ' $1').trim(),
          path: `/inventory/${c.id}`,
          component: c.id
        }))
      });
    }

    // Employees section
    const employeeComponents = components.filter(c => c.type === 'employee');
    if (employeeComponents.length > 0) {
      navigation.items.push({
        id: 'employees',
        label: 'Employees',
        icon: 'people',
        path: '/employees',
        order: 3,
        children: employeeComponents.map(c => ({
          id: c.id,
          label: c.component.replace(/([A-Z])/g, ' $1').trim(),
          path: `/employees/${c.id}`,
          component: c.id
        }))
      });
    }

    // Customers section
    const customerComponents = components.filter(c => c.type === 'customer');
    if (customerComponents.length > 0) {
      navigation.items.push({
        id: 'customers',
        label: 'Customers',
        icon: 'person',
        path: '/customers',
        order: 4,
        children: customerComponents.map(c => ({
          id: c.id,
          label: c.component.replace(/([A-Z])/g, ' $1').trim(),
          path: `/customers/${c.id}`,
          component: c.id
        }))
      });
    }

    // Industry-specific sections
    if (businessProfile.basicInfo.industry === 'Restaurant') {
      const restaurantComponents = components.filter(c => c.type === 'restaurant');
      if (restaurantComponents.length > 0) {
        navigation.items.push({
          id: 'restaurant',
          label: 'Restaurant',
          icon: 'restaurant',
          path: '/restaurant',
          order: 5,
          children: restaurantComponents.map(c => ({
            id: c.id,
            label: c.component.replace(/([A-Z])/g, ' $1').trim(),
            path: `/restaurant/${c.id}`,
            component: c.id
          }))
        });
      }
    }

    // Reports section
    const reportComponents = components.filter(c => c.type === 'reports');
    if (reportComponents.length > 0) {
      navigation.items.push({
        id: 'reports',
        label: 'Reports',
        icon: 'assessment',
        path: '/reports',
        order: 8,
        children: reportComponents.map(c => ({
          id: c.id,
          label: c.component.replace(/([A-Z])/g, ' $1').trim(),
          path: `/reports/${c.id}`,
          component: c.id
        }))
      });
    }

    // Security section
    const securityComponents = components.filter(c => c.type === 'security');
    if (securityComponents.length > 0) {
      navigation.items.push({
        id: 'security',
        label: 'Security',
        icon: 'security',
        path: '/security',
        order: 9,
        children: securityComponents.map(c => ({
          id: c.id,
          label: c.component.replace(/([A-Z])/g, ' $1').trim(),
          path: `/security/${c.id}`,
          component: c.id
        }))
      });
    }

    // Settings (always last)
    navigation.items.push({
      id: 'settings',
      label: 'Settings',
      icon: 'settings',
      path: '/settings',
      order: 10
    });

    // Sort by order
    navigation.items.sort((a, b) => a.order - b.order);

    return navigation;
  }

  /**
   * Select theme based on business profile
   */
  selectTheme(businessProfile, complexity) {
    const industry = businessProfile.basicInfo.industry;
    
    if (industry === 'Restaurant') {
      return this.themeConfigs.get('restaurant');
    }
    
    if (industry === 'Retail Store') {
      return this.themeConfigs.get('retail');
    }
    
    if (complexity >= 4 || businessProfile.basicInfo.employeeCount > 20) {
      return this.themeConfigs.get('professional');
    }
    
    return this.themeConfigs.get('clean');
  }

  /**
   * Generate responsive configuration
   */
  generateResponsiveConfig(businessProfile) {
    const industry = businessProfile.basicInfo.industry;
    const employeeCount = businessProfile.basicInfo.employeeCount;

    // POS systems are typically fixed screen
    if (industry === 'Retail Store' && businessProfile.operations.currentSystems?.includes('Point of Sale (POS)')) {
      return {
        enabled: false,
        primaryDevice: 'desktop',
        breakpoints: {}
      };
    }

    return {
      enabled: true,
      primaryDevice: employeeCount > 10 ? 'desktop' : 'tablet',
      breakpoints: {
        mobile: { width: 768, columns: 1 },
        tablet: { width: 1024, columns: 2 },
        desktop: { width: 1200, columns: 3 },
        wide: { width: 1600, columns: 4 }
      },
      adaptiveComponents: true,
      mobileOptimized: employeeCount <= 5
    };
  }

  /**
   * Generate UI code/configuration
   */
  async generateUICode(interfaceConfig) {
    const uiCode = {
      react: await this.generateReactComponents(interfaceConfig),
      css: await this.generateCSS(interfaceConfig),
      config: await this.generateConfigFiles(interfaceConfig),
      routes: await this.generateRoutes(interfaceConfig)
    };

    return uiCode;
  }

  async generateReactComponents(interfaceConfig) {
    // This would generate actual React component code
    // For now, returning configuration that would be used by a code generator
    return {
      components: interfaceConfig.components.map(component => ({
        name: component.component,
        props: component.props,
        type: component.type,
        file: `src/components/${component.type}/${component.component}.jsx`
      })),
      layout: {
        template: interfaceConfig.layout.id,
        areas: interfaceConfig.layout.layout.areas,
        responsive: interfaceConfig.responsive
      }
    };
  }

  async generateCSS(interfaceConfig) {
    const theme = interfaceConfig.theme;
    return {
      variables: {
        '--primary-color': theme.colors.primary,
        '--secondary-color': theme.colors.secondary,
        '--accent-color': theme.colors.accent,
        '--background-color': theme.colors.background,
        '--text-color': theme.colors.text,
        '--font-family': theme.typography.fontFamily,
        '--border-radius': `${theme.borderRadius}px`,
        '--spacing-base': `${theme.spacing.base}px`
      },
      utilities: this.generateUtilityClasses(theme),
      responsive: this.generateResponsiveCSS(interfaceConfig.responsive)
    };
  }

  generateUtilityClasses(theme) {
    return {
      spacing: Object.entries(theme.spacing).map(([key, value]) => 
        `.p-${key} { padding: ${value}px; }`
      ).join('\n'),
      colors: Object.entries(theme.colors).map(([key, value]) => 
        `.text-${key} { color: ${value}; }\n.bg-${key} { background-color: ${value}; }`
      ).join('\n')
    };
  }

  generateResponsiveCSS(responsive) {
    if (!responsive.enabled) return '';

    return Object.entries(responsive.breakpoints).map(([breakpoint, config]) => 
      `@media (max-width: ${config.width}px) { .grid { grid-template-columns: repeat(${config.columns}, 1fr); } }`
    ).join('\n');
  }

  async generateConfigFiles(interfaceConfig) {
    return {
      navigation: interfaceConfig.navigation,
      features: interfaceConfig.features,
      theme: interfaceConfig.theme.id,
      complexity: interfaceConfig.complexity
    };
  }

  async generateRoutes(interfaceConfig) {
    const routes = [];
    
    interfaceConfig.navigation.items.forEach(item => {
      routes.push({
        path: item.path,
        component: item.id,
        exact: item.path === '/'
      });

      if (item.children) {
        item.children.forEach(child => {
          routes.push({
            path: child.path,
            component: child.component,
            parent: item.id
          });
        });
      }
    });

    return routes;
  }

  generateFeatureList(components) {
    const features = new Set();
    
    components.forEach(component => {
      features.add(component.type);
      Object.keys(component.props).forEach(prop => {
        if (component.props[prop]) {
          features.add(`${component.type}_${prop}`);
        }
      });
    });

    return Array.from(features);
  }

  generateCustomizations(businessProfile) {
    return {
      businessName: businessProfile.basicInfo.name,
      industry: businessProfile.basicInfo.industry,
      branding: {
        logo: null, // Would be uploaded separately
        colors: null, // Would use theme defaults unless customized
        tagline: null
      },
      preferences: {
        defaultView: 'dashboard',
        notifications: true,
        autoSave: true,
        theme: 'system' // system, light, dark
      }
    };
  }

  suggestIntegrations(businessProfile) {
    const integrations = [];
    const currentSystems = businessProfile.operations.currentSystems || [];

    if (currentSystems.includes('Accounting Software')) {
      integrations.push({
        type: 'accounting',
        name: 'QuickBooks Integration',
        description: 'Sync financial data with QuickBooks',
        priority: 'high'
      });
    }

    if (currentSystems.includes('Customer Relationship Management (CRM)')) {
      integrations.push({
        type: 'crm',
        name: 'CRM Integration',
        description: 'Connect with your existing CRM system',
        priority: 'medium'
      });
    }

    if (businessProfile.basicInfo.industry === 'Retail Store') {
      integrations.push({
        type: 'payment',
        name: 'Payment Processing',
        description: 'Accept credit cards and mobile payments',
        priority: 'high'
      });
    }

    return integrations;
  }

  /**
   * Get generated interface
   */
  getInterface(businessId) {
    for (const [id, interface] of this.interfaces) {
      if (interface.businessId === businessId) {
        return interface;
      }
    }
    throw new Error('Interface not found for business');
  }

  /**
   * Update interface complexity
   */
  async updateComplexity(interfaceId, newComplexity) {
    const interface = this.interfaces.get(interfaceId);
    if (!interface) {
      throw new Error('Interface not found');
    }

    // Get business profile to regenerate with new complexity
    const businessProfile = {
      businessId: interface.businessId,
      basicInfo: {
        name: interface.businessName,
        industry: interface.customizations.industry
      }
      // Would need full profile for proper regeneration
    };

    const updatedInterface = await this.generateInterface(businessProfile, newComplexity);
    
    this.emit('interface:updated', {
      interfaceId,
      oldComplexity: interface.complexity,
      newComplexity,
      componentsAdded: updatedInterface.components.length - interface.components.length
    });

    return updatedInterface;
  }
}