"""Chart builders for the registration stats page (2D and 3D Plotly figures).

Colour rules from the PRD: soft blue tones for normal days, strong colours for anomalies.
  - Normal day:      SOFT_BLUE
  - Low day (<= 10th percentile of the month):  LOW_STRONG (strong orange)
  - High day (>= 90th percentile of the month): HIGH_STRONG (strong red)
"""

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go

SOFT_BLUE = "#A9CCEA"
SOFT_BLUE_LINE = "#5B9BD5"
BLUE_SCALE = [[0, "#F2F8FD"], [0.5, "#9CC6EA"], [1, "#2F7DC1"]]
LOW_STRONG = "#FF8C1A"
HIGH_STRONG = "#E0242F"
GRID = "#DCE8F5"
BG = "rgba(0,0,0,0)"

LOW_PCT = 0.10
HIGH_PCT = 0.90

# Cube faces (two triangles each) for a unit cube, vertex order matches CUBE_VERTS.
CUBE_VERTS = np.array(
    [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]]
)
CUBE_TRIANGLES = np.array(
    [
        [0, 1, 2], [0, 2, 3],  # bottom
        [4, 5, 6], [4, 6, 7],  # top
        [0, 1, 5], [0, 5, 4],  # front
        [1, 2, 6], [1, 6, 5],  # right
        [2, 3, 7], [2, 7, 6],  # back
        [3, 0, 4], [3, 4, 7],  # left
    ]
)
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def anomaly_thresholds(totals: pd.Series) -> tuple[float, float]:
    return float(totals.quantile(LOW_PCT)), float(totals.quantile(HIGH_PCT))


def day_colors(totals: pd.Series, low: float, high: float) -> list[str]:
    colors = []
    for value in totals:
        if value >= high:
            colors.append(HIGH_STRONG)
        elif value <= low:
            colors.append(LOW_STRONG)
        else:
            colors.append(SOFT_BLUE)
    return colors


def _calendar_grid(month_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Return (weeks x weekdays) count matrix and a matching day-number matrix for a month."""
    first_day = month_df.index[0]
    offset = first_day.weekday()  # Monday = 0
    n_weeks = int(np.ceil((len(month_df) + offset) / 7))
    counts = np.full((n_weeks, 7), np.nan)
    day_numbers = np.full((n_weeks, 7), np.nan)
    for position, (day, row) in enumerate(month_df.iterrows()):
        slot = position + offset
        counts[slot // 7, slot % 7] = row["Total"]
        day_numbers[slot // 7, slot % 7] = day.day
    return counts, day_numbers


def _axis_style(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        margin=dict(l=10, r=10, t=50, b=10),
        font=dict(color="#1B3A5C"),
    )
    return fig


SELECTED_DAY_COLOR = "#1B3A5C"


def radial_3d(month_df: pd.DataFrame, low: float, high: float, selected_day: int) -> go.Figure:
    """Interactive 3D circular chart: one segment per day, height = registrations.

    Drag to rotate and scroll to zoom (Plotly 3D controls). The selected day is
    drawn in a dark navy colour and the camera turns to face it.
    """
    n = len(month_df)
    totals = month_df["Total"].to_numpy(dtype=float)
    max_total = max(totals.max(), 1.0)
    colors = day_colors(month_df["Total"], low, high)
    r_inner, r_outer, max_height = 5.0, 8.0, 4.0
    step = 2 * np.pi / n
    span = step * 0.78

    xs, ys, zs, texts, i_idx, j_idx, k_idx, face_colors = [], [], [], [], [], [], [], []
    selected_theta = None
    for pos in range(n):
        day = int(month_df.index[pos].day)
        theta = np.pi / 2 - pos * step  # day 1 starts at the top and runs clockwise
        a0, a1 = theta - span / 2, theta + span / 2
        height = max(totals[pos] / max_total * max_height, 0.05)
        is_selected = day == selected_day
        if is_selected:
            selected_theta = theta
        color = SELECTED_DAY_COLOR if is_selected else colors[pos]
        base = len(xs)
        for u, v, w in CUBE_VERTS:  # u: radial, v: around the ring, w: height
            r = r_inner + u * (r_outer - r_inner)
            angle = a0 + v * (a1 - a0)
            xs.append(r * np.cos(angle))
            ys.append(r * np.sin(angle))
            zs.append(w * height)
            texts.append(f"Day {day}: {int(totals[pos]):,} registrations")
        tris = CUBE_TRIANGLES + base
        i_idx.extend(tris[:, 0])
        j_idx.extend(tris[:, 1])
        k_idx.extend(tris[:, 2])
        face_colors.extend([color] * len(CUBE_TRIANGLES))

    fig = go.Figure(
        go.Mesh3d(
            x=xs, y=ys, z=zs, i=i_idx, j=j_idx, k=k_idx,
            facecolor=face_colors, flatshading=True,
            text=texts, hovertemplate="%{text}<extra></extra>",
            lighting=dict(ambient=0.7, diffuse=0.6),
        )
    )

    # Base ring and day labels, drawn flat on the ground plane.
    ring_angles = np.linspace(0, 2 * np.pi, 120)
    ring_r = r_outer + 0.6
    fig.add_trace(
        go.Scatter3d(
            x=ring_r * np.cos(ring_angles), y=ring_r * np.sin(ring_angles),
            z=np.zeros_like(ring_angles), mode="lines",
            line=dict(color="#5B9BD5", width=3), hoverinfo="skip", showlegend=False,
        )
    )
    label_r = r_outer + 1.4
    label_theta = np.pi / 2 - np.arange(n) * step
    fig.add_trace(
        go.Scatter3d(
            x=label_r * np.cos(label_theta), y=label_r * np.sin(label_theta),
            z=np.zeros(n), mode="text",
            text=[str(d) for d in month_df.index.day], textfont=dict(color="#1B3A5C", size=11),
            hoverinfo="skip", showlegend=False,
        )
    )

    # Click targets: one small marker on top of each segment (Plotly.js fires click events
    # for markers, not for mesh faces).
    mid_r = (r_inner + r_outer) / 2
    fig.add_trace(
        go.Scatter3d(
            x=mid_r * np.cos(label_theta), y=mid_r * np.sin(label_theta),
            z=np.array([max(t / max_total * max_height, 0.05) for t in totals]) + 0.3,
            mode="markers", marker=dict(size=7, color=SELECTED_DAY_COLOR),
            hovertext=[f"Day {d}" for d in month_df.index.day],
            hoverinfo="text", showlegend=False,
        )
    )

    # Camera faces the selected day from outside the ring.
    if selected_theta is None:
        selected_theta = np.pi / 2
    eye = dict(x=1.5 * np.cos(selected_theta), y=1.5 * np.sin(selected_theta), z=1.3)
    axis = dict(visible=False, showbackground=False, showgrid=False, zeroline=False)
    fig.update_layout(
        title="Registrations by day (3D circular, drag to rotate, scroll to zoom)",
        showlegend=False,
        scene=dict(
            xaxis=dict(axis, range=[-r_outer - 1.6, r_outer + 1.6]),
            yaxis=dict(axis, range=[-r_outer - 1.6, r_outer + 1.6]),
            zaxis=dict(axis, range=[0, max_height * 1.2]),
            aspectmode="manual",
            aspectratio=dict(x=1, y=1, z=0.45),
            camera=dict(eye=eye, up=dict(x=0, y=0, z=1)),
        ),
        height=560,
    )
    return _axis_style(fig)


def line_2d(month_df: pd.DataFrame, low: float, high: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=month_df.index.day,
            y=month_df["Total"],
            mode="lines+markers",
            line=dict(color=SOFT_BLUE_LINE, width=2.5),
            marker=dict(
                color=day_colors(month_df["Total"], low, high), size=9, line=dict(width=0)
            ),
            name="Registrations",
        )
    )
    mean = float(month_df["Total"].mean())
    fig.add_hline(y=mean, line=dict(color="#1F6FB2", dash="dot"), annotation_text="Average")
    fig.add_hline(y=high, line=dict(color=HIGH_STRONG, dash="dash"), annotation_text="High (90th pct)")
    fig.add_hline(y=low, line=dict(color=LOW_STRONG, dash="dash"), annotation_text="Low (10th pct)")
    fig.update_layout(
        title="Registration trend across the month (2D line)",
        xaxis_title="Day of month",
        yaxis_title="Registrations",
        xaxis=dict(dtick=1, gridcolor=GRID),
        yaxis=dict(gridcolor=GRID),
        showlegend=False,
    )
    return _axis_style(fig)


def heatmap_2d(month_df: pd.DataFrame) -> go.Figure:
    counts, day_numbers = _calendar_grid(month_df)
    text = [[f"Day {int(d)}" if not np.isnan(d) else "" for d in row] for row in day_numbers]
    fig = go.Figure(
        go.Heatmap(
            z=counts,
            x=WEEKDAYS,
            y=[f"Week {i + 1}" for i in range(counts.shape[0])],
            text=text,
            texttemplate="%{text}<br>%{z}",
            colorscale=BLUE_SCALE,
            colorbar=dict(title="Registrations"),
            hovertemplate="%{text}<br>%{z:,} registrations<extra></extra>",
            xgap=3,
            ygap=3,
        )
    )
    fig.update_layout(title="Registration heat map (2D)", yaxis=dict(autorange="reversed"))
    return _axis_style(fig)


def bar_3d(month_df: pd.DataFrame, low: float, high: float) -> go.Figure:
    """Calendar layout (weeks x weekdays) with a 3D column per day, height = registrations."""
    counts, day_numbers = _calendar_grid(month_df)
    xs, ys, zs, i_idx, j_idx, k_idx, face_colors, hover = [], [], [], [], [], [], [], []
    totals = month_df["Total"].to_numpy()
    colors = day_colors(month_df["Total"], low, high)
    faces_per_cube = len(CUBE_TRIANGLES)
    base_vertex = 0
    for position in range(len(month_df)):
        slot = position + month_df.index[0].weekday()
        week, weekday = slot // 7, slot % 7
        height = max(float(totals[position]), 0.05)
        verts = CUBE_VERTS * np.array([0.8, 0.8, height]) + np.array([weekday, week, 0])
        xs.extend(verts[:, 0])
        ys.extend(verts[:, 1])
        zs.extend(verts[:, 2])
        tris = CUBE_TRIANGLES + base_vertex
        i_idx.extend(tris[:, 0])
        j_idx.extend(tris[:, 1])
        k_idx.extend(tris[:, 2])
        face_colors.extend([colors[position]] * faces_per_cube)
        hover.extend([f"Day {month_df.index[position].day}: {int(totals[position]):,}"] * faces_per_cube)
        base_vertex += len(CUBE_VERTS)

    fig = go.Figure(
        go.Mesh3d(
            x=xs,
            y=ys,
            z=zs,
            i=i_idx,
            j=j_idx,
            k=k_idx,
            facecolor=face_colors,
            flatshading=True,
            text=hover,
            hovertemplate="%{text}<extra></extra>",
            lighting=dict(ambient=0.7, diffuse=0.6),
        )
    )
    fig.update_layout(
        title="Registrations per day (3D bar)",
        scene=dict(
            xaxis=dict(title="Weekday", tickvals=list(range(7)), ticktext=WEEKDAYS),
            yaxis=dict(title="Week of month", tickvals=list(range(counts.shape[0]))),
            zaxis=dict(title="Registrations"),
        ),
    )
    return _axis_style(fig)


def surface_3d(month_df: pd.DataFrame) -> go.Figure:
    counts, _ = _calendar_grid(month_df)
    fig = go.Figure(
        go.Surface(
            z=np.nan_to_num(counts, nan=0),
            x=list(range(7)),
            y=list(range(counts.shape[0])),
            colorscale=BLUE_SCALE,
            colorbar=dict(title="Registrations"),
            hovertemplate="Week %{y}, %{x}<br>%{z:,} registrations<extra></extra>",
        )
    )
    fig.update_layout(
        title="Registration surface (3D)",
        scene=dict(
            xaxis=dict(title="Weekday", tickvals=list(range(7)), ticktext=WEEKDAYS),
            yaxis=dict(title="Week of month"),
            zaxis=dict(title="Registrations"),
        ),
    )
    return _axis_style(fig)


def monthly_bar(monthly: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=monthly.index,
            y=monthly["Y"],
            name="Y (registered)",
            marker_color="#2F7DC1",
        )
    )
    fig.add_trace(go.Bar(x=monthly.index, y=monthly["N"], name="N (not registered)", marker_color=SOFT_BLUE))
    fig.update_layout(barmode="group", title="Registrations by month", xaxis_title="Month", yaxis_title="Members")
    return _axis_style(fig)


PLOTLY_JS_URL = "https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"

RADIAL_HTML = """
<div style="font-family:Segoe UI,Arial,sans-serif;color:#1B3A5C;">
  <div id="radial-chart" style="width:100%;height:560px;"></div>
  <div id="radial-panel" style="margin-top:8px;padding:12px 14px;border:1px solid #C9DDF2;
       border-radius:10px;background:#FFFFFF;font-size:14px;">
    <b>Day details:</b> click a segment or a day number on the chart.
  </div>
</div>
<script src="__PLOTLY_JS__"></script>
<script>
const FIG = __FIG__;
const DETAILS = __DETAILS__;
const chart = document.getElementById("radial-chart");
const panel = document.getElementById("radial-panel");

Plotly.newPlot(chart, FIG.data, FIG.layout, {
  responsive: true, displaylogo: false,
  toImageButtonOptions: { format: "png", scale: 2 }
});

function showDay(pos) {
  const d = DETAILS[pos];
  if (!d) return;
  panel.innerHTML =
    "<b>Day " + d.day + " (" + d.date + ")</b><br>" +
    "Total registrations: <b>" + d.total.toLocaleString() + "</b><br>" +
    "Registered (Y): " + d.yes.toLocaleString() + " &nbsp;|&nbsp; Not registered (N): " + d.no.toLocaleString() + "<br>" +
    "Share of the month: " + d.share + "% &nbsp;|&nbsp; Compared with month average: " + d.vs_avg + "%<br>" +
    "Day type: <b style='color:" + d.color + "'>" + d.kind + "</b>";
}

// Plotly.js reports click events only for markers and labels, but hover events for every
// 3D element. So the panel updates on hover over a segment, marker or label, and on click.
// Segment mesh: 8 vertices per day (curve 0). Labels (curve 2) and markers (curve 3): one per day.
function dayFromPoint(p) {
  if (p.curveNumber === 0) return Math.floor(p.pointNumber / __VERTS__);
  if (p.curveNumber === 2 || p.curveNumber === 3) return p.pointNumber;
  return null;
}
function handle(ev) {
  const pos = dayFromPoint(ev.points[0]);
  if (pos !== null) showDay(pos);
}
chart.on("plotly_hover", handle);
chart.on("plotly_click", handle);
</script>
"""


def day_details(month_df: pd.DataFrame, low: float, high: float) -> list[dict]:
    """Per-day values shown in the details panel when a day is clicked."""
    total_month = float(month_df["Total"].sum())
    average = float(month_df["Total"].mean())
    rows = []
    for day, row in month_df.iterrows():
        total = int(row["Total"])
        if total >= high:
            kind, color = "High day (top 10%)", "#E0242F"
        elif total <= low:
            kind, color = "Low day (bottom 10%)", "#FF8C1A"
        else:
            kind, color = "Normal day", "#1F6FB2"
        rows.append(
            {
                "day": int(day.day),
                "date": day.strftime("%Y-%m-%d"),
                "total": total,
                "yes": int(row["Y"]),
                "no": int(row["N"]),
                "share": f"{100 * total / total_month:.2f}",
                "vs_avg": f"{100 * (total - average) / average:+.1f}",
                "kind": kind,
                "color": color,
            }
        )
    return rows


def radial_3d_html(month_df: pd.DataFrame, low: float, high: float, selected_day: int) -> str:
    """Interactive 3D circular chart rendered with Plotly.js.

    Same chart as radial_3d, plus a details panel: clicking a segment or a day number
    shows that day's figures and turns the segment navy.
    """
    fig = radial_3d(month_df, low, high, selected_day)
    return (
        RADIAL_HTML.replace("__PLOTLY_JS__", PLOTLY_JS_URL)
        .replace("__FIG__", fig.to_json())
        .replace("__DETAILS__", json.dumps(day_details(month_df, low, high)))
        .replace("__VERTS__", str(len(CUBE_VERTS)))
    )
