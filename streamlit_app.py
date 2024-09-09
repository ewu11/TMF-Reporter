import streamlit as st
import re

# Inject custom CSS to change the cursor for disabled text areas
st.markdown("""
    <style>
    textarea[disabled] {
        cursor: default !important;
    }
    </style>
    """, unsafe_allow_html=True)

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

# Function to process the text file input and categorize issues
def process_messages_from_content(file_content, issue_patterns, ticket_order_pattern, id_pattern):
    messages = re.split(r'\n(?=\[\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2} (?:am|pm)\])|\[\d{2}:\d{2}, \d{1,2}/\d{1,2}/\d{4}\]', file_content)
    
    result = {
        "Full Capping": [],
        "Other": []
    }

    added_tickets = set()
    added_ids = set()

    for message in messages:
        found_issue = False

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

# Section 1: Text File Processor with Regex Filtering
st.header("1. Text File Processor with Regex Filtering")
base_names_input = st.text_input("Enter base names (comma-separated) -- These names are to be removed after filtering", "Hartina, Tina, Normah, Pom, Afizan, Pijan, Ariff, Dheffirdaus, Dhef, Hazrina, Rina, Nurul, Huda, Zazarida, Zaza, Eliasaph Wan, Wan, ] : ")
base_names = [name.strip() for name in base_names_input.split(",")]

uploaded_raw_files = st.file_uploader("Upload the file(s) containing the raw text messages", accept_multiple_files=True, type="txt")

if 'cleaned_texts' not in st.session_state:
    st.session_state.cleaned_texts = {}

if st.button("Clean text messages"):
    if uploaded_raw_files:
        input_files = {file.name: file for file in uploaded_raw_files}
        results = filter_messages(input_files, base_names)

        for file_name, filtered_text in results.items():
            st.session_state.cleaned_texts[file_name] = filtered_text
            st.subheader(f"Filtered content for {file_name}:")
            st.text_area(f"Processed Content: {file_name}", filtered_text, height=300, disabled=True)

        for file_name, filtered_text in results.items():
            st.download_button(label=f"Download cleaned {file_name}", data=filtered_text, file_name=f"cleaned_{file_name}", mime="text/plain")
    else:
        st.warning("Please upload at least one text file to process.")

# Section 2: Message Processor for Text Files
st.header("2. Message Processor for Text Files")
uploaded_filtered_files = st.file_uploader("Upload the file(s) containing the filtered text messages", accept_multiple_files=True, type="txt", key="filtered_uploader")

issue_patterns = {"Full Capping": r'\bfull cap[p]?ing\b'}
ticket_order_pattern = r'\b1-\d{9,11}\b|\bT-\d{9}\b|\bt-\d{10}\b|\b1-[a-z0-9]{7}\b|\binc\b'
id_pattern = r'\bQ\d{6}\b|\bq\d{6}\b|\bTM\d{5}\b|\btm\d{5}\b'

data_source = st.radio("Choose the source for filtering:", ('Use cleaned text from Step 1', 'Upload a new filtered file(s)'))
combine_output = st.checkbox("Combine output from all files into one view")

# Ensure the correct structure of result before formatting individual results
if st.button("Filter text messages"):
    combined_result_by_issue = {"Full Capping": [], "Other": []}

    if data_source == 'Use cleaned text from Step 1':
        if st.session_state.cleaned_texts:
            for file_name, cleaned_text in st.session_state.cleaned_texts.items():
                # Process messages and get structured result
                result = process_messages_from_content(cleaned_text, issue_patterns, ticket_order_pattern, id_pattern)

                if combine_output:
                    for issue, data in result.items():
                        combined_result_by_issue[issue].extend(data)
                else:
                    # Ensure result has correct structure before passing to format function
                    if result and isinstance(result, dict):  # Check result is not None and is a dictionary
                        result_text = format_individual_results(result)
                        st.text_area(f"Results for {file_name}", value=result_text, height=300, disabled=True)
                        st.download_button(label="Download Results", data=result_text, file_name=f"processed_{file_name}", mime="text/plain")
                    else:
                        st.warning(f"Result structure is invalid for {file_name}.")
        else:
            st.warning("No cleaned text available from Step 1. Please process the files first.")

    elif data_source == 'Upload a new filtered file':
        if uploaded_filtered_files:
            for uploaded_file in uploaded_filtered_files:
                file_content = uploaded_file.read().decode("utf-8")
                result = process_messages_from_content(file_content, issue_patterns, ticket_order_pattern, id_pattern)

                if combine_output:
                    for issue, data in result.items():
                        combined_result_by_issue[issue].extend(data)
                else:
                    result_text = format_individual_results(result)
                    st.text_area(f"Results for {uploaded_file.name}", value=result_text, height=300, disabled=True)
                    st.download_button(label="Download Results", data=result_text, file_name=f"processed_{uploaded_file.name}", mime="text/plain")
        else:
            st.warning("Please upload at least one text file to process.")
    
    # Show combined output if requested
    if combine_output:
        combined_text = format_combined_results(combined_result_by_issue)
        st.subheader("Combined cleaned text")
        st.text_area("Combined Processed Content", value=combined_text, height=400, disabled=True)
        st.download_button(label="Download Combined Results", data=combined_text, file_name="combined_processed_result.txt", mime="text/plain")

# Function to format individual results
# Function to format individual results (per file)
def format_individual_results(result):
    individual_text = []
    
    for issue, data in result.items():
        individual_text.append(f"Issue: {issue}")
        
        if issue == "Other":
            # For "Other" issue, show each ticket/ID along with its corresponding message
            for number, message in data:
                individual_text.append(f"Ticket/ID: {number}\nMessage: {message}")
        else:
            # For other issues, list the IDs or ticket numbers
            individual_text.extend([f"{number}" for number in data])
        
        individual_text.append("\n")  # Add a new line after each issue block
    
    return "\n".join(individual_text)

# Function to format combined results grouped by issue
# Function to format combined results grouped by issue
def format_combined_results(combined_result_by_issue):
    combined_text = []
    
    for issue, data in combined_result_by_issue.items():
        combined_text.append(f"Issue: {issue}")
        
        if issue == "Other":
            # For "Other" issue, show each ticket/ID along with its corresponding message
            for number, message in data:
                combined_text.append(f"Ticket/ID: {number}\nMessage: {message}")
        else:
            # For issues like "Full Capping", just list the IDs or ticket numbers
            combined_text.extend([f"{number}" for number in data])
        
        combined_text.append("\n")  # Add a new line after each issue
        
    return "\n".join(combined_text)

