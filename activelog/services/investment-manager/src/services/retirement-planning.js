import { Decimal } from 'decimal.js';
import { addYears, differenceInYears, parseISO } from 'date-fns';

class RetirementPlanning {
    constructor(redisClient, portfolioTracker, monteCarloSimulator) {
        this.redis = redisClient;
        this.portfolioTracker = portfolioTracker;
        this.monteCarloSimulator = monteCarloSimulator;
        
        // Retirement planning constants
        this.constants = {
            socialSecurityFullRetirementAge: 67,
            socialSecurityMaxBenefit2024: 4873, // Monthly max benefit
            inflationRate: 0.025, // 2.5% average inflation
            safeWithdrawalRate: 0.04, // 4% rule
            rmdStartAge: 73, // Required Minimum Distribution age
            maxRetirementAge: 100,
            maxSocialSecurityWageBase2024: 160200
        };

        // Account types and contribution limits (2024)
        this.accountLimits = {
            '401k': {
                contributionLimit: 23000,
                catchUpAge: 50,
                catchUpAmount: 7500,
                rmdRequired: true
            },
            'traditionalIRA': {
                contributionLimit: 7000,
                catchUpAge: 50,
                catchUpAmount: 1000,
                rmdRequired: true
            },
            'rothIRA': {
                contributionLimit: 7000,
                catchUpAge: 50,
                catchUpAmount: 1000,
                rmdRequired: false,
                incomePhaseout: { single: 138000, married: 218000 }
            },
            'sep': {
                contributionLimit: 69000,
                contributionPercentage: 0.25,
                rmdRequired: true
            },
            'simple': {
                contributionLimit: 16000,
                catchUpAge: 50,
                catchUpAmount: 3500,
                rmdRequired: true
            }
        };
    }

    // Create comprehensive retirement plan
    async createRetirementPlan(userId, planData) {
        try {
            const {
                currentAge,
                targetRetirementAge = 65,
                currentSalary,
                salaryGrowthRate = 0.03,
                currentSavings = 0,
                monthlyContribution = 0,
                employerMatch = 0,
                socialSecurityBenefit = null,
                desiredIncomeReplacement = 0.80, // 80% of pre-retirement income
                riskTolerance = 'moderate',
                healthExpectation = 'average', // poor, average, excellent
                maritalStatus = 'single',
                spouseAge = null,
                spouseSalary = null,
                stateTaxRate = 0.05,
                federalTaxRate = 0.22,
                healthcareCosts = 500, // Monthly
                additionalExpenses = {},
                legacyGoal = 0
            } = planData;

            const planId = `retirement_${userId}_${Date.now()}`;
            
            // Calculate retirement timeline
            const yearsToRetirement = targetRetirementAge - currentAge;
            const retirementDuration = this.calculateLifeExpectancy(currentAge, healthExpectation) - targetRetirementAge;

            // Project account balances at retirement
            const projectedBalances = await this.projectRetirementBalances({
                currentSavings,
                monthlyContribution,
                employerMatch,
                yearsToRetirement,
                currentAge,
                currentSalary,
                salaryGrowthRate,
                riskTolerance
            });

            // Calculate required retirement income
            const requiredIncome = await this.calculateRequiredRetirementIncome({
                currentSalary,
                desiredIncomeReplacement,
                targetRetirementAge,
                salaryGrowthRate,
                healthcareCosts,
                additionalExpenses,
                stateTaxRate,
                federalTaxRate
            });

            // Project Social Security benefits
            const socialSecurityProjection = await this.projectSocialSecurity({
                currentAge,
                currentSalary,
                targetRetirementAge,
                socialSecurityBenefit,
                maritalStatus,
                spouseSalary
            });

            // Calculate retirement readiness
            const readinessAnalysis = await this.calculateRetirementReadiness({
                projectedBalances,
                requiredIncome,
                socialSecurityProjection,
                retirementDuration,
                legacyGoal
            });

            // Generate recommendations
            const recommendations = await this.generateRecommendations({
                readinessAnalysis,
                currentAge,
                currentSalary,
                monthlyContribution,
                employerMatch,
                yearsToRetirement,
                riskTolerance
            });

            // Run Monte Carlo simulations
            const monteCarloResults = await this.runRetirementMonteCarlo({
                currentSavings,
                monthlyContribution,
                yearsToRetirement,
                retirementDuration,
                requiredIncome: requiredIncome.monthlyIncome,
                riskTolerance
            });

            const plan = {
                planId,
                userId,
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString(),
                assumptions: {
                    currentAge,
                    targetRetirementAge,
                    currentSalary,
                    salaryGrowthRate,
                    desiredIncomeReplacement,
                    riskTolerance,
                    inflationRate: this.constants.inflationRate
                },
                projections: {
                    balances: projectedBalances,
                    income: requiredIncome,
                    socialSecurity: socialSecurityProjection,
                    timeline: {
                        yearsToRetirement,
                        retirementDuration,
                        lifeExpectancy: this.calculateLifeExpectancy(currentAge, healthExpectation)
                    }
                },
                readiness: readinessAnalysis,
                recommendations,
                monteCarloResults,
                isActive: true
            };

            // Save plan
            await this.redis.hSet(`retirement_plan:${planId}`, this.flattenPlan(plan));
            await this.redis.sAdd(`user:${userId}:retirement_plans`, planId);

            return this.sanitizePlan(plan);
        } catch (error) {
            throw new Error(`Failed to create retirement plan: ${error.message}`);
        }
    }

    // Project retirement account balances
    async projectRetirementBalances(params) {
        const {
            currentSavings,
            monthlyContribution,
            employerMatch,
            yearsToRetirement,
            currentAge,
            currentSalary,
            salaryGrowthRate,
            riskTolerance
        } = params;

        // Expected returns based on risk tolerance
        const expectedReturns = {
            conservative: 0.06,
            moderate: 0.08,
            aggressive: 0.10
        };

        const annualReturn = expectedReturns[riskTolerance] || expectedReturns.moderate;
        const monthlyReturn = annualReturn / 12;

        let currentBalance = new Decimal(currentSavings);
        let totalContributions = new Decimal(0);
        let totalEmployerMatch = new Decimal(0);
        let currentAnnualSalary = new Decimal(currentSalary);

        const yearlyProjections = [];

        for (let year = 0; year < yearsToRetirement; year++) {
            const age = currentAge + year;
            
            // Calculate annual contribution (including catch-up if eligible)
            let annualContribution = new Decimal(monthlyContribution).mul(12);
            
            // Apply catch-up contributions if age 50+
            if (age >= 50) {
                annualContribution = annualContribution.plus(7500); // 401k catch-up
            }

            // Calculate employer match (typically as percentage of salary)
            const annualEmployerMatch = currentAnnualSalary.mul(employerMatch);
            
            // Add contributions at the beginning of the year
            currentBalance = currentBalance.plus(annualContribution).plus(annualEmployerMatch);
            totalContributions = totalContributions.plus(annualContribution);
            totalEmployerMatch = totalEmployerMatch.plus(annualEmployerMatch);

            // Apply investment growth for the year
            currentBalance = currentBalance.mul(1 + annualReturn);

            // Increase salary for next year
            currentAnnualSalary = currentAnnualSalary.mul(1 + salaryGrowthRate);

            yearlyProjections.push({
                year: year + 1,
                age: age + 1,
                balance: currentBalance.toNumber(),
                annualContribution: annualContribution.toNumber(),
                employerMatch: annualEmployerMatch.toNumber(),
                salary: currentAnnualSalary.toNumber()
            });
        }

        return {
            finalBalance: currentBalance.toNumber(),
            totalContributions: totalContributions.toNumber(),
            totalEmployerMatch: totalEmployerMatch.toNumber(),
            totalGrowth: currentBalance.minus(currentSavings).minus(totalContributions).minus(totalEmployerMatch).toNumber(),
            yearlyProjections
        };
    }

    // Calculate required retirement income
    async calculateRequiredRetirementIncome(params) {
        const {
            currentSalary,
            desiredIncomeReplacement,
            targetRetirementAge,
            salaryGrowthRate,
            healthcareCosts,
            additionalExpenses,
            stateTaxRate,
            federalTaxRate
        } = params;

        const yearsToRetirement = targetRetirementAge - 25; // Assuming working from 25
        
        // Project final salary at retirement
        const finalSalary = new Decimal(currentSalary).mul(Math.pow(1 + salaryGrowthRate, yearsToRetirement));
        
        // Calculate desired pre-tax income
        const desiredAnnualIncome = finalSalary.mul(desiredIncomeReplacement);
        
        // Add healthcare costs (inflated)
        const inflatedHealthcareCosts = new Decimal(healthcareCosts).mul(12).mul(
            Math.pow(1 + this.constants.inflationRate * 2, yearsToRetirement) // Healthcare inflation is typically higher
        );
        
        // Add additional expenses
        let totalAdditionalExpenses = new Decimal(0);
        for (const [expense, amount] of Object.entries(additionalExpenses)) {
            totalAdditionalExpenses = totalAdditionalExpenses.plus(amount);
        }
        
        const totalRequiredIncome = desiredAnnualIncome.plus(inflatedHealthcareCosts).plus(totalAdditionalExpenses);
        
        // Calculate after-tax income needed
        const totalTaxRate = stateTaxRate + federalTaxRate;
        const preCarrerTaxIncome = totalRequiredIncome.div(1 - totalTaxRate);

        return {
            annualIncome: totalRequiredIncome.toNumber(),
            monthlyIncome: totalRequiredIncome.div(12).toNumber(),
            preTaxIncome: preCarrerTaxIncome.toNumber(),
            healthcareCosts: inflatedHealthcareCosts.toNumber(),
            additionalExpenses: totalAdditionalExpenses.toNumber(),
            finalSalary: finalSalary.toNumber()
        };
    }

    // Project Social Security benefits
    async projectSocialSecurity(params) {
        const {
            currentAge,
            currentSalary,
            targetRetirementAge,
            socialSecurityBenefit,
            maritalStatus,
            spouseSalary
        } = params;

        // If specific benefit provided, use that
        if (socialSecurityBenefit) {
            return {
                monthlyBenefit: socialSecurityBenefit,
                annualBenefit: socialSecurityBenefit * 12,
                startAge: Math.max(targetRetirementAge, 62),
                fullRetirementAge: this.constants.socialSecurityFullRetirementAge,
                estimationMethod: 'user_provided'
            };
        }

        // Estimate based on salary history
        const yearsWorked = Math.max(currentAge - 22, 0); // Assuming work started at 22
        const yearsToRetirement = targetRetirementAge - currentAge;
        const totalWorkYears = yearsWorked + yearsToRetirement;

        // Calculate Average Indexed Monthly Earnings (AIME)
        // Simplified calculation using current salary projected backward and forward
        const averageAnnualSalary = new Decimal(currentSalary);
        const cappedSalary = Decimal.min(averageAnnualSalary, this.constants.maxSocialSecurityWageBase2024);
        const aime = cappedSalary.div(12);

        // Calculate Primary Insurance Amount (PIA) - simplified formula
        let pia = new Decimal(0);
        
        if (aime.lte(1024)) {
            pia = aime.mul(0.90);
        } else if (aime.lte(6172)) {
            pia = new Decimal(1024).mul(0.90).plus(aime.minus(1024).mul(0.32));
        } else {
            pia = new Decimal(1024).mul(0.90)
                .plus(new Decimal(6172 - 1024).mul(0.32))
                .plus(aime.minus(6172).mul(0.15));
        }

        // Adjust for early/late retirement
        let adjustedBenefit = pia;
        if (targetRetirementAge < this.constants.socialSecurityFullRetirementAge) {
            const monthsEarly = (this.constants.socialSecurityFullRetirementAge - targetRetirementAge) * 12;
            const reductionFactor = Math.min(36, monthsEarly) * 0.0055 + Math.max(0, monthsEarly - 36) * 0.00416;
            adjustedBenefit = pia.mul(1 - reductionFactor);
        } else if (targetRetirementAge > this.constants.socialSecurityFullRetirementAge) {
            const monthsLate = (targetRetirementAge - this.constants.socialSecurityFullRetirementAge) * 12;
            const increaseFactor = monthsLate * 0.00667; // 8% per year
            adjustedBenefit = pia.mul(1 + increaseFactor);
        }

        // Spousal benefits if married
        let spouseBenefit = new Decimal(0);
        if (maritalStatus === 'married' && spouseSalary) {
            // Simplified spousal benefit calculation
            spouseBenefit = adjustedBenefit.mul(0.5); // Spousal benefit is 50% of primary
        }

        const totalMonthlyBenefit = adjustedBenefit.plus(spouseBenefit);

        return {
            monthlyBenefit: totalMonthlyBenefit.toNumber(),
            annualBenefit: totalMonthlyBenefit.mul(12).toNumber(),
            primaryBenefit: adjustedBenefit.toNumber(),
            spouseBenefit: spouseBenefit.toNumber(),
            startAge: Math.max(targetRetirementAge, 62),
            fullRetirementAge: this.constants.socialSecurityFullRetirementAge,
            aime: aime.toNumber(),
            pia: pia.toNumber(),
            estimationMethod: 'calculated'
        };
    }

    // Calculate retirement readiness
    async calculateRetirementReadiness(params) {
        const {
            projectedBalances,
            requiredIncome,
            socialSecurityProjection,
            retirementDuration,
            legacyGoal
        } = params;

        const totalSavings = new Decimal(projectedBalances.finalBalance);
        const annualSocialSecurity = new Decimal(socialSecurityProjection.annualBenefit);
        const requiredAnnualIncome = new Decimal(requiredIncome.annualIncome);
        
        // Calculate sustainable withdrawal amount using 4% rule
        const sustainableWithdrawal = totalSavings.mul(this.constants.safeWithdrawalRate);
        
        // Total annual income from all sources
        const totalAnnualIncome = sustainableWithdrawal.plus(annualSocialSecurity);
        
        // Calculate shortfall or surplus
        const annualShortfall = requiredAnnualIncome.minus(totalAnnualIncome);
        const readinessPercentage = requiredAnnualIncome.gt(0) 
            ? totalAnnualIncome.div(requiredAnnualIncome).mul(100).toNumber()
            : 100;

        // Calculate probability of success using simplified model
        const successProbability = this.calculateSuccessProbability({
            totalSavings: totalSavings.toNumber(),
            annualWithdrawal: requiredAnnualIncome.toNumber(),
            retirementDuration,
            socialSecurityIncome: annualSocialSecurity.toNumber()
        });

        // Legacy analysis
        const legacyShortfall = new Decimal(legacyGoal).minus(
            Math.max(0, totalSavings.toNumber() - (requiredAnnualIncome.toNumber() * retirementDuration))
        );

        return {
            readinessPercentage,
            isOnTrack: readinessPercentage >= 100,
            annualShortfall: annualShortfall.toNumber(),
            monthlyShortfall: annualShortfall.div(12).toNumber(),
            successProbability,
            totalRetirementIncome: totalAnnualIncome.toNumber(),
            retirementSavings: totalSavings.toNumber(),
            socialSecurityIncome: annualSocialSecurity.toNumber(),
            sustainableWithdrawal: sustainableWithdrawal.toNumber(),
            legacyProjection: {
                goal: legacyGoal,
                projected: Math.max(0, totalSavings.toNumber() - (requiredAnnualIncome.toNumber() * retirementDuration)),
                shortfall: Math.max(0, legacyShortfall.toNumber())
            }
        };
    }

    // Generate personalized recommendations
    async generateRecommendations(params) {
        const {
            readinessAnalysis,
            currentAge,
            currentSalary,
            monthlyContribution,
            employerMatch,
            yearsToRetirement,
            riskTolerance
        } = params;

        const recommendations = [];

        // Contribution recommendations
        if (readinessAnalysis.annualShortfall > 0) {
            const additionalMonthlyNeeded = Math.abs(readinessAnalysis.monthlyShortfall) * 0.7; // Accounting for growth
            
            recommendations.push({
                category: 'contributions',
                priority: 'high',
                title: 'Increase Monthly Contributions',
                description: `Consider increasing monthly contributions by $${Math.round(additionalMonthlyNeeded)} to help close the retirement gap.`,
                actionItems: [
                    'Increase 401(k) contribution percentage',
                    'Set up automatic contribution increases',
                    'Contribute tax refunds to retirement accounts'
                ],
                estimatedImpact: additionalMonthlyNeeded * 12 * yearsToRetirement * 1.5
            });
        }

        // Employer match recommendations
        const maxEmployerMatch = new Decimal(currentSalary).mul(0.06); // Typical max match
        const currentMatchUtilization = new Decimal(currentSalary).mul(employerMatch);
        
        if (currentMatchUtilization.lt(maxEmployerMatch)) {
            const missedMatch = maxEmployerMatch.minus(currentMatchUtilization);
            recommendations.push({
                category: 'employer_match',
                priority: 'critical',
                title: 'Maximize Employer Match',
                description: `You may be missing out on up to $${Math.round(missedMatch.toNumber())} in free employer matching funds annually.`,
                actionItems: [
                    'Review your employer\'s matching policy',
                    'Increase contributions to get full match',
                    'Consider front-loading contributions if allowed'
                ],
                estimatedImpact: missedMatch.toNumber() * yearsToRetirement * 2
            });
        }

        // Catch-up contribution recommendations
        if (currentAge >= 50) {
            recommendations.push({
                category: 'catch_up',
                priority: 'medium',
                title: 'Utilize Catch-Up Contributions',
                description: 'You\'re eligible for additional catch-up contributions that can significantly boost your retirement savings.',
                actionItems: [
                    'Contribute additional $7,500 to 401(k)',
                    'Contribute additional $1,000 to IRA',
                    'Consider spousal catch-up contributions if married'
                ],
                estimatedImpact: 8500 * (65 - currentAge) * 1.4
            });
        }

        // Risk tolerance recommendations
        if (yearsToRetirement > 10 && riskTolerance === 'conservative') {
            recommendations.push({
                category: 'asset_allocation',
                priority: 'medium',
                title: 'Consider More Aggressive Asset Allocation',
                description: 'With over 10 years until retirement, a more aggressive allocation could potentially increase your returns.',
                actionItems: [
                    'Review current asset allocation',
                    'Consider increasing stock allocation',
                    'Diversify across asset classes'
                ],
                estimatedImpact: readinessAnalysis.retirementSavings * 0.02 // 2% additional return
            });
        }

        // Debt reduction recommendations
        recommendations.push({
            category: 'debt',
            priority: 'high',
            title: 'Eliminate High-Interest Debt',
            description: 'Paying off high-interest debt can free up more money for retirement savings.',
            actionItems: [
                'List all debts by interest rate',
                'Focus on paying off highest-rate debts first',
                'Consider debt consolidation if beneficial'
            ],
            estimatedImpact: null
        });

        // Health Savings Account recommendations
        if (currentAge < 65) {
            recommendations.push({
                category: 'healthcare',
                priority: 'medium',
                title: 'Maximize Health Savings Account (HSA)',
                description: 'HSAs offer triple tax advantages and can be used for retirement healthcare costs.',
                actionItems: [
                    'Contribute maximum to HSA if eligible',
                    'Invest HSA funds for long-term growth',
                    'Save receipts for future reimbursements'
                ],
                estimatedImpact: 4150 * (65 - currentAge) * 1.3 // 2024 HSA limit
            });
        }

        return recommendations.sort((a, b) => {
            const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
            return priorityOrder[a.priority] - priorityOrder[b.priority];
        });
    }

    // Run Monte Carlo simulation for retirement
    async runRetirementMonteCarlo(params) {
        if (!this.monteCarloSimulator) {
            return {
                successRate: 75,
                medianEndingBalance: params.currentSavings * 2,
                percentile10: params.currentSavings * 0.5,
                percentile90: params.currentSavings * 4,
                note: 'Monte Carlo simulator not available - using estimates'
            };
        }

        return await this.monteCarloSimulator.runRetirementSimulation(params);
    }

    // Calculate retirement readiness score
    calculateRetirementReadinessScore(plan) {
        const weights = {
            savingsRate: 0.3,
            timeHorizon: 0.2,
            currentBalance: 0.2,
            riskTolerance: 0.15,
            employerMatch: 0.15
        };

        let score = 0;

        // Savings rate score (0-100)
        const savingsRate = (plan.assumptions.monthlyContribution * 12) / plan.assumptions.currentSalary;
        const savingsRateScore = Math.min(100, (savingsRate / 0.15) * 100); // 15% is excellent
        score += savingsRateScore * weights.savingsRate;

        // Time horizon score
        const yearsToRetirement = plan.projections.timeline.yearsToRetirement;
        const timeScore = yearsToRetirement >= 30 ? 100 : Math.max(20, (yearsToRetirement / 30) * 100);
        score += timeScore * weights.timeHorizon;

        // Current balance score relative to salary
        const balanceMultiple = plan.projections.balances.finalBalance / plan.assumptions.currentSalary;
        const balanceScore = Math.min(100, (balanceMultiple / 10) * 100); // 10x salary is excellent
        score += balanceScore * weights.currentBalance;

        // Risk tolerance score (based on time horizon)
        const riskScore = yearsToRetirement > 10 && plan.assumptions.riskTolerance === 'aggressive' ? 100 : 
                         yearsToRetirement > 10 && plan.assumptions.riskTolerance === 'moderate' ? 80 :
                         yearsToRetirement <= 10 && plan.assumptions.riskTolerance === 'conservative' ? 100 : 60;
        score += riskScore * weights.riskTolerance;

        // Employer match utilization score
        const matchScore = 100; // Assume full utilization for now
        score += matchScore * weights.employerMatch;

        return Math.round(score);
    }

    // Helper functions
    calculateLifeExpectancy(currentAge, healthExpectation) {
        const baseLifeExpectancy = 82; // Average US life expectancy
        
        const adjustments = {
            poor: -5,
            average: 0,
            excellent: +3
        };

        return baseLifeExpectancy + (adjustments[healthExpectation] || 0);
    }

    calculateSuccessProbability(params) {
        const { totalSavings, annualWithdrawal, retirementDuration, socialSecurityIncome } = params;
        
        // Simplified probability calculation
        const withdrawalRate = (annualWithdrawal - socialSecurityIncome) / totalSavings;
        
        if (withdrawalRate <= 0.03) return 95;
        if (withdrawalRate <= 0.04) return 85;
        if (withdrawalRate <= 0.05) return 70;
        if (withdrawalRate <= 0.06) return 50;
        if (withdrawalRate <= 0.08) return 25;
        return 10;
    }

    // Required Minimum Distribution calculations
    calculateRMD(age, accountBalance) {
        const rmdTable = {
            73: 27.4, 74: 26.5, 75: 25.6, 76: 24.7, 77: 23.8,
            78: 22.9, 79: 22.0, 80: 21.2, 81: 20.3, 82: 19.5,
            83: 18.7, 84: 17.9, 85: 17.1, 86: 16.3, 87: 15.5,
            88: 14.8, 89: 14.1, 90: 13.4, 91: 12.7, 92: 12.0,
            93: 11.4, 94: 10.8, 95: 10.2, 96: 9.6, 97: 9.1,
            98: 8.6, 99: 8.1, 100: 7.6
        };

        const divisor = rmdTable[age] || 7.6;
        return accountBalance / divisor;
    }

    // Tax planning for retirement
    calculateRetirementTaxes(income, filingStatus, state) {
        // Simplified tax calculation
        const standardDeduction = filingStatus === 'married' ? 29200 : 14600; // 2024 estimates
        const taxableIncome = Math.max(0, income - standardDeduction);
        
        // Federal tax brackets (simplified)
        let federalTax = 0;
        if (taxableIncome > 95550) federalTax = 22275 + (taxableIncome - 95550) * 0.24;
        else if (taxableIncome > 40525) federalTax = 4667.50 + (taxableIncome - 40525) * 0.22;
        else if (taxableIncome > 19900) federalTax = 1990 + (taxableIncome - 19900) * 0.12;
        else federalTax = taxableIncome * 0.10;

        // State tax (simplified - varies by state)
        const stateTaxRates = {
            'CA': 0.05, 'TX': 0, 'FL': 0, 'NY': 0.06,
            'WA': 0, 'NV': 0, 'TN': 0, 'NH': 0
        };
        const stateTax = taxableIncome * (stateTaxRates[state] || 0.05);

        return {
            federalTax,
            stateTax,
            totalTax: federalTax + stateTax,
            effectiveRate: income > 0 ? (federalTax + stateTax) / income : 0,
            afterTaxIncome: income - federalTax - stateTax
        };
    }

    // Serialization helpers
    flattenPlan(plan) {
        return {
            ...plan,
            assumptions: JSON.stringify(plan.assumptions),
            projections: JSON.stringify(plan.projections),
            readiness: JSON.stringify(plan.readiness),
            recommendations: JSON.stringify(plan.recommendations),
            monteCarloResults: JSON.stringify(plan.monteCarloResults)
        };
    }

    unflattenPlan(data) {
        return {
            ...data,
            assumptions: JSON.parse(data.assumptions || '{}'),
            projections: JSON.parse(data.projections || '{}'),
            readiness: JSON.parse(data.readiness || '{}'),
            recommendations: JSON.parse(data.recommendations || '[]'),
            monteCarloResults: JSON.parse(data.monteCarloResults || '{}'),
            isActive: data.isActive === 'true'
        };
    }

    sanitizePlan(plan) {
        // Convert any Decimal objects to strings for JSON serialization
        return JSON.parse(JSON.stringify(plan, this.decimalReplacer));
    }

    decimalReplacer(key, value) {
        return value instanceof Decimal ? value.toString() : value;
    }

    // Get retirement plan by ID
    async getRetirementPlan(planId) {
        try {
            const data = await this.redis.hGetAll(`retirement_plan:${planId}`);
            if (!data.planId) return null;

            return this.unflattenPlan(data);
        } catch (error) {
            return null;
        }
    }

    // Update retirement plan
    async updateRetirementPlan(planId, updates) {
        try {
            const plan = await this.getRetirementPlan(planId);
            if (!plan) {
                throw new Error('Retirement plan not found');
            }

            // Update specific fields
            const updatedPlan = {
                ...plan,
                ...updates,
                updatedAt: new Date().toISOString()
            };

            await this.redis.hSet(`retirement_plan:${planId}`, this.flattenPlan(updatedPlan));
            
            return this.sanitizePlan(updatedPlan);
        } catch (error) {
            throw new Error(`Failed to update retirement plan: ${error.message}`);
        }
    }

    // Get user's retirement plans
    async getUserRetirementPlans(userId) {
        try {
            const planIds = await this.redis.sMembers(`user:${userId}:retirement_plans`);
            const plans = [];

            for (const planId of planIds) {
                const plan = await this.getRetirementPlan(planId);
                if (plan && plan.isActive) {
                    plans.push(this.sanitizePlan(plan));
                }
            }

            return plans.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
        } catch (error) {
            throw new Error(`Failed to get user retirement plans: ${error.message}`);
        }
    }
}

export default RetirementPlanning;