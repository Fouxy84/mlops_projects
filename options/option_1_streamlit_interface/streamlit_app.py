import os

import requests
import streamlit as st


GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")

st.set_page_config(page_title="MLOps Demo UI", layout="wide")
st.title("MLOps Demo Interface")
st.caption("Optional Streamlit layer on top of the current gateway")


def gateway_post(endpoint: str, payload=None, form_data=None):
    url = f"{GATEWAY_URL}{endpoint}"
    if form_data is not None:
        return requests.post(url, data=form_data, timeout=30)
    return requests.post(url, json=payload, timeout=30)


def gateway_get(endpoint: str):
    return requests.get(f"{GATEWAY_URL}{endpoint}", timeout=30)


with st.sidebar:
    st.subheader("Login")
    username = st.text_input("Username", value="admin")
    password = st.text_input("Password", value="admin", type="password")
    if st.button("Login", use_container_width=True):
        response = gateway_post("/login", form_data={"username": username, "password": password})
        if response.ok:
            st.success(response.json()["message"])
        else:
            st.error(response.text)

    if st.button("Logout", use_container_width=True):
        response = gateway_post("/logout")
        if response.ok:
            st.success("Logged out")
        else:
            st.warning(response.text)


col1, col2 = st.columns(2)
with col1:
    if st.button("Gateway health", use_container_width=True):
        st.json(gateway_get("/health").json())
with col2:
    if st.button("System info", use_container_width=True):
        st.json(gateway_get("/info").json())


tab_text, tab_image, tab_multi = st.tabs(["Text", "Image", "Multimodal"])

with tab_text:
    text_value = st.text_area("Product text", "le tableau de chat est tres joli")
    if st.button("Predict text"):
        response = gateway_post("/predict/svm", payload={"text": text_value})
        st.json(response.json())

with tab_image:
    image_path = st.text_input("Image path", "image_528113_product_923222.jpg")
    if st.button("Predict image"):
        response = gateway_post("/predict/cnn", payload={"image_path": image_path})
        st.json(response.json())

with tab_multi:
    multi_text = st.text_area("Multimodal text", "le tableau de chat est tres joli", key="multi_text")
    multi_image = st.text_input("Multimodal image path", "image_528113_product_923222.jpg", key="multi_image")
    if st.button("Predict multimodal"):
        response = gateway_post("/predict/multimodal", payload={"text": multi_text, "image_path": multi_image})
        st.json(response.json())
