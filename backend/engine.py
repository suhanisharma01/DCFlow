from data_schemas import DCFAssumptions, DCFResult, YearLine


def run_dcf(assumptions: DCFAssumptions) -> DCFResult:
    n = assumptions.projection_years
    year_labels = assumptions.year_labels or [f"Year {i + 1}" for i in range(n)]

    lines: list[YearLine] = []
    revenue = assumptions.base_revenue
    sum_pv_fcf = 0.0
    final_fcf = 0.0

    for i in range(n):
        growth = assumptions.revenue_growth_rates[i]
        revenue = revenue * (1 + growth)

        ebit_margin = assumptions.ebit_margins[i]
        ebit = revenue * ebit_margin

        tax_rate = assumptions.tax_rates[i]
        taxes = ebit * tax_rate
        ebiat = ebit - taxes

        da_pct = assumptions.da_pct_sales[i]
        da = revenue * da_pct

        capex_pct = assumptions.capex_pct_sales[i]
        capex = revenue * capex_pct

        nwc_pct = assumptions.nwc_change_pct_sales[i]
        nwc_change = revenue * nwc_pct

        unlevered_fcf = ebiat + da - capex - nwc_change

        discount_factor = 1 / (1 + assumptions.wacc) ** (i + 1)
        pv_fcf = unlevered_fcf * discount_factor

        lines.append(YearLine(
            year_label=year_labels[i], revenue=revenue, revenue_growth=growth,
            ebit=ebit, ebit_margin=ebit_margin, taxes=taxes, tax_pct_ebit=tax_rate,
            ebiat=ebiat, da=da, da_pct_sales=da_pct, capex=capex, capex_pct_sales=capex_pct,
            nwc_change=nwc_change, nwc_pct_sales=nwc_pct, unlevered_fcf=unlevered_fcf,
            discount_factor=discount_factor, pv_fcf=pv_fcf,
        ))

        sum_pv_fcf += pv_fcf
        final_fcf = unlevered_fcf

    g = assumptions.terminal_growth_rate
    wacc = assumptions.wacc
    terminal_value = final_fcf * (1 + g) / (wacc - g)

    final_discount_factor = lines[-1].discount_factor
    pv_terminal_value = terminal_value * final_discount_factor

    enterprise_value = sum_pv_fcf + pv_terminal_value
    equity_value = enterprise_value + assumptions.cash - assumptions.debt
    fair_value_per_share = equity_value / assumptions.shares_outstanding

    upside_downside = None
    if assumptions.current_share_price:
        upside_downside = (fair_value_per_share / assumptions.current_share_price) - 1

    return DCFResult(
        lines=lines, terminal_value=terminal_value, pv_terminal_value=pv_terminal_value,
        enterprise_value=enterprise_value, equity_value=equity_value,
        fair_value_per_share=fair_value_per_share, sum_pv_fcf=sum_pv_fcf,
        upside_downside=upside_downside,
    )