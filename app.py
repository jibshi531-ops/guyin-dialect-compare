import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# 示例数据：添加多个省份
data = {
    "编号": ["001", "002", "003", "004", "005", "006", "007", "008"],
    "原地名": ["番禺", "南海", "东莞", "惠州", "福州", "厦门", "成都", "绵阳"],
    "今地": ["番禺区", "南海区", "东莞市", "惠州市", "福州市", "厦门市", "成都市", "绵阳市"],
    "市": ["广州", "佛山", "东莞", "惠州", "福州", "厦门", "成都", "绵阳"],
    "县": ["番禺", "南海", "东莞", "惠州", "鼓楼", "思明", "青白江", "涪城"],
    "省份": ["广东", "广东", "广东", "广东", "福建", "福建", "四川", "四川"],
    "语音特征": ["声母变化", "韵母变化", "声调变化", "音变规律", "音变规律", "声母变化", "韵母变化", "音变规律"],
    "备注": ["备注1", "备注2", "备注3", "备注4", "备注5", "备注6", "备注7", "备注8"]
}

df = pd.DataFrame(data)

# 省份选择
province_list = sorted(df["省份"].unique())
province_filter = st.sidebar.selectbox("选择省份", ["全部"] + province_list)

# 根据省份筛选市和县
if province_filter != "全部":
    df_filtered = df[df["省份"] == province_filter]
else:
    df_filtered = df

# 市选择
city_list = sorted(df_filtered["市"].unique())
city_filter = st.sidebar.selectbox("选择市", ["全部"] + city_list)

# 根据市筛选县
if city_filter != "全部":
    df_filtered = df_filtered[df_filtered["市"] == city_filter]

county_list = sorted(df_filtered["县"].unique())
county_filter = st.sidebar.selectbox("选择县", ["全部"] + county_list)

# 语音特征筛选
feature_list = sorted(df_filtered["语音特征"].unique())
feature_filter = st.sidebar.selectbox("选择语音特征", ["全部"] + feature_list)

# 搜索框
search_term = st.text_input("请输入检索关键词（如：南海）")

# 根据输入的关键词进行检索
if search_term:
    filtered = df_filtered[df_filtered["原地名"].str.contains(search_term, na=False) |
                           df_filtered["今地"].str.contains(search_term, na=False) |
                           df_filtered["语音特征"].str.contains(search_term, na=False) |
                           df_filtered["备注"].str.contains(search_term, na=False)]
else:
    filtered = df_filtered

# 显示检索到的记录
st.subheader(f"共找到 {len(filtered)} 条记录")
st.dataframe(filtered)

# 创建地图
coordinates = {
    "番禺": [23.116, 113.350],
    "南海": [23.013, 113.148],
    "东莞": [23.020, 113.751],
    "惠州": [23.113, 114.410],
    "福州": [26.075, 119.296],
    "厦门": [24.479, 118.089],
    "成都": [30.572, 104.066],
    "绵阳": [31.464, 104.741]
}

m = folium.Map(location=[23.3, 113.3], zoom_start=8, tiles="CartoDB positron")

# 根据筛选结果高亮地图上的县
for county, coord in coordinates.items():
    if county in filtered["县"].values:
        folium.CircleMarker(
            location=coord,
            radius=12,
            popup=f"{county} 方言记录",
            color="red",
            fill=True,
            fill_color="red"
        ).add_to(m)

# 展示地图
st_folium(m, width=1200, height=700)
