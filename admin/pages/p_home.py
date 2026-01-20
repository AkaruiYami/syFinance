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
    users = api.get_users()
    n_user = len(users)
    st.metric("Number of User", n_user)
    st.metric("Admin ID", users[0].id)
