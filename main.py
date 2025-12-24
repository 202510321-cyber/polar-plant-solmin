import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pathlib import Path
import unicodedata
import io

# ------------------------------
# Streamlit 기본 설정
# ------------------------------
st.set_page_config(
    page_title="🌱 극지식물 최적 EC 농도 연구",
    layout="wide"
)

# 한글 폰트 (Streamlit)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

PLOTLY_FONT = dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")

# ------------------------------
# 파일 유틸 (NFC/NFD 완전 대응)
# ------------------------------
def normalize(text):
    return unicodedata.normalize("NFC", text)

def find_file_by_name(directory: Path, target_name: str):
    target_nfc = normalize(target_name)
    for f in directory.iterdir():
        if normalize(f.name) == target_nfc:
            return f
    return None

# ------------------------------
# 데이터 로딩
# ------------------------------
@st.cache_data
def load_environment_data():
    data_dir = Path("data")
    env_files = {}
    for file in data_dir.iterdir():
        if file.suffix.lower() == ".csv":
            env_files[normalize(file.stem)] = file

    if not env_files:
        return None

    dfs = {}
    for school, path in env_files.items():
        df = pd.read_csv(path)
        df["school"] = school
        dfs[school] = df

    return dfs

@st.cache_data
def load_growth_data():
    data_dir = Path("data")
    xlsx_path = None
    for f in data_dir.iterdir():
        if f.suffix.lower() == ".xlsx":
            xlsx_path = f
            break

    if xlsx_path is None:
        return None

    xls = pd.ExcelFile(xlsx_path)
    dfs = {}
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        df["school"] = sheet
        dfs[sheet] = df

    return dfs

# ------------------------------
# 데이터 로딩 UI
# ------------------------------
with st.spinner("📂 데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if env_data is None or growth_data is None:
    st.error("❌ 데이터 파일을 찾을 수 없습니다. data 폴더를 확인하세요.")
    st.stop()

# ------------------------------
# 사이드바
# ------------------------------
schools = sorted(set(list(env_data.keys()) + list(growth_data.keys())))
school_option = st.sidebar.selectbox(
    "🏫 학교 선택",
    ["전체"] + schools
)

# ------------------------------
# 공통 데이터
# ------------------------------
env_all = pd.concat(env_data.values(), ignore_index=True)
growth_all = pd.concat(growth_data.values(), ignore_index=True)

if school_option != "전체":
    env_filtered = env_all[env_all["school"] == school_option]
    growth_filtered = growth_all[growth_all["school"] == school_option]
else:
    env_filtered = env_all
    growth_filtered = growth_all

# ------------------------------
# 제목
# ------------------------------
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ==================================================
# Tab 1 : 실험 개요
# ==================================================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.markdown(
        """
        본 연구는 학교별 상이한 EC 조건에서 극지식물의 생육 반응을 분석하여  
        **최적 EC 농도**를 도출하는 것을 목표로 한다.
        """
    )

    ec_table = []
    for school in schools:
        ec_mean = env_all[env_all["school"] == school]["ec"].mean()
        count = len(growth_all[growth_all["school"] == school])
        ec_table.append({
            "학교명": school,
            "평균 EC": round(ec_mean, 2),
            "개체수": count
        })

    ec_df = pd.DataFrame(ec_table)
    st.dataframe(ec_df, use_container_width=True)

    total_plants = len(growth_all)
    avg_temp = env_all["temperature"].mean()
    avg_hum = env_all["humidity"].mean()

    ec_weight = growth_all.groupby("school")["생중량(g)"].mean()
    optimal_ec_school = ec_weight.idxmax()
    optimal_ec_value = env_all[env_all["school"] == optimal_ec_school]["ec"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌿 총 개체수", total_plants)
    c2.metric("🌡 평균 온도", f"{avg_temp:.1f} ℃")
    c3.metric("💧 평균 습도", f"{avg_hum:.1f} %")
    c4.metric("⭐ 최적 EC", f"{optimal_ec_value:.2f}")

# ==================================================
# Tab 2 : 환경 데이터
# ==================================================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    avg_env = env_filtered.groupby("school").mean(numeric_only=True)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 온도", "평균 습도", "평균 pH", "EC 비교")
    )

    fig.add_bar(x=avg_env.index, y=avg_env["temperature"], row=1, col=1)
    fig.add_bar(x=avg_env.index, y=avg_env["humidity"], row=1, col=2)
    fig.add_bar(x=avg_env.index, y=avg_env["ph"], row=2, col=1)
    fig.add_bar(x=avg_env.index, y=avg_env["ec"], row=2, col=2)

    fig.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("환경 변화 시계열")

    for col, label in [("temperature", "온도"), ("humidity", "습도"), ("ec", "EC")]:
        fig_line = px.line(
            env_filtered,
            x="time",
            y=col,
            color="school",
            title=f"{label} 변화"
        )
        fig_line.update_layout(font=PLOTLY_FONT)
        st.plotly_chart(fig_line, use_container_width=True)

    with st.expander("📄 환경 데이터 원본"):
        st.dataframe(env_filtered, use_container_width=True)
        csv = env_filtered.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "CSV 다운로드",
            data=csv,
            file_name="환경데이터.csv",
            mime="text/csv"
        )

# ==================================================
# Tab 3 : 생육 결과
# ==================================================
with tab3:
    st.subheader("🥇 EC별 평균 생중량")

    weight_by_school = growth_filtered.groupby("school")["생중량(g)"].mean().reset_index()
    best_idx = weight_by_school["생중량(g)"].idxmax()

    fig_weight = px.bar(
        weight_by_school,
        x="school",
        y="생중량(g)",
        text_auto=".2f"
    )
    fig_weight.update_traces(
        marker_color=[
            "gold" if i == best_idx else None
            for i in range(len(weight_by_school))
        ]
    )
    fig_weight.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_weight, use_container_width=True)

    st.subheader("EC별 생육 비교")

    metrics = [
        ("생중량(g)", "평균 생중량"),
        ("잎 수(장)", "평균 잎 수"),
        ("지상부 길이(mm)", "평균 지상부 길이"),
        ("개체번호", "개체수")
    ]

    fig2 = make_subplots(
        rows=2, cols=2,
        subplot_titles=[m[1] for m in metrics]
    )

    for i, (col, _) in enumerate(metrics):
        row = i // 2 + 1
        col_i = i % 2 + 1
        if col == "개체번호":
            y = growth_filtered.groupby("school").count()[col]
        else:
            y = growth_filtered.groupby("school").mean(numeric_only=True)[col]
        fig2.add_bar(x=y.index, y=y.values, row=row, col=col_i)

    fig2.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("학교별 생중량 분포")
    fig_box = px.box(
        growth_filtered,
        x="school",
        y="생중량(g)"
    )
    fig_box.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("상관관계 분석")

    c1, c2 = st.columns(2)
    with c1:
        fig_sc1 = px.scatter(
            growth_filtered,
            x="잎 수(장)",
            y="생중량(g)",
            color="school"
        )
        fig_sc1.update_layout(font=PLOTLY_FONT)
        st.plotly_chart(fig_sc1, use_container_width=True)

    with c2:
        fig_sc2 = px.scatter(
            growth_filtered,
            x="지상부 길이(mm)",
            y="생중량(g)",
            color="school"
        )
        fig_sc2.update_layout(font=PLOTLY_FONT)
        st.plotly_chart(fig_sc2, use_container_width=True)

    with st.expander("📥 생육 데이터 다운로드"):
        st.dataframe(growth_filtered, use_container_width=True)
        buffer = io.BytesIO()
        growth_filtered.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="생육결과.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
