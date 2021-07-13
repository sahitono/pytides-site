from datetime import datetime
from typing import List

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from pytides2.tide import Tide

st.title("Calculate tidal constittuent using pytides2")
uploaded_file = st.file_uploader("Choose your .csv file", type=["csv", "txt"])
print(uploaded_file)


with st.sidebar:
    st.write("show data table")
    show_data = st.checkbox("show data table")


def load_file():
    tide_data: "pd.DataFrame" = pd.read_csv(
        uploaded_file,
    )

    if tuple(tide_data.columns) != ("datetime", "water level"):
        raise ValueError("Column name should be 'datetime' and 'water level'")

    tide_data["datetime"] = pd.to_datetime(tide_data["datetime"], dayfirst=True)
    return tide_data


def main():

    tide_data = load_file()

    tide_data["type"] = ["source"] * len(tide_data.index)
    tide_data.sort_values(by="datetime", inplace=True)

    tide = Tide.decompose(tide_data["water level"], tide_data["datetime"])

    constituents = [c.name for c in tide.model["constituent"]]
    tide_harmonic = pd.DataFrame(tide.model, index=constituents).drop(
        "constituent", axis=1
    )

    with st.sidebar:
        st.write("show prediction")
        show_prediction = st.checkbox("show prediction", True)
        if show_prediction:
            start_date = st.date_input("start date", tide_data.datetime.array[0])
            end_date = st.date_input("end date", tide_data.datetime.array[-1])
            interval = st.number_input("interval (seconds)", 3600)

            st.write(start_date, end_date)

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

    selection = alt.selection_multi(fields=["type"], bind="legend")
    chart = (
        alt.Chart(tide_data)
        .mark_line()
        .encode(
            x="datetime",
            y="water level",
            color="type",
            opacity=alt.condition(selection, alt.value(1), alt.value(0.2)),
        )
        .add_selection(selection)
        .interactive()
    )

    ## Visualizing
    if show_data:
        st.write("data source")
        st.write(tide_data)

    st.write(tide_harmonic)

    st.altair_chart(chart, use_container_width=True)


if uploaded_file is not None:
    main()
