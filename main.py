# =========================
# 🌱 극지식물 최적 EC 농도 연구 대시보드
# Streamlit Cloud + 한글 파일명(NFC/NFD) 완벽 대응
# =========================

import streamlit as st
import pandas as pd
import unicodedata
from pathlib import Path
from io import BytesIO

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =========================
# 기본 설정
# =========================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

# 한글 폰트 깨짐 방지 (Streamlit + Plotly)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
    }
    </style>
    """,
    unsafe_allow_html=True
)

PLOTLY_FONT = dict(
    family="Malgun Gothic, Apple SD Gothic Neo, sans-serif",
    size=14
)

# =========================
# 상수 정의
# =========================
DATA_DIR = Path("data")

SCHOOL_EC_INFO = {
    "송도고": 1.0,
    "하늘고": 2.0,   # ⭐ 최적
    "아라고": 4.0,
    "동산고": 8.0
}

SCHOOL_COLOR = {
    "송도고": "#4C78A8",
    "하늘고": "#F58518",
    "아라고": "#54A24B",
    "동산고": "#E45756"
}

# =========================
# 유틸: NFC/NFD 안전 파일 탐색
# =========================
def normalize_name(name: str) -> str:
    return unicodedata.normalize("NFC", name)

def find_file_by_normalized_name(directory: Path, target_name: str):
    target_norm = normalize_name(target_name)
    for file in directory.iterdir():
        if normalize_name(file.name) == target_norm:
            return file
    return None

# =========================
# 데이터 로딩 (캐시)
# =========================
@st.cache_data
def load_environment_data():
    env_data = {}
    for school in SCHOOL_EC_INFO.keys():
        filename = f"{school}_환경데이터.csv"
        file_path = find_file_by_normalized_name(DATA_DIR, filename)
        if file_path is None:
            continue
        df = pd.read_csv(file_path)
        df["school"] = school
        env_data[school] = df
    return env_data

@st.cache_data
def load_growth_data():
    xlsx_path = find_file_by_normalized_name(DATA_DIR, "4개교_생육결과데이터.xlsx")
    if xlsx_path is None:
        return {}

    xls = pd.ExcelFile(xlsx_path, engine="openpyxl")
    growth_data = {}

    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        df["school"] = sheet
        df["ec"] = SCHOOL_EC_INFO.get(sheet, None)
        growth_data[sheet] = df

    return growth_data

# =========================
# 데이터 로딩 UI
# =========================
with st.spinner("📂 데이터 불러오는 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if not env_data or not growth_data:
    st.error("❌ 데이터 파일을 찾을 수 없습니다. data 폴더와 파일명을 확인하세요.")
    st.stop()

# =========================
# 제목
# =========================
st.title("🌱 극지식물 최적 EC 농도 연구")

# =========================
# 사이드바
# =========================
school_option = st.sidebar.selectbox(
    "🏫 학교 선택",
    ["전체"] + list(SCHOOL_EC_INFO.keys())
)

# =========================
# 탭 구성
# =========================
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# =========================
# 📖 Tab 1: 실험 개요
# =========================
with tab1:
    st.subheader("🔬 연구 배경 및 목적")
    st.write(
        """
        본 연구는 극지식물 재배 환경에서 **전기전도도(EC)** 농도가
        생육에 미치는 영향을 분석하여 **최적 EC 농도**를 도출하는 것을 목표로 한다.
        """
    )

    overview_df = []
    for school, ec in SCHOOL_EC_INFO.items():
        count = len(growth_data.get(school, []))
        overview_df.append([school, ec, count])

    overview_df = pd.DataFrame(
        overview_df,
        columns=["학교명", "EC 목표", "개체수"]
    )

    st.dataframe(overview_df, use_container_width=True)

    total_count = sum(len(df) for df in growth_data.values())
    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()

    st.markdown("### 📌 주요 지표")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 개체수", f"{total_count} 개")
    col2.metric("평균 온도", f"{avg_temp:.1f} ℃")
    col3.metric("평균 습도", f"{avg_hum:.1f} %")
    col4.metric("최적 EC", "2.0 (하늘고) ⭐")

# =========================
# 🌡️ Tab 2: 환경 데이터
# =========================
with tab2:
    st.subheader("📊 학교별 환경 평균 비교")

    env_all = pd.concat(env_data.values())

    env_mean = env_all.groupby("school").mean(numeric_only=True).reset_index()

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC")
    )

    fig.add_trace(go.Bar(x=env_mean["school"], y=env_mean["temperature"]), 1, 1)
    fig.add_trace(go.Bar(x=env_mean["school"], y=env_mean["humidity"]), 1, 2)
    fig.add_trace(go.Bar(x=env_mean["school"], y=env_mean["ph"]), 2, 1)

    fig.add_trace(go.Bar(
        x=env_mean["school"],
        y=[SCHOOL_EC_INFO[s] for s in env_mean["school"]],
        name="목표 EC"
    ), 2, 2)

    fig.add_trace(go.Bar(
        x=env_mean["school"],
        y=env_mean["ec"],
        name="실측 EC"
    ), 2, 2)

    fig.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

    if school_option != "전체":
        st.subheader(f"⏱️ {school_option} 시계열 변화")
        df = env_data[school_option]

        fig_ts = px.line(
            df,
            x="time",
            y=["temperature", "humidity", "ec"],
            labels={"value": "값", "variable": "지표"},
            title="환경 변화"
        )
        fig_ts.add_hline(
            y=SCHOOL_EC_INFO[school_option],
            line_dash="dash",
            annotation_text="목표 EC"
        )
        fig_ts.update_layout(font=PLOTLY_FONT)
        st.plotly_chart(fig_ts, use_container_width=True)

    with st.expander("📥 환경 데이터 원본"):
        st.dataframe(env_all, use_container_width=True)
        buffer = BytesIO()
        env_all.to_csv(buffer, index=False)
        buffer.seek(0)
        st.download_button(
            "CSV 다운로드",
            data=buffer,
            file_name="환경데이터_전체.csv",
            mime="text/csv"
        )

# =========================
# 📊 Tab 3: 생육 결과
# =========================
with tab3:
    st.subheader("🥇 EC별 평균 생중량")

    growth_all = pd.concat(growth_data.values())

    ec_mean = growth_all.groupby("ec")["생중량(g)"].mean().reset_index()
    best_ec = ec_mean.loc[ec_mean["생중량(g)"].idxmax(), "ec"]

    st.metric("최적 EC", f"{best_ec} ⭐")

    fig_weight = px.bar(
        ec_mean,
        x="ec",
        y="생중량(g)",
        text_auto=".2f",
        title="EC별 평균 생중량"
    )
    fig_weight.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_weight, use_container_width=True)

    st.subheader("📈 EC별 생육 비교")

    metrics = ["생중량(g)", "잎 수(장)", "지상부 길이(mm)"]
    fig2 = make_subplots(rows=2, cols=2)

    for i, m in enumerate(metrics):
        r, c = divmod(i, 2)
        mean_df = growth_all.groupby("ec")[m].mean().reset_index()
        fig2.add_trace(go.Bar(x=mean_df["ec"], y=mean_df[m], name=m), r+1, c+1)

    count_df = growth_all.groupby("ec").size().reset_index(name="개체수")
    fig2.add_trace(go.Bar(x=count_df["ec"], y=count_df["개체수"], name="개체수"), 2, 2)

    fig2.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig2, use_container_width=True)

    fig_box = px.box(
        growth_all,
        x="school",
        y="생중량(g)",
        color="school",
        title="학교별 생중량 분포"
    )
    fig_box.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("🔗 상관관계 분석")

    col1, col2 = st.columns(2)
    with col1:
        fig_sc1 = px.scatter(
            growth_all,
            x="잎 수(장)",
            y="생중량(g)",
            color="school"
        )
        fig_sc1.update_layout(font=PLOTLY_FONT)
        st.plotly_chart(fig_sc1, use_container_width=True)

    with col2:
        fig_sc2 = px.scatter(
            growth_all,
            x="지상부 길이(mm)",
            y="생중량(g)",
            color="school"
        )
        fig_sc2.update_layout(font=PLOTLY_FONT)
        st.plotly_chart(fig_sc2, use_container_width=True)

    with st.expander("📥 생육 데이터 원본 다운로드"):
        buffer = BytesIO()
        growth_all.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="생육결과_전체.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
