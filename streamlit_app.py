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

# Initialize global result storage with various categories
global_result = {
    "Full Capping": [],
    "Other": []  # This will store both the ticket/ID and the message content
}

# Function to process the text file input
def process_messages_from_content(file_content, issue_patterns, ticket_order_pattern, id_pattern):
    global global_result

    # Split content into individual messages based on the pattern of new blocks
    messages = re.split(r'\n(?=\[\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2} (?:am|pm)\])|\[\d{2}:\d{2}, \d{1,2}/\d{1,2}/\d{4}\]', file_content)
    
    # Result storage
    result = {
        "Full Capping": [],
        "Other": []
    }

    # Track tickets and IDs already added
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

                # For "Full Capping," capture only IDs
                if issue == "Full Capping":
                    if ids:
                        result[issue].extend(i for i in ids if i not in added_ids)
                        added_ids.update(ids)
                else:
                    # For other issues, capture both tickets and IDs
                    if tickets:
                        result[issue].extend(t for t in tickets if t not in added_tickets)
                        added_tickets.update(tickets)
                    if ids:
                        result[issue].extend(i for i in ids if i not in added_ids)
                        added_ids.update(ids)
                
                found_issue = True
                break  # Stop once a matching issue is found

        # If no specific issue is found, categorize under "Other" and store both the message and ticket/ID
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

# Streamlit UI
st.title("Message Processor for Text Files")

# Upload text files
uploaded_files = st.file_uploader("Upload text files", accept_multiple_files=True, type="txt")

# Define issue patterns (expandable in the future)
issue_patterns = {
    "Full Capping": r'\bfull cap[p]?ing\b|\bbukan dlm id ui\b|\bcap(p)?ing full\b|\b(tidak|x) as(s)?ign pd ru\b|\bfull slot\b|\btidak boleh ass(i)?gn pada team\b|\bslot id( ni)? x( ?)lepas\b|\bn(a)?k slot id\b|\bfull dalam list\b|\bcapping penuh\b|\bid.*full t(a)?p(i)? d(a)?l(a)?m list tmf.*ada \d order\b|\bui.*(tak|x) n(a)?mp(a)?k (d)?(e)?kat dia\b|\bui kata (x|tak) n(a)?mp(a)?k o(r)?d(e)?r\b|\bbukan ui pnya\b|\bslot balik p(a)?d(a)? (team|ru|ra|ui)\b|\border return(ed)? s(e)?m(a)?l(a)?m.*m(a)?s(i)?h ada d(a)?l(a)?m tm( )?f(orce)?.*ru\b|\bui inf(o)?(r)?m (t(a)?k|x) n(a)?mp(a)?k order\b|\bini order m(e)?m(a)?(n)?g ru p(u)?(n)?ya\b|\b(belum ada|xada|teda|tiada) id mana(2)? ru\b|\b(tidak|tak|x) d(a)?p(a)?t( )?(nak)?assign.*(ru|team)\b|\bord(er)?.*tak( )?d(a)?p(a)?t.*assign p(a)?d(a)? (team|ru)\b|\bbukan order (ui|team)\b|\bid( dah)?( )?full.*d(a)?l(a)?m tm( )?f(orce)?.*hanya ada [1-9] order\b|\b(takleh|xboleh|xleh) slot id\b|\bin( )?hand ui.*assign( ke)? ui\b|\bmasih full/7 order\b|\bin hand.*yg nak assign\b|\bid.*ada \d order t(a)?p(i)? id.*full\b|\bfull.*t(a)?p(i)?.*tm( )?f(orce)? ada \d order\b|\bo(r)?der (d(i)?|p(a)?d(a)?)( id)? ui\b|\bid ni.*(x|tak|tidak)( )?l(e)?p(a)?s.*slot order( lain)?\b|\bd(a)?h full (x|tak)( )?l(e)?p(a)?s slot( order)?\b|\border# ada dlm inhand.*order# nak assign ke ui\b|\btmf saya detect baru \d order\b|\border.*perlu.*masuk.*t(a)?p(i)? (x|tak)( )?(boleh|leh)( masuk)?\b|\bini b(u)?k(a)?n.*ini p(e)?(r)?lu.*masuk(kan)?\b|\btmf.*detect \d order\b|\bfull cappinng\b|\bcapping.*(full|p(e)?n(u)?h)\b'
}

# Ticket/order and ID patterns
ticket_order_pattern = r'\b1-\d{9,11}\b|\bT-\d{9}\b|\bt-\d{10}\b|\b1-[a-z0-9]{7}\b|\binc\b'
id_pattern = r'\bQ\d{6}\b|\bq\d{6}\b|\bTM\d{5}\b|\btm\d{5}\b'

# Process the uploaded files
if st.button("Process Files"):
    if uploaded_files:
        for uploaded_file in uploaded_files:
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

