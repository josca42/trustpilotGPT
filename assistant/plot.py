import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly
from datetime import timedelta
import ast
import pandas as pd
from assistant.db import crud
from assistant import analyse
from assistant.config import (
    LABEL_COLORS,
    LABELS,
    COLORS,
)


def create(metadata: dict, plots: list[str]) -> str:
    companies = metadata["companies"]
    _in = dict(company=companies, category=metadata["categories"])
    df = crud.review.where(
        _in=_in,
        cols=["company", "timestamp", "rating", "category"],
        start_date=metadata["start_date"],
        end_date=metadata["end_date"],
    )
    if df.empty:
        return "No data available"

    plots_fig = []
    for plot in plots:
        if plot == "ratings time series for single company":
            fig_data = ratings_time_series(df)
        elif plot == "ratings piecharts by review category for single company":
            fig_data = ratings_pie_chart_category(df)
        elif plot == "ratings piechart for single company":
            fig_data = ratings_pie_chart_total(df)
        elif plot == "ratings and review count time series comparing companies":
            fig_data = timeseries_compare(df, companies=companies)
        elif plot == "ratings distribution comparing companies":
            fig_data = bar_plot_compare(df, companies=companies)
        else:
            raise ValueError(f"Unknown plot type: {plot_type}")

        plots_fig.append(fig_data)
    return plots_fig


def ratings_pie_chart_total(df):
    ratings = df["rating"].value_counts().sort_index()
    fig = go.Figure(layout=dict(margin=dict(t=0, b=0, l=0, r=0)))
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

    # Create dataframe used to describe plot
    ratings = ratings.reset_index()
    ratings["percentage"] = (ratings["count"] / ratings["count"].sum() * 100).round(1)
    plot_descr = "the distribution of review ratings."
    return dict(fig=fig, data=ratings.reset_index(), descr=plot_descr)


def ratings_pie_chart_category(df):
    N = len(LABELS)
    dfs = []
    fig = make_subplots(rows=1, cols=N, specs=[[{"type": "domain"}] * N])
    for i, (label, label_val) in enumerate(LABELS):
        ratings = df[df["category"] == label_val]["rating"].value_counts().sort_index()
        colors = [COLORS[int(rating) - 1] for rating in ratings.index]
        pie_chart = go.Pie(
            values=ratings.values,
            name=label,
            text=[label_val] * N,
            title=f"{label}<br> {ratings.sum()}",
            textinfo="percent",
            sort=False,
            marker=dict(colors=colors),
        )
        fig.add_trace(
            pie_chart,
            1,
            i + 1,
        )

        # Add ratings row to dataframe used for interpreting plot
        ratings = ratings.to_frame().T
        ratings.index = [label]
        dfs.append(ratings)

    dfs = pd.concat(dfs).fillna(0).reset_index().rename(columns={"index": "category"})
    dfs = dfs.rename(
        columns={c: f"# reviews {c} stars" for c in dfs.columns if c in list(range(6))}
    )
    plot_descr = "the distribution of review ratings for each review category."

    fig = fig.update_traces(
        hole=0.6,
        hoverinfo="percent+value+name",
    )
    fig = fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
    return dict(fig=fig, data=dfs, descr=plot_descr)


def ratings_time_series(df):
    start_date, end_date = df["timestamp"].min(), df["timestamp"].max()
    df = df.set_index("timestamp")

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

    # Create dataframe used to describe plot
    ratings = ratings.abs()
    star_cols = [c for c in ratings.columns if c in list(range(6))]
    ratings[star_cols] = (
        ratings[star_cols] / ratings[star_cols].sum(axis=1).values.reshape(-1, 1) * 100
    ).round(2)
    ratings = (
        ratings.reset_index()
        .rename(columns={"rating": "mean rating"})
        .rename(columns={i: f"# reviews {i} stars" for i in star_cols})
    )
    # Plot description
    plot_descr = "the average review rating and the number of reviews with 0 stars, 1 stars, 2 stars ..., 5 stars for different time periods. Each row corresponds to the review ratings for a time period."

    return dict(fig=fig, data=ratings, descr=plot_descr)


def timeseries_compare(df, companies):
    start_date, end_date = df["timestamp"].min(), df["timestamp"].max()
    df = df.set_index("timestamp")
    if df.empty:
        return go.Figure()

    colors = plotly.colors.qualitative.T10
    COLORS = LABEL_COLORS
    freq = set_time_frequence(start_date, end_date)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)
    # Add mean and count time series plots
    data = {}
    i = 0
    for company in companies:
        df_t = df.loc[df["company"] == company, "rating"]
        df_t = df_t.resample(freq).agg(["mean", "count"]).fillna(0)
        fig.add_trace(
            go.Scatter(
                x=df_t.index,
                y=df_t["mean"].round(2),
                name=company,
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
                name=company,
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
        data[company] = df_t.reset_index().round(1)

    fig.update_layout(
        margin=dict(t=0, b=0, l=0, r=0),
        template="simple_white",
        legend=dict(
            x=1.15,
            xanchor="right",
        ),
        hovermode="x unified",
        # legend_tracegroupgap=260,
    )
    fig.update_yaxes(range=[1, 5], row=1, col=1)
    fig.update_yaxes(title_text="☆ rating", row=1, col=1)
    fig.update_yaxes(title_text="# reviews", row=2, col=1)

    if freq == "M":
        fig = fig.update_xaxes(title_text="Måned", row=3, col=1)
    elif freq == "W":
        fig = fig.update_xaxes(title_text="Uge", row=3, col=1)
    elif freq == "D":
        fig = fig.update_xaxes(title_text="Dag", row=3, col=1)
    else:
        pass
    plot_descr = "the average review rating and the number of reviews for different time periods. Each row corresponds to the review ratings for a time period."
    return dict(fig=fig, data=data, descr=plot_descr)


def bar_plot_compare(df_r, companies):
    GRAPH_LAYOUT = dict(
        margin=dict(t=0, b=0, l=0, r=0), xaxis=dict(zeroline=True, showgrid=True)
    )

    fig = go.Figure(layout=GRAPH_LAYOUT)
    fig = fig.update_layout(
        template="simple_white",
        xaxis=dict(title_text="%"),
        yaxis=dict(title_text="Firma"),
        barmode="relative",
        showlegend=False,
    )

    colors = ["#ee6055", "#ff9b85", "#ffd97d", "#aaf683", "#60d394"]
    rating_labels = ["1", "2", "3", "4", "5"]
    for company in companies:
        df_t = (
            df_r.loc[df_r["company"] == company, "rating"]
            .value_counts()
            .reset_index()
            .assign(pct=lambda df: df["count"] / df["count"].sum())
        )
        agg_stats = df_r.loc[df_r["company"] == company, "rating"].agg(
            ["mean", "count"]
        )
        x_axis_name = f"{company} <br> ☆{agg_stats['mean'].round(2)} <br> #{int(agg_stats['count'])}"
        for rating_label, color in zip(rating_labels, colors):
            rating = int(rating_label)
            df_rating = df_t[df_t["rating"] == rating].copy()

            if df_rating.empty:
                continue

            fig.add_trace(
                go.Bar(
                    x=df_rating["pct"],
                    y=[company, [x_axis_name]],
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

    # Create dataframe used to describe plot
    df = (
        df_r.drop("category", axis=1)
        .groupby("company")["rating"]
        .value_counts()
        .unstack(1)
        .fillna(0)
    )
    star_cols = [c for c in df.columns if c in list(range(6))]
    df[star_cols] = (df[star_cols] / df.sum(axis=1).values.reshape(-1, 1) * 100).round(
        1
    )
    df = df.reset_index().rename(columns={c: f"% {c} stars reviews" for c in star_cols})
    plot_descr = "the distribution of review ratings for each company."

    return dict(fig=fig, data=df, descr=plot_descr)


def set_time_frequence(start_date, end_date):
    time_interval = end_date - start_date
    if time_interval < timedelta(days=45):
        time_freq = "D"
    elif time_interval < timedelta(days=30 * 5):
        time_freq = "W"
    else:
        time_freq = "M"
    return time_freq
