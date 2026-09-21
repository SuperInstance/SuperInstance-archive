import { Plugin, PluginManifest, PluginContext, TriggerEvent, TriggerResult, api_endpoint, trigger_handler, validate_params, cache } from '@activelog/plugin-sdk';
import * as d3 from 'd3';
import * as Plotly from 'plotly.js';
import { Chart, ChartConfiguration, ChartType } from 'chart.js';
import * as fs from 'fs/promises';
import * as path from 'path';
import { createCanvas } from 'canvas';
import puppeteer from 'puppeteer';
import sharp from 'sharp';
import * as _ from 'lodash';
import * as moment from 'moment';

interface ChartConfig {
  id: string;
  title: string;
  type: ChartType;
  library: 'plotly' | 'd3' | 'chartjs';
  data_source: string;
  data_query: string;
  styling: ChartStyling;
  options: any;
  created_at: Date;
  updated_at: Date;
}

interface ChartStyling {
  colors: string[];
  font_family: string;
  font_size: number;
  background_color: string;
  border_color: string;
  grid_color: string;
}

interface Dashboard {
  id: string;
  title: string;
  description: string;
  widgets: DashboardWidget[];
  layout: DashboardLayout;
  created_at: Date;
  updated_at: Date;
}

interface DashboardWidget {
  id: string;
  chart_id: string;
  position: { x: number; y: number; width: number; height: number };
  title: string;
  refresh_interval?: number;
}

interface DashboardLayout {
  columns: number;
  rows: number;
  gap: number;
  responsive: boolean;
}

interface DataSource {
  name: string;
  type: 'database' | 'api' | 'file';
  connection: any;
  schema?: any;
}

interface ExportOptions {
  format: 'png' | 'jpg' | 'svg' | 'pdf' | 'html';
  width: number;
  height: number;
  quality: number;
  include_data: boolean;
}

/**
 * Data Visualization Plugin for ActiveLog
 * 
 * Creates interactive charts, graphs, and dashboards from ActiveLog data
 * using multiple charting libraries and export formats.
 */
export default class DataVisualizationPlugin extends Plugin {
  private charts = new Map<string, ChartConfig>();
  private dashboards = new Map<string, Dashboard>();
  private dataSources = new Map<string, DataSource>();
  private browser?: puppeteer.Browser;

  getManifest(): PluginManifest {
    return require('./manifest.json');
  }

  /**
   * Initialize the plugin with charting libraries and data sources
   */
  async onLoad(context: PluginContext): Promise<void> {
    await super.onLoad(context);
    this.log('info', 'Data Visualization plugin loaded');
    
    // Initialize browser for PDF/image exports
    try {
      this.browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
      });
    } catch (error) {
      this.log('warn', 'Failed to initialize browser for exports', error);
    }
    
    await this.loadExistingCharts();
    await this.loadExistingDashboards();
    await this.initializeDataSources();
  }

  /**
   * Activate the plugin and start services
   */
  async onActivate(context: PluginContext): Promise<void> {
    await super.onActivate(context);
    this.log('info', 'Data Visualization plugin activated');
    
    // Create necessary database tables
    await this.createTables();
    
    // Start dashboard refresh scheduler if enabled
    const config = this.getConfig();
    if (config.dashboard_settings?.auto_refresh) {
      await this.startDashboardRefresh();
    }
  }

  /**
   * Handle trigger events
   */
  @trigger_handler('user-action', 'Handle user-triggered visualization actions')
  async onTrigger(event: TriggerEvent, context: PluginContext): Promise<TriggerResult> {
    try {
      switch (event.type) {
        case 'user-action':
          return await this.handleUserAction(event.data);
        case 'schedule':
          return await this.handleScheduledTask(event.data);
        default:
          return { success: false, error: 'Unsupported trigger type' };
      }
    } catch (error) {
      this.log('error', 'Trigger execution failed', error);
      return { success: false, error: (error as Error).message };
    }
  }

  /**
   * List all saved charts
   */
  @api_endpoint('/charts', 'GET', 'List all saved charts')
  @cache(300) // Cache for 5 minutes
  async getCharts(page: number = 1, limit: number = 20, search?: string): Promise<any> {
    try {
      const sql = search 
        ? 'SELECT * FROM charts WHERE title LIKE ? ORDER BY updated_at DESC LIMIT ? OFFSET ?'
        : 'SELECT * FROM charts ORDER BY updated_at DESC LIMIT ? OFFSET ?';
      
      const params = search 
        ? [`%${search}%`, limit, (page - 1) * limit]
        : [limit, (page - 1) * limit];
      
      const result = await this.dbQuery(sql, params);
      
      const charts = result.rows.map(row => ({
        ...row,
        styling: JSON.parse(row.styling),
        options: JSON.parse(row.options)
      }));

      // Get total count
      const countSql = search 
        ? 'SELECT COUNT(*) as total FROM charts WHERE title LIKE ?'
        : 'SELECT COUNT(*) as total FROM charts';
      const countParams = search ? [`%${search}%`] : [];
      const countResult = await this.dbQuery(countSql, countParams);
      
      return {
        success: true,
        charts,
        pagination: {
          page,
          limit,
          total: countResult.rows[0].total,
          pages: Math.ceil(countResult.rows[0].total / limit)
        }
      };
    } catch (error) {
      this.log('error', 'Failed to get charts', error);
      return { success: false, error: (error as Error).message };
    }
  }

  /**
   * Create a new chart
   */
  @api_endpoint('/charts', 'POST', 'Create a new chart')
  @validate_params({
    title: { type: 'string', required: true, minLength: 1, maxLength: 255 },
    type: { type: 'string', required: true },
    data_source: { type: 'string', required: true },
    data_query: { type: 'string', required: true }
  })
  async createChart(chartData: any): Promise<any> {
    try {
      const config = this.getConfig();
      const chartId = this.generateId();
      
      // Set default styling from theme
      const theme = config.theme || {};
      const styling: ChartStyling = {
        colors: [theme.primary_color || '#3498db', theme.secondary_color || '#2ecc71'],
        font_family: theme.font_family || 'Arial, sans-serif',
        font_size: 12,
        background_color: theme.background_color || '#ffffff',
        border_color: '#cccccc',
        grid_color: '#eeeeee',
        ...chartData.styling
      };

      const chart: ChartConfig = {
        id: chartId,
        title: chartData.title,
        type: chartData.type,
        library: chartData.library || config.default_chart_library || 'plotly',
        data_source: chartData.data_source,
        data_query: chartData.data_query,
        styling,
        options: chartData.options || {},
        created_at: new Date(),
        updated_at: new Date()
      };

      // Validate data query
      const testData = await this.executeDataQuery(chart.data_source, chart.data_query, true);
      if (!testData || testData.length === 0) {
        return { success: false, error: 'Data query returned no results' };
      }

      // Save chart
      await this.saveChart(chart);
      
      this.log('info', `Chart created: ${chart.title} (${chartId})`);
      
      // Track analytics
      await this.trackEvent('chart_created', {
        chart_id: chartId,
        type: chart.type,
        library: chart.library,
        data_source: chart.data_source
      });

      return {
        success: true,
        chart: {
          id: chartId,
          title: chart.title,
          type: chart.type,
          library: chart.library,
          created_at: chart.created_at
        }
      };
    } catch (error) {
      this.log('error', 'Failed to create chart', error);
      return { success: false, error: (error as Error).message };
    }
  }

  /**
   * Get chart by ID with rendered data
   */
  @api_endpoint('/charts/:id', 'GET', 'Get chart by ID')
  @cache(180) // Cache for 3 minutes
  async getChart(id: string, includeData: boolean = false): Promise<any> {
    try {
      const chart = await this.loadChart(id);
      if (!chart) {
        return { success: false, error: 'Chart not found' };
      }

      let responseData: any = {
        success: true,
        chart: {
          id: chart.id,
          title: chart.title,
          type: chart.type,
          library: chart.library,
          styling: chart.styling,
          options: chart.options,
          created_at: chart.created_at,
          updated_at: chart.updated_at
        }
      };

      if (includeData) {
        // Get chart data
        const data = await this.executeDataQuery(chart.data_source, chart.data_query);
        responseData.chart.data = data;
        
        // Generate chart specification based on library
        const chartSpec = await this.generateChartSpec(chart, data);
        responseData.chart.spec = chartSpec;
      }

      return responseData;
    } catch (error) {
      this.log('error', `Failed to get chart ${id}`, error);
      return { success: false, error: (error as Error).message };
    }
  }

  /**
   * Update chart
   */
  @api_endpoint('/charts/:id', 'PUT', 'Update chart')
  async updateChart(id: string, updates: any): Promise<any> {
    try {
      const chart = await this.loadChart(id);
      if (!chart) {
        return { success: false, error: 'Chart not found' };
      }

      // Update chart properties
      if (updates.title) chart.title = updates.title;
      if (updates.type) chart.type = updates.type;
      if (updates.data_query) chart.data_query = updates.data_query;
      if (updates.styling) chart.styling = { ...chart.styling, ...updates.styling };
      if (updates.options) chart.options = { ...chart.options, ...updates.options };
      
      chart.updated_at = new Date();

      // Validate updated data query if changed
      if (updates.data_query) {
        const testData = await this.executeDataQuery(chart.data_source, chart.data_query, true);
        if (!testData || testData.length === 0) {
          return { success: false, error: 'Updated data query returns no results' };
        }
      }

      await this.saveChart(chart);
      
      this.log('info', `Chart updated: ${chart.title} (${id})`);

      return {
        success: true,
        chart: {
          id: chart.id,
          title: chart.title,
          updated_at: chart.updated_at
        }
      };
    } catch (error) {
      this.log('error', `Failed to update chart ${id}`, error);
      return { success: false, error: (error as Error).message };
    }
  }

  /**
   * Delete chart
   */
  @api_endpoint('/charts/:id', 'DELETE', 'Delete chart')
  async deleteChart(id: string): Promise<any> {
    try {
      const chart = await this.loadChart(id);
      if (!chart) {
        return { success: false, error: 'Chart not found' };
      }

      // Remove from database
      await this.dbQuery('DELETE FROM charts WHERE id = ?', [id]);
      
      // Remove from cache
      this.charts.delete(id);
      
      this.log('info', `Chart deleted: ${chart.title} (${id})`);

      return { success: true, message: 'Chart deleted successfully' };
    } catch (error) {
      this.log('error', `Failed to delete chart ${id}`, error);
      return { success: false, error: (error as Error).message };
    }
  }

  /**
   * Export chart to file
   */
  @api_endpoint('/charts/:id/export', 'POST', 'Export chart to file')
  async exportChart(id: string, exportOptions: ExportOptions): Promise<any> {
    try {
      const chart = await this.loadChart(id);
      if (!chart) {
        return { success: false, error: 'Chart not found' };
      }

      // Get chart data
      const data = await this.executeDataQuery(chart.data_source, chart.data_query);
      
      // Generate chart
      const chartSpec = await this.generateChartSpec(chart, data);
      
      // Export based on format
      const exportPath = await this.exportChartToFile(chart, chartSpec, exportOptions);
      
      this.log('info', `Chart exported: ${chart.title} to ${exportOptions.format}`);
      
      // Track export
      await this.trackEvent('chart_exported', {
        chart_id: id,
        format: exportOptions.format,
        width: exportOptions.width,
        height: exportOptions.height
      });

      return {
        success: true,
        export_path: exportPath,
        format: exportOptions.format,
        size: {
          width: exportOptions.width,
          height: exportOptions.height
        }
      };
    } catch (error) {
      this.log('error', `Failed to export chart ${id}`, error);
      return { success: false, error: (error as Error).message };
    }
  }

  /**
   * List all dashboards
   */
  @api_endpoint('/dashboards', 'GET', 'List all dashboards')
  async getDashboards(): Promise<any> {
    try {
      const sql = 'SELECT * FROM dashboards ORDER BY updated_at DESC';
      const result = await this.dbQuery(sql);
      
      const dashboards = result.rows.map(row => ({
        ...row,
        widgets: JSON.parse(row.widgets),
        layout: JSON.parse(row.layout)
      }));

      return {
        success: true,
        dashboards
      };
    } catch (error) {
      this.log('error', 'Failed to get dashboards', error);
      return { success: false, error: (error as Error).message };
    }
  }

  /**
   * Create new dashboard
   */
  @api_endpoint('/dashboards', 'POST', 'Create new dashboard')
  @validate_params({
    title: { type: 'string', required: true },
    description: { type: 'string' }
  })
  async createDashboard(dashboardData: any): Promise<any> {
    try {
      const dashboardId = this.generateId();
      
      const dashboard: Dashboard = {
        id: dashboardId,
        title: dashboardData.title,
        description: dashboardData.description || '',
        widgets: [],
        layout: dashboardData.layout || { columns: 12, rows: 6, gap: 16, responsive: true },
        created_at: new Date(),
        updated_at: new Date()
      };

      await this.saveDashboard(dashboard);
      
      this.log('info', `Dashboard created: ${dashboard.title} (${dashboardId})`);

      return {
        success: true,
        dashboard: {
          id: dashboardId,
          title: dashboard.title,
          created_at: dashboard.created_at
        }
      };
    } catch (error) {
      this.log('error', 'Failed to create dashboard', error);
      return { success: false, error: (error as Error).message };
    }
  }

  /**
   * Get dashboard by ID
   */
  @api_endpoint('/dashboards/:id', 'GET', 'Get dashboard by ID')
  async getDashboard(id: string): Promise<any> {
    try {
      const dashboard = await this.loadDashboard(id);
      if (!dashboard) {
        return { success: false, error: 'Dashboard not found' };
      }

      // Load chart data for each widget
      const widgetsWithData = await Promise.all(
        dashboard.widgets.map(async (widget) => {
          try {
            const chart = await this.loadChart(widget.chart_id);
            if (chart) {
              const data = await this.executeDataQuery(chart.data_source, chart.data_query);
              const chartSpec = await this.generateChartSpec(chart, data);
              
              return {
                ...widget,
                chart: {
                  id: chart.id,
                  title: chart.title,
                  type: chart.type,
                  library: chart.library,
                  spec: chartSpec
                }
              };
            }
            return widget;
          } catch (error) {
            this.log('warn', `Failed to load chart data for widget ${widget.id}`, error);
            return widget;
          }
        })
      );

      return {
        success: true,
        dashboard: {
          ...dashboard,
          widgets: widgetsWithData
        }
      };
    } catch (error) {
      this.log('error', `Failed to get dashboard ${id}`, error);
      return { success: false, error: (error as Error).message };
    }
  }

  /**
   * Get data from source for visualization
   */
  @api_endpoint('/data/:source', 'GET', 'Get data from source for visualization')
  @cache(120) // Cache for 2 minutes
  async getData(source: string, query: string, limit: number = 1000): Promise<any> {
    try {
      if (!this.dataSources.has(source)) {
        return { success: false, error: 'Data source not found' };
      }

      const data = await this.executeDataQuery(source, query, false, limit);
      
      return {
        success: true,
        data,
        source,
        count: data.length
      };
    } catch (error) {
      this.log('error', `Failed to get data from ${source}`, error);
      return { success: false, error: (error as Error).message };
    }
  }

  /**
   * Get chart templates
   */
  @api_endpoint('/templates', 'GET', 'List chart templates')
  async getTemplates(): Promise<any> {
    const templates = [
      {
        id: 'line_chart',
        name: 'Line Chart',
        description: 'Time series line chart',
        type: 'line',
        library: 'plotly',
        sample_query: 'SELECT date, value FROM metrics WHERE date >= NOW() - INTERVAL 30 DAY'
      },
      {
        id: 'bar_chart',
        name: 'Bar Chart',
        description: 'Categorical bar chart',
        type: 'bar',
        library: 'plotly',
        sample_query: 'SELECT category, COUNT(*) as count FROM data GROUP BY category'
      },
      {
        id: 'pie_chart',
        name: 'Pie Chart',
        description: 'Pie chart for proportions',
        type: 'pie',
        library: 'plotly',
        sample_query: 'SELECT category, COUNT(*) as count FROM data GROUP BY category'
      },
      {
        id: 'scatter_plot',
        name: 'Scatter Plot',
        description: 'X-Y scatter plot',
        type: 'scatter',
        library: 'plotly',
        sample_query: 'SELECT x_value, y_value FROM data_points'
      },
      {
        id: 'heatmap',
        name: 'Heatmap',
        description: 'Correlation heatmap',
        type: 'heatmap',
        library: 'd3',
        sample_query: 'SELECT x, y, value FROM heatmap_data'
      }
    ];

    return {
      success: true,
      templates
    };
  }

  // Private helper methods

  private async createTables(): Promise<void> {
    // Charts table
    const chartsSql = `
      CREATE TABLE IF NOT EXISTS charts (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        type TEXT NOT NULL,
        library TEXT NOT NULL,
        data_source TEXT NOT NULL,
        data_query TEXT NOT NULL,
        styling TEXT NOT NULL,
        options TEXT NOT NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL
      )
    `;
    
    // Dashboards table
    const dashboardsSql = `
      CREATE TABLE IF NOT EXISTS dashboards (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        widgets TEXT NOT NULL,
        layout TEXT NOT NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL
      )
    `;

    await this.dbQuery(chartsSql);
    await this.dbQuery(dashboardsSql);
  }

  private async loadExistingCharts(): Promise<void> {
    try {
      const result = await this.dbQuery('SELECT * FROM charts');
      
      for (const row of result.rows) {
        const chart: ChartConfig = {
          ...row,
          styling: JSON.parse(row.styling),
          options: JSON.parse(row.options),
          created_at: new Date(row.created_at),
          updated_at: new Date(row.updated_at)
        };
        
        this.charts.set(chart.id, chart);
      }
      
      this.log('info', `Loaded ${this.charts.size} existing charts`);
    } catch (error) {
      this.log('error', 'Failed to load existing charts', error);
    }
  }

  private async loadExistingDashboards(): Promise<void> {
    try {
      const result = await this.dbQuery('SELECT * FROM dashboards');
      
      for (const row of result.rows) {
        const dashboard: Dashboard = {
          ...row,
          widgets: JSON.parse(row.widgets),
          layout: JSON.parse(row.layout),
          created_at: new Date(row.created_at),
          updated_at: new Date(row.updated_at)
        };
        
        this.dashboards.set(dashboard.id, dashboard);
      }
      
      this.log('info', `Loaded ${this.dashboards.size} existing dashboards`);
    } catch (error) {
      this.log('error', 'Failed to load existing dashboards', error);
    }
  }

  private async initializeDataSources(): Promise<void> {
    // Default database data source
    this.dataSources.set('database', {
      name: 'ActiveLog Database',
      type: 'database',
      connection: 'default'
    });
    
    // Add other data sources based on configuration
    // This could be extended to support external APIs, files, etc.
  }

  private async executeDataQuery(source: string, query: string, testOnly: boolean = false, limit?: number): Promise<any[]> {
    const dataSource = this.dataSources.get(source);
    if (!dataSource) {
      throw new Error(`Data source '${source}' not found`);
    }

    if (dataSource.type === 'database') {
      // Apply data limits from configuration
      const config = this.getConfig();
      const maxDataPoints = config.data_limits?.max_data_points || 10000;
      
      if (limit) {
        query += ` LIMIT ${Math.min(limit, maxDataPoints)}`;
      } else if (!testOnly) {
        query += ` LIMIT ${maxDataPoints}`;
      } else {
        query += ' LIMIT 1';
      }

      const result = await this.dbQuery(query);
      return result.rows;
    }
    
    // Handle other data source types (API, files, etc.)
    throw new Error(`Data source type '${dataSource.type}' not implemented`);
  }

  private async generateChartSpec(chart: ChartConfig, data: any[]): Promise<any> {
    switch (chart.library) {
      case 'plotly':
        return this.generatePlotlySpec(chart, data);
      case 'd3':
        return this.generateD3Spec(chart, data);
      case 'chartjs':
        return this.generateChartJsSpec(chart, data);
      default:
        throw new Error(`Chart library '${chart.library}' not supported`);
    }
  }

  private generatePlotlySpec(chart: ChartConfig, data: any[]): any {
    const spec: any = {
      data: [],
      layout: {
        title: chart.title,
        font: {
          family: chart.styling.font_family,
          size: chart.styling.font_size,
          color: chart.styling.background_color === '#ffffff' ? '#000' : '#fff'
        },
        paper_bgcolor: chart.styling.background_color,
        plot_bgcolor: chart.styling.background_color,
        ...chart.options.layout
      }
    };

    // Generate traces based on chart type
    switch (chart.type) {
      case 'line':
        spec.data.push({
          type: 'scatter',
          mode: 'lines+markers',
          x: data.map(d => Object.values(d)[0]),
          y: data.map(d => Object.values(d)[1]),
          line: { color: chart.styling.colors[0] },
          marker: { color: chart.styling.colors[0] }
        });
        break;
        
      case 'bar':
        spec.data.push({
          type: 'bar',
          x: data.map(d => Object.values(d)[0]),
          y: data.map(d => Object.values(d)[1]),
          marker: { color: chart.styling.colors[0] }
        });
        break;
        
      case 'pie':
        spec.data.push({
          type: 'pie',
          labels: data.map(d => Object.values(d)[0]),
          values: data.map(d => Object.values(d)[1]),
          marker: { colors: chart.styling.colors }
        });
        break;
        
      case 'scatter':
        spec.data.push({
          type: 'scatter',
          mode: 'markers',
          x: data.map(d => Object.values(d)[0]),
          y: data.map(d => Object.values(d)[1]),
          marker: { 
            color: chart.styling.colors[0],
            size: 8
          }
        });
        break;
    }

    return spec;
  }

  private generateD3Spec(chart: ChartConfig, data: any[]): any {
    // D3 specification would be more complex
    // This is a simplified version
    return {
      library: 'd3',
      type: chart.type,
      data,
      styling: chart.styling,
      options: chart.options
    };
  }

  private generateChartJsSpec(chart: ChartConfig, data: any[]): ChartConfiguration {
    const config: ChartConfiguration = {
      type: chart.type as ChartType,
      data: {
        labels: data.map(d => Object.values(d)[0] as string),
        datasets: [{
          label: chart.title,
          data: data.map(d => Object.values(d)[1] as number),
          backgroundColor: chart.styling.colors[0],
          borderColor: chart.styling.colors[0],
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        plugins: {
          title: {
            display: true,
            text: chart.title,
            font: {
              family: chart.styling.font_family,
              size: chart.styling.font_size
            }
          }
        },
        ...chart.options
      }
    };

    return config;
  }

  private async exportChartToFile(chart: ChartConfig, chartSpec: any, options: ExportOptions): Promise<string> {
    const fileName = `${chart.id}_${Date.now()}.${options.format}`;
    const filePath = path.join('/tmp', fileName);

    if (options.format === 'png' || options.format === 'jpg') {
      await this.exportAsImage(chartSpec, filePath, options);
    } else if (options.format === 'svg') {
      await this.exportAsSVG(chartSpec, filePath, options);
    } else if (options.format === 'pdf') {
      await this.exportAsPDF(chartSpec, filePath, options);
    } else if (options.format === 'html') {
      await this.exportAsHTML(chart, chartSpec, filePath, options);
    }

    return filePath;
  }

  private async exportAsImage(chartSpec: any, filePath: string, options: ExportOptions): Promise<void> {
    if (this.browser) {
      // Use Puppeteer to render chart and take screenshot
      const page = await this.browser.newPage();
      await page.setViewport({ width: options.width, height: options.height });
      
      const htmlContent = this.generateChartHTML(chartSpec);
      await page.setContent(htmlContent);
      
      await page.screenshot({
        path: filePath,
        type: options.format === 'png' ? 'png' : 'jpeg',
        quality: options.format === 'jpg' ? options.quality : undefined,
        fullPage: true
      });
      
      await page.close();
    } else {
      throw new Error('Browser not available for image export');
    }
  }

  private async exportAsSVG(chartSpec: any, filePath: string, options: ExportOptions): Promise<void> {
    // Generate SVG using D3 or similar
    const svgContent = `<svg width="${options.width}" height="${options.height}">
      <!-- Chart SVG content would go here -->
      <text x="50" y="50">Chart SVG Export - Not Implemented</text>
    </svg>`;
    
    await fs.writeFile(filePath, svgContent);
  }

  private async exportAsPDF(chartSpec: any, filePath: string, options: ExportOptions): Promise<void> {
    if (this.browser) {
      const page = await this.browser.newPage();
      await page.setViewport({ width: options.width, height: options.height });
      
      const htmlContent = this.generateChartHTML(chartSpec);
      await page.setContent(htmlContent);
      
      await page.pdf({
        path: filePath,
        width: options.width,
        height: options.height,
        printBackground: true
      });
      
      await page.close();
    } else {
      throw new Error('Browser not available for PDF export');
    }
  }

  private async exportAsHTML(chart: ChartConfig, chartSpec: any, filePath: string, options: ExportOptions): Promise<void> {
    const htmlContent = this.generateChartHTML(chartSpec, true);
    await fs.writeFile(filePath, htmlContent);
  }

  private generateChartHTML(chartSpec: any, standalone: boolean = false): string {
    const plotlyScript = standalone 
      ? '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>'
      : '';

    return `
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chart Export</title>
        ${plotlyScript}
        <style>
            body { margin: 0; padding: 20px; font-family: Arial, sans-serif; }
            #chart { width: 100%; height: 100vh; }
        </style>
    </head>
    <body>
        <div id="chart"></div>
        <script>
            const spec = ${JSON.stringify(chartSpec)};
            if (typeof Plotly !== 'undefined') {
                Plotly.newPlot('chart', spec.data, spec.layout);
            } else {
                document.getElementById('chart').innerHTML = '<p>Plotly.js required for chart rendering</p>';
            }
        </script>
    </body>
    </html>`;
  }

  private async saveChart(chart: ChartConfig): Promise<void> {
    const sql = `
      INSERT OR REPLACE INTO charts 
      (id, title, type, library, data_source, data_query, styling, options, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `;
    
    await this.dbQuery(sql, [
      chart.id,
      chart.title,
      chart.type,
      chart.library,
      chart.data_source,
      chart.data_query,
      JSON.stringify(chart.styling),
      JSON.stringify(chart.options),
      chart.created_at.toISOString(),
      chart.updated_at.toISOString()
    ]);
    
    this.charts.set(chart.id, chart);
  }

  private async loadChart(id: string): Promise<ChartConfig | undefined> {
    if (this.charts.has(id)) {
      return this.charts.get(id);
    }
    
    const result = await this.dbQuery('SELECT * FROM charts WHERE id = ?', [id]);
    if (result.rows.length > 0) {
      const row = result.rows[0];
      const chart: ChartConfig = {
        ...row,
        styling: JSON.parse(row.styling),
        options: JSON.parse(row.options),
        created_at: new Date(row.created_at),
        updated_at: new Date(row.updated_at)
      };
      
      this.charts.set(id, chart);
      return chart;
    }
    
    return undefined;
  }

  private async saveDashboard(dashboard: Dashboard): Promise<void> {
    const sql = `
      INSERT OR REPLACE INTO dashboards 
      (id, title, description, widgets, layout, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `;
    
    await this.dbQuery(sql, [
      dashboard.id,
      dashboard.title,
      dashboard.description,
      JSON.stringify(dashboard.widgets),
      JSON.stringify(dashboard.layout),
      dashboard.created_at.toISOString(),
      dashboard.updated_at.toISOString()
    ]);
    
    this.dashboards.set(dashboard.id, dashboard);
  }

  private async loadDashboard(id: string): Promise<Dashboard | undefined> {
    if (this.dashboards.has(id)) {
      return this.dashboards.get(id);
    }
    
    const result = await this.dbQuery('SELECT * FROM dashboards WHERE id = ?', [id]);
    if (result.rows.length > 0) {
      const row = result.rows[0];
      const dashboard: Dashboard = {
        ...row,
        widgets: JSON.parse(row.widgets),
        layout: JSON.parse(row.layout),
        created_at: new Date(row.created_at),
        updated_at: new Date(row.updated_at)
      };
      
      this.dashboards.set(id, dashboard);
      return dashboard;
    }
    
    return undefined;
  }

  private generateId(): string {
    return Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
  }

  private async handleUserAction(data: any): Promise<TriggerResult> {
    if (data.action === 'create_visualization') {
      // Handle user-triggered visualization creation
      return { success: true, data: { message: 'Visualization created' } };
    }
    
    return { success: false, error: 'Unknown user action' };
  }

  private async handleScheduledTask(data: any): Promise<TriggerResult> {
    // Generate daily dashboard reports
    this.log('info', 'Generating scheduled dashboard reports');
    
    // This could generate and email dashboard snapshots
    
    return { success: true, data: { message: 'Daily reports generated' } };
  }

  private async startDashboardRefresh(): Promise<void> {
    // Implementation for dashboard auto-refresh would go here
    this.log('info', 'Dashboard auto-refresh started');
  }

  async onDeactivate(context: PluginContext): Promise<void> {
    if (this.browser) {
      await this.browser.close();
    }
    await super.onDeactivate(context);
  }
}