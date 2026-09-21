import { EventEmitter } from 'events';
import { v4 as uuidv4 } from 'uuid';
import QRCode from 'qrcode';
import { createCanvas, Canvas } from 'canvas';
import sharp from 'sharp';

export interface LabelPrinter {
  id: string;
  name: string;
  model: string;
  manufacturer: string;
  type: 'thermal' | 'inkjet' | 'laser' | 'dot-matrix';
  connection: {
    type: 'usb' | 'ethernet' | 'wifi' | 'bluetooth';
    address: string;
    port?: number;
  };
  capabilities: {
    maxWidth: number; // mm
    maxHeight: number; // mm
    minWidth: number; // mm
    minHeight: number; // mm
    resolution: { x: number; y: number }; // DPI
    colorSupport: boolean;
    duplex: boolean;
    cutter: boolean;
    peeler: boolean;
  };
  supportedMediaTypes: string[];
  currentMedia?: {
    type: string;
    width: number;
    height: number;
    remaining: number; // labels remaining
  };
  status: 'online' | 'offline' | 'busy' | 'error' | 'maintenance';
  errorMessage?: string;
  totalLabels: number;
  location: {
    facility: string;
    zone: string;
    position: string;
  };
  lastMaintenanceDate: Date;
  createdAt: Date;
  updatedAt: Date;
}

export interface LabelTemplate {
  id: string;
  name: string;
  description: string;
  category: 'shipping' | 'product' | 'qr-code' | 'barcode' | 'warning' | 'certification' | 'inventory';
  dimensions: {
    width: number; // mm
    height: number; // mm
  };
  elements: LabelElement[];
  variables: LabelVariable[];
  compatiblePrinters: string[];
  previewUrl?: string;
  isDefault: boolean;
  usageCount: number;
  createdBy: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface LabelElement {
  id: string;
  type: 'text' | 'barcode' | 'qrcode' | 'image' | 'line' | 'rectangle' | 'logo';
  position: {
    x: number; // mm from left
    y: number; // mm from top
  };
  size: {
    width: number; // mm
    height: number; // mm
  };
  properties: {
    content?: string;
    variable?: string;
    fontSize?: number;
    fontFamily?: string;
    fontWeight?: 'normal' | 'bold';
    textAlign?: 'left' | 'center' | 'right';
    color?: string;
    backgroundColor?: string;
    border?: {
      width: number;
      color: string;
      style: 'solid' | 'dashed' | 'dotted';
    };
    rotation?: number; // degrees
    barcodeType?: 'CODE128' | 'CODE39' | 'EAN13' | 'UPC-A' | 'DATAMATRIX';
    qrErrorLevel?: 'L' | 'M' | 'Q' | 'H';
    imageUrl?: string;
    imageScaling?: 'fit' | 'stretch' | 'crop';
  };
  conditional?: {
    showIf?: string;
    hideIf?: string;
  };
}

export interface LabelVariable {
  id: string;
  name: string;
  type: 'text' | 'number' | 'date' | 'boolean' | 'image' | 'computed';
  description: string;
  required: boolean;
  defaultValue?: any;
  validation?: {
    pattern?: string;
    minLength?: number;
    maxLength?: number;
    minValue?: number;
    maxValue?: number;
  };
  computeFunction?: string; // JavaScript function for computed variables
}

export interface PrintJob {
  id: string;
  templateId: string;
  printerId: string;
  copies: number;
  data: Record<string, any>;
  status: 'queued' | 'printing' | 'completed' | 'failed' | 'cancelled';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  submittedBy: string;
  submittedAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  errorMessage?: string;
  actualCopiesPrinted?: number;
  estimatedTime: number; // seconds
  actualTime?: number; // seconds
  cost?: number;
  previewGenerated: boolean;
  previewUrl?: string;
  metadata?: {
    orderNumber?: string;
    customerInfo?: any;
    partNumber?: string;
    batchId?: string;
  };
  createdAt: Date;
  updatedAt: Date;
}

export interface LabelBatch {
  id: string;
  name: string;
  description: string;
  templateId: string;
  printerId: string;
  dataSource: 'manual' | 'csv' | 'database' | 'api';
  dataSourceConfig?: {
    csvFile?: string;
    query?: string;
    apiEndpoint?: string;
    mapping?: Record<string, string>;
  };
  totalLabels: number;
  printedLabels: number;
  failedLabels: number;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  jobs: string[]; // Print job IDs
  startedAt?: Date;
  completedAt?: Date;
  estimatedTime: number;
  actualTime?: number;
  createdBy: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface PrinterMetrics {
  printerId: string;
  totalJobs: number;
  successfulJobs: number;
  failedJobs: number;
  totalLabels: number;
  averageJobTime: number;
  uptime: number;
  errorRate: number;
  throughputPerHour: number;
  mediaUsage: {
    labelsUsed: number;
    rollsConsumed: number;
    costPerLabel: number;
  };
  maintenanceHistory: {
    lastCleaning: Date;
    lastCalibration: Date;
    totalMaintenanceHours: number;
    maintenanceCost: number;
  };
}

export class LabelPrintingSystem extends EventEmitter {
  private printers: Map<string, LabelPrinter> = new Map();
  private templates: Map<string, LabelTemplate> = new Map();
  private printJobs: Map<string, PrintJob> = new Map();
  private batches: Map<string, LabelBatch> = new Map();
  private printQueue: string[] = [];
  private queueProcessor?: NodeJS.Timeout;

  constructor() {
    super();
    this.initializeDefaultData();
    this.startQueueProcessor();
  }

  private initializeDefaultData(): void {
    this.createDefaultPrinters();
    this.createDefaultTemplates();
  }

  private createDefaultPrinters(): void {
    const printers: Omit<LabelPrinter, 'id' | 'totalLabels' | 'createdAt' | 'updatedAt'>[] = [
      {
        name: 'Zebra ZD620',
        model: 'ZD620',
        manufacturer: 'Zebra Technologies',
        type: 'thermal',
        connection: {
          type: 'ethernet',
          address: '192.168.1.50',
          port: 9100
        },
        capabilities: {
          maxWidth: 108,
          maxHeight: 3200,
          minWidth: 12,
          minHeight: 12,
          resolution: { x: 300, y: 300 },
          colorSupport: false,
          duplex: false,
          cutter: true,
          peeler: true
        },
        supportedMediaTypes: ['direct-thermal', 'thermal-transfer'],
        currentMedia: {
          type: 'direct-thermal',
          width: 102,
          height: 152,
          remaining: 250
        },
        status: 'online',
        location: {
          facility: 'Main Floor',
          zone: 'Packaging Area',
          position: 'Station 1'
        },
        lastMaintenanceDate: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000)
      },
      {
        name: 'Brother QL-820NWB',
        model: 'QL-820NWB',
        manufacturer: 'Brother',
        type: 'thermal',
        connection: {
          type: 'wifi',
          address: '192.168.1.51'
        },
        capabilities: {
          maxWidth: 62,
          maxHeight: 300,
          minWidth: 12,
          minHeight: 12,
          resolution: { x: 300, y: 600 },
          colorSupport: true,
          duplex: false,
          cutter: true,
          peeler: false
        },
        supportedMediaTypes: ['thermal-paper', 'tape'],
        currentMedia: {
          type: 'thermal-paper',
          width: 62,
          height: 29,
          remaining: 400
        },
        status: 'online',
        location: {
          facility: 'Main Floor',
          zone: 'Quality Control',
          position: 'QC Station'
        },
        lastMaintenanceDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
      },
      {
        name: 'Dymo LabelWriter 4XL',
        model: 'LabelWriter 4XL',
        manufacturer: 'Dymo',
        type: 'thermal',
        connection: {
          type: 'usb',
          address: 'USB001'
        },
        capabilities: {
          maxWidth: 104,
          maxHeight: 159,
          minWidth: 6,
          minHeight: 6,
          resolution: { x: 300, y: 300 },
          colorSupport: false,
          duplex: false,
          cutter: false,
          peeler: false
        },
        supportedMediaTypes: ['direct-thermal'],
        currentMedia: {
          type: 'direct-thermal',
          width: 104,
          height: 159,
          remaining: 220
        },
        status: 'online',
        location: {
          facility: 'Office Area',
          zone: 'Shipping Desk',
          position: 'Desktop'
        },
        lastMaintenanceDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
      }
    ];

    printers.forEach(printerData => {
      const printer: LabelPrinter = {
        ...printerData,
        id: uuidv4(),
        totalLabels: Math.floor(Math.random() * 50000) + 10000,
        createdAt: new Date(),
        updatedAt: new Date()
      };
      this.printers.set(printer.id, printer);
    });
  }

  private createDefaultTemplates(): void {
    const printerIds = Array.from(this.printers.keys());

    const templates: Omit<LabelTemplate, 'id' | 'usageCount' | 'createdAt' | 'updatedAt'>[] = [
      {
        name: 'Shipping Label',
        description: 'Standard shipping label with address and tracking',
        category: 'shipping',
        dimensions: { width: 100, height: 150 },
        elements: [
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 5, y: 5 },
            size: { width: 90, height: 8 },
            properties: {
              content: 'FROM:',
              fontSize: 10,
              fontWeight: 'bold',
              textAlign: 'left'
            }
          },
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 5, y: 13 },
            size: { width: 90, height: 25 },
            properties: {
              variable: 'fromAddress',
              fontSize: 8,
              textAlign: 'left'
            }
          },
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 5, y: 45 },
            size: { width: 90, height: 8 },
            properties: {
              content: 'TO:',
              fontSize: 10,
              fontWeight: 'bold',
              textAlign: 'left'
            }
          },
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 5, y: 53 },
            size: { width: 90, height: 35 },
            properties: {
              variable: 'toAddress',
              fontSize: 9,
              textAlign: 'left'
            }
          },
          {
            id: uuidv4(),
            type: 'barcode',
            position: { x: 5, y: 95 },
            size: { width: 90, height: 15 },
            properties: {
              variable: 'trackingNumber',
              barcodeType: 'CODE128'
            }
          },
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 5, y: 113 },
            size: { width: 90, height: 6 },
            properties: {
              variable: 'trackingNumber',
              fontSize: 8,
              textAlign: 'center'
            }
          },
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 5, y: 125 },
            size: { width: 90, height: 20 },
            properties: {
              variable: 'serviceType',
              fontSize: 14,
              fontWeight: 'bold',
              textAlign: 'center'
            }
          }
        ],
        variables: [
          {
            id: uuidv4(),
            name: 'fromAddress',
            type: 'text',
            description: 'Sender address (multiple lines)',
            required: true
          },
          {
            id: uuidv4(),
            name: 'toAddress',
            type: 'text',
            description: 'Recipient address (multiple lines)',
            required: true
          },
          {
            id: uuidv4(),
            name: 'trackingNumber',
            type: 'text',
            description: 'Tracking number for barcode and text',
            required: true,
            validation: {
              pattern: '^[A-Z0-9]{10,20}$'
            }
          },
          {
            id: uuidv4(),
            name: 'serviceType',
            type: 'text',
            description: 'Shipping service type',
            required: true,
            defaultValue: 'STANDARD'
          }
        ],
        compatiblePrinters: printerIds,
        isDefault: true,
        createdBy: 'system'
      },
      {
        name: 'Product Label',
        description: 'Product identification label with QR code',
        category: 'product',
        dimensions: { width: 50, height: 30 },
        elements: [
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 2, y: 2 },
            size: { width: 46, height: 6 },
            properties: {
              variable: 'productName',
              fontSize: 8,
              fontWeight: 'bold',
              textAlign: 'center'
            }
          },
          {
            id: uuidv4(),
            type: 'qrcode',
            position: { x: 2, y: 10 },
            size: { width: 15, height: 15 },
            properties: {
              variable: 'qrData',
              qrErrorLevel: 'M'
            }
          },
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 19, y: 10 },
            size: { width: 29, height: 4 },
            properties: {
              content: 'Part #:',
              fontSize: 6,
              textAlign: 'left'
            }
          },
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 19, y: 14 },
            size: { width: 29, height: 4 },
            properties: {
              variable: 'partNumber',
              fontSize: 7,
              fontWeight: 'bold',
              textAlign: 'left'
            }
          },
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 19, y: 18 },
            size: { width: 29, height: 4 },
            properties: {
              content: 'Date:',
              fontSize: 6,
              textAlign: 'left'
            }
          },
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 19, y: 22 },
            size: { width: 29, height: 4 },
            properties: {
              variable: 'productionDate',
              fontSize: 6,
              textAlign: 'left'
            }
          }
        ],
        variables: [
          {
            id: uuidv4(),
            name: 'productName',
            type: 'text',
            description: 'Product name or title',
            required: true
          },
          {
            id: uuidv4(),
            name: 'partNumber',
            type: 'text',
            description: 'Part number or SKU',
            required: true
          },
          {
            id: uuidv4(),
            name: 'productionDate',
            type: 'date',
            description: 'Production date',
            required: true,
            defaultValue: new Date().toISOString().split('T')[0]
          },
          {
            id: uuidv4(),
            name: 'qrData',
            type: 'computed',
            description: 'QR code data (computed from other variables)',
            required: true,
            computeFunction: 'JSON.stringify({part: data.partNumber, date: data.productionDate, name: data.productName})'
          }
        ],
        compatiblePrinters: printerIds,
        isDefault: true,
        createdBy: 'system'
      },
      {
        name: 'Inventory Label',
        description: 'Simple inventory tracking label',
        category: 'inventory',
        dimensions: { width: 38, height: 25 },
        elements: [
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 2, y: 2 },
            size: { width: 34, height: 5 },
            properties: {
              variable: 'itemName',
              fontSize: 8,
              fontWeight: 'bold',
              textAlign: 'center'
            }
          },
          {
            id: uuidv4(),
            type: 'barcode',
            position: { x: 2, y: 8 },
            size: { width: 34, height: 10 },
            properties: {
              variable: 'itemCode',
              barcodeType: 'CODE39'
            }
          },
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 2, y: 19 },
            size: { width: 34, height: 4 },
            properties: {
              variable: 'itemCode',
              fontSize: 6,
              textAlign: 'center'
            }
          }
        ],
        variables: [
          {
            id: uuidv4(),
            name: 'itemName',
            type: 'text',
            description: 'Item or part name',
            required: true
          },
          {
            id: uuidv4(),
            name: 'itemCode',
            type: 'text',
            description: 'Item code or barcode data',
            required: true,
            validation: {
              pattern: '^[A-Z0-9-]+$'
            }
          }
        ],
        compatiblePrinters: printerIds.slice(0, 2), // Only thermal printers
        isDefault: true,
        createdBy: 'system'
      },
      {
        name: 'Quality Control Label',
        description: 'QC inspection and approval label',
        category: 'certification',
        dimensions: { width: 60, height: 40 },
        elements: [
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 5, y: 3 },
            size: { width: 50, height: 6 },
            properties: {
              content: 'QUALITY APPROVED',
              fontSize: 10,
              fontWeight: 'bold',
              textAlign: 'center',
              color: '#008000'
            }
          },
          {
            id: uuidv4(),
            type: 'rectangle',
            position: { x: 3, y: 1 },
            size: { width: 54, height: 10 },
            properties: {
              border: {
                width: 1,
                color: '#008000',
                style: 'solid'
              }
            }
          },
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 5, y: 14 },
            size: { width: 25, height: 4 },
            properties: {
              content: 'Inspector:',
              fontSize: 7,
              textAlign: 'left'
            }
          },
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 32, y: 14 },
            size: { width: 23, height: 4 },
            properties: {
              variable: 'inspector',
              fontSize: 7,
              textAlign: 'left'
            }
          },
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 5, y: 20 },
            size: { width: 25, height: 4 },
            properties: {
              content: 'Date:',
              fontSize: 7,
              textAlign: 'left'
            }
          },
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 32, y: 20 },
            size: { width: 23, height: 4 },
            properties: {
              variable: 'inspectionDate',
              fontSize: 7,
              textAlign: 'left'
            }
          },
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 5, y: 26 },
            size: { width: 25, height: 4 },
            properties: {
              content: 'Job ID:',
              fontSize: 7,
              textAlign: 'left'
            }
          },
          {
            id: uuidv4(),
            type: 'text',
            position: { x: 32, y: 26 },
            size: { width: 23, height: 4 },
            properties: {
              variable: 'jobId',
              fontSize: 7,
              textAlign: 'left'
            }
          },
          {
            id: uuidv4(),
            type: 'qrcode',
            position: { x: 22, y: 32 },
            size: { width: 6, height: 6 },
            properties: {
              variable: 'qrCode',
              qrErrorLevel: 'L'
            }
          }
        ],
        variables: [
          {
            id: uuidv4(),
            name: 'inspector',
            type: 'text',
            description: 'Inspector name or ID',
            required: true
          },
          {
            id: uuidv4(),
            name: 'inspectionDate',
            type: 'date',
            description: 'Date of inspection',
            required: true,
            defaultValue: new Date().toISOString().split('T')[0]
          },
          {
            id: uuidv4(),
            name: 'jobId',
            type: 'text',
            description: 'Print job ID',
            required: true
          },
          {
            id: uuidv4(),
            name: 'qrCode',
            type: 'computed',
            description: 'QR code with inspection data',
            required: true,
            computeFunction: 'JSON.stringify({inspector: data.inspector, date: data.inspectionDate, job: data.jobId, status: "approved"})'
          }
        ],
        compatiblePrinters: printerIds,
        isDefault: true,
        createdBy: 'system'
      }
    ];

    templates.forEach(templateData => {
      const template: LabelTemplate = {
        ...templateData,
        id: uuidv4(),
        usageCount: Math.floor(Math.random() * 500),
        createdAt: new Date(),
        updatedAt: new Date()
      };
      this.templates.set(template.id, template);
    });
  }

  private startQueueProcessor(): void {
    this.queueProcessor = setInterval(() => {
      this.processQueue();
    }, 5000); // Process every 5 seconds
  }

  private async processQueue(): Promise<void> {
    if (this.printQueue.length === 0) return;

    const jobId = this.printQueue[0];
    const job = this.printJobs.get(jobId);
    
    if (!job || job.status !== 'queued') {
      this.printQueue.shift();
      return;
    }

    const printer = this.printers.get(job.printerId);
    if (!printer || printer.status !== 'online') {
      // Skip for now, will retry later
      return;
    }

    // Start printing
    this.printQueue.shift();
    await this.startPrinting(job);
  }

  private async startPrinting(job: PrintJob): Promise<void> {
    const printer = this.printers.get(job.printerId);
    if (!printer) return;

    job.status = 'printing';
    job.startedAt = new Date();
    job.updatedAt = new Date();

    printer.status = 'busy';
    printer.updatedAt = new Date();

    this.emit('printJobStarted', { job, printer });

    try {
      // Generate the actual label
      const labelBuffer = await this.generateLabel(job);
      
      // Simulate printing time
      const printTime = job.estimatedTime * 1000; // Convert to milliseconds
      
      setTimeout(async () => {
        await this.completePrintJob(job, labelBuffer);
      }, printTime);

    } catch (error) {
      await this.failPrintJob(job, error.message);
    }
  }

  private async generateLabel(job: PrintJob): Promise<Buffer> {
    const template = this.templates.get(job.templateId);
    if (!template) {
      throw new Error('Template not found');
    }

    // Create canvas with template dimensions (convert mm to pixels at 300 DPI)
    const pixelsPerMM = 300 / 25.4; // 300 DPI conversion
    const canvasWidth = Math.round(template.dimensions.width * pixelsPerMM);
    const canvasHeight = Math.round(template.dimensions.height * pixelsPerMM);

    const canvas = createCanvas(canvasWidth, canvasHeight);
    const ctx = canvas.getContext('2d');

    // White background
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);

    // Process computed variables first
    const processedData = await this.processVariables(template, job.data);

    // Render elements
    for (const element of template.elements) {
      await this.renderElement(ctx, element, processedData, pixelsPerMM);
    }

    return canvas.toBuffer('image/png');
  }

  private async processVariables(template: LabelTemplate, data: Record<string, any>): Promise<Record<string, any>> {
    const processedData = { ...data };

    // Process computed variables
    for (const variable of template.variables) {
      if (variable.type === 'computed' && variable.computeFunction) {
        try {
          // Simple evaluation of compute function
          // In production, this would use a sandboxed environment
          const computeFunc = new Function('data', `return ${variable.computeFunction}`);
          processedData[variable.name] = computeFunc(processedData);
        } catch (error) {
          console.warn(`Failed to compute variable ${variable.name}:`, error);
          processedData[variable.name] = variable.defaultValue || '';
        }
      } else if (variable.type === 'date' && !data[variable.name] && variable.defaultValue) {
        processedData[variable.name] = variable.defaultValue;
      }
    }

    return processedData;
  }

  private async renderElement(ctx: any, element: LabelElement, data: Record<string, any>, pixelsPerMM: number): Promise<void> {
    const x = element.position.x * pixelsPerMM;
    const y = element.position.y * pixelsPerMM;
    const width = element.size.width * pixelsPerMM;
    const height = element.size.height * pixelsPerMM;

    // Apply rotation if specified
    if (element.properties.rotation) {
      ctx.save();
      ctx.translate(x + width / 2, y + height / 2);
      ctx.rotate((element.properties.rotation * Math.PI) / 180);
      ctx.translate(-width / 2, -height / 2);
    }

    switch (element.type) {
      case 'text':
        await this.renderText(ctx, element, data, width, height);
        break;
      case 'barcode':
        await this.renderBarcode(ctx, element, data, width, height);
        break;
      case 'qrcode':
        await this.renderQRCode(ctx, element, data, width, height);
        break;
      case 'rectangle':
        await this.renderRectangle(ctx, element, width, height);
        break;
      case 'line':
        await this.renderLine(ctx, element, width, height);
        break;
      case 'image':
        await this.renderImage(ctx, element, data, width, height);
        break;
    }

    if (element.properties.rotation) {
      ctx.restore();
    }
  }

  private async renderText(ctx: any, element: LabelElement, data: Record<string, any>, width: number, height: number): Promise<void> {
    const content = element.properties.variable ? 
      (data[element.properties.variable] || '') : 
      (element.properties.content || '');

    const fontSize = (element.properties.fontSize || 12) * (300 / 72); // Convert pt to pixels at 300 DPI
    const fontFamily = element.properties.fontFamily || 'Arial';
    const fontWeight = element.properties.fontWeight || 'normal';

    ctx.font = `${fontWeight} ${fontSize}px ${fontFamily}`;
    ctx.fillStyle = element.properties.color || 'black';

    // Handle multi-line text
    const lines = content.toString().split('\n');
    const lineHeight = fontSize * 1.2;
    
    lines.forEach((line: string, index: number) => {
      let textX = 0;
      const textY = (index + 1) * lineHeight;

      switch (element.properties.textAlign) {
        case 'center':
          textX = width / 2;
          ctx.textAlign = 'center';
          break;
        case 'right':
          textX = width;
          ctx.textAlign = 'right';
          break;
        default:
          textX = 0;
          ctx.textAlign = 'left';
      }

      ctx.fillText(line, textX, textY);
    });
  }

  private async renderBarcode(ctx: any, element: LabelElement, data: Record<string, any>, width: number, height: number): Promise<void> {
    const content = element.properties.variable ? 
      (data[element.properties.variable] || '') : 
      (element.properties.content || '');

    // Simple barcode simulation (vertical lines)
    // In production, would use a proper barcode library
    const barcodeData = content.toString();
    const barWidth = width / (barcodeData.length * 2);

    ctx.fillStyle = 'black';
    
    for (let i = 0; i < barcodeData.length; i++) {
      const charCode = barcodeData.charCodeAt(i);
      const barHeight = height * (0.6 + (charCode % 4) * 0.1); // Vary height based on character
      
      ctx.fillRect(i * barWidth * 2, height - barHeight, barWidth, barHeight);
    }
  }

  private async renderQRCode(ctx: any, element: LabelElement, data: Record<string, any>, width: number, height: number): Promise<void> {
    const content = element.properties.variable ? 
      (data[element.properties.variable] || '') : 
      (element.properties.content || '');

    try {
      const qrCodeDataUrl = await QRCode.toDataURL(content.toString(), {
        errorCorrectionLevel: element.properties.qrErrorLevel || 'M',
        type: 'image/png',
        margin: 1,
        width: Math.min(width, height)
      });

      const img = new Image();
      img.onload = () => {
        ctx.drawImage(img, 0, 0, width, height);
      };
      img.src = qrCodeDataUrl;
    } catch (error) {
      console.warn('Failed to generate QR code:', error);
      // Fallback to simple rectangle
      ctx.fillStyle = 'black';
      ctx.fillRect(0, 0, width, height);
    }
  }

  private async renderRectangle(ctx: any, element: LabelElement, width: number, height: number): Promise<void> {
    if (element.properties.backgroundColor) {
      ctx.fillStyle = element.properties.backgroundColor;
      ctx.fillRect(0, 0, width, height);
    }

    if (element.properties.border) {
      ctx.strokeStyle = element.properties.border.color;
      ctx.lineWidth = element.properties.border.width;
      
      if (element.properties.border.style === 'dashed') {
        ctx.setLineDash([5, 5]);
      } else if (element.properties.border.style === 'dotted') {
        ctx.setLineDash([2, 2]);
      }
      
      ctx.strokeRect(0, 0, width, height);
      ctx.setLineDash([]);
    }
  }

  private async renderLine(ctx: any, element: LabelElement, width: number, height: number): Promise<void> {
    ctx.strokeStyle = element.properties.color || 'black';
    ctx.lineWidth = element.properties.border?.width || 1;
    
    ctx.beginPath();
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();
  }

  private async renderImage(ctx: any, element: LabelElement, data: Record<string, any>, width: number, height: number): Promise<void> {
    const imageUrl = element.properties.imageUrl;
    if (!imageUrl) return;

    // In production, would load actual image
    // For now, render placeholder
    ctx.fillStyle = '#cccccc';
    ctx.fillRect(0, 0, width, height);
    
    ctx.fillStyle = 'black';
    ctx.font = `${Math.min(width, height) / 4}px Arial`;
    ctx.textAlign = 'center';
    ctx.fillText('IMG', width / 2, height / 2);
  }

  private async completePrintJob(job: PrintJob, labelBuffer: Buffer): Promise<void> {
    const printer = this.printers.get(job.printerId);
    if (!printer) return;

    job.status = 'completed';
    job.completedAt = new Date();
    job.actualTime = (job.completedAt.getTime() - job.startedAt!.getTime()) / 1000;
    job.actualCopiesPrinted = job.copies;
    job.cost = this.calculatePrintCost(job, printer);
    job.updatedAt = new Date();

    printer.status = 'online';
    printer.totalLabels += job.copies;
    if (printer.currentMedia) {
      printer.currentMedia.remaining -= job.copies;
    }
    printer.updatedAt = new Date();

    this.emit('printJobCompleted', { job, printer, labelBuffer });
  }

  private async failPrintJob(job: PrintJob, errorMessage: string): Promise<void> {
    const printer = this.printers.get(job.printerId);
    if (!printer) return;

    job.status = 'failed';
    job.completedAt = new Date();
    job.errorMessage = errorMessage;
    job.updatedAt = new Date();

    printer.status = 'error';
    printer.errorMessage = errorMessage;
    printer.updatedAt = new Date();

    this.emit('printJobFailed', { job, printer, error: errorMessage });
  }

  private calculatePrintCost(job: PrintJob, printer: LabelPrinter): number {
    // Simple cost calculation based on media type and printer
    const baseCostPerLabel = printer.type === 'thermal' ? 0.05 : 0.08;
    const totalCost = job.copies * baseCostPerLabel;
    
    return Math.round(totalCost * 100) / 100;
  }

  async submitPrintJob(jobData: Omit<PrintJob, 'id' | 'status' | 'submittedAt' | 'previewGenerated' | 'createdAt' | 'updatedAt'>): Promise<PrintJob> {
    const job: PrintJob = {
      ...jobData,
      id: uuidv4(),
      status: 'queued',
      submittedAt: new Date(),
      previewGenerated: false,
      createdAt: new Date(),
      updatedAt: new Date()
    };

    // Validate printer compatibility
    const template = this.templates.get(job.templateId);
    const printer = this.printers.get(job.printerId);
    
    if (!template || !printer) {
      throw new Error('Invalid template or printer');
    }

    if (!template.compatiblePrinters.includes(job.printerId)) {
      throw new Error('Printer not compatible with template');
    }

    // Validate required variables
    const missingVariables = template.variables
      .filter(variable => variable.required && !job.data[variable.name])
      .map(variable => variable.name);

    if (missingVariables.length > 0) {
      throw new Error(`Missing required variables: ${missingVariables.join(', ')}`);
    }

    // Estimate print time (simplified calculation)
    const template_area = template.dimensions.width * template.dimensions.height;
    const timePerLabel = Math.max(5, template_area / 100); // seconds
    job.estimatedTime = timePerLabel * job.copies;

    this.printJobs.set(job.id, job);
    this.printQueue.push(job.id);

    // Generate preview
    setTimeout(async () => {
      try {
        const previewBuffer = await this.generateLabel(job);
        job.previewUrl = `/previews/${job.id}.png`;
        job.previewGenerated = true;
        job.updatedAt = new Date();
        
        this.emit('previewGenerated', { job, previewBuffer });
      } catch (error) {
        console.warn('Failed to generate preview:', error);
      }
    }, 1000);

    this.emit('printJobSubmitted', job);
    return job;
  }

  async cancelPrintJob(jobId: string): Promise<boolean> {
    const job = this.printJobs.get(jobId);
    if (!job || job.status === 'completed' || job.status === 'failed') {
      return false;
    }

    job.status = 'cancelled';
    job.completedAt = new Date();
    job.updatedAt = new Date();

    // Remove from queue if queued
    const queueIndex = this.printQueue.indexOf(jobId);
    if (queueIndex > -1) {
      this.printQueue.splice(queueIndex, 1);
    }

    // If printing, mark printer as available
    if (job.status === 'printing') {
      const printer = this.printers.get(job.printerId);
      if (printer) {
        printer.status = 'online';
        printer.updatedAt = new Date();
      }
    }

    this.emit('printJobCancelled', job);
    return true;
  }

  async createBatch(batchData: Omit<LabelBatch, 'id' | 'totalLabels' | 'printedLabels' | 'failedLabels' | 'status' | 'jobs' | 'estimatedTime' | 'createdAt' | 'updatedAt'>): Promise<LabelBatch> {
    const batch: LabelBatch = {
      ...batchData,
      id: uuidv4(),
      totalLabels: 0,
      printedLabels: 0,
      failedLabels: 0,
      status: 'pending',
      jobs: [],
      estimatedTime: 0,
      createdAt: new Date(),
      updatedAt: new Date()
    };

    this.batches.set(batch.id, batch);
    this.emit('batchCreated', batch);

    return batch;
  }

  async processBatch(batchId: string, batchData: any[]): Promise<void> {
    const batch = this.batches.get(batchId);
    if (!batch) {
      throw new Error('Batch not found');
    }

    batch.status = 'processing';
    batch.startedAt = new Date();
    batch.totalLabels = batchData.length;
    batch.updatedAt = new Date();

    this.emit('batchProcessingStarted', batch);

    for (const data of batchData) {
      try {
        const job = await this.submitPrintJob({
          templateId: batch.templateId,
          printerId: batch.printerId,
          copies: 1,
          data,
          priority: 'normal',
          submittedBy: batch.createdBy,
          estimatedTime: 0,
          metadata: {
            batchId: batch.id
          }
        });

        batch.jobs.push(job.id);
        batch.estimatedTime += job.estimatedTime;
        
      } catch (error) {
        batch.failedLabels++;
        console.error('Failed to create batch job:', error);
      }
    }

    batch.updatedAt = new Date();
    this.emit('batchProcessingCompleted', batch);
  }

  async getPrinterMetrics(printerId: string, days: number = 30): Promise<PrinterMetrics> {
    const printer = this.printers.get(printerId);
    if (!printer) {
      throw new Error('Printer not found');
    }

    const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
    const jobs = Array.from(this.printJobs.values())
      .filter(job => job.printerId === printerId && job.createdAt >= startDate);

    const totalJobs = jobs.length;
    const successfulJobs = jobs.filter(job => job.status === 'completed').length;
    const failedJobs = jobs.filter(job => job.status === 'failed').length;
    const totalLabels = jobs.reduce((sum, job) => sum + (job.actualCopiesPrinted || 0), 0);

    const completedJobs = jobs.filter(job => job.actualTime);
    const averageJobTime = completedJobs.length > 0
      ? completedJobs.reduce((sum, job) => sum + job.actualTime!, 0) / completedJobs.length
      : 0;

    const uptime = 95; // Simplified - would be calculated from actual uptime data
    const errorRate = totalJobs > 0 ? (failedJobs / totalJobs) * 100 : 0;
    const throughputPerHour = totalLabels / (days * 24);

    return {
      printerId,
      totalJobs,
      successfulJobs,
      failedJobs,
      totalLabels,
      averageJobTime: Math.round(averageJobTime * 100) / 100,
      uptime: Math.round(uptime * 100) / 100,
      errorRate: Math.round(errorRate * 100) / 100,
      throughputPerHour: Math.round(throughputPerHour * 100) / 100,
      mediaUsage: {
        labelsUsed: totalLabels,
        rollsConsumed: Math.ceil(totalLabels / 500), // Assume 500 labels per roll
        costPerLabel: 0.05
      },
      maintenanceHistory: {
        lastCleaning: printer.lastMaintenanceDate,
        lastCalibration: printer.lastMaintenanceDate,
        totalMaintenanceHours: 5,
        maintenanceCost: 150
      }
    };
  }

  // Getter methods
  getPrinter(id: string): LabelPrinter | undefined {
    return this.printers.get(id);
  }

  getAllPrinters(): LabelPrinter[] {
    return Array.from(this.printers.values());
  }

  getOnlinePrinters(): LabelPrinter[] {
    return Array.from(this.printers.values()).filter(p => p.status === 'online');
  }

  getTemplate(id: string): LabelTemplate | undefined {
    return this.templates.get(id);
  }

  getAllTemplates(): LabelTemplate[] {
    return Array.from(this.templates.values());
  }

  getTemplatesByCategory(category: LabelTemplate['category']): LabelTemplate[] {
    return Array.from(this.templates.values()).filter(t => t.category === category);
  }

  getPrintJob(id: string): PrintJob | undefined {
    return this.printJobs.get(id);
  }

  getAllPrintJobs(): PrintJob[] {
    return Array.from(this.printJobs.values());
  }

  getJobsByStatus(status: PrintJob['status']): PrintJob[] {
    return Array.from(this.printJobs.values()).filter(j => j.status === status);
  }

  getBatch(id: string): LabelBatch | undefined {
    return this.batches.get(id);
  }

  getAllBatches(): LabelBatch[] {
    return Array.from(this.batches.values());
  }

  getQueueStatus(): { position: number; estimatedWaitTime: number }[] {
    return this.printQueue.map((jobId, index) => {
      const job = this.printJobs.get(jobId);
      const estimatedWaitTime = this.printQueue.slice(0, index)
        .reduce((total, id) => {
          const queueJob = this.printJobs.get(id);
          return total + (queueJob?.estimatedTime || 0);
        }, 0);

      return {
        position: index + 1,
        estimatedWaitTime
      };
    });
  }

  destroy(): void {
    if (this.queueProcessor) {
      clearInterval(this.queueProcessor);
      this.queueProcessor = undefined;
    }
    
    this.removeAllListeners();
  }
}

export const labelPrinting = new LabelPrintingSystem();