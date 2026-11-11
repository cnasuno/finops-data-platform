
import streamlit as st
import requests

API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="FinOps Dashboard",
    layout="wide"
)

st.title("FinOps Data Platform")
st.write("Financial Transaction Dashboard")

# API Key 입력
api_key = st.sidebar.text_input(
    "API Key",
    type="password"
)

page = st.sidebar.radio(
    "Menu",
    ["Overview", "Transactions", "Data Quality"]
)

st.subheader(page)

if page == "Overview":
    if not api_key:
        st.warning("Please enter your API Key.")
        st.stop()

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/analytics/summary",
            headers={"X-API-Key": api_key},
            timeout=5
        )

        response.raise_for_status()
        data = response.json()

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Total Transactions",
            data["total_transactions"]
        )

        col2.metric(
            "Total Amount",
            f'{data["total_amount"]:, 1_000_000:,.1f}'
        )

        col3.metric(
            "Deposits",
            data["deposit_count"]
        )

        st.metric(
            "Withdrawals",
            data["withdrawal_count"]
        )

        # 거래 유형별 분포 차트
        st.subheader("Transaction Type Distribution")

        chart_data = {
            "Deposit": data["deposit_count"],
            "Withdrawal": data["withdrawal_count"]
        }

        st.bar_chart(chart_data)

    except requests.exceptions.HTTPError:
        st.error(
            f"API request failed: HTTP {response.status_code}"
        )

    except requests.exceptions.RequestException:
        st.error("Cannot connect to FastAPI server.")



if page == "Transactions":

    if not api_key:
        st.warning("Please enter your API Key.")
        st.stop()

    st.subheader("Transaction Filters")

    col1, col2 = st.columns(2)

    with col1:
        transaction_type = st.selectbox(
            "Transaction Type",
            ["ALL", "DEPOSIT", "WITHDRAWAL"]
        )

    with col2:
        page_number = st.number_input(
            "Page",
            min_value=1,
            value=1,
            step=1
        )

    col3, col4 = st.columns(2)

    with col3:
        start_date = st.date_input(
            "Start Date",
            value=None
        )

    with col4:
        end_date = st.date_input(
            "End Date",
            value=None
        )


    params = {
        "page": int(page_number),
        "size": 20
    }

    if transaction_type != "ALL":
        params["transaction_type"] = transaction_type

    if start_date:
        params["start_date"] = start_date.isoformat()

    if end_date:
        params["end_date"] = end_date.isoformat()

    if start_date and end_date and start_date > end_date:
        st.error("Start Date must be before End Date.")
        st.stop()


    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/transactions",
            headers={"X-API-Key": api_key},
            params=params,
            timeout=5
        )

        response.raise_for_status()
        data = response.json()

        st.dataframe(
            data["transactions"],
            use_container_width=True
        )

        st.caption(
            f"Page {data['page']} | "
            f"Records per page: {data['size']}"
        )

    except requests.exceptions.HTTPError:
        st.error(
            f"API request failed: HTTP {response.status_code}"
        )

    except requests.exceptions.RequestException:
        st.error("Cannot connect to FastAPI server.")



if page == "Data Quality":

    if not api_key:
        st.warning("Please enter your API Key.")
        st.stop()

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/data-quality/summary",
            headers={"X-API-Key": api_key},
            timeout=5
        )

        response.raise_for_status()
        data = response.json()

        # 데이터 품질 지표
        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Rejected Records",
            data["total_rejected"]
        )

        col2.metric(
            "Pipeline Runs",
            data["total_runs"]
        )

        col3.metric(
            "Duplicates Detected",
            data["duplicate_count"]
        )

        # 파이프라인 실행 결과
        st.subheader("Pipeline Execution Status")

        col4, col5 = st.columns(2)

        col4.metric(
            "Successful Runs",
            data["successful_runs"]
        )

        col5.metric(
            "Failed Runs",
            data["failed_runs"]
        )

        chart_data = {
            "Success": data["successful_runs"],
            "Failed": data["failed_runs"]
        }

        st.bar_chart(chart_data)


        # Admin 전용 파이프라인 실행 이력
        st.subheader("Recent Pipeline Runs")

        runs_response = requests.get(
            f"{API_BASE_URL}/api/v1/pipeline/runs",
            headers={"X-API-Key": api_key},
            timeout=5
        )

        if runs_response.status_code == 200:
            runs_data = runs_response.json()

            st.dataframe(
                runs_data["runs"],
                use_container_width=True
            )

        elif runs_response.status_code == 403:
            st.info(
                "Pipeline execution history requires Admin permission."
            )

        else:
            runs_response.raise_for_status()


    except requests.exceptions.HTTPError:
        st.error(
            f"API request failed: HTTP {response.status_code}"
        )

    except requests.exceptions.RequestException:
        st.error("Cannot connect to FastAPI server.")
