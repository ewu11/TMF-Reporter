import streamlit as st
import re
import os
from io import StringIO
from pathlib import Path

# Function to process the uploaded files
def filter_messages(input_files, base_names):
    timestamp_pattern = re.compile(r'\[\d{2}:\d{2}, \d{1,2}/\d{1,2}/\d{4}\]|^\[\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2} [APM]{2}]')
    name_patterns = [re.compile(rf'\b{re.escape(name)}\b', re.IGNORECASE) for name in base_names]

    results = {}
    
    for file_name, file_data in input_files.items():
        file_content = file_data.getvalue().decode("utf-8")
        lines = file_content.splitlines()

        filtered_lines = []
        skip_block = False
        current_message = []

        for line in lines:
            if timestamp_pattern.match(line):
                if current_message:
                    filtered_lines.append(' '.join(current_message).strip().lower())
                    current_message = []

                if any(pattern.search(line) for pattern in name_patterns):
                    skip_block = True
                else:
                    skip_block = False

            if not skip_block:
                current_message.append(line.strip().lower())

        if not skip_block and current_message:
            filtered_lines.append(' '.join(current_message).strip().lower())

        filtered_text = '\n\n'.join(filtered_lines)
        results[file_name] = filtered_text

    return results

# Streamlit app
st.title("Text File Processor with Regex Filtering")

# Input section for base names
base_names_input = st.text_input(
    "Enter base names (comma-separated)", 
    "Hartina, Tina, Normah, Pom, Afizan, Pijan, Ariff, Dheffirdaus, Dhef, Hazrina, Rina, Nurul, Huda, Zazarida, Zaza, Eliasaph Wan, Wan"
)
base_names = [name.strip() for name in base_names_input.split(",")]

# File upload
uploaded_files = st.file_uploader("Upload your text files", accept_multiple_files=True, type="txt")

if uploaded_files:
    # Store the uploaded files in a dictionary with file name as key and file content as value
    input_files = {file.name: file for file in uploaded_files}
    
    if st.button("Process Files"):
        # Process the uploaded files with the provided base names
        results = filter_messages(input_files, base_names)

        # Display the results for each file
        for file_name, filtered_text in results.items():
            st.subheader(f"Filtered content for {file_name}:")
            st.text_area(f"Processed Content: {file_name}", filtered_text, height=300)

        # Option to download the cleaned files
        for file_name, filtered_text in results.items():
            st.download_button(
                label=f"Download cleaned {file_name}",
                data=filtered_text,
                file_name=f"cleaned_{file_name}",
                mime="text/plain"
            )
