import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# ===============================
# 기본 설정
# ===============================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

# 한글 폰트 (UI)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

PLOTLY_FONT = dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")

DATA_DIR = Path("data")

SCHOOL_EC = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

SCHOOL_COLOR = {
    "송도고": "#4C72B0",
    "하늘고": "#55A868",
    "아라고": "#C44E52",
    "동산고": "#8172B2"
}

# ===============================
# 파일 유틸 (NFC/NFD 안전)
# ===============================
def normalize(text):
    return unicodedata.normalize("NFC", text)

def find_file_by_normalized_name(directory: Path, target_name: str):
    target_norm = normalize(target_name)
    for p in directory.iterdir():
        if normalize(p.name) == target_norm:
            return p
    return None

# ===============================
# 데이터 로딩
# ===============================
@st.cache_data
def load_environment_data():
    data = {}
    for school in SCHOOL_EC.keys():
        filename = f"{school}_환경데이터.csv"
        file_path = find_file_by_normalized_name(DATA_DIR, filename)
        if file_path is None:
            st.error(f"❌ 환경 데이터 파일을 찾을 수 없습니다: {filename}")
            continue
        df = pd.read_csv(file_path)
        df["school"] = school
        data[school] = df
    return data

@st.cache_data
def load_growth_data():
    xlsx_path = find_file_by_normalized_name(DATA_DIR, "4개교_생육결과데이터.xlsx")
    if xlsx_path is None:
        st.error("❌ 생육 결과 XLSX 파일을 찾을 수 없습니다.")
        return {}

    xls = pd.ExcelFile(xlsx_path)
    data = {}
    for sheet in xls.sheet_names:
        df = pd.read_excel(xlsx_path, sheet_name=sheet)
        df["school"] = sheet
        data[sheet] = df
    return data

with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if not env_data or not growth_data:
    st.stop()

# ===============================
# 사이드바
# ===============================
st.sidebar.title("학교 선택")
selected_school = st.sidebar.selectbox(
    "학교",
    ["전체"] + list(SCHOOL_EC.keys())
)

# ===============================
# 제목
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ===============================
# TAB 1 : 실험 개요
# ===============================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.markdown(
        """
        극지 환경에서의 식물 생육 최적화를 위해  
        **EC 농도 조건별 생육 결과와 환경 요인**을 비교 분석하였다.
        """
    )

    overview_rows = []
    total_count = 0
    for school, ec in SCHOOL_EC.items():
        count = len(growth_data.get(school, []))
        total_count += count
        overview_rows.append({
            "학교명": school,
            "EC 목표": ec,
            "개체수": count,
            "색상": SCHOOL_COLOR[school]
        })

    overview_df = pd.DataFrame(overview_rows)
    st.dataframe(overview_df, use_container_width=True)

    all_env = pd.concat(env_data.values())
    avg_temp = all_env["temperature"].mean()
    avg_hum = all_env["humidity"].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 개체수", total_count)
    col2.metric("평균 온도 (℃)", f"{avg_temp:.1f}")
    col3.metric("평균 습도 (%)", f"{avg_hum:.1f}")
    col4.metric("최적 EC", "2.0 (하늘고) ⭐")

# ===============================
# TAB 2 : 환경 데이터
# ===============================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    avg_env_rows = []
    for school, df in env_data.items():
        avg_env_rows.append({
            "school": school,
            "temperature": df["temperature"].mean(),
            "humidity": df["humidity"].mean(),
            "ph": df["ph"].mean(),
            "ec": df["ec"].mean(),
            "target_ec": SCHOOL_EC[school]
        })

    avg_env = pd.DataFrame(avg_env_rows)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"]
    )

    fig.add_bar(x=avg_env["school"], y=avg_env["temperature"], row=1, col=1)
    fig.add_bar(x=avg_env["school"], y=avg_env["humidity"], row=1, col=2)
    fig.add_bar(x=avg_env["school"], y=avg_env["ph"], row=2, col=1)

    fig.add_bar(x=avg_env["school"], y=avg_env["target_ec"], name="목표 EC", row=2, col=2)
    fig.add_bar(x=avg_env["school"], y=avg_env["ec"], name="실측 EC", row=2, col=2)

    fig.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

    if selected_school != "전체":
        df = env_data[selected_school]

        st.subheader(f"{selected_school} 시계열 데이터")

        fig_ts = go.Figure()
        fig_ts.add_line(x=df["time"], y=df["temperature"], name="온도")
        fig_ts.add_line(x=df["time"], y=df["humidity"], name="습도")
        fig_ts.add_line(x=df["time"], y=df["ec"], name="EC")
        fig_ts.add_hline(y=SCHOOL_EC[selected_school], line_dash="dash", name="목표 EC")

        fig_ts.update_layout(font=PLOTLY_FONT)
        st.plotly_chart(fig_ts, use_container_width=True)

    with st.expander("환경 데이터 원본"):
        all_env_df = pd.concat(env_data.values())
        st.dataframe(all_env_df)

        csv_buffer = io.BytesIO()
        all_env_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        st.download_button(
            "CSV 다운로드",
            data=csv_buffer,
            file_name="환경데이터_전체.csv",
            mime="text/csv"
        )

# ===============================
# TAB 3 : 생육 결과
# ===============================
with tab3:
    all_growth = pd.concat(growth_data.values())
    all_growth["EC"] = all_growth["school"].map(SCHOOL_EC)

    ec_group = all_growth.groupby("EC").mean(numeric_only=True).reset_index()
    best_ec = ec_group.loc[ec_group["생중량(g)"].idxmax(), "EC"]

    st.metric("🥇 최고 평균 생중량 EC", f"{best_ec} ⭐")

    fig_growth = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수"]
    )

    fig_growth.add_bar(x=ec_group["EC"], y=ec_group["생중량(g)"], row=1, col=1)
    fig_growth.add_bar(x=ec_group["EC"], y=ec_group["잎 수(장)"], row=1, col=2)
    fig_growth.add_bar(x=ec_group["EC"], y=ec_group["지상부 길이(mm)"], row=2, col=1)
    fig_growth.add_bar(x=ec_group["EC"], y=all_growth.groupby("EC").size().values, row=2, col=2)

    fig_growth.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig_growth, use_container_width=True)

    fig_box = px.box(
        all_growth,
        x="school",
        y="생중량(g)",
        color="school"
    )
    fig_box.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_box, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        fig_sc1 = px.scatter(all_growth, x="잎 수(장)", y="생중량(g)", color="school")
        fig_sc1.update_layout(font=PLOTLY_FONT)
        st.plotly_chart(fig_sc1, use_container_width=True)

    with col2:
        fig_sc2 = px.scatter(all_growth, x="지상부 길이(mm)", y="생중량(g)", color="school")
        fig_sc2.update_layout(font=PLOTLY_FONT)
        st.plotly_chart(fig_sc2, use_container_width=True)

    with st.expander("생육 데이터 원본"):
        st.dataframe(all_growth)

        buffer = io.BytesIO()
        all_growth.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="생육결과_전체.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
