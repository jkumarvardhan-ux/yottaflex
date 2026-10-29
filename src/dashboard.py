"""
YottaFlex Dock & Yard Appointment Scheduler – Interactive Dashboard
Run:  streamlit run src/dashboard.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Paths & page config
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT / "data" / "csv"

st.set_page_config(
    page_title="YottaFlex Dock Scheduler",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Data loaders (cached)
# ---------------------------------------------------------------------------
@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    path = CSV_DIR / f"{name}.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data
def load_all():
    tables = {
        "facilities": load_csv("facilities"),
        "docks": load_csv("docks"),
        "yard_slots": load_csv("yard_slots"),
        "carriers": load_csv("carriers"),
        "vehicles": load_csv("vehicles"),
        "labor_shifts": load_csv("labor_shifts"),
        "appointments": load_csv("appointments"),
        "shipments": load_csv("shipments"),
        "handling_requirements": load_csv("handling_requirements"),
        "events": load_csv("check_in_events"),
        "exceptions": load_csv("exceptions"),
        "ground_truth": load_csv("ground_truth"),
    }
    return tables


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def kpi_card(label: str, value, delta: str | None = None):
    st.metric(label, value, delta=delta)


def empty_state(msg: str = "No data found. Run:  python -m src.generate --mode starter --seed 20261022"):
    st.warning(msg)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("🚛 YottaFlex")
st.sidebar.caption("Dock & Yard Appointment Scheduler")

tables = load_all()
appts = tables["appointments"]
docks = tables["docks"]
events = tables["events"]
exceptions = tables["exceptions"]
gt = tables["ground_truth"]
shipments = tables["shipments"]
facilities = tables["facilities"]
carriers = tables["carriers"]

if appts.empty:
    empty_state()
    st.stop()

page = st.sidebar.radio(
    "Navigate",
    [
        "Overview",
        "Appointments",
        "Dock Utilization",
        "Events Timeline",
        "Exceptions & Ground Truth",
        "Shipments & Handling",
        "Master Data",
        "Raw Tables",
    ],
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Seed:** `20261022`")
st.sidebar.markdown(f"**Facilities:** {len(facilities)}")
st.sidebar.markdown(f"**Docks:** {len(docks)}")
st.sidebar.markdown(f"**Appointments:** {len(appts)}")
st.sidebar.markdown(f"**Events:** {len(events)}")
st.sidebar.markdown(f"**Exceptions:** {len(exceptions)}")

# ---------------------------------------------------------------------------
# PAGE: Overview
# ---------------------------------------------------------------------------
if page == "Overview":
    st.title("Dashboard Overview")
    st.caption("Synthetic end-to-end dock/yard appointment workflow – YottaFlex Challenge")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("Facilities", len(facilities))
    with c2:
        kpi_card("Docks", len(docks))
    with c3:
        kpi_card("Appointments", len(appts))
    with c4:
        kpi_card("Events", len(events))
    with c5:
        kpi_card("Exceptions", len(exceptions))

    st.markdown("---")

    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Appointment Status Mix")
        status_counts = appts["status"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        fig = px.pie(
            status_counts,
            names="status",
            values="count",
            color="status",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=360)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Appointment Type (In / Out)")
        type_counts = appts["appointment_type"].value_counts().reset_index()
        type_counts.columns = ["type", "count"]
        fig2 = px.bar(
            type_counts,
            x="type",
            y="count",
            color="type",
            text="count",
            color_discrete_sequence=["#4C78A8", "#F58518"],
        )
        fig2.update_layout(showlegend=False, height=360, margin=dict(t=20, b=20))
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Appointments per Day")
    date_col = appts["confirmed_date"].fillna(appts["requested_date"])
    daily = date_col.value_counts().sort_index().reset_index()
    daily.columns = ["date", "appointments"]
    fig3 = px.area(daily, x="date", y="appointments", markers=True)
    fig3.update_layout(height=320, margin=dict(t=10, b=10))
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Exception Severity")
    if not exceptions.empty:
        sev = exceptions["severity"].value_counts().reset_index()
        sev.columns = ["severity", "count"]
        fig4 = px.bar(
            sev,
            x="severity",
            y="count",
            color="severity",
            text="count",
            color_discrete_map={
                "LOW": "#54A24B",
                "MEDIUM": "#EECA3B",
                "HIGH": "#F58518",
                "CRITICAL": "#E45756",
            },
        )
        fig4.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No exceptions in current dataset.")

# ---------------------------------------------------------------------------
# PAGE: Appointments
# ---------------------------------------------------------------------------
elif page == "Appointments":
    st.title("Appointments")

    # Filters
    f1, f2, f3 = st.columns(3)
    with f1:
        status_filter = st.multiselect(
            "Status",
            options=sorted(appts["status"].dropna().unique()),
            default=list(appts["status"].dropna().unique()),
        )
    with f2:
        type_filter = st.multiselect(
            "Type",
            options=sorted(appts["appointment_type"].dropna().unique()),
            default=list(appts["appointment_type"].dropna().unique()),
        )
    with f3:
        fac_filter = st.multiselect(
            "Facility",
            options=sorted(appts["facility_id"].dropna().unique()),
            default=list(appts["facility_id"].dropna().unique()),
        )

    filtered = appts[
        appts["status"].isin(status_filter)
        & appts["appointment_type"].isin(type_filter)
        & appts["facility_id"].isin(fac_filter)
    ]

    st.caption(f"Showing **{len(filtered)}** of {len(appts)} appointments")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Filtered", len(filtered))
    with c2:
        kpi_card("Avg service (min)", int(filtered["service_duration_min"].mean()) if len(filtered) else 0)
    with c3:
        kpi_card("Departed", int((filtered["status"] == "DEPARTED").sum()))
    with c4:
        kpi_card("No-show", int((filtered["status"] == "NO_SHOW").sum()))

    st.dataframe(
        filtered[
            [
                "appointment_id",
                "facility_id",
                "dock_id",
                "carrier_id",
                "appointment_type",
                "requested_date",
                "requested_window_start",
                "status",
                "service_duration_min",
            ]
        ],
        use_container_width=True,
        height=420,
    )

    st.subheader("Service Duration Distribution")
    fig = px.histogram(
        filtered,
        x="service_duration_min",
        nbins=30,
        color="appointment_type",
        barmode="overlay",
        opacity=0.75,
    )
    fig.update_layout(height=320)
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# PAGE: Dock Utilization
# ---------------------------------------------------------------------------
elif page == "Dock Utilization":
    st.title("Dock Utilization")

    # Booked count per dock (ignore cancelled / no-show)
    active = appts[~appts["status"].isin(["CANCELLED", "NO_SHOW"])].copy()
    active["book_date"] = active["confirmed_date"].fillna(active["requested_date"])

    dock_booked = active.groupby("dock_id").size().reset_index(name="booked")
    dock_info = docks.merge(dock_booked, on="dock_id", how="left").fillna({"booked": 0})
    dock_info["utilization"] = (dock_info["booked"] / (dock_info["daily_capacity"] * 60)).clip(upper=1.5)
    # rough: 60-day horizon hardcoded from config
    dock_info["util_pct"] = (dock_info["utilization"] * 100).round(1)

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("Total docks", len(dock_info))
    with c2:
        kpi_card("Avg util %", f"{dock_info['util_pct'].mean():.1f}%")
    with c3:
        kpi_card("Peak util %", f"{dock_info['util_pct'].max():.1f}%")

    st.subheader("Utilization by Dock")
    fig = px.bar(
        dock_info.sort_values("util_pct", ascending=False),
        x="dock_id",
        y="util_pct",
        color="dock_type",
        hover_data=["facility_id", "daily_capacity", "booked"],
        labels={"util_pct": "Utilization %"},
    )
    fig.update_layout(height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Bookings by Dock Type")
    by_type = dock_info.groupby("dock_type").agg(
        docks=("dock_id", "count"),
        capacity=("daily_capacity", "sum"),
        booked=("booked", "sum"),
    ).reset_index()
    fig2 = px.bar(by_type, x="dock_type", y=["booked", "capacity"], barmode="group")
    fig2.update_layout(height=320)
    st.plotly_chart(fig2, use_container_width=True)

    st.dataframe(
        dock_info[
            ["dock_id", "facility_id", "dock_type", "daily_capacity", "booked", "util_pct"]
        ].sort_values("util_pct", ascending=False),
        use_container_width=True,
        height=300,
    )

# ---------------------------------------------------------------------------
# PAGE: Events Timeline
# ---------------------------------------------------------------------------
elif page == "Events Timeline":
    st.title("Events Timeline")

    if events.empty:
        empty_state("No events generated.")
        st.stop()

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("Total events", len(events))
    with c2:
        avg_wait = events["wait_time_min"].dropna()
        kpi_card("Avg wait (min)", f"{avg_wait.mean():.0f}" if len(avg_wait) else "—")
    with c3:
        avg_dwell = events["dwell_time_min"].dropna()
        kpi_card("Avg dwell (min)", f"{avg_dwell.mean():.0f}" if len(avg_dwell) else "—")

    st.subheader("Event Type Distribution")
    et = events["event_type"].value_counts().reset_index()
    et.columns = ["event_type", "count"]
    fig = px.bar(et, x="event_type", y="count", color="event_type", text="count")
    fig.update_layout(showlegend=False, height=360, xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Browse events for one appointment")
    appt_ids = sorted(events["appointment_id"].unique())
    selected = st.selectbox("Appointment ID", appt_ids[:200])  # limit dropdown size
    sub = events[events["appointment_id"] == selected].sort_values("sequence")
    st.dataframe(sub, use_container_width=True, height=280)

    if not sub.empty and "event_ts" in sub.columns:
        sub = sub.copy()
        sub["event_ts"] = pd.to_datetime(sub["event_ts"])
        fig2 = px.scatter(
            sub,
            x="event_ts",
            y="sequence",
            color="event_type",
            size=[12] * len(sub),
            hover_data=["event_id", "actor_role", "wait_time_min", "dwell_time_min"],
            title=f"Timeline – {selected}",
        )
        fig2.update_layout(height=320)
        st.plotly_chart(fig2, use_container_width=True)

# ---------------------------------------------------------------------------
# PAGE: Exceptions & Ground Truth
# ---------------------------------------------------------------------------
elif page == "Exceptions & Ground Truth":
    st.title("Exceptions & Ground Truth")

    c1, c2 = st.columns(2)
    with c1:
        kpi_card("Exceptions", len(exceptions))
    with c2:
        kpi_card("Ground-truth labels", len(gt))

    if exceptions.empty:
        st.info("No exceptions injected in this run.")
    else:
        st.subheader("Exceptions by Issue Type")
        ic = exceptions["issue_type"].value_counts().reset_index()
        ic.columns = ["issue_type", "count"]
        fig = px.bar(
            ic,
            x="issue_type",
            y="count",
            color="issue_type",
            text="count",
        )
        fig.update_layout(showlegend=False, height=340, xaxis_tickangle=-25)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Exception records")
        st.dataframe(
            exceptions[
                ["exception_id", "entity_id", "issue_type", "severity", "cause_code", "description"]
            ],
            use_container_width=True,
            height=320,
        )

    st.markdown("---")
    st.subheader("Ground Truth (separate labels – not mixed into features)")
    if gt.empty:
        st.info("No ground-truth rows.")
    else:
        st.dataframe(gt, use_container_width=True, height=320)

        # Match rate
        if not exceptions.empty:
            matched = set(exceptions["entity_id"]) & set(gt["entity_id"])
            st.success(f"Exception ↔ Ground-truth entity overlap: **{len(matched)}** / {len(exceptions)}")

# ---------------------------------------------------------------------------
# PAGE: Shipments & Handling
# ---------------------------------------------------------------------------
elif page == "Shipments & Handling":
    st.title("Shipments & Handling Requirements")

    handling = tables["handling_requirements"]

    c1, c2, c3 = st.columns(3)
    with c1:
        kpi_card("Shipments", len(shipments))
    with c2:
        kpi_card("Handling reqs", len(handling))
    with c3:
        if not shipments.empty:
            kpi_card("Avg weight (kg)", f"{shipments['weight_kg'].mean():.0f}")

    if not shipments.empty:
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Commodity mix")
            com = shipments["commodity"].value_counts().head(10).reset_index()
            com.columns = ["commodity", "count"]
            fig = px.bar(com, x="count", y="commodity", orientation="h")
            fig.update_layout(height=360, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.subheader("Special handling flags")
            flags = pd.DataFrame(
                {
                    "flag": ["Refrigerated", "Hazardous", "Oversize"],
                    "count": [
                        int(shipments["is_refrigerated"].sum()),
                        int(shipments["is_hazardous"].sum()),
                        int(shipments["is_oversize"].sum()),
                    ],
                }
            )
            fig2 = px.bar(flags, x="flag", y="count", color="flag", text="count")
            fig2.update_layout(showlegend=False, height=360)
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Weight distribution")
        fig3 = px.histogram(shipments, x="weight_kg", nbins=40, color="direction")
        fig3.update_layout(height=300)
        st.plotly_chart(fig3, use_container_width=True)

    if not handling.empty:
        st.subheader("Handling type mix")
        ht = handling["handling_type"].value_counts().reset_index()
        ht.columns = ["handling_type", "count"]
        fig4 = px.pie(ht, names="handling_type", values="count", hole=0.4)
        fig4.update_layout(height=320)
        st.plotly_chart(fig4, use_container_width=True)

# ---------------------------------------------------------------------------
# PAGE: Master Data
# ---------------------------------------------------------------------------
elif page == "Master Data":
    st.title("Master Data")

    tab1, tab2, tab3, tab4 = st.tabs(["Facilities", "Docks", "Carriers", "Vehicles"])

    with tab1:
        st.dataframe(facilities, use_container_width=True, height=360)
    with tab2:
        st.dataframe(docks, use_container_width=True, height=360)
        if not docks.empty:
            fig = px.histogram(docks, x="dock_type", color="dock_type")
            fig.update_layout(showlegend=False, height=280)
            st.plotly_chart(fig, use_container_width=True)
    with tab3:
        st.dataframe(carriers, use_container_width=True, height=360)
    with tab4:
        vehicles = tables["vehicles"]
        st.dataframe(vehicles, use_container_width=True, height=360)
        if not vehicles.empty:
            fig = px.histogram(vehicles, x="vehicle_type", color="vehicle_type")
            fig.update_layout(showlegend=False, height=280)
            st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# PAGE: Raw Tables
# ---------------------------------------------------------------------------
elif page == "Raw Tables":
    st.title("Raw Tables")
    choice = st.selectbox("Choose table", sorted(tables.keys()))
    df = tables[choice]
    st.caption(f"{len(df)} rows × {len(df.columns)} columns")
    st.dataframe(df, use_container_width=True, height=500)

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"Download {choice}.csv",
        data=csv_bytes,
        file_name=f"{choice}.csv",
        mime="text/csv",
    )
