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
#   roster   <- load_employees()                           (fixed; not uploaded)
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
from payroll.extract import load_employees, load_export
from payroll.summarize import build_history, summarize_employees
from payroll.reshape import hours_grid, missed_weeks, pay_by_month


# title and instructions
st.title("Salt City Coffee — Quarterly Payroll Report")
st.text(
    "Upload the weekly payroll exports for the period you want to review - old "
    "spreadsheet weeks and new app weeks can be mixed. The roster is loaded "
    "automatically."
)

# load in data
roster = load_employees()
uploads = st.file_uploader(
    "Upload Weekly payroll exports (CSV)",
    key="exports",
    accept_multiple_files=True,
)
# pipeline
if len(uploads) > 0:
    history = build_history([load_export(u) for u in uploads], roster)
    # unmatched employee_id warning
    unmatched_ids = history[history["department"].isna()]
    if len(unmatched_ids) > 0:
        history = history[history["department"].notna()]
        warning = ""
        for row in unmatched_ids.itertuples():
            warning += row.employeeid
            warning += ", "
        st.warning(
            f"{len(unmatched_ids)} Employee(s) not on the roster: "
            f"{warning}"
                )
    # department select box
    departments = list(history["department"].drop_duplicates())
    departments.insert(0, "ALL")
    department_selection = st.selectbox("Department", departments, key='Department')

    # date selection
    start_date = history["pay_date"].min().date()
    end_date = history["pay_date"].max().date()
    date_range = st.date_input("Pay dates", key="inputs", value=(start_date, end_date))
    start_string = date_range[0].strftime("%Y-%m-%d")
    end_string = date_range[1].strftime("%Y-%m-%d")

    # filtered summary
    st.subheader(f"{department_selection} | {start_string} to {end_string}")
    date_filter = (
        (history['pay_date'].dt.date >= date_range[0])
        & (history['pay_date'].dt.date <= date_range[1])
    )
    filtered_data = history[date_filter]
    col1, col2, col3, col4 = st.columns(4)
    if department_selection == "ALL":
        with col1:
            st.metric("Weeks", filtered_data["pay_date"].nunique())
        with col2:
            st.metric("Employees", filtered_data["display_name"].nunique())
        with col3:
            st.metric("Total hours", f"{filtered_data["hours_worked"].sum():,.2f}")
        with col4:
            st.metric("Total gross pay", f"${filtered_data['gross_pay'].sum():,.2f}")
    else:
        filtered = filtered_data[filtered_data["department"] == department_selection]
        with col1:
            st.metric("Weeks", filtered["pay_date"].nunique())
        with col2:
            st.metric("Employees", filtered["display_name"].nunique())
        with col3:
            st.metric("Total hours", f"{filtered["hours_worked"].sum():,.2f}")
        with col4:
            st.metric("Total gross pay", f"${filtered['gross_pay'].sum():,.2f}")

    # bar chat
    st.subheader("Gross pay by month")
    pay_data = pay_by_month(history)
    st.bar_chart(pay_data, x="month", x_label="department")

    # df for employee summary
    st.subheader("Employees")
    employee_summary = summarize_employees(history)
    st.dataframe(employee_summary)

    # df for hours grid
    st.subheader("Hours by week")
    grid_hours = hours_grid(history)
    st.dataframe(grid_hours)

    # df for weeks missed
    st.subheader("Missed weeks")
    weeks_missed = missed_weeks(grid_hours)
    st.dataframe(weeks_missed)

    # export as CSV
    export_final = pay_data.to_csv(index=False)
    st.download_button(
        key="download",
        label="Download pay by month for accountant (CSV)",
        data=export_final,
    )
