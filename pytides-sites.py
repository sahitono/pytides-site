import base64

import altair as alt
import pandas as pd
import plotly.express as px
import streamlit as st
from pytides2.tide import Tide

st.title("🌊 Pytides Online")
st.markdown("_--brought to you by [sahitono](https://github.com/sahitono)_")
st.markdown(
    """
This website can calculate harmonic constituent using library [pytides2](https://github.com/sahitono/pytides). 
The calculation is based on [P. Schureman in Special Publication 98](https://tidesandcurrents.noaa.gov/publications/SpecialPubNo98.pdf).
The original pytides is written by [Sam Cox](https://github.com/sam-cox/pytides).

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
    st.write("show data table")
    show_data = st.checkbox("show data table")


@st.cache
def load_file():
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
    tide_data["type"] = ["source"] * len(tide_data.index)
    tide_data.sort_values(by="datetime", inplace=True)

    return tide_data


def main():

    tide_data = load_file()

    tide = Tide.decompose(tide_data["water level"], tide_data["datetime"])

    constituents = [c.name for c in tide.model["constituent"]]
    tide_harmonic = pd.DataFrame(tide.model, index=constituents).drop(
        "constituent", axis=1
    )

    interval = 0
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
                "type": ["prediction"] * len(datetime_arr),
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

    csv = tide_harmonic.to_csv(index=False)
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
    main()
