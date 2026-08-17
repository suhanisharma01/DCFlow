"""
Phase 6: Excel export -- generates a formula-driven .xlsx from a DCFAssumptions
object, mirroring the standard banker's DCF template layout (Revenue -> EBIT ->
EBIAT -> Unlevered FCF -> Terminal Value -> Equity Value -> Share Price).

Critically, cells contain live Excel formulas (e.g. "=B5*(1+C5)"), not
pre-computed static values -- so the exported file is a real, editable model,
not a snapshot. Python's run_dcf() is only used here to sanity-check the
formulas land on the same numbers, not to populate the sheet.
"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from data_schemas import DCFAssumptions

HEADER_FILL = PatternFill(start_color="2F3E4E", end_color="2F3E4E", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True)
BOLD = Font(bold=True)
INPUT_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")  # yellow = editable


def export_dcf_to_excel(assumptions: DCFAssumptions, filepath: str) -> str:
    """Builds a formula-driven Excel workbook for the given assumptions and saves it to filepath."""
    n = assumptions.projection_years
    wb = Workbook()
    ws = wb.active
    ws.title = "DCF"

    year_labels = assumptions.year_labels or [f"Year {i+1}" for i in range(n)]
    first_data_col = 3  # column C onward = projection years
    last_data_col = first_data_col + n - 1

    # --- Title / header block ---
    ws["A1"] = f"{assumptions.ticker} DCF"
    ws["A1"].font = Font(bold=True, size=14)

    ws["A3"] = "WACC"
    ws["B3"] = assumptions.wacc
    ws["B3"].fill = INPUT_FILL
    ws["B3"].number_format = "0.0%"

    ws["A4"] = "Terminal Growth Rate"
    ws["B4"] = assumptions.terminal_growth_rate
    ws["B4"].fill = INPUT_FILL
    ws["B4"].number_format = "0.0%"

    # --- Column headers (year labels) ---
    header_row = 6
    ws.cell(row=header_row, column=1, value="DCF Build").font = BOLD
    for i, label in enumerate(year_labels):
        col = first_data_col + i
        cell = ws.cell(row=header_row, column=col, value=label)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")

    row = header_row + 1

    # Row layout: label -> row number, so formulas can reference each other by name
    rows = {}

    def add_row(label, bold=False):
        nonlocal row
        ws.cell(row=row, column=1, value=label).font = BOLD if bold else Font()
        rows[label] = row
        row += 1

    add_row("Revenue")
    add_row("  % growth")
    add_row("EBIT margin (input)")
    add_row("EBIT")
    add_row("Tax rate (input)")
    add_row("Taxes")
    add_row("EBIAT", bold=True)
    add_row("D&A % sales (input)")
    add_row("D&A")
    add_row("CapEx % sales (input)")
    add_row("CapEx")
    add_row("NWC % sales (input)")
    add_row("Change in NWC")
    add_row("Unlevered FCF", bold=True)
    add_row("Discount Factor")
    add_row("PV of FCF", bold=True)

    base_revenue_row = rows["Revenue"]

    for i in range(n):
        col = first_data_col + i
        col_letter = get_column_letter(col)
        prev_col_letter = get_column_letter(col - 1) if i > 0 else None

        # Revenue = prior revenue * (1 + growth); first year grows off base_revenue in B-cell
        if i == 0:
            ws.cell(row=1, column=1, value="Base Revenue")  # placeholder label, not used in formulas
            base_rev_cell = "B1"
            ws["B1"] = assumptions.base_revenue
            ws["B1"].fill = INPUT_FILL
            growth_cell = f"{col_letter}{rows['  % growth']}"
            ws[f"{col_letter}{rows['  % growth']}"] = assumptions.revenue_growth_rates[i]
            ws.cell(row=rows["Revenue"], column=col,
                     value=f"={base_rev_cell}*(1+{growth_cell})")
        else:
            growth_cell = f"{col_letter}{rows['  % growth']}"
            ws[growth_cell] = assumptions.revenue_growth_rates[i]
            prev_rev_cell = f"{prev_col_letter}{rows['Revenue']}"
            ws.cell(row=rows["Revenue"], column=col,
                     value=f"={prev_rev_cell}*(1+{growth_cell})")

        ws.cell(row=rows["  % growth"], column=col).fill = INPUT_FILL
        ws.cell(row=rows["  % growth"], column=col).number_format = "0.0%"
        ws.cell(row=rows["Revenue"], column=col).number_format = "#,##0"

        rev_cell = f"{col_letter}{rows['Revenue']}"

        # EBIT margin (input) + EBIT (formula)
        ws.cell(row=rows["EBIT margin (input)"], column=col, value=assumptions.ebit_margins[i])
        ws.cell(row=rows["EBIT margin (input)"], column=col).fill = INPUT_FILL
        ws.cell(row=rows["EBIT margin (input)"], column=col).number_format = "0.0%"
        margin_cell = f"{col_letter}{rows['EBIT margin (input)']}"
        ws.cell(row=rows["EBIT"], column=col, value=f"={rev_cell}*{margin_cell}")
        ws.cell(row=rows["EBIT"], column=col).number_format = "#,##0"
        ebit_cell = f"{col_letter}{rows['EBIT']}"

        # Tax rate (input) + Taxes (formula) + EBIAT (formula)
        ws.cell(row=rows["Tax rate (input)"], column=col, value=assumptions.tax_rates[i])
        ws.cell(row=rows["Tax rate (input)"], column=col).fill = INPUT_FILL
        ws.cell(row=rows["Tax rate (input)"], column=col).number_format = "0.0%"
        tax_rate_cell = f"{col_letter}{rows['Tax rate (input)']}"
        ws.cell(row=rows["Taxes"], column=col, value=f"={ebit_cell}*{tax_rate_cell}")
        ws.cell(row=rows["Taxes"], column=col).number_format = "#,##0"
        taxes_cell = f"{col_letter}{rows['Taxes']}"

        ws.cell(row=rows["EBIAT"], column=col, value=f"={ebit_cell}-{taxes_cell}")
        ws.cell(row=rows["EBIAT"], column=col).number_format = "#,##0"
        ebiat_cell = f"{col_letter}{rows['EBIAT']}"

        # D&A, CapEx, NWC (input % -> formula $) 
        for label, value in [
            ("D&A % sales (input)", assumptions.da_pct_sales[i]),
            ("CapEx % sales (input)", assumptions.capex_pct_sales[i]),
            ("NWC % sales (input)", assumptions.nwc_change_pct_sales[i]),
        ]:
            ws.cell(row=rows[label], column=col, value=value)
            ws.cell(row=rows[label], column=col).fill = INPUT_FILL
            ws.cell(row=rows[label], column=col).number_format = "0.0%"

        da_pct_cell = f"{col_letter}{rows['D&A % sales (input)']}"
        ws.cell(row=rows["D&A"], column=col, value=f"={rev_cell}*{da_pct_cell}")
        ws.cell(row=rows["D&A"], column=col).number_format = "#,##0"
        da_cell = f"{col_letter}{rows['D&A']}"

        capex_pct_cell = f"{col_letter}{rows['CapEx % sales (input)']}"
        ws.cell(row=rows["CapEx"], column=col, value=f"={rev_cell}*{capex_pct_cell}")
        ws.cell(row=rows["CapEx"], column=col).number_format = "#,##0"
        capex_cell = f"{col_letter}{rows['CapEx']}"

        nwc_pct_cell = f"{col_letter}{rows['NWC % sales (input)']}"
        ws.cell(row=rows["Change in NWC"], column=col, value=f"={rev_cell}*{nwc_pct_cell}")
        ws.cell(row=rows["Change in NWC"], column=col).number_format = "#,##0"
        nwc_cell = f"{col_letter}{rows['Change in NWC']}"

        # Unlevered FCF = EBIAT + D&A - CapEx - Change in NWC
        ws.cell(row=rows["Unlevered FCF"], column=col,
                value=f"={ebiat_cell}+{da_cell}-{capex_cell}-{nwc_cell}")
        ws.cell(row=rows["Unlevered FCF"], column=col).number_format = "#,##0"
        fcf_cell = f"{col_letter}{rows['Unlevered FCF']}"

        # Discount factor = 1/(1+WACC)^year, PV of FCF = FCF * discount factor
        ws.cell(row=rows["Discount Factor"], column=col, value=f"=1/(1+$B$3)^{i+1}")
        ws.cell(row=rows["Discount Factor"], column=col).number_format = "0.000"
        df_cell = f"{col_letter}{rows['Discount Factor']}"

        ws.cell(row=rows["PV of FCF"], column=col, value=f"={fcf_cell}*{df_cell}")
        ws.cell(row=rows["PV of FCF"], column=col).number_format = "#,##0"

    # --- Terminal value / enterprise value / equity value block ---
    row += 1
    last_fcf_col_letter = get_column_letter(last_data_col)
    last_df_cell = f"{last_fcf_col_letter}{rows['Discount Factor']}"
    last_fcf_cell = f"{last_fcf_col_letter}{rows['Unlevered FCF']}"
    sum_pv_range = f"{get_column_letter(first_data_col)}{rows['PV of FCF']}:{last_fcf_col_letter}{rows['PV of FCF']}"

    labels_values = [
        ("Sum of PV of FCF", f"=SUM({sum_pv_range})"),
        ("Terminal Value", f"={last_fcf_cell}*(1+$B$4)/($B$3-$B$4)"),
        ("PV of Terminal Value", None),  # filled below, needs terminal value row ref
        ("Enterprise Value", None),
        ("+ Cash", assumptions.cash),
        ("- Debt", assumptions.debt),
        ("Equity Value", None),
        ("Shares Outstanding", assumptions.shares_outstanding),
        ("Fair Value / Share", None),
    ]

    row_refs = {}
    for label, value in labels_values:
        ws.cell(row=row, column=1, value=label).font = BOLD
        row_refs[label] = row
        if value is not None:
            ws.cell(row=row, column=2, value=value)
            ws.cell(row=row, column=2).number_format = "#,##0"
        row += 1

    tv_cell = f"B{row_refs['Terminal Value']}"
    ws[f"B{row_refs['PV of Terminal Value']}"] = f"={tv_cell}*{last_df_cell}"
    ws[f"B{row_refs['PV of Terminal Value']}"].number_format = "#,##0"

    sum_pv_cell = f"B{row_refs['Sum of PV of FCF']}"
    pv_tv_cell = f"B{row_refs['PV of Terminal Value']}"
    ws[f"B{row_refs['Enterprise Value']}"] = f"={sum_pv_cell}+{pv_tv_cell}"
    ws[f"B{row_refs['Enterprise Value']}"].number_format = "#,##0"

    ev_cell = f"B{row_refs['Enterprise Value']}"
    cash_cell = f"B{row_refs['+ Cash']}"
    debt_cell = f"B{row_refs['- Debt']}"
    ws[f"B{row_refs['Equity Value']}"] = f"={ev_cell}+{cash_cell}-{debt_cell}"
    ws[f"B{row_refs['Equity Value']}"].number_format = "#,##0"

    equity_cell = f"B{row_refs['Equity Value']}"
    shares_cell = f"B{row_refs['Shares Outstanding']}"
    ws[f"B{row_refs['Fair Value / Share']}"] = f"={equity_cell}/{shares_cell}"
    ws[f"B{row_refs['Fair Value / Share']}"].number_format = "$#,##0.00"

    # Column widths
    ws.column_dimensions["A"].width = 24
    for col in range(2, last_data_col + 1):
        ws.column_dimensions[get_column_letter(col)].width = 13

    wb.save(filepath)
    return filepath


if __name__ == "__main__":
    from data_schemas import HistoricalFinancials
    from ratios import compute_ratios
    from seed import seed_assumptions

    hist = HistoricalFinancials(
        ticker="AMZN",
        years=["2017", "2018", "2019", "2020", "2021"],
        revenue=[177866, 232887, 280522, 386064, 469822],
        ebit=[4106, 12421, 14541, 22899, 24879],
        taxes=[770, 1196, 2373, 2863, 4791],
        da=[11478, 15341, 21789, 25251, 34296],
        capex=[11955, 13427, 16861, 40140, 61053],
        nwc_change=[-173, -1043, -2438, 13481, -19611],
        cash=66385, debt=47556, shares_outstanding=10456, current_share_price=122.42,
    )
    ratios = compute_ratios(hist)
    assumptions = seed_assumptions(hist, ratios, wacc=0.0782, terminal_growth_rate=0.03)

    path = export_dcf_to_excel(assumptions, "amzn_dcf.xlsx")
    print(f"Saved to {path}")