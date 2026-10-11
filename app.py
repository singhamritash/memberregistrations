"""Member Registration Tracker: Streamlit UI.

Left side: three options. Right side: the selected option's page.
Run with:  streamlit run app.py
"""

from datetime import date

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import charts
import data_store as ds
import outreach

st.set_page_config(page_title="Member Registration Tracker", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: #F4F9FE; }
    section[data-testid="stSidebar"] { background: #DCEBFA; }
    h1, h2, h3 { color: #1F4E79; }
    div[data-testid="stMetric"] {
        background: #FFFFFF; border: 1px solid #C9DDF2; border-radius: 10px; padding: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

PLOT_CONFIG = {
    "displaylogo": False,
    "toImageButtonOptions": {"format": "png", "scale": 2},
}


def legend() -> None:
    st.markdown(
        "**Legend:** soft blue = normal day · "
        "<span style='color:#FF8C1A'>**strong orange**</span> = low day (bottom 10% of the month) · "
        "<span style='color:#E0242F'>**strong red**</span> = high day (top 10% of the month)",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- Option 1
def page_registration_stats() -> None:
    st.header("Option 1: View registration stats")
    picked = st.date_input(
        "Choose a month (the month of the date you pick is used)",
        value=ds.REG_MIN.date(),
        min_value=ds.REG_MIN.date(),
        max_value=ds.REG_MAX.date(),
    )
    month_df = ds.month_daily(picked.year, picked.month)
    low, high = charts.anomaly_thresholds(month_df["Total"])

    total = int(month_df["Total"].sum())
    low_days = month_df.index[month_df["Total"] <= low].day.tolist()
    high_days = month_df.index[month_df["Total"] >= high].day.tolist()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Registrations in month", f"{total:,}")
    c2.metric("Average per day", f"{month_df['Total'].mean():,.0f}")
    c3.metric("Low days (count)", f"{len(low_days)}", help=f"Days at or below {low:,.0f}")
    c4.metric("High days (count)", f"{len(high_days)}", help=f"Days at or above {high:,.0f}")

    st.caption(
        f"Low days: {', '.join(map(str, low_days)) or 'none'} · "
        f"High days: {', '.join(map(str, high_days)) or 'none'}"
    )
    legend()

    # All visualisations on one page. The 3D circular chart is interactive:
    # drag to rotate, scroll to zoom, and pick a day to bring it to the front.
    day_pick = st.slider(
        "Go to day in the circular chart",
        min_value=1,
        max_value=len(month_df),
        value=1,
        key=f"day-{picked:%Y-%m}",
    )
    selected_row = month_df.iloc[day_pick - 1]
    st.caption(
        f"Selected day {day_pick}: {int(selected_row['Total']):,} registrations "
        f"(Y {int(selected_row['Y']):,}, N {int(selected_row['N']):,})"
    )
    components.html(
        charts.radial_3d_html(month_df, low, high, selected_day=day_pick),
        height=800,
        scrolling=False,
    )
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(charts.line_2d(month_df, low, high), use_container_width=True, config=PLOT_CONFIG)
    with col_b:
        st.plotly_chart(charts.heatmap_2d(month_df), use_container_width=True, config=PLOT_CONFIG)
    col_c, col_d = st.columns(2)
    with col_c:
        st.plotly_chart(charts.bar_3d(month_df, low, high), use_container_width=True, config=PLOT_CONFIG)
    with col_d:
        st.plotly_chart(charts.surface_3d(month_df), use_container_width=True, config=PLOT_CONFIG)

    st.caption("Use the camera icon on any chart to download it as PNG.")
    daily_out = month_df.reset_index()
    daily_out["date"] = daily_out["date"].dt.strftime("%Y-%m-%d")
    st.download_button(
        "Download daily stats (CSV)",
        data=daily_out.to_csv(index=False).encode("utf-8"),
        file_name=f"registration_daily_{picked:%Y-%m}.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------- Option 2
def page_outreach() -> None:
    st.header("Option 2: Member outreach")
    search_by = st.radio("Search by", ["member_id", "SSN"], horizontal=True)
    query = st.text_input(f"Enter {search_by} (partial match allowed)").strip()
    if not query:
        st.info("Enter a member_id or SSN to find a member.")
        return

    matches, total_matches = ds.search_members(search_by, query)
    if total_matches == 0:
        st.warning("No member found.")
        return

    st.write(f"{total_matches:,} match(es). Showing {len(matches)}.")
    shown = matches[
        ["member_id", "first_name", "last_name", "Date_of_Birth", "SSN", "email_id",
         "relationship_code", "registration_status", "registration_date"]
    ].copy()
    shown["SSN"] = shown["SSN"].map(outreach.mask_ssn)
    shown["registration_date"] = shown["registration_date"].dt.strftime("%Y-%m-%d")
    st.dataframe(shown, hide_index=True, use_container_width=True)

    labels = {
        idx: f"{row.member_id} - {row.first_name} {row.last_name}" for idx, row in matches.iterrows()
    }
    chosen_idx = st.selectbox("Select member to contact", list(labels), format_func=labels.get)
    member = matches.loc[chosen_idx]

    st.subheader("Outreach message")
    template_name = st.selectbox("Outreach template", list(outreach.TEMPLATES))
    default_subject, default_body = outreach.render_template(template_name, member["first_name"])
    key_suffix = f"{chosen_idx}-{template_name}"
    subject = st.text_input("Subject", value=default_subject, key=f"subject-{key_suffix}")
    body = st.text_area("Message", value=default_body, height=180, key=f"body-{key_suffix}")
    st.caption(f"To: {member['email_id']}")

    if st.button("Send email", type="primary"):
        if not body.strip():
            st.error("The message is empty. Add text before sending.")
        else:
            outreach.log_outreach(member["member_id"], member["email_id"], subject, body)
            st.success(
                f"Simulated send to {member['email_id']} logged in outreach_log.csv. "
                "No email was delivered."
            )


# ---------------------------------------------------------------- Option 3
def page_reporting() -> None:
    st.header("Option 3: Reporting")
    report = st.selectbox(
        "Choose a report",
        [
            "Members not registered (by month)",
            "Registration stats for a day",
            "Registration spread over the last 6 months",
            "Query by registration status and month",
            "Query by relationship code",
        ],
    )

    if report == "Members not registered (by month)":
        picked = st.date_input("Month (any date in the month)", value=ds.REG_MIN.date(),
                               min_value=ds.REG_MIN.date(), max_value=ds.REG_MAX.date(), key="r1")
        rows = ds.members_not_registered(picked.year, picked.month)
        rows = outreach.mask_ssn_column(rows)  # SSN shows only the last 4 digits
        st.metric("Members not registered", f"{len(rows):,}")
        st.dataframe(rows.head(500), hide_index=True, use_container_width=True)
        st.caption("The table shows the first 500 rows. The download contains all rows.")
        st.download_button("Download CSV", data=rows.to_csv(index=False).encode("utf-8"),
                           file_name=f"not_registered_{picked:%Y-%m}.csv", mime="text/csv")

    elif report == "Registration stats for a day":
        picked = st.date_input("Day", value=ds.REG_MIN.date(),
                               min_value=ds.REG_MIN.date(), max_value=ds.REG_MAX.date(), key="r2")
        breakdown = ds.stats_for_day(pd.Timestamp(picked))
        st.dataframe(breakdown, hide_index=True, use_container_width=True)
        st.download_button("Download CSV", data=breakdown.to_csv(index=False).encode("utf-8"),
                           file_name=f"registration_day_{picked:%Y-%m-%d}.csv", mime="text/csv")

    elif report == "Registration spread over the last 6 months":
        monthly = ds.monthly_table()
        last_six = monthly.tail(6)
        st.plotly_chart(charts.monthly_bar(last_six), use_container_width=True, config=PLOT_CONFIG)
        st.dataframe(last_six.reset_index(), hide_index=True, use_container_width=True)
        st.caption(f"Last 6 months of data: {last_six.index[0]} to {last_six.index[-1]}.")
        st.download_button("Download CSV", data=last_six.reset_index().to_csv(index=False).encode("utf-8"),
                           file_name="registration_last_6_months.csv", mime="text/csv")

    elif report == "Query by registration status and month":
        c1, c2 = st.columns(2)
        status = c1.selectbox("Registration status", ds.STATUS_VALUES)
        picked = c2.date_input("Month (any date in the month)", value=ds.REG_MIN.date(),
                               min_value=ds.REG_MIN.date(), max_value=ds.REG_MAX.date(), key="r4")
        rows = ds.status_by_month(status, picked.year, picked.month)
        rows = outreach.mask_ssn_column(rows)  # SSN shows only the last 4 digits
        st.metric(f"Members with status {status}", f"{len(rows):,}")
        st.dataframe(rows.head(500), hide_index=True, use_container_width=True)
        st.caption("The table shows the first 500 rows. The download contains all rows.")
        st.download_button("Download CSV", data=rows.to_csv(index=False).encode("utf-8"),
                           file_name=f"status_{status}_{picked:%Y-%m}.csv", mime="text/csv")

    elif report == "Query by relationship code":
        code = st.selectbox("Relationship code", ds.RELATIONSHIP_VALUES,
                            format_func=lambda c: {"EE": "EE (employee)", "SP": "SP (spouse)"}[c])
        rows = ds.by_relationship(code)
        rows = outreach.mask_ssn_column(rows)  # SSN shows only the last 4 digits
        st.metric(f"Members with code {code}", f"{len(rows):,}")
        st.dataframe(rows.head(500), hide_index=True, use_container_width=True)
        st.caption("The table shows the first 500 rows. The download contains all rows.")
        st.download_button("Download CSV", data=rows.to_csv(index=False).encode("utf-8"),
                           file_name=f"relationship_{code}.csv", mime="text/csv")


# ---------------------------------------------------------------- Shell
st.sidebar.title("Member Registration Tracker")
choice = st.sidebar.radio(
    "Menu",
    [
        "1. View registration stats",
        "2. Member outreach",
        "3. Reporting",
    ],
)
st.sidebar.caption("Data: Data/Master.csv (1,000,000 synthetic records)")

if choice.startswith("1"):
    page_registration_stats()
elif choice.startswith("2"):
    page_outreach()
else:
    page_reporting()
