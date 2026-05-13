# -*- coding: utf-8 -*-

import json
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium


st.set_page_config(
    page_title="广东方言特征可视化平台",
    page_icon="🗺️",
    layout="wide"
)

st.title("广东方言特征可视化平台")
st.caption("选择某个语音特征后，地图只高亮出现该特征的县区。")


GEOJSON_PATH = "data/guangdong_county.geojson"
RECORDS_PATH = "data/dialect_records.csv"
COUNTS_PATH = "data/feature_counts.csv"


@st.cache_data
def load_geojson():
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_records():
    return pd.read_csv(RECORDS_PATH, encoding="utf-8-sig")


@st.cache_data
def load_counts():
    return pd.read_csv(COUNTS_PATH, encoding="utf-8-sig")


geojson_data = load_geojson()
records = load_records()
counts = load_counts()


key_col = "市县匹配键"

if key_col not in records.columns:
    st.error("records 中没有“市县匹配键”字段。")
    st.stop()

if key_col not in counts.columns:
    st.error("feature_counts 中没有“市县匹配键”字段。")
    st.stop()


# ======================
# 筛选区：用 form，避免每点一下就重新跑
# ======================

st.sidebar.header("筛选条件")

feature_fields = sorted(counts["特征字段"].dropna().unique().tolist())

with st.sidebar.form("filter_form"):
    selected_field = st.selectbox(
        "选择特征字段",
        feature_fields
    )

    values = (
        counts[counts["特征字段"] == selected_field]["特征值"]
        .dropna()
        .astype(str)
        .sort_values()
        .unique()
        .tolist()
    )

    selected_value = st.selectbox(
        "选择具体特征",
        values
    )

    submit = st.form_submit_button("更新地图")


# ======================
# 读取当前特征的县区数量
# ======================

current_counts = counts[
    (counts["特征字段"] == selected_field) &
    (counts["特征值"].astype(str) == str(selected_value))
].copy()

count_dict = dict(
    zip(current_counts[key_col], current_counts["特征数量"])
)


# ======================
# 筛选明细表
# ======================

field_text = records[selected_field].fillna("").astype(str).str.strip()

filtered = records[field_text == str(selected_value)].copy()


# ======================
# 给 GeoJSON 添加数量
# ======================

# 注意：这里复制一份，避免缓存对象被反复修改
map_geojson = json.loads(json.dumps(geojson_data, ensure_ascii=False))

for feature in map_geojson["features"]:
    props = feature["properties"]

    key = props.get("市县匹配键", "")
    if key == "":
        key = props.get("match_key", "")

    props["特征数量"] = int(count_dict.get(key, 0))


# ======================
# 顶部统计
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
# 地图样式
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
        return "#eeeeee"


def style_function(feature):
    count = feature["properties"].get("特征数量", 0)

    if count > 0:
        return {
            "fillColor": get_color(count),
            "color": "#555555",
            "weight": 0.8,
            "fillOpacity": 0.75
        }
    else:
        return {
            "fillColor": "#eeeeee",
            "color": "#cccccc",
            "weight": 0.3,
            "fillOpacity": 0.18
        }


m = folium.Map(
    location=[23.4, 113.4],
    zoom_start=7,
    tiles="CartoDB positron",
    prefer_canvas=True
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
    style_function=style_function,
    tooltip=folium.GeoJsonTooltip(
        fields=tooltip_fields,
        aliases=tooltip_aliases,
        localize=True
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
<span style="background:#eeeeee;width:18px;height:12px;display:inline-block;border:1px solid #ccc;"></span> 0
</div>
"""

m.get_root().html.add_child(folium.Element(legend_html))

st_folium(
    m,
    width=1300,
    height=720
)


# ======================
# 表格展示
# ======================

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

safe_name = str(selected_value).replace("/", "_").replace("\\", "_").replace(" ", "_")

st.download_button(
    label="下载当前筛选结果 CSV",
    data=download_csv,
    file_name=f"{selected_field}_{safe_name}_筛选结果.csv",
    mime="text/csv"
)
