from datetime import datetime
import streamlit as st
import pandas as pd
import altair as alt

from admin import api
from utils import config
from models.income import Income
from models.transaction import Transactions


from utils.auth import require_login

require_login()

st.set_page_config(page_title=config.APP_NAME, layout="wide")

st.title(config.APP_NAME)
st.markdown("Under construction")
st.divider()


with st.container():
    st.button("Create User")


with st.container():
    users = api.get_users()
    n_user = len(users)
    st.metric("Number of User", n_user)

    data = {}
    data["User ID"] = [user.id for user in users]
    data["Name"] = [user.name for user in users]
    df = pd.DataFrame(data)

    df2 = df.copy()
    df2.insert(0, "Select", False)

    edited = st.data_editor(
        df2,
        disabled=["User ID", "Name"],  # keep columns read-only except Select
        hide_index=True,
    )

    selected_ids = edited.index[edited["Select"]].tolist()

    if selected_ids:
        st.dataframe(
            df.loc[selected_ids],
            hide_index=True,
        )
