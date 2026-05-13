# -*- coding: utf-8 -*-

import os
import json
import pandas as pd
import streamlit as st
import folium
import plotly.express as px
from streamlit_folium import st_folium


# ======================
# 页面设置
# ======================

st.set_page_config(
    page_title="广东方言特征可视化平台",
    page_icon="🗺️",
    layout="wide"
)

st.title("广东方言特征可视化平台")
st.caption(
    "选择某个语音特征后，地图只高亮出现该特征的县区。"
    "选择“区域倾向”时，右侧显示区域倾向统计图。"
)


# ======================
# 文件路径：兼容 data 文件夹和根目录
# ======================

def find_file(possible_paths):
    for p in possible_paths:
        if os.path.exists(p):
            return p
    return possible_paths[0]


GEOJSON_PATH = find_file([
    "data/guangdong_county.geojson",
    "guangdong_county.geojson"
])

RECORDS_PATH = find_file([
    "data/dialect_records.csv",
    "dialect_records.csv"
])

COUNTS_PATH = find_file([
    "data/feature_counts.csv",
    "feature_counts.csv"
])


# ======================
# 数据读取
# ======================

@st.cache_data(show_spinner="正在读取广东县区边界...")
def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner="正在读取方言记录...")
def load_records(path):
    return pd.read_csv(path, encoding="utf-8-sig")


@st.cache_data(show_spinner="正在读取特征统计表...")
def load_counts(path):
    return pd.read_csv(path, encoding="utf-8-sig")


if not os.path.exists(GEOJSON_PATH):
    st.error(f"没有找到边界文件：{GEOJSON_PATH}")
    st.stop()

if not os.path.exists(RECORDS_PATH):
    st.error(f"没有找到记录文件：{RECORDS_PATH}")
    st.stop()

if not os.path.exists(COUNTS_PATH):
    st.error(f"没有找到统计文件：{COUNTS_PATH}")
    st.stop()


geojson_data = load_geojson(GEOJSON_PATH)
records = load_records(RECORDS_PATH)
counts = load_counts(COUNTS_PATH)


# ======================
# 基础字段检查
# ======================

key_col = "市县匹配键"

required_count_cols = [
    key_col,
    "特征字段",
    "特征值",
    "特征数量"
]

for c in required_count_cols:
    if c not in counts.columns:
        st.error(f"feature_counts.csv 中没有字段：{c}")
        st.stop()

if key_col not in records.columns:
    st.error("dialect_records.csv 中没有“市县匹配键”字段。")
    st.stop()


# ======================
# 侧边栏筛选
# 注意：form key 必须唯一，避免 Duplicate form key 报错
# ======================

st.sidebar.header("筛选条件")

feature_fields = sorted(
    counts["特征字段"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

if len(feature_fields) == 0:
    st.error("feature_counts.csv 中没有可用的特征字段。")
    st.stop()


# 默认优先选择“区域倾向”
default_field_index = 0
for i, f in enumerate(feature_fields):
    if f in ["區域傾向", "区域倾向"]:
        default_field_index = i
        break


with st.sidebar.form(key="feature_filter_form_v20260513"):
    selected_field = st.selectbox(
        "选择特征字段",
        feature_fields,
        index=default_field_index,
        key="selected_field_v20260513"
    )

    values = (
        counts[counts["特征字段"].astype(str) == str(selected_field)]["特征值"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    values = values[
        (values != "") &
        (values.str.lower() != "nan") &
        (values != "/")
    ]

    feature_values = sorted(values.unique().tolist())

    if len(feature_values) == 0:
        selected_value = ""
    else:
        selected_value = st.selectbox(
            "选择具体特征",
            feature_values,
            key="selected_value_v20260513"
        )

    update_button = st.form_submit_button("更新地图")


if selected_value == "":
    st.warning("当前特征字段没有可选特征值。")
    st.stop()


# ======================
# 当前特征的县区数量
# ======================

current_counts = counts[
    (counts["特征字段"].astype(str) == str(selected_field)) &
    (counts["特征值"].astype(str) == str(selected_value))
].copy()

current_counts["特征数量"] = (
    current_counts["特征数量"]
    .fillna(0)
    .astype(int)
)

count_dict = dict(
    zip(current_counts[key_col], current_counts["特征数量"])
)


# ======================
# 筛选明细记录
# ======================

if selected_field in records.columns:
    field_text = records[selected_field].fillna("").astype(str).str.strip()
    filtered = records[field_text == str(selected_value)].copy()
else:
    filtered = pd.DataFrame()


# ======================
# 给 GeoJSON 添加特征数量
# ======================

map_geojson = json.loads(json.dumps(geojson_data, ensure_ascii=False))

for feature in map_geojson["features"]:
    props = feature["properties"]

    key = props.get("市县匹配键", "")
    if key == "":
        key = props.get("match_key", "")

    props["特征数量"] = int(count_dict.get(key, 0))


# ======================
# 顶部统计信息
# ======================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("当前特征记录数", len(filtered))

with col2:
    st.metric("涉及县区数", len(current_counts))

with col3:
    st.metric("选择字段", selected_field)

st.markdown(
    f"""
当前展示：  
**{selected_field} = {selected_value}**
"""
)


# ======================
# 地图颜色规则
# ======================

def get_color(count):
    if count >= 20:
        return "#b10026"
    elif count >= 10:
        return "#e31a1c"
    elif count >= 5:
        return "#fc4e2a"
    elif count >= 2:
        return "#fd8d3c"
    elif count >= 1:
        return "#feb24c"
    else:
        return "#f2f2f2"


def style_function(feature):
    count = feature["properties"].get("特征数量", 0)

    if count > 0:
        return {
            "fillColor": get_color(count),
            "color": "#555555",
            "weight": 0.8,
            "fillOpacity": 0.80
        }
    else:
        return {
            "fillColor": "#f2f2f2",
            "color": "#bbbbbb",
            "weight": 0.4,
            "fillOpacity": 0.35
        }


def highlight_function(feature):
    return {
        "weight": 2,
        "color": "#000000",
        "fillOpacity": 0.90
    }


# ======================
# 地图 + 右侧区域倾向统计图
# ======================

left_col, right_col = st.columns([2.2, 1])

with left_col:
    st.subheader("空间分布图")

    # 无在线底图，只显示广东县区边界，提高速度
    m = folium.Map(
        location=[23.4, 113.4],
        zoom_start=7,
        tiles=None,
        prefer_canvas=True,
        control_scale=False,
        zoom_control=True
    )

    sample_props = map_geojson["features"][0]["properties"]

    tooltip_fields = []
    tooltip_aliases = []

    for f, a in [
        ("省", "省："),
        ("市", "市："),
        ("县", "县："),
        ("市县匹配键", "匹配键："),
        ("特征数量", "特征数量：")
    ]:
        if f in sample_props:
            tooltip_fields.append(f)
            tooltip_aliases.append(a)

    folium.GeoJson(
        map_geojson,
        name="广东县区边界",
        style_function=style_function,
        highlight_function=highlight_function,
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            localize=True,
            sticky=False
        )
    ).add_to(m)

    legend_html = """
    <div style="
    position: fixed;
    bottom: 40px;
    left: 40px;
    z-index: 9999;
    background-color: white;
    padding: 12px 14px;
    border: 1px solid #cccccc;
    border-radius: 6px;
    font-size: 14px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    ">
    <b>特征数量</b><br>
    <span style="background:#b10026;width:18px;height:12px;display:inline-block;"></span> ≥ 20<br>
    <span style="background:#e31a1c;width:18px;height:12px;display:inline-block;"></span> 10 - 19<br>
    <span style="background:#fc4e2a;width:18px;height:12px;display:inline-block;"></span> 5 - 9<br>
    <span style="background:#fd8d3c;width:18px;height:12px;display:inline-block;"></span> 2 - 4<br>
    <span style="background:#feb24c;width:18px;height:12px;display:inline-block;"></span> 1<br>
    <span style="background:#f2f2f2;width:18px;height:12px;display:inline-block;border:1px solid #bbb;"></span> 0
    </div>
    """

    m.get_root().html.add_child(folium.Element(legend_html))

    st_folium(
        m,
        width=900,
        height=650,
        returned_objects=[]
    )


with right_col:
    st.subheader("区域倾向统计图")

    if selected_field in ["區域傾向", "区域倾向"]:
        region_df = counts[
            counts["特征字段"].astype(str) == str(selected_field)
        ].copy()

        region_df["特征值"] = (
            region_df["特征值"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        region_df = region_df[
            (region_df["特征值"] != "") &
            (region_df["特征值"].str.lower() != "nan") &
            (region_df["特征值"] != "/")
        ]

        exclude_unknown = st.checkbox(
            "排除“不明”",
            value=False,
            key="exclude_unknown_region_v20260513"
        )

        if exclude_unknown:
            region_df = region_df[region_df["特征值"] != "不明"]

        region_summary = (
            region_df.groupby("特征值")["特征数量"]
            .sum()
            .reset_index()
            .sort_values("特征数量", ascending=True)
        )

        if len(region_summary) == 0:
            st.info("区域倾向没有可统计的数据。")
        else:
            fig_region = px.bar(
                region_summary,
                x="特征数量",
                y="特征值",
                orientation="h",
                text="特征数量",
                title="区域倾向类别数量统计"
            )

            fig_region.update_traces(
                textposition="outside"
            )

            fig_region.update_layout(
                height=650,
                margin=dict(l=10, r=20, t=60, b=20),
                xaxis_title="记录数量",
                yaxis_title="区域倾向",
                showlegend=False
            )

            st.plotly_chart(
                fig_region,
                use_container_width=True
            )

    else:
        st.info(
            "当前右侧统计图仅在选择“区域倾向 / 區域傾向”字段时显示。\n\n"
            "请在左侧将“选择特征字段”切换为“区域倾向”。"
        )


# ======================
# 县区数量排行
# ======================

st.subheader("县区特征数量排行")

rank_df = current_counts.sort_values("特征数量", ascending=False).copy()

if len(rank_df) > 0:
    st.dataframe(
        rank_df.head(30),
        use_container_width=True,
        height=260
    )
else:
    st.info("当前特征没有匹配到县区。")


# ======================
# 明细表：默认不显示，减少页面压力
# ======================

show_detail = st.checkbox(
    "显示当前特征对应的文献记录明细",
    value=False,
    key="show_detail_v20260513"
)

if show_detail:
    st.subheader("当前筛选结果")

    preferred_cols = [
        "編號",
        "编号",
        "原地名",
        "今地",
        "今属行政区划",
        "省",
        "市",
        "县",
        "語音特徵大類",
        "語音特徵小類及編碼",
        "標準化語音特徵",
        "方言類型判斷",
        "區域傾向",
        "区域倾向",
        "現代方言區參照",
        "古今關係",
        "證據等級",
        "文獻來源",
        "原文"
    ]

    show_cols = [c for c in preferred_cols if c in filtered.columns]

    if len(show_cols) == 0:
        show_cols = filtered.columns.tolist()

    st.dataframe(
        filtered[show_cols],
        use_container_width=True,
        height=360
    )

    download_csv = filtered.to_csv(index=False, encoding="utf-8-sig")

    safe_name = (
        str(selected_value)
        .replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
        .replace(":", "_")
        .replace("：", "_")
    )

    st.download_button(
        label="下载当前筛选结果 CSV",
        data=download_csv,
        file_name=f"{selected_field}_{safe_name}_筛选结果.csv",
        mime="text/csv",
        key="download_filtered_v20260513"
    )
