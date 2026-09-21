const User = require('../models/User');
const config = require('../config/config');
const { v4: uuidv4 } = require('uuid');

class ParentChildController {
  constructor() {
    this.config = config.parentChild;
  }

  // Parent-Child Account Linking
  async linkChildAccount(req, res) {
    try {
      const { parentId } = req.params;
      const { childUserId, childAge, permissions = {} } = req.body;

      const parent = await User.findByUserId(parentId);
      const child = await User.findByUserId(childUserId);

      if (!parent || !child) {
        return res.status(404).json({ error: 'Parent or child account not found' });
      }

      if (parent.parentChild.role !== 'parent' && parent.parentChild.role !== 'independent') {
        return res.status(400).json({ error: 'User is not eligible to be a parent' });
      }

      if (child.parentChild.role !== 'independent') {
        return res.status(400).json({ error: 'Child account is already linked' });
      }

      // Determine age group and default allowances
      const ageGroup = this.determineAgeGroup(childAge);
      const defaultAllowance = this.config.defaultAllowances[ageGroup];
      const approvalThreshold = this.config.approvalThresholds[ageGroup];

      // Update parent account
      parent.parentChild.role = 'parent';
      if (!parent.parentChild.children.includes(childUserId)) {
        parent.parentChild.children.push(childUserId);
      }

      // Update child account
      child.parentChild.role = 'child';
      child.parentChild.parentId = parentId;
      child.profile.age = childAge;
      child.profile.ageGroup = ageGroup;
      
      // Set up allowance system
      child.parentChild.allowance = {
        daily: permissions.dailyAllowance || defaultAllowance.daily,
        weekly: permissions.weeklyAllowance || defaultAllowance.weekly,
        remaining: permissions.dailyAllowance || defaultAllowance.daily,
        lastReset: new Date()
      };

      // Set up approval system
      child.parentChild.approvals = {
        required: permissions.requireApproval !== false, // default true
        threshold: permissions.approvalThreshold || approvalThreshold,
        pendingRequests: []
      };

      // Set up restrictions
      child.parentChild.restrictions = {
        maxDailySpending: permissions.maxDailySpending || defaultAllowance.daily,
        allowedCategories: permissions.allowedCategories || [],
        requireApprovalFor: permissions.requireApprovalFor || ['premium_features', 'external_purchases']
      };

      await parent.save();
      await child.save();

      res.json({
        success: true,
        linkingDetails: {
          parentId,
          childId: childUserId,
          ageGroup,
          allowance: child.parentChild.allowance,
          approvals: child.parentChild.approvals,
          restrictions: child.parentChild.restrictions
        }
      });

    } catch (error) {
      console.error('Error linking child account:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Set Child Allowance
  async setChildAllowance(req, res) {
    try {
      const { parentId, childId } = req.params;
      const { dailyAllowance, weeklyAllowance, resetSchedule = 'daily' } = req.body;

      const parent = await User.findByUserId(parentId);
      const child = await User.findByUserId(childId);

      if (!parent || !child) {
        return res.status(404).json({ error: 'Parent or child account not found' });
      }

      if (!this.verifyParentChildRelationship(parent, child)) {
        return res.status(403).json({ error: 'Not authorized to manage this child account' });
      }

      // Validate allowance amounts
      const maxAllowances = {
        child: { daily: 100, weekly: 500 },
        teen: { daily: 200, weekly: 1000 },
        young_adult: { daily: 500, weekly: 2500 }
      };

      const ageGroup = child.profile.ageGroup;
      const maxAllowance = maxAllowances[ageGroup];

      if (dailyAllowance > maxAllowance.daily || weeklyAllowance > maxAllowance.weekly) {
        return res.status(400).json({ 
          error: 'Allowance exceeds maximum for age group',
          maxAllowances: maxAllowance
        });
      }

      // Update allowance
      child.parentChild.allowance.daily = dailyAllowance;
      child.parentChild.allowance.weekly = weeklyAllowance;
      child.parentChild.allowance.remaining = dailyAllowance; // Reset current allowance
      child.parentChild.allowance.lastReset = new Date();

      // Record allowance transaction
      await child.addCredits(
        dailyAllowance,
        'allowance',
        `Daily allowance from parent`,
        { parentId, resetSchedule }
      );

      await child.save();

      res.json({
        success: true,
        allowance: child.parentChild.allowance,
        childBalance: child.credits.balance
      });

    } catch (error) {
      console.error('Error setting child allowance:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Get Spending Approval Request
  async requestSpendingApproval(req, res) {
    try {
      const { childId } = req.params;
      const { amount, purpose, description, metadata = {} } = req.body;

      const child = await User.findByUserId(childId);
      if (!child) {
        return res.status(404).json({ error: 'Child account not found' });
      }

      if (child.parentChild.role !== 'child') {
        return res.status(400).json({ error: 'Account is not a child account' });
      }

      // Check if approval is required
      const requiresApproval = this.requiresParentalApproval(child, amount, purpose);
      
      if (!requiresApproval.required) {
        return res.json({
          approvalRequired: false,
          canProceed: true,
          reason: requiresApproval.reason
        });
      }

      // Check for existing pending request for same purpose
      const existingRequest = child.parentChild.approvals.pendingRequests.find(
        req => req.purpose === purpose && req.status === 'pending'
      );

      if (existingRequest) {
        return res.json({
          approvalRequired: true,
          requestExists: true,
          existingRequest: {
            id: existingRequest._id,
            amount: existingRequest.amount,
            requestedAt: existingRequest.requestedAt,
            status: existingRequest.status
          }
        });
      }

      // Create new approval request
      const approvalRequest = {
        amount,
        purpose,
        description: description || `Spending approval for ${purpose}`,
        requestedAt: new Date(),
        status: 'pending',
        metadata
      };

      child.parentChild.approvals.pendingRequests.push(approvalRequest);
      await child.save();

      // In a real app, this would send notification to parent
      this.notifyParentOfApprovalRequest(child.parentChild.parentId, approvalRequest, child);

      res.json({
        success: true,
        approvalRequired: true,
        requestId: approvalRequest._id,
        estimatedResponseTime: '24 hours'
      });

    } catch (error) {
      console.error('Error requesting spending approval:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Parent Reviews and Approves/Denies Spending
  async reviewSpendingRequest(req, res) {
    try {
      const { parentId, requestId } = req.params;
      const { decision, reason = '', conditions = {} } = req.body;

      const parent = await User.findByUserId(parentId);
      if (!parent) {
        return res.status(404).json({ error: 'Parent account not found' });
      }

      // Find the child with this pending request
      let targetChild = null;
      let targetRequest = null;

      for (const childId of parent.parentChild.children) {
        const child = await User.findByUserId(childId);
        if (child) {
          const request = child.parentChild.approvals.pendingRequests.id(requestId);
          if (request && request.status === 'pending') {
            targetChild = child;
            targetRequest = request;
            break;
          }
        }
      }

      if (!targetChild || !targetRequest) {
        return res.status(404).json({ error: 'Approval request not found' });
      }

      // Update request status
      targetRequest.status = decision; // 'approved' or 'denied'
      targetRequest.reviewedAt = new Date();
      targetRequest.reviewReason = reason;

      if (decision === 'approved') {
        // Add conditions if any
        if (conditions.timeLimit) {
          targetRequest.conditions = { ...conditions };
        }

        // If approved, child can now spend
        targetRequest.approvedAmount = targetRequest.amount;
        
        // Log approval in child's transaction history
        targetChild.credits.transactions.push({
          type: 'approval',
          amount: 0, // No credits added, just permission granted
          source: 'parent_approval',
          description: `Parent approved spending: ${targetRequest.purpose}`,
          timestamp: new Date(),
          metadata: {
            requestId: targetRequest._id,
            parentId,
            conditions
          }
        });
      }

      await targetChild.save();

      // Notify child of decision (in real app)
      this.notifyChildOfApprovalDecision(targetChild.userId, targetRequest, decision);

      res.json({
        success: true,
        decision,
        requestId,
        childId: targetChild.userId,
        request: {
          amount: targetRequest.amount,
          purpose: targetRequest.purpose,
          status: targetRequest.status,
          reviewReason: reason,
          conditions
        }
      });

    } catch (error) {
      console.error('Error reviewing spending request:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Get Child Account Status and Stats
  async getChildAccountStatus(req, res) {
    try {
      const { parentId, childId } = req.params;

      const parent = await User.findByUserId(parentId);
      const child = await User.findByUserId(childId);

      if (!parent || !child) {
        return res.status(404).json({ error: 'Parent or child account not found' });
      }

      if (!this.verifyParentChildRelationship(parent, child)) {
        return res.status(403).json({ error: 'Not authorized to view this child account' });
      }

      const status = {
        childInfo: {
          userId: child.userId,
          username: child.username,
          age: child.profile.age,
          ageGroup: child.profile.ageGroup
        },
        credits: {
          balance: child.credits.balance,
          earnedToday: child.credits.earned.today,
          spentToday: child.credits.spent.today,
          earnedThisWeek: child.credits.earned.thisWeek,
          spentThisWeek: child.credits.spent.thisWeek
        },
        allowance: {
          daily: child.parentChild.allowance.daily,
          weekly: child.parentChild.allowance.weekly,
          remaining: child.parentChild.allowance.remaining,
          lastReset: child.parentChild.allowance.lastReset,
          nextReset: this.calculateNextReset(child.parentChild.allowance.lastReset)
        },
        approvals: {
          threshold: child.parentChild.approvals.threshold,
          pendingCount: child.parentChild.approvals.pendingRequests.filter(r => r.status === 'pending').length,
          totalRequests: child.parentChild.approvals.pendingRequests.length,
          recentRequests: child.parentChild.approvals.pendingRequests
            .slice(-5)
            .map(req => ({
              id: req._id,
              amount: req.amount,
              purpose: req.purpose,
              status: req.status,
              requestedAt: req.requestedAt
            }))
        },
        activity: {
          lastActive: child.usage.sessions.lastActive,
          sessionsToday: child.usage.sessions.today,
          computeUsageToday: child.usage.compute.today,
          adViewsToday: child.ads.viewedToday
        },
        restrictions: child.parentChild.restrictions,
        recentTransactions: child.credits.transactions
          .slice(-10)
          .map(tx => ({
            type: tx.type,
            amount: tx.amount,
            source: tx.source,
            description: tx.description,
            timestamp: tx.timestamp
          }))
      };

      res.json(status);

    } catch (error) {
      console.error('Error getting child account status:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Update Child Restrictions
  async updateChildRestrictions(req, res) {
    try {
      const { parentId, childId } = req.params;
      const { restrictions } = req.body;

      const parent = await User.findByUserId(parentId);
      const child = await User.findByUserId(childId);

      if (!parent || !child) {
        return res.status(404).json({ error: 'Parent or child account not found' });
      }

      if (!this.verifyParentChildRelationship(parent, child)) {
        return res.status(403).json({ error: 'Not authorized to manage this child account' });
      }

      // Update restrictions
      child.parentChild.restrictions = {
        ...child.parentChild.restrictions,
        ...restrictions
      };

      // Update approval threshold if provided
      if (restrictions.approvalThreshold) {
        child.parentChild.approvals.threshold = restrictions.approvalThreshold;
      }

      await child.save();

      res.json({
        success: true,
        childId,
        updatedRestrictions: child.parentChild.restrictions,
        approvalSettings: {
          required: child.parentChild.approvals.required,
          threshold: child.parentChild.approvals.threshold
        }
      });

    } catch (error) {
      console.error('Error updating child restrictions:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Get All Children for Parent
  async getParentDashboard(req, res) {
    try {
      const { parentId } = req.params;
      const parent = await User.findByUserId(parentId);

      if (!parent) {
        return res.status(404).json({ error: 'Parent account not found' });
      }

      if (parent.parentChild.role !== 'parent') {
        return res.status(403).json({ error: 'Account is not a parent account' });
      }

      const children = [];
      let totalPendingApprovals = 0;

      for (const childId of parent.parentChild.children) {
        const child = await User.findByUserId(childId);
        if (child) {
          const pendingApprovals = child.parentChild.approvals.pendingRequests.filter(
            r => r.status === 'pending'
          );

          totalPendingApprovals += pendingApprovals.length;

          children.push({
            userId: child.userId,
            username: child.username,
            age: child.profile.age,
            ageGroup: child.profile.ageGroup,
            credits: {
              balance: child.credits.balance,
              spentToday: child.credits.spent.today
            },
            allowance: {
              daily: child.parentChild.allowance.daily,
              remaining: child.parentChild.allowance.remaining
            },
            activity: {
              lastActive: child.usage.sessions.lastActive,
              isActive: this.isRecentlyActive(child.usage.sessions.lastActive)
            },
            pendingApprovals: pendingApprovals.length,
            alerts: this.getChildAlerts(child)
          });
        }
      }

      const dashboard = {
        parentInfo: {
          userId: parent.userId,
          username: parent.username,
          childrenCount: children.length
        },
        children,
        summary: {
          totalPendingApprovals,
          activeChildren: children.filter(c => c.activity.isActive).length,
          totalCreditsManaged: children.reduce((sum, c) => sum + c.credits.balance, 0),
          alertsCount: children.reduce((sum, c) => sum + c.alerts.length, 0)
        },
        quickActions: [
          'Process pending approvals',
          'Review spending reports',
          'Update allowances',
          'Set new restrictions'
        ]
      };

      res.json(dashboard);

    } catch (error) {
      console.error('Error getting parent dashboard:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Process Daily Allowance Reset
  async processDailyAllowanceReset(req, res) {
    try {
      // This would typically be called by a scheduled job
      const childAccounts = await User.find({ 'parentChild.role': 'child' });
      const resetResults = [];

      for (const child of childAccounts) {
        const shouldReset = this.shouldResetAllowance(child);
        
        if (shouldReset) {
          const previousRemaining = child.parentChild.allowance.remaining;
          child.parentChild.allowance.remaining = child.parentChild.allowance.daily;
          child.parentChild.allowance.lastReset = new Date();

          // Add daily allowance credits
          await child.addCredits(
            child.parentChild.allowance.daily,
            'daily_allowance',
            'Daily allowance reset',
            { 
              previousRemaining,
              parentId: child.parentChild.parentId 
            }
          );

          await child.save();

          resetResults.push({
            childId: child.userId,
            allowanceAmount: child.parentChild.allowance.daily,
            newBalance: child.credits.balance
          });
        }
      }

      res.json({
        success: true,
        resetCount: resetResults.length,
        resets: resetResults
      });

    } catch (error) {
      console.error('Error processing allowance reset:', error);
      res.status(500).json({ error: 'Internal server error' });
    }
  }

  // Helper Methods
  determineAgeGroup(age) {
    if (age < 13) return 'child';
    if (age < 18) return 'teen';
    if (age < 22) return 'young_adult';
    return 'adult';
  }

  verifyParentChildRelationship(parent, child) {
    return parent.parentChild.children.includes(child.userId) &&
           child.parentChild.parentId === parent.userId;
  }

  requiresParentalApproval(child, amount, purpose) {
    const threshold = child.parentChild.approvals.threshold;
    const restrictions = child.parentChild.restrictions;

    // Check amount threshold
    if (amount > threshold) {
      return { required: true, reason: 'Amount exceeds approval threshold' };
    }

    // Check category restrictions
    if (restrictions.requireApprovalFor.includes(purpose)) {
      return { required: true, reason: 'Purpose requires approval' };
    }

    // Check daily spending limit
    const dailySpent = child.credits.spent.today;
    if (dailySpent + amount > restrictions.maxDailySpending) {
      return { required: true, reason: 'Would exceed daily spending limit' };
    }

    return { required: false, reason: 'No approval required' };
  }

  calculateNextReset(lastReset) {
    const nextReset = new Date(lastReset);
    nextReset.setDate(nextReset.getDate() + 1);
    nextReset.setHours(0, 0, 0, 0);
    return nextReset;
  }

  shouldResetAllowance(child) {
    const lastReset = child.parentChild.allowance.lastReset;
    if (!lastReset) return true;

    const now = new Date();
    const lastResetDate = lastReset.toDateString();
    const todayDate = now.toDateString();

    return lastResetDate !== todayDate;
  }

  isRecentlyActive(lastActive) {
    if (!lastActive) return false;
    const hoursSinceActive = (Date.now() - lastActive.getTime()) / (1000 * 60 * 60);
    return hoursSinceActive < 24;
  }

  getChildAlerts(child) {
    const alerts = [];

    // Low balance alert
    if (child.credits.balance < 10) {
      alerts.push({
        type: 'low_balance',
        message: 'Credit balance is low',
        priority: 'medium'
      });
    }

    // High spending alert
    if (child.credits.spent.today > child.parentChild.allowance.daily * 0.8) {
      alerts.push({
        type: 'high_spending',
        message: 'High spending today',
        priority: 'high'
      });
    }

    // Pending approvals
    const pendingCount = child.parentChild.approvals.pendingRequests.filter(
      r => r.status === 'pending'
    ).length;
    
    if (pendingCount > 0) {
      alerts.push({
        type: 'pending_approvals',
        message: `${pendingCount} pending approval${pendingCount > 1 ? 's' : ''}`,
        priority: 'medium'
      });
    }

    return alerts;
  }

  // Notification methods (mock implementations)
  notifyParentOfApprovalRequest(parentId, request, child) {
    console.log(`[NOTIFICATION] Parent ${parentId}: Child ${child.username} requests approval for ${request.purpose} (${request.amount} CCC)`);
    // In real app, this would send push notification, email, etc.
  }

  notifyChildOfApprovalDecision(childId, request, decision) {
    console.log(`[NOTIFICATION] Child ${childId}: Your request for ${request.purpose} was ${decision}`);
    // In real app, this would send push notification, email, etc.
  }
}

module.exports = ParentChildController;