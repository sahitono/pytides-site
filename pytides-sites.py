import base64
from typing import Any, Dict, List, Tuple

import matplotlib.dates as mdates
import pandas as pd
import plotly.express as px
import streamlit as st
import utide
from pytides2.tide import Tide

st.set_page_config(layout="wide")
st.title("🌊 Pytides Online")

st.markdown("_--brought to you by [sahitono](https://github.com/sahitono)_")
st.markdown(
    """
This website can calculate harmonic constituent using:
- [pytides2](https://github.com/sahitono/pytides). The calculation is based on [P. Schureman in Special Publication 98](https://tidesandcurrents.noaa.gov/publications/SpecialPubNo98.pdf). The original pytides is written by [Sam Cox](https://github.com/sam-cox/pytides).
- [utide](https://github.com/wesleybowman/UTide). Originally made by [Codiga, D.L](http://www.po.gso.uri.edu/~codiga/utide/utide.htm) in matlab.

Notes:
- The data should be something like this:
    ```csv
    datetime,water level
    2020-11-1T00:00:00Z,228
    2020-11-1T01:00:00Z,177
    ```
    datetime should follow [ISO 8601 format](https://www.w3.org/TR/NOTE-datetime) in the form of `yyyy-mm-ddThh:mm:ssTZD`
- 👈 There is a left sidebar which you can use to show csv and predict tide.
- The chart can be viewed in fullscreen. Find a fullscreen icon on the right-upper side of the chart.
- Try to click the legend name in the chart, it will show the selected line only. Ah, it is interactive too.

Have a nice day, stay healthy & dont forget to wear your mask 😄 

---
""",
    unsafe_allow_html=True,
)
uploaded_file: str = st.file_uploader("Choose your .csv file", type=["csv", "txt"])


with st.sidebar:
    tide_backend: str = st.sidebar.selectbox(
        "Choose tides calculation method", ("utide", "pytides")
    )
    show_data: bool = st.checkbox("show datasource table")
    if tide_backend == "utide":
        lat: float = st.sidebar.number_input("latitude", -10.0, step=0.1)
        conf_int: str = st.sidebar.selectbox(
            "Confidence interval", ("linear", "MC", "none")
        )
        # phase: str = st.sidebar.selectbox(
        #     "Phase lags", ("Greenwich", "linear_time", "raw")
        # )
        nodal: bool = st.checkbox("include nodal/satellite corrections")
        trend: bool = st.checkbox("include a linear trend in the model")
        method: str = st.sidebar.selectbox("Choose method", ("ols", "robust"))


@st.cache
def load_file() -> pd.DataFrame:
    tide_data: "pd.DataFrame" = pd.read_csv(
        uploaded_file,
    )

    if tuple(tide_data.columns) != ("datetime", "water level"):
        raise ValueError(
            f"""
        Column name should be 'datetime' and 'water level'.\b
        Your column is f{tuple(tide_data.columns)}"""
        )

    tide_data["datetime"] = pd.to_datetime(tide_data["datetime"], yearfirst=True)
    # tide_data["datetime"] = pd.to_datetime(tide_data["datetime"], dayfirst=True)
    tide_data["type"] = ["source"] * len(tide_data.index)
    tide_data.sort_values(by="datetime", inplace=True)

    return tide_data


def solve_pytides(data: pd.DataFrame) -> Tuple["Tide", pd.DataFrame]:
    tide = Tide.decompose(data["water level"], data["datetime"])
    if not isinstance(tide, Tide):
        raise ValueError(f"{tide} is not a valid tide.")

    constituents: List[str] = [c.name for c in tide.model["constituent"]]
    tide_harmonic = pd.DataFrame(tide.model, index=constituents).drop(
        "constituent", axis=1
    )

    return tide, tide_harmonic


def solve_utide(data: pd.DataFrame) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    time = mdates.date2num(data.datetime)
    coef = utide.solve(
        time, data["water level"].to_numpy(), lat=-25, method="ols", conf_int="MC"
    )
    tide = utide.reconstruct(time, coef)
    return tide, coef


def main_utide(tide_data: pd.DataFrame) -> None:
    tide, coef = solve_utide(tide_data)
    tide_harmonic = pd.DataFrame(
        {
            "name": ["mean"] + list(coef["name"]),
            "amplitude": [coef["mean"]] + list(coef["A"]),
            "phase": [0] + list(coef["g"]),
        }
    )

    start_date: pd.Timestamp = tide_data.datetime.array[0]
    end_date: pd.Timestamp = tide_data.datetime.array[-1]
    interval: int = 3600

    with st.sidebar:
        st.write("show prediction")
        show_prediction = st.checkbox("show prediction", True)
        if show_prediction:
            start_date = st.date_input("start date", tide_data.datetime.array[0])
            end_date = st.date_input("end date", tide_data.datetime.array[-1])
            interval = st.number_input("interval (seconds)", 3600, step=3600)

    if show_prediction and interval >= 3600:
        datetime_arr = pd.date_range(start_date, end_date, freq=f"{interval}S").array
        df_predicted = pd.DataFrame(
            {
                "datetime": datetime_arr,
                "water level": utide.reconstruct(mdates.date2num(datetime_arr), coef).h,
                "type": ["prediction"] * datetime_arr.size,
            }
        )
        tide_data = tide_data.append(df_predicted)

    ## Visualizing
    if show_data:
        st.write("data source")
        st.write(tide_data)

    fig = px.line(
        tide_data, x="datetime", y="water level", color="type", render_mode="webgl"
    )
    fig.update_layout(dragmode="pan")
    st.plotly_chart(fig, config=dict({"scrollZoom": True}), use_container_width=True)

    csv: str = tide_harmonic.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    st.markdown(
        f"""
    Harmonic constituent table. 
    Download it <a href="data:file/csv;base64,{b64}">here</a>
    """,
        unsafe_allow_html=True,
    )
    st.write(tide_harmonic)


def main_pytide(tide_data: pd.DataFrame) -> None:
    tide, tide_harmonic = solve_pytides(tide_data)

    start_date: pd.Timestamp = tide_data.datetime.array[0]
    end_date: pd.Timestamp = tide_data.datetime.array[-1]
    interval: int = 3600

    with st.sidebar:
        st.write("show prediction")
        show_prediction = st.checkbox("show prediction", True)
        if show_prediction:
            start_date = st.date_input("start date", tide_data.datetime.array[0])
            end_date = st.date_input("end date", tide_data.datetime.array[-1])
            interval = st.number_input("interval (seconds)", 3600, step=3600)
    tide_harmonic.sort_values("amplitude", ascending=False).head(10)

    if show_prediction and interval >= 3600:
        datetime_arr = pd.date_range(start_date, end_date, freq=f"{interval}S").array
        df_predicted = pd.DataFrame(
            {
                "datetime": datetime_arr,
                "water level": tide.at(datetime_arr),
                "type": ["prediction"] * datetime_arr.size,
            }
        )
        tide_data = tide_data.append(df_predicted)

    ## Visualizing
    if show_data:
        st.write("data source")
        st.write(tide_data)

    fig = px.line(
        tide_data, x="datetime", y="water level", color="type", render_mode="webgl"
    )
    fig.update_layout(dragmode="pan")
    st.plotly_chart(fig, config=dict({"scrollZoom": True}), use_container_width=True)

    csv: str = tide_harmonic.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    st.markdown(
        f"""
    Harmonic constituent table. 
    Download it <a href="data:file/csv;base64,{b64}">here</a>
    """,
        unsafe_allow_html=True,
    )
    st.write(tide_harmonic)


def main() -> None:

    tide_data = load_file()

    # tide = Tide.decompose(tide_data["water level"], tide_data["datetime"])
    # if not isinstance(tide, Tide):
    #     raise ValueError(f"{tide} is not a valid tide.")

    # constituents: List[str] = [c.name for c in tide.model["constituent"]]
    # tide_harmonic = pd.DataFrame(tide.model, index=constituents).drop(
    #     "constituent", axis=1
    # )

    if tide_backend == "utide":
        tide, coef = solve_utide(tide_data)
    else:
        tide, coef = solve_pytides(tide_data)

    start_date: pd.Timestamp = tide_data.datetime.array[0]
    end_date: pd.Timestamp = tide_data.datetime.array[-1]
    interval: int = 3600

    with st.sidebar:
        st.write("show prediction")
        show_prediction = st.checkbox("show prediction", True)
        if show_prediction:
            start_date = st.date_input("start date", tide_data.datetime.array[0])
            end_date = st.date_input("end date", tide_data.datetime.array[-1])
            interval = st.number_input("interval (seconds)", 3600, step=3600)
    coef.sort_values("amplitude", ascending=False).head(10)

    if show_prediction and interval >= 3600:
        datetime_arr = pd.date_range(start_date, end_date, freq=f"{interval}S").array
        df_predicted = pd.DataFrame(
            {
                "datetime": datetime_arr,
                "water level": tide.at(datetime_arr),
                "type": ["prediction"] * datetime_arr.size,
            }
        )
        tide_data = tide_data.append(df_predicted)

    ## Visualizing
    if show_data:
        st.write("data source")
        st.write(tide_data)

    fig = px.line(
        tide_data, x="datetime", y="water level", color="type", render_mode="webgl"
    )
    fig.update_layout(dragmode="pan")
    st.plotly_chart(fig, config=dict({"scrollZoom": True}), use_container_width=True)

    csv: str = tide_harmonic.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    st.markdown(
        f"""
    Harmonic constituent table. 
    Download it <a href="data:file/csv;base64,{b64}">here</a>
    """,
        unsafe_allow_html=True,
    )
    st.write(tide_harmonic)


if uploaded_file is not None:
    tide_data = load_file()
    if tide_backend == "utide":
        main_utide(tide_data)
    else:
        main_pytide(tide_data)
    # main()
