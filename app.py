import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd

st.title("Visualisation géographique des entités extraites")

data = [
    {"lieu": "Rabat", "lat": 34.0209, "lon": -6.8416, "info": "Conférence sur l'IA"},
    {"lieu": "Casablanca", "lat": 33.5731, "lon": -7.5898, "info": "Siège d'une entreprise"},
    {"lieu": "Fès", "lat": 34.0331, "lon": -5.0003, "info": "Festival culturel"},
]

df = pd.DataFrame(data)

map = folium.Map(location=[33.9716, -6.8498], zoom_start=6)

for _, row in df.iterrows():
    folium.Marker(
        location=[row["lat"], row["lon"]],
        popup=row["info"],
        tooltip=row["lieu"],
        icon=folium.Icon(color='blue')
    ).add_to(map)

st.subheader("Carte des entités nommées extraites des articles")
folium_static(map)
