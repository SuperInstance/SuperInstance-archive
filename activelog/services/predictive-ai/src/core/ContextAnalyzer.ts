export class ContextAnalyzer {
  
  async getCurrentContext(providedContext?: any): Promise<any> {
    const now = new Date();
    
    const baseContext = {
      timestamp: now,
      timeOfDay: now.getHours(),
      dayOfWeek: now.getDay(),
      month: now.getMonth(),
      isWeekend: now.getDay() === 0 || now.getDay() === 6,
      isBusinessHours: now.getHours() >= 9 && now.getHours() <= 17,
      season: this.getSeason(now.getMonth()),
      ...providedContext
    };
    
    return this.enrichContext(baseContext);
  }

  private getSeason(month: number): string {
    if (month >= 2 && month <= 4) return 'spring';
    if (month >= 5 && month <= 7) return 'summer';
    if (month >= 8 && month <= 10) return 'fall';
    return 'winter';
  }

  private enrichContext(context: any): any {
    context.workMode = this.determineWorkMode(context);
    context.activityLevel = this.predictActivityLevel(context);
    context.focusTime = this.isFocusTime(context);
    
    return context;
  }

  private determineWorkMode(context: any): 'work' | 'personal' | 'mixed' {
    if (!context.isBusinessHours || context.isWeekend) {
      return 'personal';
    }
    
    if (context.isBusinessHours && !context.isWeekend) {
      return 'work';
    }
    
    return 'mixed';
  }

  private predictActivityLevel(context: any): 'low' | 'medium' | 'high' {
    if (context.timeOfDay >= 22 || context.timeOfDay <= 6) {
      return 'low';
    }
    
    if (context.timeOfDay >= 9 && context.timeOfDay <= 11) {
      return 'high';
    }
    
    if (context.timeOfDay >= 14 && context.timeOfDay <= 16) {
      return 'high';
    }
    
    return 'medium';
  }

  private isFocusTime(context: any): boolean {
    return (context.timeOfDay >= 9 && context.timeOfDay <= 11) ||
           (context.timeOfDay >= 14 && context.timeOfDay <= 16);
  }
}