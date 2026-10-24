"""
payroll_report_app.py — the quarter at a glance, for someone who never opens a terminal.

Every Friday since September the office manager at Salt City Coffee has downloaded
a payroll export from the Assignment 04 app; before that she typed the same file
by hand. The owner now wants to know where the hours went this quarter, the
accountant wants pay by month and department, and the manager wants to see who
has been missing shifts. This page answers all three from the pile of exports.

Same shape as Assignment 04: the page *assembles* the pipeline — one call to
`build_history` does the cleaning — and then shows the reports, filtered by the
department and dates the user picks.

Run it:  Run and Debug -> "Streamlit Run: Current File"
Test it: pytest tests/test_pipeline.py -k app
"""

# --- The page ---------------------------------------------------------------------
#
# No scaffolding. Every function this page needs already exists in the payroll
# package, and every widget it needs you used in Assignments 03 and 04 — plus two
# new ones, st.date_input and st.bar_chart. README Step 8 has the exact widgets,
# keys and labels; the tests in tests/test_pipeline.py -k app check them.
#
# The shape, in words:
#
#   title and a sentence of instructions
#   roster   <- load_employees()                          (fixed; not uploaded)
#   uploads  <- st.file_uploader, key="exports", accept_multiple_files=True
#               (an empty list until files are chosen)
#   if there are uploads:
#       history <- build_history([load_export(u) for u in uploads], roster)
#       st.warning naming any employeeid with no department (not on the roster);
#           the reports below use only the rows that matched
#       st.selectbox, key="department": "All" plus each department
#       st.date_input, key="dates": a (start, end) range, defaulting to the first
#           and last pay_date — compare against pay_date.dt.date to filter
#       the selection as a subheader
#       four st.metric cards in st.columns(4): Weeks, Employees, Total hours,
#           Total gross pay — counts are .nunique(), totals are .sum()
#       st.bar_chart of pay_by_month(selected), with month as the x axis
#       st.dataframe of summarize_employees(selected)
#       st.dataframe of hours_grid(selected), then of missed_weeks(that grid)
#       st.download_button, key="download": pay_by_month(...).to_csv(index=False)
#
# What the page does NOT do: cleaning, grouping, pivoting. If you find yourself
# writing a groupby or a pivot_table here, that logic belongs in the package.
import streamlit as st
from payroll.summarize import build_history, summarize_employees
from payroll.extract import load_employees, load_export
from payroll.reshape import pay_by_month, missed_weeks, hours_grid

st.title("Salt City Coffee — Quarterly Payroll Report")
st.write(
    "Upload the weekly payroll exports for the period you want\
to review - old spreadsheet weeks and new app weeks can be mixed.\
the roster is loaded automatically"
)

roster = load_employees()

uploads = st.file_uploader(
    "Upload weekly payroll exports",
    key="exports",
    type=["csv"],
    accept_multiple_files=True,
)

if uploads:
    exports = [load_export(upload) for upload in uploads]
    history = build_history(exports, roster)
    unmatched_ids = (
        history.loc[history["department"].isna(), "employeeid"].dropna().unique()
    )
    if len(unmatched_ids):
        st.warning(
            f"These employee IDs are not on the roster: {', '.join(unmatched_ids)}"
        )

    matched_history = history.loc[history["department"].notna()].copy()
    departments = ["All", *sorted(matched_history["department"].unique())]
    selected_dept = st.selectbox("Department", departments, key="department")
    selected_dates = st.date_input(
        "Pay Dates",
        value=(
            matched_history["pay_date"].dt.date.min(),
            matched_history["pay_date"].dt.date.max(),
        ),
        key="dates",
    )
    start_date, end_date = selected_dates
    selected = matched_history.loc[
        matched_history["pay_date"].dt.date.between(start_date, end_date)
    ]
    if selected_dept != "All":
        selected = selected.loc[selected["department"] == selected_dept]

    start_label = start_date.strftime("%Y-%m-%d")
    end_label = end_date.strftime("%Y-%m-%d")
    st.subheader(f"{selected_dept} {start_label} to {end_label}")

    summary = summarize_employees(selected)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Weeks", selected["week_ending"].nunique())
    col2.metric("Employees", selected["employee_id"].nunique())
    col3.metric("Total hours", f"{selected['hours_worked'].sum():,.2f}")
    total_gross_pay = summary["total_pay"].sum()
    col4.metric("Total gross pay", f"${total_gross_pay:,.2f}")

    st.subheader("Gross pay by month")
    bar = pay_by_month(selected)
    hours_df = hours_grid(selected)
    missed_df = missed_weeks(hours_df)

    st.bar_chart(bar, x="month")
    st.subheader("Employees")
    st.dataframe(summary)
    st.subheader("Hours by week")
    st.dataframe(hours_df)
    st.subheader("Missed weeks")
    st.dataframe(missed_df)

    monthly_pay = pay_by_month(selected)
    st.download_button(
        "Download pay by month for the accountant (CSV)",
        data=monthly_pay.to_csv(index=False),
        file_name="pay_by_month.csv",
        mime="text/csv",
        key="download",
    )
