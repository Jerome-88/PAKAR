import type { BusinessAnalysis } from "../../api/business";

export type ScenarioAssumptions = { price: number | null; unitCost: number | null; fixedMonthly: number | null; volume: number | null; rejection: number; capex: number; amortizationMonths: number };
export type ScenarioMetrics = { cost: number | null; contribution: number | null; margin: number | null; fixed: number | null; breakEven: number | null; operatingMonthly: number | null; cashAnnual: number | null; paybackMonths: number | null };
export const baselineReject = 2;
export function scenarioBaseline(analysis: BusinessAnalysis): ScenarioAssumptions {
  const inputs = analysis.result.simulation?.calculation?.inputs ?? {};
  const amount = (key: string) => {
    const value = inputs[key];
    return value != null && value !== "" && Number.isFinite(Number(value)) && Number(value) >= 0 ? Number(value) : null;
  };
  return { price: amount("selling_price"), unitCost: amount("variable_cost"), fixedMonthly: amount("fixed_cost_monthly"), volume: amount("volume_monthly"), rejection: baselineReject, capex: 0, amortizationMonths: 24 };
}
export function scenarioMetrics(input: ScenarioAssumptions, supplierIncrease = 0, priceOverride?: number | null): ScenarioMetrics {
  const price = priceOverride === undefined ? input.price : priceOverride;
  const cost = input.unitCost != null && input.rejection < 100
    ? input.unitCost * ((1 - baselineReject / 100) / (1 - input.rejection / 100)) * (1 + supplierIncrease / 100) : null;
  const contribution = price != null && cost != null ? price - cost : null;
  const fixed = input.fixedMonthly != null ? input.fixedMonthly + input.capex / input.amortizationMonths : null;
  const operatingMonthly = contribution != null && input.volume != null && input.fixedMonthly != null ? contribution * input.volume - input.fixedMonthly : null;
  return { cost, contribution, margin: contribution != null && price != null && price > 0 ? contribution / price * 100 : null, fixed,
    breakEven: contribution != null && contribution > 0 && fixed != null ? Math.ceil(fixed / contribution) : null,
    operatingMonthly, cashAnnual: operatingMonthly != null ? operatingMonthly * 12 - input.capex : null,
    paybackMonths: input.capex === 0 ? 0 : operatingMonthly != null && operatingMonthly > 0 ? Math.ceil(input.capex / operatingMonthly) : null };
}
