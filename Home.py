'''
import streamlit as st
from openai import OpenAI

# Show title and description.
st.title("💬 Chatbot")
st.write(
    "This is a simple chatbot that uses OpenAI's GPT-3.5 model to generate responses. "
    "To use this app, you need to provide an OpenAI API key, which you can get [here](https://platform.openai.com/account/api-keys). "
    "You can also learn how to build this app step by step by [following our tutorial](https://docs.streamlit.io/develop/tutorials/llms/build-conversational-apps)."
)

# Ask user for their OpenAI API key via `st.text_input`.
# Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
# via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management
openai_api_key = st.text_input("OpenAI API Key", type="password")
if not openai_api_key:
    st.info("Please add your OpenAI API key to continue.", icon="🗝️")
else:

    # Create an OpenAI client.
    client = OpenAI(api_key=openai_api_key)

    # Create a session state variable to store the chat messages. This ensures that the
    # messages persist across reruns.
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display the existing chat messages via `st.chat_message`.
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Create a chat input field to allow the user to enter a message. This will display
    # automatically at the bottom of the page.
    if prompt := st.chat_input("What is up?"):

        # Store and display the current prompt.
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate a response using the OpenAI API.
        stream = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        )

        # Stream the response to the chat using `st.write_stream`, then store it in 
        # session state.
        with st.chat_message("assistant"):
            response = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})
'''
import streamlit as st
import prompts
import re
from openai import OpenAI
from model_utils import call_chat_model, call_image_model
import os

client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

st.set_page_config(layout="wide")

# Header
title = "myfitnessagent"
logo_path = "logo.png"

col1, col2 = st.columns([1, 10])

with col1:
    st.image(logo_path, width=100)

# Display the title in the second column
with col2:
    st.title(title)

# Initialize internal and external chat history
if "internal_messages" not in st.session_state:
    st.session_state.internal_messages = [{
        "role": "system",
        "content": prompts.system_prompt
    }]

if "external_messages" not in st.session_state:
    st.session_state.external_messages = []

# Initialize trackers
if "nutrition_tracker" not in st.session_state:
    st.session_state.nutrition_tracker = ""
if "training_tracker" not in st.session_state:
    st.session_state.training_tracker = ""


# Function to extract tracker tags from response
def parse_messages(text):
    message_pattern = r"<message>(.*?)</message>"
    nutrition_pattern = r"<nutrition_plan>(.*?)</nutrition_plan>"
    training_pattern = r"<training_plan>(.*?)</training_plan>"

    message = re.findall(message_pattern, text, re.DOTALL)
    nutrition = re.findall(nutrition_pattern, text, re.DOTALL)
    training = re.findall(training_pattern, text, re.DOTALL)

    return message[0] if message else "", nutrition[
        0] if nutrition else "", training[0] if training else ""


# Create two columns
col1, col2 = st.columns([1, 1])

with col1:
    st.header("Chat with coach")

    # Create a container for chat messages
    chat_container = st.container(height=400)

    # Create a container for the input box
    input_container = st.container()

    # Display chat messages from history on app rerun
    with chat_container:
        for message in st.session_state.external_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Accept user input
    with input_container:
        upload_col1, upload_col2 = st.columns([4, 1])

        with upload_col1:
            # image upload and processing
            uploaded_file = st.file_uploader("Choose an image...",
                                             type=["jpg", "png"],
                                             label_visibility="collapsed")

            if uploaded_file is not None:
                with upload_col2:
                    if st.button("Process Image"):
                        st.write('Processing image...')
                        st.session_state.internal_messages.append({
                            "role":
                            "user",
                            "content":
                            "Uploaded a photo of food"
                        })
                        st.session_state.external_messages.append({
                            "role":
                            "user",
                            "content":
                            "Uploaded a photo of food"
                        })

                        message, nutrition_tracker = call_image_model(
                            client, uploaded_file)

                        if nutrition_tracker:
                            st.session_state.nutrition_tracker = nutrition_tracker

                        st.session_state.internal_messages.append({
                            "role":
                            "assistant",
                            "content":
                            message
                        })
                        st.session_state.external_messages.append({
                            "role":
                            "assistant",
                            "content":
                            message
                        })

                        st.rerun()

        if prompt := st.chat_input("Enter text..."):
            # Add user message to chat history
            st.session_state.internal_messages.append({
                "role": "user",
                "content": prompt
            })
            st.session_state.external_messages.append({
                "role": "user",
                "content": prompt
            })

            with chat_container:
                # Display user message in chat message container
                with st.chat_message("user"):
                    st.markdown(prompt)

            # with chat_container:
                with st.chat_message("assistant"):
                    messages = [{
                        "role": m["role"],
                        "content": m["content"]
                    } for m in st.session_state.internal_messages]

                    # call the chat model to generate a completion
                    completion = call_chat_model(client, messages)

                    response = completion.choices[0].message.content

                    print('***RAW OUTPUTS***')
                    print(response)

                    # add raw message to internal messages
                    st.session_state.internal_messages.append({
                        "role":
                        "assistant",
                        "content":
                        response
                    })

                    message, nutrition_tracker, training_tracker = parse_messages(
                        response)

                    # add parsed message to external messages
                    st.session_state.external_messages.append({
                        "role":
                        "assistant",
                        "content":
                        message
                    })

                    # Update session state trackers
                    if nutrition_tracker:
                        st.session_state.nutrition_tracker = nutrition_tracker
                    if training_tracker:
                        st.session_state.training_tracker = training_tracker
                    st.rerun()

with col2:
    st.header("Training and Nutrition Log")
    training_log_container = st.container(height=260)
    with training_log_container:
        st.write("### Training Plan")
        if len(st.session_state.training_tracker) > 0:
            st.write(st.session_state.training_tracker)

    nutrition_log_container = st.container(height=260)
    with nutrition_log_container:
        st.write("### Nutrition Plan")
        if len(st.session_state.nutrition_tracker) > 0:
            st.write(st.session_state.nutrition_tracker)
