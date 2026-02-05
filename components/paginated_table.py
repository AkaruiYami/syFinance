import streamlit as st
import pandas as pd


def paginated_table(data, page_size=25, to_display=None, table_id=None):
    data = pd.DataFrame(data)
    page_session_id = f"page_number_{table_id}"

    # --- Pagination Setup ---
    total_records = len(data)
    total_pages = (total_records - 1) // page_size + 1

    # Store current page in session_state so it persists between reruns
    if page_session_id not in st.session_state:
        st.session_state[page_session_id] = 1

    # Pagination controls (centered)
    col_prev, col_next = st.columns(2)
    with col_prev:
        if (
            st.button("⬅️ Previous", width="stretch", key=f"{table_id}_prev")
            and st.session_state[page_session_id] > 1
        ):
            st.session_state[page_session_id] -= 1
    with col_next:
        if (
            st.button("Next ➡️", width="stretch", key=f"{table_id}_next")
            and st.session_state[page_session_id] < total_pages
        ):
            st.session_state[page_session_id] += 1

    # --- Paginate Data ---
    start_idx = (st.session_state[page_session_id] - 1) * page_size
    end_idx = start_idx + page_size
    paginated_df = data.iloc[start_idx:end_idx]

    # --- Display Table ---
    if to_display is None:
        st.table(paginated_df)
    else:
        st.table(paginated_df[to_display])

    # --- Displat Pagination ---
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.html(
            f"<p style='text-align: center;'>{st.session_state[page_session_id]} of {total_pages}</p>"
        )
