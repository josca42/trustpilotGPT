import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly
from datetime import timedelta
from .CONSTANTS import (
    APP_REVIEW_LABELS,
    APP_LABEL_COLORS,
    BANK_LABEL_COLORS,
    BANK_REVIEW_LABELS,
    COLORS,
)


def create_plot():
    ...


def ratings_pie_chart_total(df):
    ratings = df["rating"].value_counts().sort_index()
    fig = go.Figure()
    fig.add_trace(
        go.Pie(
            values=ratings.values,
            name="Total",
            title=f"Total<br> {ratings.sum()}",
            textinfo="percent",
            sort=False,
        )
    )
    colors = [COLORS[int(rating) - 1] for rating in ratings.index]
    fig = fig.update_traces(
        hole=0.6,
        hoverinfo="percent+value+name",
        marker=dict(colors=colors),
    )
    fig = fig.update_layout(showlegend=False)
    return fig


def ratings_pie_chart_category(df, review_type, categories):
    LABELS = APP_REVIEW_LABELS if review_type == "App anm." else BANK_REVIEW_LABELS
    N = len(LABELS)
    categories = categories if categories else list(range(N))
    fig = make_subplots(rows=1, cols=N, specs=[[{"type": "domain"}] * N])
    for i, (label, label_val) in enumerate(LABELS):
        ratings = df[df["label"] == label_val]["rating"].value_counts().sort_index()
        colors = [COLORS[int(rating) - 1] for rating in ratings.index]
        pie_chart = go.Pie(
            values=ratings.values,
            name=label,
            text=[label_val] * N,
            title=f"{label}<br> {ratings.sum()}",
            textinfo="percent",
            sort=False,
            marker=dict(colors=colors),
            opacity=0.5 if label_val not in categories else 1.0,
        )
        fig.add_trace(
            pie_chart,
            1,
            i + 1,
        )

    fig = fig.update_traces(
        hole=0.6,
        hoverinfo="percent+value+name",
        # marker=dict(colors=COLORS),
    )
    fig = fig.update_layout(showlegend=False)
    return fig


def ratings_time_series(df, start_date, end_date):
    GRAPH_LAYOUT = dict(
        margin=dict(t=0, b=0, l=0, r=0),
        xaxis=dict(rangeslider=dict(visible=False)),
        yaxis=dict(zeroline=True, showgrid=True),
        yaxis2=dict(
            title_text="Gnm. rating",
            overlaying="y",
            side="right",
            zeroline=False,
            range=[1, 5],
        ),
    )

    fig = go.Figure(layout=GRAPH_LAYOUT)
    fig = fig.update_layout(
        template="simple_white",
        xaxis=dict(title_text="Måned"),
        yaxis=dict(title_text="Antal"),
        barmode="relative",
        showlegend=False,
    )
    colors = ["#ff9b85", "#ee6055", "#ffd97d", "#aaf683", "#60d394"]
    rating_labels = ["2", "1", "3", "4", "5"]

    time_freq = set_time_frequence(start_date, end_date)
    ratings_counts = (
        df.resample(time_freq)["rating"].value_counts().unstack("rating").fillna(0)
    )
    ratings_mean = df.resample(time_freq)["rating"].mean()
    ratings = ratings_mean.to_frame().join(ratings_counts, how="left").fillna(0)
    for rating_label, color in zip(rating_labels, colors):
        rating = int(rating_label)
        if rating in ratings.columns:
            if rating <= 2:
                ratings[rating] *= -1
            fig.add_trace(
                go.Bar(
                    x=ratings.index,
                    y=ratings[rating],
                    name=rating_label,
                    marker_color=color,
                ),
            )

    fig.add_trace(
        go.Scatter(
            x=ratings.index,
            y=ratings["rating"],
            name="Gnm. rating",
            marker_color="black",
            yaxis="y2",
        ),
    )

    if time_freq == "W":
        fig = fig.update_layout(xaxis=dict(title_text="Uge"))
    elif time_freq == "D":
        fig = fig.update_layout(xaxis=dict(title_text="Dag"))
    else:
        pass
    return fig


def cross_section_compare(df_h):
    df_p = df_h.reset_index()
    fig = go.Figure(
        go.Icicle(
            labels=df_p["entity"],
            parents=df_p["parent"],
            text=df_p["name"],
            values=df_p["log_count_int"],
            customdata=df_p[["mean", "count", "id"]],
            branchvalues="total",
            maxdepth=5,
            marker_colors=df_p["color"],
            texttemplate=(
                "%{text} <br>" "☆ %{customdata[0]:.1f}<br>" "# %{customdata[1]}<br>"
            ),
            hovertemplate=(
                "<b>%{text} </b> <br>"
                "Gnm. rating: %{customdata[0]:.1f}<br>"
                "Antal anmeldelser: %{customdata[1]:.1f}<br>"
                "<extra></extra>"
            ),
        )
    )
    fig = fig.update_layout(margin=dict(t=20, b=0, l=0, r=0))
    return fig


def timeseries_compare(df_r, lookups_plot, start_date, end_date, review_type):
    if df_r.empty:
        return go.Figure()

    colors = plotly.colors.qualitative.T10
    LABELS = APP_REVIEW_LABELS if review_type == "App anm." else BANK_REVIEW_LABELS
    COLORS = APP_LABEL_COLORS if review_type == "App anm." else BANK_LABEL_COLORS
    freq = set_time_frequence(start_date, end_date)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True)
    # Add mean and count time series plots
    i = 0
    for col, values in lookups_plot:
        for value in values:
            if value == "total":
                df_t = df_r["rating"]
            else:
                df_t = df_r.loc[df_r[col] == value, "rating"]
            df_t = df_t.resample(freq).agg(["mean", "count"]).fillna(0)
            fig.add_trace(
                go.Scatter(
                    x=df_t.index,
                    y=df_t["mean"].round(2),
                    name=value,
                    mode="lines",
                    marker=dict(color=colors[i]),
                    # stackgroup="one",
                    legendgroup="module",
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df_t.index,
                    y=df_t["count"],
                    name=value,
                    mode="lines",
                    # stackgroup="one",
                    marker=dict(color=colors[i]),
                    legendgroup="module",
                    showlegend=False,
                ),
                row=2,
                col=1,
            )
            i += 1

    # Add error type time series plot
    total = df_r[df_r["label"].notna()]["label"].resample(freq).count()
    for i, (label, label_val) in enumerate(LABELS):
        df_t = df_r.loc[df_r["label"] == label_val, "rating"]
        df_t = (df_t.resample(freq).count() / total * 100).fillna(0)
        fig.add_trace(
            go.Scatter(
                x=df_t.index,
                y=df_t.round(1),
                name=label,
                line=dict(color=COLORS[i]),
                stackgroup="one",
                showlegend=False,
            ),
            row=3,
            col=1,
        )
    fig.update_yaxes(title_text="% kategori", row=3, col=1)

    fig.update_layout(
        margin=dict(t=0, b=0, l=0, r=0),
        template="simple_white",
        legend=dict(
            x=1.15,
            xanchor="right",
        ),
        hovermode="x unified"
        # legend_tracegroupgap=260,
    )
    fig.update_yaxes(range=[1, 5], row=1, col=1)
    fig.update_yaxes(title_text="☆ rating", row=1, col=1)
    fig.update_yaxes(title_text="# anmeldelser", row=2, col=1)

    if freq == "M":
        fig = fig.update_xaxes(title_text="Måned", row=3, col=1)
    elif freq == "W":
        fig = fig.update_xaxes(title_text="Uge", row=3, col=1)
    elif freq == "D":
        fig = fig.update_xaxes(title_text="Dag", row=3, col=1)
    else:
        pass

    return fig


def bar_plot_compare(df_r, lookups_plot):
    GRAPH_LAYOUT = dict(
        margin=dict(t=0, b=0, l=0, r=0), xaxis=dict(zeroline=True, showgrid=True)
    )

    fig = go.Figure(layout=GRAPH_LAYOUT)
    fig = fig.update_layout(
        template="simple_white",
        xaxis=dict(title_text="%"),
        yaxis=dict(title_text="Bank"),
        barmode="relative",
        showlegend=False,
    )

    colors = ["#ee6055", "#ff9b85", "#ffd97d", "#aaf683", "#60d394"]
    rating_labels = ["1", "2", "3", "4", "5"]
    for col, values in lookups_plot:
        for value in values:
            df_t = (
                df_r.loc[df_r[col] == value, "rating"]
                .value_counts()
                .reset_index()
                .rename(columns={"index": "rating", "rating": "count"})
                .assign(pct=lambda df: df["count"] / df["count"].sum())
            )
            agg_stats = df_r.loc[df_r[col] == value, "rating"].agg(["mean", "count"])
            x_axis_name = f"{value} <br> ☆{agg_stats['mean'].round(2)} <br> #{int(agg_stats['count'])}"
            for rating_label, color in zip(rating_labels, colors):
                rating = int(rating_label)
                df_rating = df_t[df_t["rating"] == rating].copy()

                if df_rating.empty:
                    continue

                fig.add_trace(
                    go.Bar(
                        x=df_rating["pct"],
                        y=[[col.split("_")[-1]], [x_axis_name]],
                        name=rating_label,
                        marker_color=color,
                        orientation="h",
                        text="% "
                        + df_rating["pct"].pipe(lambda s: s * 100).round(1).astype(str)
                        + "<br>"
                        + "# "
                        + df_rating["count"].astype(str),
                    ),
                )
    return


def set_time_frequence(start_date, end_date):
    time_interval = end_date - start_date
    if time_interval < timedelta(days=45):
        time_freq = "D"
    elif time_interval < timedelta(days=30 * 5):
        time_freq = "W"
    else:
        time_freq = "M"
    return time_freq
