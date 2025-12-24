import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# ===============================
# Streamlit 기본 설정
# ===============================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

# ===============================
# 한글 폰트 (깨짐 방지)
# ===============================
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
# 경로 및 유틸
# ===============================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFC", text)

def find_file_by_name(directory: Path, target_name: str):
    target_nfc = normalize_text(target_name)
    for file in directory.iterdir():
        if normalize_text(file.name) == target_nfc:
            return file
    return None

# ===============================
# 데이터 로딩
# ===============================
@st.cache_data
def load_environment_data():
    with st.spinner("환경 데이터 로딩 중..."):
        env_data = {}
        csv_files = list(DATA_DIR.iterdir())

        for file in csv_files:
            if file.suffix.lower() == ".csv":
                school_name = file.stem.replace("_환경데이터", "")
                df = pd.read_csv(file)
                env_data[school_name] = df

        if not env_data:
            st.error("환경 데이터 CSV 파일을 찾을 수 없습니다.")
        return env_data

@st.cache_data
def load_growth_data():
    with st.spinner("생육 결과 데이터 로딩 중..."):
        xlsx_file = None
        for file in DATA_DIR.iterdir():
            if file.suffix.lower() == ".xlsx":
                xlsx_file = file
                break

        if xlsx_file is None:
            st.error("생육 결과 XLSX 파일을 찾을 수 없습니다.")
            return {}

        xls = pd.ExcelFile(xlsx_file, engine="openpyxl")
        growth_data = {}

        for sheet in xls.sheet_names:
            growth_data[sheet] = xls.parse(sheet)

        return growth_data

env_data = load_environment_data()
growth_data = load_growth_data()

if not env_data or not growth_data:
    st.stop()

# ===============================
# 메타 정보
# ===============================
EC_INFO = {
    "송도고": {"ec": 1.0, "color": "#1f77b4"},
    "하늘고": {"ec": 2.0, "color": "#2ca02c"},
    "아라고": {"ec": 4.0, "color": "#ff7f0e"},
    "동산고": {"ec": 8.0, "color": "#d62728"},
}

ALL_SCHOOLS = list(EC_INFO.keys())

# ===============================
# 제목
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")

# ===============================
# 사이드바
# ===============================
selected_school = st.sidebar.selectbox(
    "학교 선택",
    ["전체"] + ALL_SCHOOLS
)

# ===============================
# 탭 구성
# ===============================
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ===============================
# Tab 1: 실험 개요
# ===============================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.write(
        """
        본 연구는 **극지식물 생육에 최적화된 EC 농도**를 도출하기 위해  
        4개 학교에서 서로 다른 EC 조건 하에서 환경 데이터와 생육 결과를 비교 분석하였다.
        """
    )

    overview_rows = []
    total_plants = 0
    for school, info in EC_INFO.items():
        count = len(growth_data.get(school, []))
        total_plants += count
        overview_rows.append({
            "학교명": school,
            "EC 목표": info["ec"],
            "개체수": count,
            "색상": info["color"]
        })

    overview_df = pd.DataFrame(overview_rows)
    st.dataframe(overview_df, use_container_width=True)

    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()

    best_ec = 2.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", f"{total_plants} 개")
    c2.metric("평균 온도", f"{avg_temp:.1f} ℃")
    c3.metric("평균 습도", f"{avg_hum:.1f} %")
    c4.metric("최적 EC", f"{best_ec} ⭐")

# ===============================
# Tab 2: 환경 데이터
# ===============================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    summary = []
    for school, df in env_data.items():
        summary.append({
            "학교": school,
            "온도": df["temperature"].mean(),
            "습도": df["humidity"].mean(),
            "pH": df["ph"].mean(),
            "실측 EC": df["ec"].mean(),
            "목표 EC": EC_INFO[school]["ec"]
        })

    summary_df = pd.DataFrame(summary)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC")
    )

    fig.add_bar(x=summary_df["학교"], y=summary_df["온도"], row=1, col=1)
    fig.add_bar(x=summary_df["학교"], y=summary_df["습도"], row=1, col=2)
    fig.add_bar(x=summary_df["학교"], y=summary_df["pH"], row=2, col=1)

    fig.add_bar(
        x=summary_df["학교"],
        y=summary_df["목표 EC"],
        name="목표 EC",
        row=2, col=2
    )
    fig.add_bar(
        x=summary_df["학교"],
        y=summary_df["실측 EC"],
        name="실측 EC",
        row=2, col=2
    )

    fig.update_layout(height=700, font=PLOTLY_FONT, showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

    if selected_school != "전체":
        df = env_data[selected_school]

        fig_ts = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            subplot_titles=("온도 변화", "습도 변화", "EC 변화")
        )

        fig_ts.add_scatter(x=df["time"], y=df["temperature"], row=1, col=1)
        fig_ts.add_scatter(x=df["time"], y=df["humidity"], row=2, col=1)
        fig_ts.add_scatter(x=df["time"], y=df["ec"], row=3, col=1)
        fig_ts.add_hline(
            y=EC_INFO[selected_school]["ec"],
            line_dash="dash",
            row=3, col=1
        )

        fig_ts.update_layout(height=700, font=PLOTLY_FONT)
        st.plotly_chart(fig_ts, use_container_width=True)

        with st.expander("📄 환경 데이터 원본"):
            st.dataframe(df, use_container_width=True)
            buffer = io.BytesIO()
            df.to_csv(buffer, index=False)
            buffer.seek(0)
            st.download_button(
                "CSV 다운로드",
                data=buffer,
                file_name=f"{selected_school}_환경데이터.csv",
                mime="text/csv"
            )

# ===============================
# Tab 3: 생육 결과
# ===============================
with tab3:
    st.subheader("EC별 생육 결과 비교")

    growth_summary = []
    for school, df in growth_data.items():
        growth_summary.append({
            "학교": school,
            "EC": EC_INFO[school]["ec"],
            "평균 생중량": df["생중량(g)"].mean(),
            "평균 잎 수": df["잎 수(장)"].mean(),
            "평균 지상부 길이": df["지상부 길이(mm)"].mean(),
            "개체수": len(df)
        })

    gs_df = pd.DataFrame(growth_summary)
    best_row = gs_df.loc[gs_df["평균 생중량"].idxmax()]

    st.metric(
        "🥇 최적 EC 평균 생중량",
        f"{best_row['평균 생중량']:.2f} g",
        help=f"EC {best_row['EC']} ({best_row['학교']})"
    )

    fig_bar = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 생중량 ⭐", "평균 잎 수", "평균 지상부 길이", "개체수")
    )

    fig_bar.add_bar(x=gs_df["EC"], y=gs_df["평균 생중량"], row=1, col=1)
    fig_bar.add_bar(x=gs_df["EC"], y=gs_df["평균 잎 수"], row=1, col=2)
    fig_bar.add_bar(x=gs_df["EC"], y=gs_df["평균 지상부 길이"], row=2, col=1)
    fig_bar.add_bar(x=gs_df["EC"], y=gs_df["개체수"], row=2, col=2)

    fig_bar.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig_bar, use_container_width=True)

    all_growth = pd.concat(
        [df.assign(학교=school) for school, df in growth_data.items()]
    )

    fig_box = px.box(
        all_growth,
        x="학교",
        y="생중량(g)",
        color="학교"
    )
    fig_box.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_box, use_container_width=True)

    fig_scatter1 = px.scatter(
        all_growth,
        x="잎 수(장)",
        y="생중량(g)",
        color="학교"
    )
    fig_scatter2 = px.scatter(
        all_growth,
        x="지상부 길이(mm)",
        y="생중량(g)",
        color="학교"
    )

    fig_scatter1.update_layout(font=PLOTLY_FONT)
    fig_scatter2.update_layout(font=PLOTLY_FONT)

    st.plotly_chart(fig_scatter1, use_container_width=True)
    st.plotly_chart(fig_scatter2, use_container_width=True)

    with st.expander("📄 생육 데이터 원본"):
        st.dataframe(all_growth, use_container_width=True)
        buffer = io.BytesIO()
        all_growth.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="전체_생육결과.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
