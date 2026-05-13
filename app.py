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


# ======================
# 数据路径
# ======================

GEOJSON_PATH = "guangdong_county.geojson"
CSV_PATH = "dialect_records.csv"


# ======================
# 读取数据
# ======================

@st.cache_data
def load_geojson():
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_records():
    return pd.read_csv(CSV_PATH, encoding="utf-8-sig")


geojson_data = load_geojson()
records = load_records()


# ======================
# 字段识别
# ======================

def find_col(columns, candidates):
    for c in candidates:
        if c in columns:
            return c
    return None


key_col = find_col(
    records.columns,
    ["市县匹配键", "match_key", "匹配键"]
)

id_col = find_col(
    records.columns,
    ["編號", "编号", "ID", "id"]
)

city_col = find_col(
    records.columns,
    ["市_表格", "市_边界", "市", "市名"]
)

county_col = find_col(
    records.columns,
    ["县_表格", "县_边界", "县", "县名", "区县"]
)

if key_col is None:
    st.error("CSV 中没有找到“市县匹配键”字段。")
    st.stop()

if id_col is None:
    id_col = records.columns[0]


feature_fields = [
    "語音特徵大類",
    "語音特徵小類及編碼",
    "標準化語音特徵",
    "方言類型判斷",
    "區域傾向",
    "現代方言區參照",
    "古今關係",
    "證據等級",
    "语音特征大类",
    "语音特征小类及编码",
    "标准化语音特征",
    "方言类型判断",
    "区域倾向",
    "现代方言区参照",
    "古今关系",
    "证据等级"
]

feature_fields = [c for c in feature_fields if c in records.columns]

if len(feature_fields) == 0:
    st.error("CSV 中没有找到可筛选的特征字段。")
    st.stop()


# ======================
# 侧边栏筛选
# ======================

st.sidebar.header("筛选条件")

selected_field = st.sidebar.selectbox(
    "选择特征字段",
    feature_fields
)

values = (
    records[selected_field]
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

selected_value = st.sidebar.selectbox(
    "选择具体特征",
    feature_values
)

match_mode = st.sidebar.radio(
    "匹配方式",
    ["精确匹配", "包含匹配"],
    horizontal=True
)

if city_col is not None:
    city_values = (
        records[city_col]
        .dropna()
        .astype(str)
        .str.strip()
    )
    city_values = sorted(city_values[city_values != ""].unique().tolist())

    selected_city = st.sidebar.selectbox(
        "选择市",
        ["全部"] + city_values
    )
else:
    selected_city = "全部"


# ======================
# 执行筛选
# ======================

valid_records = records[records[id_col].notna()].copy()

field_text = valid_records[selected_field].fillna("").astype(str).str.strip()

if match_mode == "精确匹配":
    filtered = valid_records[field_text == selected_value].copy()
else:
    filtered = valid_records[
        field_text.str.contains(selected_value, regex=False, na=False)
    ].copy()

if city_col is not None and selected_city != "全部":
    filtered = filtered[filtered[city_col].astype(str) == selected_city]


# ======================
# 按县统计数量
# ======================

count_df = (
    filtered.groupby(key_col)
    .size()
    .reset_index(name="特征数量")
)

count_dict = dict(zip(count_df[key_col], count_df["特征数量"]))


# ======================
# 给 GeoJSON 写入数量
# ======================

for feature in geojson_data["features"]:
    props = feature["properties"]

    key = props.get("市县匹配键", "")

    # 如果 geojson 里的字段名不是市县匹配键，尝试 match_key
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
    st.metric("涉及县区数", len(count_df))

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
            "weight": 0.4,
            "fillOpacity": 0.25
        }


# ======================
# 绘制地图
# ======================

m = folium.Map(
    location=[23.4, 113.4],
    zoom_start=7,
    tiles="CartoDB positron"
)

# 自动设置 tooltip 字段
sample_props = geojson_data["features"][0]["properties"]

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
    geojson_data,
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
    height=380
)


# ======================
# 下载
# ======================

download_csv = filtered.to_csv(index=False, encoding="utf-8-sig")

safe_name = str(selected_value).replace("/", "_").replace("\\", "_").replace(" ", "_")

st.download_button(
    label="下载当前筛选结果 CSV",
    data=download_csv,
    file_name=f"{selected_field}_{safe_name}_筛选结果.csv",
    mime="text/csv"
)
