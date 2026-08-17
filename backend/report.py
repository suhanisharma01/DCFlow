from data_schemas import DCFAssumptions, DCFResult


def _pct(x): return f"{x * 100:.1f}%"
def _num(x): return f"{x:,.0f}"


def print_dcf_report(assumptions: DCFAssumptions, result: DCFResult) -> None:
    print(f"\n{assumptions.ticker} DCF")
    print("=" * 78)
    print(f"WACC: {_pct(assumptions.wacc)}   TGR: {_pct(assumptions.terminal_growth_rate)}")

    if assumptions.current_share_price is not None:
        print(f"Implied Share Price: ${result.fair_value_per_share:,.2f}   "
              f"Today's Price: ${assumptions.current_share_price:,.2f}   "
              f"Upside/(Downside): {_pct(result.upside_downside)}")

    headers = [line.year_label for line in result.lines]
    col_width = 12

    print("\n" + "-" * 78)
    print("DCF Build".ljust(20) + "".join(h.rjust(col_width) for h in headers))
    print("-" * 78)

    rows = [
        ("Revenue", [_num(l.revenue) for l in result.lines]),
        ("  % growth", [_pct(l.revenue_growth) for l in result.lines]),
        ("EBIT", [_num(l.ebit) for l in result.lines]),
        ("  % margin", [_pct(l.ebit_margin) for l in result.lines]),
        ("Taxes", [_num(l.taxes) for l in result.lines]),
        ("  % of EBIT", [_pct(l.tax_pct_ebit) for l in result.lines]),
        ("EBIAT", [_num(l.ebiat) for l in result.lines]),
        ("D&A", [_num(l.da) for l in result.lines]),
        ("CapEx", [_num(l.capex) for l in result.lines]),
        ("Change in NWC", [_num(l.nwc_change) for l in result.lines]),
        ("Unlevered FCF", [_num(l.unlevered_fcf) for l in result.lines]),
        ("PV of FCF", [_num(l.pv_fcf) for l in result.lines]),
    ]
    for label, values in rows:
        print(label.ljust(20) + "".join(v.rjust(col_width) for v in values))

    print("-" * 78)
    print(f"Terminal Value:              {_num(result.terminal_value)}")
    print(f"PV of Terminal Value:        {_num(result.pv_terminal_value)}")
    print(f"Enterprise Value:            {_num(result.enterprise_value)}")
    print(f"+ Cash:                      {_num(assumptions.cash)}")
    print(f"- Debt:                      {_num(assumptions.debt)}")
    print(f"Equity Value:                {_num(result.equity_value)}")
    print(f"Shares:                      {_num(assumptions.shares_outstanding)}")
    print(f"Share Price:                 ${result.fair_value_per_share:,.2f}")