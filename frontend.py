import streamlit as st
import openai
from dotenv import dotenv_values
import numpy as np

config = dotenv_values()


st.title("ChatGPT-like clone")

openai.api_key = config["OPENAI_API_KEY"]


with st.sidebar:
    new_chat = st.button(
        ":heavy_plus_sign: New chat", key="new_chat", use_container_width=True
    )
    st.sidebar.button(":exclamation: Stop generating", use_container_width=True)

    st.caption("Today")
    st.button("Enter some text", key="1", use_container_width=True)
    st.button("Enter some text", key="2", use_container_width=True)
    st.button("Enter some text", key="3", use_container_width=True)
    st.caption("Yesterday")
    st.button("Enter some text", key="5", use_container_width=True)
    st.button("Enter some text", key="6", use_container_width=True)
    st.button("Enter some text", key="7", use_container_width=True)
    st.caption("7 days")
    st.button("Enter some text", key="8", use_container_width=True)
    st.button("Enter some text", key="9", use_container_width=True)
    st.button("Enter some text", key="10", use_container_width=True)
    st.button("Enter some text", key="11", use_container_width=True)
    st.button("Enter some text", key="12", use_container_width=True)
    st.button("Enter some text", key="13", use_container_width=True)
    st.button("Enter some text", key="14", use_container_width=True)
    st.button("Enter some text", key="15", use_container_width=True)
    st.button("Enter some text", key="16", use_container_width=True)
    st.button("Enter some text", key="17", use_container_width=True)


if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        stop_button = st.button("Stop Generating")
        full_response = ""
        for response in openai.ChatCompletion.create(
            model=st.session_state["openai_model"],
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        ):
            full_response += response.choices[0].delta.get("content", "")
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# clear_button = clear_button_slot.button("Clear Conversation", key="clear")

# import streamlit as st
# with st.expander('an expander'):
#     if st.button('a button'):
#         with st.spinner('a spinner'):
#             # do something

# https://github.com/microsoft/az-oai-chatgpt-streamlit-harness


# with st.chat_message("assistant"):
#     st.write("Hello human")
#     st.bar_chart(np.random.randn(30, 3))