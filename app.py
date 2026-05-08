
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# 设置页面
st.set_page_config(layout="wide")
st.title("广东方言记录地图展示")

# 示例数据
data = {
    "编号": ["001", "002", "003", "004"],
    "原地名": ["番禺", "南海", "东莞", "惠州"],
    "今地": ["番禺区", "南海区", "东莞市", "惠州市"],
    "市": ["广州", "佛山", "东莞", "惠州"],
    "县": ["番禺", "南海", "东莞", "惠州"],
    "语音特征": ["声母变化", "韵母变化", "声调变化", "音变规律"],
    "备注": ["备注1", "备注2", "备注3", "备注4"]
}

df = pd.DataFrame(data)

# 假设每个县的坐标
coordinates = {
    "番禺": [23.116, 113.350],
    "南海": [23.013, 113.148],
    "东莞": [23.020, 113.751],
    "惠州": [23.113, 114.410]
}

# 地图初始化
m = folium.Map(location=[23.3, 113.3], zoom_start=8, tiles="CartoDB positron")

# 添加虚拟数据点到地图
for county, coord in coordinates.items():
    folium.CircleMarker(
        location=coord,
        radius=10,
        popup=f"{county} 方言记录",
        color="blue",
        fill=True,
        fill_color="blue"
    ).add_to(m)

# 在侧边栏添加搜索框
search_term = st.text_input("请输入关键词（如：南海）进行检索", "")

# 根据搜索关键词过滤数据
filtered = df[df["原地名"].str.contains(search_term, na=False)]

# 高亮地图区域
if search_term:
    # 在地图中高亮与关键词匹配的区域
    for county, coord in coordinates.items():
        if search_term in county:
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

# 显示检索结果
st.subheader(f"共找到 {len(filtered)} 条记录")
st.dataframe(filtered)
