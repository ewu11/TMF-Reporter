import streamlit as st
import re

# Function to process the uploaded files for text file processing with regex filtering
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


# Function to process the text file input
def process_messages_from_content(file_content, issue_patterns, ticket_order_pattern, id_pattern):
    # Split content into individual messages based on the pattern of new blocks
    messages = re.split(r'\n(?=\[\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2} (?:am|pm)\])|\[\d{2}:\d{2}, \d{1,2}/\d{1,2}/\d{4}\]', file_content)
    
    result = {
        "Full Capping": [],
        "Other": []
    }

    added_tickets = set()
    added_ids = set()

    # Process each message block
    for message in messages:
        found_issue = False

        # Check for issues and collect tickets/IDs
        for issue, pattern in issue_patterns.items():
            if re.search(pattern, message, re.IGNORECASE):
                tickets = re.findall(ticket_order_pattern, message)
                ids = re.findall(id_pattern, message)

                if issue == "Full Capping":
                    if ids:
                        result[issue].extend(i for i in ids if i not in added_ids)
                        added_ids.update(ids)
                else:
                    if tickets:
                        result[issue].extend(t for t in tickets if t not in added_tickets)
                        added_tickets.update(tickets)
                    if ids:
                        result[issue].extend(i for i in ids if i not in added_ids)
                        added_ids.update(ids)
                
                found_issue = True
                break

        if not found_issue:
            tickets = re.findall(ticket_order_pattern, message)
            ids = re.findall(id_pattern, message)
            if tickets or ids:
                if tickets:
                    result["Other"].extend([(t, message) for t in tickets if t not in added_tickets])
                    added_tickets.update(tickets)
                if ids:
                    result["Other"].extend([(i, message) for i in ids if i not in added_ids])
                    added_ids.update(ids)

    return result


# Streamlit app
st.title("TMF Daily Report Generator")

# 1. Section for "Text File Processor with Regex Filtering"
st.header("1. Text File Processor with Regex Filtering")

# Input section for base names
base_names_input = st.text_input(
    "Enter base names (comma-separated) -- These names are to be removed after filteration", 
    "Hartina, Tina, Normah, Pom, Afizan, Pijan, Ariff, Dheffirdaus, Dhef, Hazrina, Rina, Nurul, Huda, Zazarida, Zaza, Eliasaph Wan, Wan, ] : "
)
base_names = [name.strip() for name in base_names_input.split(",")]

# File upload for raw text files
uploaded_raw_files = st.file_uploader("Upload the file(s) containing the raw text messages", accept_multiple_files=True, type="txt")

# Session state to store cleaned text
if 'cleaned_texts' not in st.session_state:
    st.session_state.cleaned_texts = {}

# Button for processing raw files with regex filtering
if st.button("Clean text messages"):
    if uploaded_raw_files:
        input_files = {file.name: file for file in uploaded_raw_files}
        
        # Process the uploaded files with the provided base names
        results = filter_messages(input_files, base_names)

        # Display and store the cleaned texts in session state
        for file_name, filtered_text in results.items():
            st.session_state.cleaned_texts[file_name] = filtered_text
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


# 2. Section for "Message Processor for Text Files"
st.header("2. Message Processor for Text Files")

# File upload for filtered text messages
uploaded_filtered_files = st.file_uploader("Upload the file(s) containing the filtered text messages", accept_multiple_files=True, type="txt", key="filtered_uploader")

# Define issue patterns
issue_patterns = {
    "Full Capping": r'\bfull cap[p]?ing\b'
}

# Ticket/order and ID patterns
ticket_order_pattern = r'\b1-\d{9,11}\b|\bT-\d{9}\b|\bt-\d{10}\b|\b1-[a-z0-9]{7}\b|\binc\b'
id_pattern = r'\bQ\d{6}\b|\bq\d{6}\b|\bTM\d{5}\b|\btm\d{5}\b'

# Dropdown to select between cleaned text from previous step or uploaded file
data_source = st.radio(
    "Choose the source for filtering:",
    ('Use cleaned text from Step 1', 'Upload a new filtered file(s)')
)

# Button for processing filtered text messages
if st.button("Filter text messages"):
    # If using cleaned text from Step 1
    if data_source == 'Use cleaned text from Step 1':
        if st.session_state.cleaned_texts:
            for file_name, cleaned_text in st.session_state.cleaned_texts.items():
                st.subheader(f"Processing cleaned text from {file_name}")
                
                # Process the file content
                result = process_messages_from_content(cleaned_text, issue_patterns, ticket_order_pattern, id_pattern)

                # Display the result
                for issue, data in result.items():
                    st.subheader(f"Issue: {issue}")
                    if issue == "Other":
                        for number, message in data:
                            st.write(f"{number}: {message}")
                    else:
                        for number in data:
                            st.write(number)

                # Option to download the result as a text file
                result_text = "\n".join([f"{issue}: {', '.join([str(item) for item in data])}" for issue, data in result.items()])
                st.download_button(
                    label="Download Results",
                    data=result_text,
                    file_name=f"processed_{file_name}",
                    mime="text/plain"
                )
        else:
            st.warning("No cleaned text available from Step 1. Please process the files first.")

    # If using a newly uploaded filtered file
    elif data_source == 'Upload a new filtered file':
        if uploaded_filtered_files:
            for uploaded_file in uploaded_filtered_files:
                file_content = uploaded_file.read().decode("utf-8")

                # Process the file content
                result = process_messages_from_content(file_content, issue_patterns, ticket_order_pattern, id_pattern)

                # Display the result
                for issue, data in result.items():
                    st.subheader(f"Issue: {issue}")
                    if issue == "Other":
                        for number, message in data:
                            st.write(f"{number}: {message}")
                    else:
                        for number in data:
                            st.write(number)

                # Option to download the result as a text file
                result_text = "\n".join([f"{issue}: {', '.join([str(item) for item in data])}" for issue, data in result.items()])
                st.download_button(
                    label="Download Results",
                    data=result_text,
                    file_name=f"processed_{uploaded_file.name}",
                    mime="text/plain"
                )
        else:
            st.warning("Please upload at least one text file to process.")
