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
st.set_page_config(page_title="🌱 극지식물 최적 EC 농도 연구", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

PLOTLY_FONT = dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")

# ===============================
# NFC 정규화
# ===============================
def normalize(text):
    return unicodedata.normalize("NFC", text)

# ===============================
# 데이터 로딩
# ===============================
@st.cache_data
def load_environment_data(data_dir: Path):
    result = {}
    for f in data_dir.iterdir():
        if f.suffix.lower() == ".csv":
            school = normalize(f.stem.replace("_환경데이터", ""))
            df = pd.read_csv(f)
            df["time"] = pd.to_datetime(df["time"])
            df["school"] = school
            result[school] = df
    return result

@st.cache_data
def load_growth_data(data_dir: Path):
    xlsx = None
    for f in data_dir.iterdir():
        if f.suffix.lower() == ".xlsx":
            xlsx = f
            break
    if xlsx is None:
        return {}

    xls = pd.ExcelFile(xlsx)
    result = {}
    for sheet in xls.sheet_names:
        school = normalize(sheet)
        df = xls.parse(sheet)
        df["school"] = school
        result[school] = df
    return result

# ===============================
# 데이터 로드
# ===============================
DATA_DIR = Path("data")

with st.spinner("📂 데이터 로딩 중..."):
    env_data = load_environment_data(DATA_DIR)
    growth_data = load_growth_data(DATA_DIR)

if not env_data or not growth_data:
    st.error("❌ 데이터 로딩 실패")
    st.stop()

schools = sorted(set(env_data) & set(growth_data))
if not schools:
    st.error("❌ 공통 학교 없음")
    st.stop()

# ===============================
# 사이드바
# ===============================
selected_school = st.sidebar.selectbox("🏫 학교 선택", ["전체"] + schools)

# ===============================
# 공통 데이터
# ===============================
env_all = pd.concat(env_data.values(), ignore_index=True)
growth_all = pd.concat(growth_data.values(), ignore_index=True)

ec_map = {s: env_data[s]["ec"].mean() for s in schools}
growth_all["EC"] = growth_all["school"].map(ec_map)

# ===============================
# UI
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ===============================
# Tab 1
# ===============================
with tab1:
    st.metric("총 개체수", len(growth_all))
    st.metric("최적 EC", f"{growth_all.groupby('EC')['생중량(g)'].mean().idxmax():.2f}")

# ===============================
# Tab 2
# ===============================
with tab2:
    avg_env = env_all.groupby("school").mean(numeric_only=True)

    fig = make_subplots(rows=2, cols=2,
                        subplot_titles=["온도", "습도", "pH", "EC"])

    fig.add_bar(x=avg_env.index, y=avg_env["temperature"], row=1, col=1)
    fig.add_bar(x=avg_env.index, y=avg_env["humidity"], row=1, col=2)
    fig.add_bar(x=avg_env.index, y=avg_env["ph"], row=2, col=1)
    fig.add_bar(x=avg_env.index, y=avg_env["ec"], row=2, col=2)

    fig.update_layout(height=650, font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

    if selected_school != "전체":
        df = env_data[selected_school]

        fig_ts = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            subplot_titles=["온도", "습도", "EC"]
        )

        fig_ts.add_trace(
            go.Scatter(x=df["time"], y=df["temperature"], mode="lines"),
            row=1, col=1
        )
        fig_ts.add_trace(
            go.Scatter(x=df["time"], y=df["humidity"], mode="lines"),
            row=2, col=1
        )
        fig_ts.add_trace(
            go.Scatter(x=df["time"], y=df["ec"], mode="lines"),
            row=3, col=1
        )

        fig_ts.update_layout(height=700, font=PLOTLY_FONT)
        st.plotly_chart(fig_ts, use_container_width=True)

# ===============================
# Tab 3
# ===============================
with tab3:
    ec_avg = growth_all.groupby("EC")["생중량(g)"].mean().reset_index()
    fig_ec = px.bar(ec_avg, x="EC", y="생중량(g)", text_auto=".2f")
    fig_ec.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_ec, use_container_width=True)

    buffer = io.BytesIO()
    growth_all.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)

    st.download_button(
        "📥 생육 데이터 XLSX 다운로드",
        buffer,
        "생육결과.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
