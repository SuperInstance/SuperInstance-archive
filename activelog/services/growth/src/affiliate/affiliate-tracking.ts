import { NextRequest } from 'next/server';
import crypto from 'crypto';

export interface AffiliateUser {
  id: string;
  email: string;
  name: string;
  affiliateCode: string;
  commissionRate: number;
  totalEarnings: number;
  status: 'active' | 'pending' | 'suspended';
  createdAt: Date;
  updatedAt: Date;
}

export interface AffiliateClick {
  id: string;
  affiliateId: string;
  clickedAt: Date;
  ipAddress: string;
  userAgent: string;
  referrerUrl?: string;
  landingPage: string;
  converted: boolean;
  conversionValue?: number;
}

export interface AffiliateCommission {
  id: string;
  affiliateId: string;
  orderId: string;
  commissionAmount: number;
  commissionRate: number;
  orderValue: number;
  status: 'pending' | 'approved' | 'paid';
  createdAt: Date;
  paidAt?: Date;
}

export interface AffiliateLink {
  id: string;
  affiliateId: string;
  targetUrl: string;
  shortCode: string;
  clicks: number;
  conversions: number;
  createdAt: Date;
}

export interface AffiliateAnalytics {
  totalClicks: number;
  totalConversions: number;
  conversionRate: number;
  totalCommissions: number;
  pendingCommissions: number;
  topPerformers: AffiliateUser[];
  recentActivity: AffiliateClick[];
}

export class AffiliateTrackingSystem {
  private affiliates: Map<string, AffiliateUser> = new Map();
  private clicks: Map<string, AffiliateClick> = new Map();
  private commissions: Map<string, AffiliateCommission> = new Map();
  private links: Map<string, AffiliateLink> = new Map();

  async createAffiliate(data: {
    email: string;
    name: string;
    commissionRate?: number;
  }): Promise<AffiliateUser> {
    const affiliate: AffiliateUser = {
      id: crypto.randomUUID(),
      email: data.email,
      name: data.name,
      affiliateCode: this.generateAffiliateCode(),
      commissionRate: data.commissionRate || 0.15,
      totalEarnings: 0,
      status: 'pending',
      createdAt: new Date(),
      updatedAt: new Date()
    };

    this.affiliates.set(affiliate.id, affiliate);
    return affiliate;
  }

  async approveAffiliate(affiliateId: string): Promise<boolean> {
    const affiliate = this.affiliates.get(affiliateId);
    if (!affiliate) return false;

    affiliate.status = 'active';
    affiliate.updatedAt = new Date();
    return true;
  }

  async generateAffiliateLink(affiliateId: string, targetUrl: string): Promise<string | null> {
    const affiliate = this.affiliates.get(affiliateId);
    if (!affiliate || affiliate.status !== 'active') return null;

    const shortCode = crypto.randomBytes(8).toString('hex');
    const link: AffiliateLink = {
      id: crypto.randomUUID(),
      affiliateId,
      targetUrl,
      shortCode,
      clicks: 0,
      conversions: 0,
      createdAt: new Date()
    };

    this.links.set(shortCode, link);
    return `https://activelogapp.com/ref/${shortCode}`;
  }

  async trackClick(request: NextRequest, shortCode: string): Promise<AffiliateClick | null> {
    const link = this.links.get(shortCode);
    if (!link) return null;

    const click: AffiliateClick = {
      id: crypto.randomUUID(),
      affiliateId: link.affiliateId,
      clickedAt: new Date(),
      ipAddress: this.getClientIP(request),
      userAgent: request.headers.get('user-agent') || '',
      referrerUrl: request.headers.get('referer') || undefined,
      landingPage: link.targetUrl,
      converted: false
    };

    this.clicks.set(click.id, click);
    link.clicks++;

    this.setCookie(request, 'affiliate_code', link.affiliateId, 30);
    return click;
  }

  async trackConversion(orderId: string, orderValue: number, customerInfo: any): Promise<AffiliateCommission | null> {
    const affiliateId = this.getCookieValue('affiliate_code', customerInfo.cookies);
    if (!affiliateId) return null;

    const affiliate = this.affiliates.get(affiliateId);
    if (!affiliate || affiliate.status !== 'active') return null;

    const commissionAmount = orderValue * affiliate.commissionRate;
    const commission: AffiliateCommission = {
      id: crypto.randomUUID(),
      affiliateId,
      orderId,
      commissionAmount,
      commissionRate: affiliate.commissionRate,
      orderValue,
      status: 'pending',
      createdAt: new Date()
    };

    this.commissions.set(commission.id, commission);

    const clicks = Array.from(this.clicks.values()).filter(
      click => click.affiliateId === affiliateId && !click.converted
    );
    if (clicks.length > 0) {
      clicks[0].converted = true;
      clicks[0].conversionValue = orderValue;
    }

    return commission;
  }

  async approveCommission(commissionId: string): Promise<boolean> {
    const commission = this.commissions.get(commissionId);
    if (!commission || commission.status !== 'pending') return false;

    commission.status = 'approved';
    
    const affiliate = this.affiliates.get(commission.affiliateId);
    if (affiliate) {
      affiliate.totalEarnings += commission.commissionAmount;
      affiliate.updatedAt = new Date();
    }

    return true;
  }

  async payCommission(commissionId: string): Promise<boolean> {
    const commission = this.commissions.get(commissionId);
    if (!commission || commission.status !== 'approved') return false;

    commission.status = 'paid';
    commission.paidAt = new Date();
    return true;
  }

  async getAffiliateAnalytics(affiliateId: string, days: number = 30): Promise<any> {
    const affiliate = this.affiliates.get(affiliateId);
    if (!affiliate) return null;

    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    const affiliateClicks = Array.from(this.clicks.values()).filter(
      click => click.affiliateId === affiliateId && click.clickedAt >= startDate
    );

    const affiliateCommissions = Array.from(this.commissions.values()).filter(
      commission => commission.affiliateId === affiliateId && commission.createdAt >= startDate
    );

    const conversions = affiliateClicks.filter(click => click.converted);
    const totalClicks = affiliateClicks.length;
    const totalConversions = conversions.length;
    const conversionRate = totalClicks > 0 ? (totalConversions / totalClicks) * 100 : 0;

    const totalCommissions = affiliateCommissions
      .filter(c => c.status === 'approved' || c.status === 'paid')
      .reduce((sum, c) => sum + c.commissionAmount, 0);

    const pendingCommissions = affiliateCommissions
      .filter(c => c.status === 'pending')
      .reduce((sum, c) => sum + c.commissionAmount, 0);

    return {
      affiliate,
      period: { days, startDate, endDate: new Date() },
      performance: {
        totalClicks,
        totalConversions,
        conversionRate: Math.round(conversionRate * 100) / 100,
        totalCommissions: Math.round(totalCommissions * 100) / 100,
        pendingCommissions: Math.round(pendingCommissions * 100) / 100
      },
      recentClicks: affiliateClicks.slice(-10),
      recentCommissions: affiliateCommissions.slice(-5)
    };
  }

  async getSystemAnalytics(): Promise<AffiliateAnalytics> {
    const allClicks = Array.from(this.clicks.values());
    const allCommissions = Array.from(this.commissions.values());
    
    const totalClicks = allClicks.length;
    const totalConversions = allClicks.filter(c => c.converted).length;
    const conversionRate = totalClicks > 0 ? (totalConversions / totalClicks) * 100 : 0;

    const totalCommissions = allCommissions
      .filter(c => c.status === 'approved' || c.status === 'paid')
      .reduce((sum, c) => sum + c.commissionAmount, 0);

    const pendingCommissions = allCommissions
      .filter(c => c.status === 'pending')
      .reduce((sum, c) => sum + c.commissionAmount, 0);

    const topPerformers = Array.from(this.affiliates.values())
      .sort((a, b) => b.totalEarnings - a.totalEarnings)
      .slice(0, 10);

    return {
      totalClicks,
      totalConversions,
      conversionRate: Math.round(conversionRate * 100) / 100,
      totalCommissions: Math.round(totalCommissions * 100) / 100,
      pendingCommissions: Math.round(pendingCommissions * 100) / 100,
      topPerformers,
      recentActivity: allClicks.slice(-20)
    };
  }

  async generatePayouts(): Promise<{ affiliateId: string; amount: number; commissions: string[] }[]> {
    const payouts: { affiliateId: string; amount: number; commissions: string[] }[] = [];
    const approvedCommissions = Array.from(this.commissions.values())
      .filter(c => c.status === 'approved');

    const commissionsByAffiliate = new Map<string, AffiliateCommission[]>();
    approvedCommissions.forEach(commission => {
      if (!commissionsByAffiliate.has(commission.affiliateId)) {
        commissionsByAffiliate.set(commission.affiliateId, []);
      }
      commissionsByAffiliate.get(commission.affiliateId)!.push(commission);
    });

    commissionsByAffiliate.forEach((commissions, affiliateId) => {
      const totalAmount = commissions.reduce((sum, c) => sum + c.commissionAmount, 0);
      if (totalAmount >= 50) {
        payouts.push({
          affiliateId,
          amount: Math.round(totalAmount * 100) / 100,
          commissions: commissions.map(c => c.id)
        });
      }
    });

    return payouts;
  }

  async processPayout(payout: { affiliateId: string; amount: number; commissions: string[] }): Promise<boolean> {
    const affiliate = this.affiliates.get(payout.affiliateId);
    if (!affiliate) return false;

    for (const commissionId of payout.commissions) {
      await this.payCommission(commissionId);
    }

    return true;
  }

  private generateAffiliateCode(): string {
    return crypto.randomBytes(4).toString('hex').toUpperCase();
  }

  private getClientIP(request: NextRequest): string {
    return request.headers.get('x-forwarded-for')?.split(',')[0] ||
           request.headers.get('x-real-ip') ||
           '127.0.0.1';
  }

  private setCookie(request: NextRequest, name: string, value: string, days: number): void {
    // Implementation would set HTTP cookie
    console.log(`Setting cookie: ${name}=${value}, expires in ${days} days`);
  }

  private getCookieValue(name: string, cookies: any): string | null {
    // Implementation would read HTTP cookie
    return cookies?.[name] || null;
  }

  getAffiliateById(id: string): AffiliateUser | undefined {
    return this.affiliates.get(id);
  }

  getAllAffiliates(): AffiliateUser[] {
    return Array.from(this.affiliates.values());
  }

  getAffiliateLinks(affiliateId: string): AffiliateLink[] {
    return Array.from(this.links.values()).filter(link => link.affiliateId === affiliateId);
  }

  getPendingCommissions(): AffiliateCommission[] {
    return Array.from(this.commissions.values()).filter(c => c.status === 'pending');
  }
}

export const affiliateTracking = new AffiliateTrackingSystem();