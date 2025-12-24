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
    page_title="🌱 극지식물 최적 EC 농도 연구",
    layout="wide"
)

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
# 유틸: NFC/NFD 완전 대응
# ===============================
def normalize(text: str) -> str:
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
    if not DATA_DIR.exists():
        st.error("❌ data 폴더가 존재하지 않습니다.")
        st.stop()

    env_data = load_environment_data(DATA_DIR)
    growth_data = load_growth_data(DATA_DIR)

if not env_data or not growth_data:
    st.error("❌ 데이터가 비어 있습니다.")
    st.stop()

schools = sorted(set(env_data) & set(growth_data))
if not schools:
    st.error("❌ 환경/생육 데이터가 매칭되지 않습니다.")
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
# 제목 & 탭
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ==================================================
# Tab 1
# ==================================================
with tab1:
    st.markdown("""
    **EC(전기전도도) 농도 차이에 따른 극지식물 생육 반응을 분석하여  
    최적 EC 농도를 도출하는 연구 대시보드**
    """)

    summary = []
    for s in schools:
        summary.append({
            "학교명": s,
            "평균 EC": round(ec_map[s], 2),
            "개체수": len(growth_data[s])
        })

    st.dataframe(pd.DataFrame(summary), use_container_width=True)

    optimal_ec = (
        growth_all.groupby("EC")["생중량(g)"]
        .mean()
        .idxmax()
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", len(growth_all))
    c2.metric("평균 온도", f"{env_all['temperature'].mean():.1f}℃")
    c3.metric("평균 습도", f"{env_all['humidity'].mean():.1f}%")
    c4.metric("⭐ 최적 EC", f"{optimal_ec:.2f}")

# ==================================================
# Tab 2
# ==================================================
with tab2:
    avg_env = env_all.groupby("school").mean(numeric_only=True)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["온도", "습도", "pH", "EC"]
    )

    fig.add_bar(x=avg_env.index, y=avg_env["temperature"], row=1, col=1)
    fig.add_bar(x=avg_env.index, y=avg_env["humidity"], row=1, col=2)
    fig.add_bar(x=avg_env.index, y=avg_env["ph"], row=2, col=1)
    fig.add_bar(x=avg_env.index, y=avg_env["ec"], row=2, col=2)

    fig.update_layout(height=650, font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

    if selected_school != "전체":
        df = env_data[selected_school]
        target_ec = ec_map[selected_school]

        fig_ts = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            subplot_titles=["온도", "습도", "EC"]
        )

        fig_ts.add_line(x=df["time"], y=df["temperature"], row=1, col=1)
        fig_ts.add_line(x=df["time"], y=df["humidity"], row=2, col=1)
        fig_ts.add_line(x=df["time"], y=df["ec"], row=3, col=1)
        fig_ts.add_hline(
            y=target_ec,
            row=3, col=1,
            line_dash="dash",
            annotation_text="목표 EC"
        )

        fig_ts.update_layout(height=700, font=PLOTLY_FONT)
        st.plotly_chart(fig_ts, use_container_width=True)

    with st.expander("📥 환경 데이터 원본"):
        st.dataframe(env_all, use_container_width=True)
        csv = env_all.to_csv(index=False).encode("utf-8-sig")
        st.download_button("CSV 다운로드", csv, "환경데이터.csv", "text/csv")

# ==================================================
# Tab 3
# ==================================================
with tab3:
    ec_avg = growth_all.groupby("EC")["생중량(g)"].mean().reset_index()

    fig_ec = px.bar(
        ec_avg,
        x="EC",
        y="생중량(g)",
        text_auto=".2f"
    )
    fig_ec.update_traces(
        marker_color=[
            "gold" if ec == 2.0 else None
            for ec in ec_avg["EC"]
        ]
    )
    fig_ec.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_ec, use_container_width=True)

    fig_box = px.box(growth_all, x="school", y="생중량(g)")
    fig_box.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_box, use_container_width=True)

    with st.expander("📥 생육 데이터 다운로드"):
        st.dataframe(growth_all, use_container_width=True)
        buffer = io.BytesIO()
        growth_all.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        st.download_button(
            "XLSX 다운로드",
            buffer,
            "생육결과.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
