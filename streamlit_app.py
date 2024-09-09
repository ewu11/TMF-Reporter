import streamlit as st
import re
import codecs
import chardet

# Inject custom CSS to change the cursor for disabled text areas
st.markdown("""
    <style>
    textarea[disabled] {
        cursor: default !important;
    }
    </style>
    """, unsafe_allow_html=True)


# Function to detect file encoding using chardet and convert it to UTF-8
def detect_and_convert_to_utf8(file_data):
    raw_data = file_data.read()
    
    # Detect the encoding using chardet
    detected = chardet.detect(raw_data)
    encoding = detected['encoding']
    
    if encoding is None:
        st.warning("Could not detect the encoding. Assuming UTF-8.")
        encoding = 'utf-8'
    
    # Convert to UTF-8 using the detected encoding
    try:
        text_data = raw_data.decode(encoding)
    except UnicodeDecodeError:
        st.error(f"Failed to decode the file using detected encoding: {encoding}.")
        return None

    return text_data


# Function to process the uploaded files for text file processing with regex filtering
def filter_messages(input_files, base_names):
    timestamp_pattern = re.compile(r'\[\d{2}:\d{2}, \d{1,2}/\d{1,2}/\d{4}\]|^\[\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2} [APM]{2}]')
    name_patterns = [re.compile(rf'\b{re.escape(name)}\b', re.IGNORECASE) for name in base_names]

    results = {}
    
    for file_name, file_data in input_files.items():
        # Detect and convert to UTF-8
        file_content = detect_and_convert_to_utf8(file_data)
        if file_content is None:
            continue  # Skip file if conversion fails
        
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
        "Order Missing/ Pending Processing": [],
        "Missing Manual Assign Button": [],
        "Next Activity Not Appear": [],
        "Double @iptv": [],
        "Equipment New to Existing": [],
        "Design & Assign": [],
        "HSI No Password": [],
        "CPE New/ Existing/ Delete": [],
        "Update CPE Equipment Details": [],
        "Missing/ Update Network Details": [],
        "Update Contact Details": [],
        "Update Customer Email": [],
        "Bypass HSI": [],
        "Bypass Voice": [],
        "Bypass IPTV": [],
        "Bypass Extra Port": [],
        "Revert Order to TMF": [],
        "Release Assign To Me": [],
        "Propose Cancel to Propose Reappt/ Return": [],
        "Unsync Order": [],
        "Order Transfer SWIFT-TMF": [],
        "Duplicated Order Activity": [],
        "TT RG6/ Combo Update": [],
        "TT CPE LOV": [],
        "TT Unable to Slot/ Error 400": [],
        "TT Missing/ Update Network Details": [],
        "TT V1P": [],
        "TT CPE Not Tally with Physical": [],
        "TT Link LR Appear TMF": [],
        "TT Blank Source Skill": [],
        "ID Locking/ Unlock/ 3rd Attempt": [],
        "TT Unsync": [],
        "TT Missing": [],
        "TT Update DiagnosisCode": [],
        "TT Granite Network Info Error": [],
        "TT HSBA Reappointment": [],
        "Resource Management Issue": [],
        "Other": []  # This will store both the ticket/ID and the message content
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
    "Enter base names (comma-separated) -- These names are to be removed after filtering", 
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
            st.text_area(f"Processed Content: {file_name}", filtered_text, height=300, disabled=True)

        # Option to download the cleaned files
        for file_name, filtered_text in results.items():
            st.download_button(
                label=f"Download cleaned {file_name}",
                data=filtered_text,
                file_name=f"cleaned_{file_name}",
                mime="text/plain"
            )
    else:
        st.warning("Please upload at least one text file to process.")

# 2. Section for "Message Processor for Text Files"
st.header("2. Message Processor for Text Files")

# File upload for filtered text messages
uploaded_filtered_files = st.file_uploader("Upload the file(s) containing the filtered text messages", accept_multiple_files=True, type="txt", key="filtered_uploader")

# Define issue patterns
issue_patterns = {
    "Full Capping": r'\bfull cap[p]?ing\b|\bbukan dlm id ui\b|\bcap(p)?ing full\b|\b(tidak|x) as(s)?ign pd ru\b|\bfull slot\b|\btidak boleh ass(i)?gn pada team\b|\bslot id( ni)? x( ?)lepas\b|\bn(a)?k slot id\b|\bfull dalam list\b|\bcapping penuh\b|\bid.*full t(a)?p(i)? d(a)?l(a)?m list tmf.*ada \d order\b|\bui.*(tak|x) n(a)?mp(a)?k (d)?(e)?kat dia\b|\bui kata (x|tak) n(a)?mp(a)?k o(r)?d(e)?r\b|\bbukan ui pnya\b|\bslot balik p(a)?d(a)? (team|ru|ra|ui)\b|\border return(ed)? s(e)?m(a)?l(a)?m.*m(a)?s(i)?h ada d(a)?l(a)?m tm( )?f(orce)?.*ru\b|\bui inf(o)?(r)?m (t(a)?k|x) n(a)?mp(a)?k order\b|\bini order m(e)?m(a)?(n)?g ru p(u)?(n)?ya\b|\b(belum ada|xada|teda|tiada) id mana(2)? ru\b|\b(tidak|tak|x) d(a)?p(a)?t( )?(nak)?assign.*(ru|team)\b|\bord(er)?.*tak( )?d(a)?p(a)?t.*assign p(a)?d(a)? (team|ru)\b|\bbukan order (ui|team)\b|\bid( dah)?( )?full.*d(a)?l(a)?m tm( )?f(orce)?.*hanya ada [1-9] order\b|\b(takleh|xboleh|xleh) slot id\b|\bin( )?hand ui.*assign( ke)? ui\b|\bmasih full/7 order\b|\bin hand.*yg nak assign\b|\bid.*ada \d order t(a)?p(i)? id.*full\b|\bfull.*t(a)?p(i)?.*tm( )?f(orce)? ada \d order\b|\bo(r)?der (d(i)?|p(a)?d(a)?)( id)? ui\b|\bid ni.*(x|tak|tidak)( )?l(e)?p(a)?s.*slot order( lain)?\b|\bd(a)?h full (x|tak)( )?l(e)?p(a)?s slot( order)?\b|\border# ada dlm inhand.*order# nak assign ke ui\b|\btmf saya detect baru \d order\b|\border.*perlu.*masuk.*t(a)?p(i)? (x|tak)( )?(boleh|leh)( masuk)?\b|\bini b(u)?k(a)?n.*ini p(e)?(r)?lu.*masuk(kan)?\b|\btmf.*detect \d order\b|\bfull cappinng\b|\bcapping.*(full|p(e)?n(u)?h)\b',
    "Order Missing/ Pending Processing": r'\b(di|dlm|dalam) (oal|order(?: activity)?(?: list)?)\b|\btmf (?:tak (?:wujud|appear)|x ?appear)\b|\b(di dlm oal|di oal|oal missing|tmf tak wujud|oal record not found|oal not found|oal xfound|oal xappear|oal not appear|oal x appear)\b|\b(?:tiada |masukkan |appear )?(?:order )?(dlm|dalam|in) rol\b|\b(tiada (dalam|dlm)|xda(?: di)?)( scheduled page)\b|\bponr\b|\bpending processing\b|\bmissing( dalam)? oal\b|\b(x?|tak ) masuk( di)?( dlm| dalam)( bakul| basket)\b|\b(?:order\s)?(?:tak\s|tiada\s|xda\s)?(?:masuk\s)?(?:dalam\s)?(?:bakul|basket)\b|\b(tiada|xda|takda) di( dalam)?( page)? activity\b|\btask sync\b|\bpending processing\b|\b(tak|x|tiada)\s*(?:di|dekat|dkt|dalam|dlm)?\s*(scheduled|unscheduled)( page)?\b|\btiada (dlm|dalam) (activity|act|aktivity|actvty) list\b|\b(xtvt|act|activity|actvty) (tak|x) (wujud|wjd)\b|\bmasukkan semula.*rol\b|\bstat(u)?(s)? unshedule(d)?.*(ra|mir|cc)\b|\bstatus( pending)?( )?processing\b|\bo(r)?d(e)?r.*(x|tak)( )?masuk (tmf|tmforce)\b|\b(order )?jadi unschedule(d)?\b|\breschedule(d)?( semula)? ke tm( )?f(orce)?\b|\border x( )?appear( at| di| in)? oal\b|\border ni ada (di)?( )?mana\b|\border return.*status unschedul(e)?(d)?\b|\bb(u)?(t)?t(o)?n return (tiada|xda|xde|takda)\b|\border return(ed)? jadi uns(c)?hedule(d)?\b|\border pending pro(c)?es(s)?ing\b|\border.*hilang.*id ui\b|\border ra.*(tak|x) (m(a)?s(u)?k d(a)?l(a)?m (act(ivity)?)|aktiviti|xtvt) order list\b|\bupdate semula ke rol\b|\btiada|xda d(a)?l(a)?m ro(l|c)\b|\bescalate( )?(ke|m(a)?s(u)?k|d(a)?l(a)?m)?( )?rol\b|\border return j(a)?d(i)? unschedul(e)?(d)?\b|\bb(e)?l(u)?m appear d(a)?l(a)?m act(ivity)? list\b|\border (tidak|x|tak) n(a)?m(p)?(a)?k d(a)?l(a)?m.*d\b|\brecord not found.*slot\b',
    "Missing Manual Assign Button": r'\bma\b|\b([.*]anual|man[n]?ual) (assign|slot|assgn|assigned)\b|\btm( )?f(orce)? (takdak|tiada|xd(a|e)) m(anual)?(.)?( )?assign\b', #ma btn xappear
    "Next Activity Not Appear": r'\b(?:next )?(?:activity )?tak appear\b|\b(xda|tiada) (cc|mir|ra)\b|\b(mir|ra|cc) (tiada|not appear|xappear|x appear|tak|x|missing)\b|\b(mir|ra|cc).*(ip|inprogress|missing)\b|\bnext (?:(owner|activity|act|actv))\b|\breturn(?: order)(?: list)\b|\bnot found(?: to)? (ra|mir|cc)\b|\bmir/?ra (in|ip)\b|\bcc (belum|x) appear\b|\b(mir|ra) in progress\b|\b(act|activity|activities|aktiviti) (x|not)\b|\b(masuk|masukkan)( ke (dalam|dlm))? rol\b|\bmasukkan order ke rol\b|\b(nxt|next)? (actvty|act|activities|activity|aktiviti) (not appear|xappear|xfound|not found|missing)\b|\blist rol\b|\bmasih unschedu(led)?\b|\bnpua|no pending user activity|pending (activity|act|activities|actvty)\b|\b(order )?(tiada|takda|xda) owner\b|\baktifkan order utk ra\b|\b(cc|ma|manual assign)(.*keluar|tiada)\b|\bpending (cc|ma|mir)\b|\b(nova )?(aktiviti|act|actvty|activity)? (tidak)? [x]?update[d]?\b|\bt[u|i]?ada bu[t]?ton (cc|mir|ra)\b|\bmissing owner\b|\b(tak|x) k(e)?luar cc\b|\bno pending user\b|\b(cc|mir|ra) m(a)?s(i)?h (tak|x) appear\b|\b(ra|mir|cc) status in( |-)?progres(s)?\b|\bmasuk(kan)?.*r(r)?ol\b|\bnext (xtvt|act|activity|actvty|aktiviti).*appear\b|\bbelum (r)?rol\b|\bcc (t(i)?d(a)?k|tak|x) muncul\b|\btiada (butang|b(u)?(t)?t(o)?n) cc\b|\border (tiada|xd(e|a)) d(a)?l(a)?m roc\b|\b(confirmation call|cc) (tak|x|tiada) appear(ed)?\b|\btiada.*done cc\b|\bmir(\/)?( )?ra m(a)?s(i)?h in( )?progres(s)?\b|\bmir(\/)?( )?ra.*(in progress|(i)?( )?(p)?)\b|\bbelum.*(cc|mir|mir/ra) appear\b|\bmir( )?(&)?( )?ra\b|\bmi(r)?(-)?ip\b|\bcc( )?(not|x|t(a)?k)( )?( )?appear\b|\bo(r)?der m(a)?s(i)?h (sangkut|sekat|stuck|missing)\b', #mir masih ip/ ra masih ip/ cc not appear/ next owner/ NPUA
    "Double @iptv": r'\b(?:double )?iptv(?:@iptv)?\b',
    "Equipment New to Existing": r'\b(?:new )?(ke|to|kepada) (existing|exstng|existhing)\b|\bexisting(kan| kan?)( onu|btu|sp|router|wifi|wi-fi|rg|modem)\b|\btukar ke (existing|esxting)\b|\bmohon jadikan existing\b|\bupdate(d)?.*existing\b|\bmohon tukar.*existing\b|\bmohon existing( )?(kan)?\b|\bexisting(kan)?.*order relocat(e)?(d)?\b|\b(order relocate)?.*tukar.*(jadi|ke) ex(i)?(s)?ting\b|\bbantuan order force done cancel\b|\bmohon.*j(a)?di ex(i)?(s)?ting\b|\bj(a)?d(i)?k(a)?n.*ex(i)?(s)?ting\b|\border relocate existing( )?k(a)?n (btu|sp|mesh|service point)\b|\badd existing (mesh|sp|service point|rg|router|wifi|wi-fi)\b',
    "Design & Assign": r'\b(d&a|dna|design|d&n (&|and) assign)\b|\bd&n\b|\bd&s ip\b',
    "HSI No Password": r'\b(xda|tiada) (pw|password) (hsi|ppoe)\b|\b(xda|tiada) (hsi|ppoe) (pw|password)\b|\bnak (password|pw|pass|pword) h(s)?(i)?\b',
    "CPE New/ Existing/ Delete": r'\btukar existing\b|\b(extng|exstng|existing) (ke|to) new\b|\b(uonu|rg|btu|sp|wifi|router) (ke|kepada|to) new\b|\b(update|updte|updt)( .*)?( new)\b|\bexisting (to|ke|kpda|kepada) new\b|\bm(o)?h(o)?n (del|delete).*(relocate)?\b|\bt(u)?k(a)?rkan existing.*new\b|\b(upd(a)?t(e)?|add).*new.*order modify\b|\b(granite)?(service point|sp|btu).*subsequent\b|\badd new( ata)?\b|\bupdate(d)?.*(pd|kpd|kpada|kepada|pada).*new\b|\bcpe y(an)?g new hanya (mesh|rg|modem)?.*done.*exist(ing)?.*tukar\b|\btmf ad(a|e).*no del.*nova.*del\b|\border new install.*existing tukar new\b|\bb(a)?ntu tukar.*k(e)?p(a)?d(a)? combo\b|\badd (service point|sp|btu).*order modify\b|\badd (service point|sp|mesh) ke new\b|\border existing.*(eqp|equipment) (x|tak)( )?s(a)?m(a)?\b|\bbantuan.*replace cpe baru\b|\bminta b(a)?ntu del(ete)?( )?( )?existing\b|\bbantu del(ete)? (equipment|eqp|eqmnt)\b|\bdelete combo mesh\b|\badd.*d(a)?l(a)?m eq(u)?(i)?(p)?m(e)?n(t)?\b|\bbantu tukar(kan)? rg5 k(e|r) rg6.*order (ni|new install)\b|\border modify minta add (equipment|eqmnt|eqp)\b',
    "Update CPE Equipment Details": r"\btidak boleh(?: (?:replace|update|tukar))? (?:cpe|rg|router|wifi|mesh|btu|sp|service point)\b|\border modify\b(?=.*\b(sn lama\/existing|sn baru)\b)|\bmodify (fixed|fix) ip\b|\border relocate guna existing cpe\b|\b(btn|button).*(replace|rplce).*(existing)?\b|\border force done( equipment)?.*(tak|x)( )?sama.*(tmf|tmforce)\b|\border.*fd\b|\btukar equipment daripada vm kepada sbvm\b|\bui.*scan.*keluar err(or)?\b|\b(tidak|x|tak) d(a)?p(a)?t complete order.*m(a)?s(a)?l(a)?h cpe\b|\bcomplete order.*onu combo: (unc.*|rg6.*|comb.*)\b|\bequipment.*(tak|x)( )?s(a)?m(a)? d(e)?n(g)?(a)?n mesh\b|\border relocation.*err(or)?.*done(kan)?\b|\border force done.*er(r)?(o)?(r)?\b|\bru sudah guna yang betul dan cpe ada dlm list ru\b|\bnak replace mesh tapi takde button save/update\b|\bcpe.*hanya ada (rg|mesh|btu|sp|onu)\b",
    "Missing/ Update Network Details": r"\b(fail to )?(slot )?(appointment|appmnt|apmt|appmt)\b|\btukar(kan)? (building|cab|cabinet|fdp|fp|fdc|dc)\b|\bxleh n(a)?k slot\b|\bgranite n(e)?twork info\b|\bft order ke hari ini\b|\bbooking c(a)?l(a|e)?nder (tak|x) keluar date available\b|\bgranite fail(ed)?\b|\brefresh granite info\b|\bslot not available\b|\bfailed to ra\b|\bexchange (berlainan|lain) d(a)?l(a)?m tm( )?f(orce)?.*nova b(e)?t(u)?l\b",
    "Update Contact Details": r"\b(updt|updte|update) (contact|ctc|hp|phone|mobile)( num| number)?\b|\b(tukar|tukarkan|tkr) (contact|ctc|phone)( number| #| num)?\b|\bctc num\b|\bremove nombor( pic)?\b",
    "Update Customer Email": r"\bemail.*salah\b",
    "Bypass HSI": r"\b(bypass|done|skip|donekan) (aktivity|act|activity|activities|actvty)?hsi\b|\bhsi.*bypas(s)?\b|\bby( )?pas(s)? h(si|is)\b|\bqos\b|\bdone( )?kan (hsi|his)\b|\bsession up verify fail\b|\bmohon by( )?pas(s)?( act(ivity)?)? hsi\b|\bbypas(s)?( testing)? (hsi|his)\b|\bby( )?pas(s)?.*(hsi|his)\b|\bo(r)?d(e)?r (force done|fd).*by( )?pas(s)? verification\b",
    "Bypass Voice": r"\b(by pass|bypass).*voice\b|\bvobb.*bypass\b|\b(voice|vobb).*bypas(s)?\b|\bmohon by( )?pas(s)?( act(ivity)?)? voice\b",
    "Bypass IPTV": r"\b(by pass|bypass).*iptv\b|\biptv.*bypas(s)?\b|\bbypas(s).*upb\b|\bmohon by( )?pas(s)?( act(ivity)?)? ip( )?(tv)?\b",
    "Bypass Extra Port": r"\b(by pass|bypass) (extraport|extrapot|extra port|extra pot)\b|\bby( )?pas(s)? xp\b|\bbantuan bypass kan extraport\b|\bmohon by( )?pas(s)?( act(ivity)?)? (extra( )?port)\b|\bby( )?pas(s)? ext(r)?a( )?port\b",
    "Revert Order to TMF": r"\brevert (order|order2).*ke(.*|tmf)\b|\bremove mdf\b",
    "Release Assign To Me": r"\brelease (assign(?: to me)?|assgn)\b|\brelease(kan)? order\b|\brelease(kan)?( order)?( dari)? id\b|\bfail to slot\b|\brelease(kan)?( )?( )?dr id\b|\breleasekan( )?( )?order\b|\bfail(ed)? to rescheduled\b|\brelease from me\b|\brelease kan order\b|\brelease(k(a)?n)? order\b|\brelease(kan)? assign to me\b|\brelese(kan)?( order)?\b|\bmohon bantu r(e)?lease\b|\bmohon release(kan)?\b|\bfail to ra\b|\bbantuan release(kan)?.*1-(8|9)\d{10,11}.*q[0-9]{5,6}\b",
    "Propose Cancel to Propose Reappt/ Return": r"\brcl|propose cancel|propose reappt\b|\brtn cancel\b|\brrol\b|\border proposed cancel.*nak proceed pasang\b|\brevert semula dari propose(d)? cancel ke (r)?rol\b|\baktif(kan)? s(e)?m(u)?la order( silap)? return(ed)? cancel((l)?ed)?\b|\br(e)?t(u)?(r)?n cancel(led)?.*proceed ra\b|\border propose(d)? cancel(led)? n(a)?k (ra|reappt)\b",
    "Unsync Order": r"\bstatus not sync\b|\bunsync(h|ed)? order\b|\b(dalam|dlm) tmf( masih)?( status)? assign(ed)?\b|\bdone (tapi|tp) status( masih)? (ip|in progress|in-progress|inprogress)\b|\btmf.*schedule(d)?.*t(e)?(t)?(a)?p(i)?.*(nova)?complete(d)?.*(nova)?\b|\b(mohon )?tarik atau cancel (dari|dr) (tmf|tm( )?force)\b|\border.*status complete(d)?.*(x)( )?h(i)?l(a)?(n)?g d(a)?r(i)? tm( )?f(orce)?\b|\bt(e)?t(a)?p(i)? status m(a)?s(i)?h in( |-)?progress d(a)?l(a)?m( portal)? tm( )?f(orce)?\b|\bprocessing-complete\b|\bdone pending complete(d)?\b|\border( d(a)?h)? siap.*t(a)?p(i)?.*m(a)?s(i)?h processing\b|\bstatus.*(not|tak|x).*sync((h)?ed)? tm( )?f(orce)?.*nova\b|\b(activity|xtvt|aktivity).*nova done.*tm()?f(orce)?.*w(u)?j(u)?d\b|\btukar status k(e)?p(a)?d(a)? complet(ed)?\b|\border return(ed)? t(a)?p(i)? unschedule(d)?\b|\bcomplete(kan)? order.*p(e)?m(a)?s(a)?(n)?g(a)?n (siap|sudah|settle|beres)\b",
    "Order Transfer SWIFT-TMF": r"\bmohon transfer ke tmf\b|\btransfer order ni ke tm( )?f(orce)?\b",
    "Duplicated Order Activity": r"\bduplicate(d)? di( )?(portal|tm( )?f(orce)?)?\b",
    "TT RG6/ Combo Update": r"\bnew (rg|router|wifi|mesh|btu|sp|service point)\b|\bs\/?n baru\b|\bnew\b.*\b(unc.*|mt.*|wfh.*|rg6.*|rgx.*|hp.*|com.*|uon.*)\b|\b(c)?tt.*(combo box|cbox|combo) sn: \b|\b(c)?tt.*(rg|rg6|combo|cbox|combo box)\b.*\b(unc|mt|wfh|rg6|rgx|hp|com|uon).*\b|\b(serial no|sn|serial)( baru| lama)?\b.*\b(unc|mt|wfh|rg6|rgx|hp|com|uon).*\b|\b(new)( rg)?\b.*\b(unc|mt|wfh|rg6|rgx|hp|com|uon).*\b|\b(new)(.*)?\b.*\b(unc|mt|wfh|rg6|rgx|hp|com|uon).*\b|\bsn rg baru( )?( )?:( )?(unc|mt|wfh|rg6|rgx|hp|com|uon).*\b|\b(s(/)?n) fizikal( )?(:)?( )?(unc|mt|wfh|rg6|rgx|hp|com|uon).*\b|\bs(\/)?n cpe baru(:)?(unc|mt|wfh|rg6|rgx|hp|com|uon).*\b|\btukar combo box.*(s(\/)?n|serial number)\b|\btukar.*combo.*(s(\/)?n|serial number)\b|\beqpmnt sama tapi keluar error\b|\b(x ?|tak ?)d(a)?p(a)?t (tukar|tkr).*(rg.*|com.*).*upgrade.*mb(p)?(s)?\b|\bcpe does not exist in hand\b|\b(tidak|x|tak) d(a)?p(a)?t t(u)?k(a)?r rg(5|6)\b|\bd(a)?p(a)?t err(or)?.*t(u)?k(a)?r cpe.*sn rg :( )?\b|\bmaklum pelanggan change equipment\b|\btiada detail.*equipment.*sn: \b|\b(replace)?( )?rg(4|5) (to|k(e)?p(a)?d(a)?) (rg6|combo)\b|\brg lama.*combo baru\b|\b(c)?tt no:  1-(8|9)\d{9,11}  lama :  baru : (unc[a-z0-9]{14,16}|rg[a-z0-9]{14,16})\b|\b(c)?tt.*1-(8|9)\d{10,11}.*baru.*lama( )?:( )?\b",
    "TT CPE LOV": r"\bfaulty reason\b", # check list faulty reason tak keluar
    "TT Unable to Slot/ Error 400": r"\b((c)?tt)( )?unable to slot((c)?tt)?\b|\bno( appoint)? slot\b|\b(error|err) 400\b|\bmcat\b|\btidak slot\b|\b(tidak|tak|x) (dapat|dpt|boleh) slot\b|\bskill ?set\b|\b(tiada|xda) (dp|dc|cab|fdc|fdp) id\b|\b(1-9\d{10,11}).*(tiada|xda)? slot appt\b|\b(tiada|xda)? slot appt.*(1-9\d{10,11})\b|\bslot (error|err)\b|\b(del|delete) (cab|cabinet|dp|fdp|fdc)\b|\bx ada (dp|cab) id\b|\bslot aptt\b|\bwork type\b|\b(tidak|x) auto slot\b|\bctt tiada slot\b|\bappoint err(or)?\b|\baptt error\b|\b(add|tambah) (cab|dp|cabinet) u(n)?t(u)?k map((p)?ing)?\b|\bxleh slot\b|\btiada slot (u(n)?t(u)?k) (slot|appt|appointment)\b|\bmissing granite info.*(appt|appointment|appmnt)?\b|\bctt.*(tiada|xda|xde) slot\b|\badd id\b|\bskill( )?set\b|\bx( )?k(e)?luar book (appt|appmnt|appointment) time\b|\berr(or)? u(n)?t(u)?k slot(ting)?\b|\b(appt|appointment|appmnt) slot.*err(or)?\b|\b(c|k)ab(inet)? id.*d(a)?l(a)?m tm( )?f(orce)?\b",
    "TT Missing/ Update Network Details": r"\b(tiada|xda|tidak ada) detail (cab|dp|fdp|fdc)\b|\bmissing (cab|cabinet|fdc|fdpp|cab|dc|dp)( id\/(dp )?(id)?)?\b|\bexchange (sbnr|sebenar)\b|\bbuang (dp|cab|cabinet).*(c)?tt\b|\b(cab|cabinet|dp|fdp) id null\b|\btiada slot.*( appear)?( cab| cabinet)\b|\btiada dp/cabinet detail\b|\bupdate (dp|cab|cabinet) id\b|\bupdate granite\b|\bbantu..tiada kabinet id\b|\b(dp|cab|cabinet) melek(a)?t\b|\badd mapping( zon(e)?)?\b|\bprovide (dp|cab) id\b|\bbantuan add (cab|cabinet|dp)\b|\bmohon( betulk(a)?n)? dp id\b|\bmohon provide cab( ?/dp)? id\b|\b(mohon )?(update|updte|updt) detail (cab|cabinet|fdp|dp)\b|\btiada m(a)?kl(u)?mat network\b|\b(c)?tt( hsba)? xda(a)? (cab(inet)?|(f)?dp) id\b|\b(c)?tt( hsba)? (xd(a)?|tiada) ((f)?dp|cab(inet)?) id\b|\bmohon bantu buang dp id\b|\b((f)?dp|cab(inet)?) id (xd(a|e)?|tiada)\b|\b(cab(inet)?|(f)?dp) (tiada|xd(a|e)) d(a)?l(a)?m list\b|\bbantuan add c(a)?b(i)?(n)?(e)?t( missing| h(i)?l(a)?(n)?g)?.*(primary|secondary)\b|\berr((o)?(r)?|.*) 400\b|\bmohon betul((a)?(k)?(n)?|.*) (k|c)ab(inet)? id\b|\bupdate detail ((f)?dc|(c|k)ab|(c|k)abinet)\b|\bbetul.*building.*((f)?dc|(c|k)ab|(c|k)abinet)\b|\bbantu retrigger cab/dp\b",
    "TT V1P": r"\b(ctt |tt )?v1p\b|\b(ctt |tt )?whp\b|\bappt @ \d{3,4}(pm|am)?\b|\b(appt|appmnt|appointment)\.\d{1,2}(\.\d{2})?\b|\b(appt|appmnt|appointment)\s+(pkul\s?)?\d{1,2}\.\d{2}\b|\bvip\b|\b(?:ra|appointment|appt|appmnt)\s*\d{1,2}[:.]\d{2}\s*(?:am|pm)?\b|\bslot.*?\b1-2\d{9,11}\b(?!\d)|\b1-2\d{10,11}.*slot.*(?:[01]?\d|2[0-3])[:.]?[0-5]\d(?:[ap]m)?\b|\b(c)?tt.*1-2\d{9,10}\b @|\b(1-2\d{9,10})?( mohon)?(.*ra|.*book).*(1-2\d{9,10})?(am|pm)\b|\b1-2\d{9,10} mohon(.*ra|.*book).*(am|pm)\b|\bb(a)?nt(u)?(a)?n(.*ra|.*book).*(am|pm)( 1-2\d{9,10})\b",
    "TT CPE Not Tally with Physical": r"\bclose?d\b.*\b(cpe|mesh|wifi|rg|modem|router)\b(?!.*\bnew (rg|router|wifi|mesh|btu|sp|service point)\b|\bs\/?n baru\b)|\b(tak|x)?sama (dengan|dgn) (fizikal|physical|site)\b|\bxbole(h)? close (c)?tt\b|\bs(/)?n onu d(a)?l(a)?m tmf (tak|x) (sma|sama) d(e)?g(a)?n s(/)?n (d)?(e)?kat fizikal\b|\bupd(a)?t(e)?.*(physical|fizikal)\b|\b(tiada|xd(a|e)?).*d(e)?k(a)?t.*site.*ad(a)?\b|\b(pckg|pakej|package).*(ada)?.*(tmf|tmforce).*(xd(a|e)|tiada)\b|\bpremise.*ada.*(tmf|tmforce|tm force).*(tiada|takda|xda|xde)\b|\bmohon update equipment dalam tm( )?force\b|\bc(u)?st(o)?m(e)?r (i)?ni(e)? ada.*d(a)?l(a)?m tm( )?f(orce)? (tiada|xd(a|e)|takda)\b|\bservice point takde onu tak nampak\b|\bx( )?s(a)?m(a)?.*fizikal.*tm( )?f(orce)?\b|\bdekat site.*ada (mesh|rg|wifi|modem|btu|sp|service point)\b|\bs(/)?n.*(tak|x)( )?s(a)?m(a)?.*fizikal.*tm( )?f(orce)?\b",
    "TT Link LR Appear TMF": r'\bctt link lr appear tmf\b|\b(next )?ntt linkage\b|\bexternal list|ext list\b|\bappear di tmf\b|\bctt under lr\b|\breturn l(a)?ma t(a)?p(i)? m(a)?s(i)?h ada d(a)?l(a)?m (tmf|tm( )?force)\b|\bctt not appear in tm( )?f(orce)? l(e)?p(a)?s (un)?link (ntt|lr)?\b|\bmasih ada di tmf.*lr.*\b|\b(c)?tt link lr\b',
    "TT Blank Source Skill": r'\b(blank )?source skill( blank)?\b',
    "ID Locking/ Unlock/ 3rd Attempt": r'\bunlock id\b|\b(pass|pw|password|pwd).*(betul|btl|btul)\b|\b(tak|tk) (boleh|blh) login\b|\b(x|tak|tidak) (dapat|dpt) login\b|\b(?:fail(?:ed)?)\s*(?:log[ -]?in|login|sign[ -]?in|masuk|msk)\b|\bfailed to log in\b|\byour login has been locked after 3 attempts\b|\btmf kena blo(c)?k\b|\bid lock(ed)?\b|\bxbole(h)? login\b|\b(mohon|mhn)\s*(bantuan|bntn|bntuan)\s*(tm\d{5}|q\d{6})\b|\b(tak|x) (blh|boleh) (masuk|msk) tmf\b|\b(x( )?|tak( )?)(boleh|blh).*log( )?in.*tmf\b|\bunlock( )?(semula)?( )?id\b|\bid.*lock(ed)?\b|\b(tidak|tak|x) d(a)?p(a)?t log( )?in\b|\bk(e)?na lock(ed)? 3 attempt fail(ed)?\b|\bxleh log in.*id\b|\b(tidak|x|tak)( )?(boleh|dapat) login tm( )?f(orce)?\b|\b(ui|ru) (tak|x) d(a)?p(a)?t m(a)?s(u)?k tm( )?f(orce)?\b|\bid.*(t(i)?(d)?(a)?k|x).*tm( )?f(orce)?\b|\bid.*(t(a)?k|x) d(a)?p(a)?t login\b|\btm( )?f(orce)?.*lock\b|\b(tidak|x|tak) d(a)?p(a)?t m(a)?s(u)?k tm( )?f(ouce|orce)? mobile\b|\blog( )in fail(ed)?\b|\b(x|tak|tidak) b(o)?l(e)?h.*log( )?in\b|\bg(a)?g(a)?l log( )?in\b',
    "TT Unsync": r"\bTMF resolv(?:ed)?\b.*\bnova (in[- ]?progress|ip)\b|\bclearkn tmf[.,]?\s*Nova cancelled\b|\bcleark(a)?n tmf\b|\b(c)?tt unlink(ed)? from ntt\b|\bopen.*tm( )?f(orce)?.*nova cancel(led)?\b|\bctt d(a)?l(a)?m nova.*done.*d(a)?l(a)?m tm( )?f(orce)?.*open\b|\bbantu clear( )?(kan)? tm( )?f(orce)?.*nova (cancel(led)?|close(d)?)\b|\btmf open.*icp/next closed\b|\btrigger(k(a)?n)? (c)?tt\b|\b(c)?tt unsync(h)?(ed)?\b|\b(c)?tt.*cancel.*nova.*cancel di tm( )?f(orce)?\b|\bcancel (activity|xtvt|aktiviti|actvty).*(c)?tt\b",
    "TT Missing": r"\bada (dalam|dlm|dekat|dkt) nova (tapi|tp) (tiada|xda|takda) (dalam|dlm|dekat|dkt) tmf\b|\b(retrigger|trigger) ctt\b|\bada dlm nova tp x de dlm tmf\b|\bctt missing\b|\bctt tiada dalam tmf\b|\bm(o)?h(o)?n (re)?(-)?trigger.*(missing|h(i)?l(a)?(n)?g) d(a)?l(a)?m (act(ivity)?|xtvt|aktiviti) list\b",
    "TT Update DiagnosisCode": r"\bdiagnosis( missing| unsync)\b|\b(rno|fs) troubleshooting\b",
    "TT Granite Network Info Error": r"\bcamelia detect data no found\b|\b(tidak|tak|x) dapat pas(s)?( ke)? next\b",
    "TT HSBA Reappointment": r"\bappt( ctt)? hsba\b",
    "Resource Management Issue": r"\bsalah zone id\b"
}

# Ticket/order and ID patterns
ticket_order_pattern = r'\b1-\d{9,11}\b|\bT-\d{9}\b|\bt-\d{10}\b|\b1-[a-z0-9]{7}\b|\binc\b'
id_pattern = r'\bQ\d{6}\b|\bq\d{6}\b|\bTM\d{5}\b|\btm\d{5}\b'

# Dropdown to select between cleaned text from previous step or uploaded file
data_source = st.radio(
    "Choose the source for filtering:",
    ('Use cleaned text from Step 1', 'Upload a new filtered file(s)')
)

# Option to choose output display format
output_format = st.radio(
    "Choose the output display format:",
    ('Show results separately for each file', 'Show all results in one text area')
)

# Button for processing filtered text messages
if st.button("Filter text messages"):
    if data_source == 'Use cleaned text from Step 1':
        if st.session_state.cleaned_texts:
            if output_format == 'Show all results in one text area':
                combined_results = []
                for file_name, cleaned_text in st.session_state.cleaned_texts.items():
                    st.subheader(f"Processing cleaned text from {file_name}")
                    
                    # Process the file content
                    result = process_messages_from_content(cleaned_text, issue_patterns, ticket_order_pattern, id_pattern)

                    # Prepare the result text for display
                    result_text = []
                    for issue, data in result.items():
                        result_text.append(f"{issue}:")
                        if issue == "Other":
                            for number, message in data:
                                result_text.append(f"{number}\n{message}")
                        else:
                            result_text.extend([f"{number}" for number in data])
                        result_text.append("\n")  # Add a newline for separation

                    # Join the result text into a single string
                    combined_results.append("\n".join(result_text))

                # Join all results into a single text area
                display_text = "\n\n".join(combined_results)

                # Display the result in a read-only text area
                st.text_area("Results", value=display_text, height=600, disabled=True)

                # Option to download the combined result as a text file
                st.download_button(
                    label="Download Combined Results",
                    data=display_text,
                    file_name="combined_processed_results.txt",
                    mime="text/plain"
                )
            else:
                for file_name, cleaned_text in st.session_state.cleaned_texts.items():
                    st.subheader(f"Processing cleaned text from {file_name}")

                    # Process the file content
                    result = process_messages_from_content(cleaned_text, issue_patterns, ticket_order_pattern, id_pattern)

                    # Prepare the result text for display
                    result_text = []
                    for issue, data in result.items():
                        result_text.append(f"{issue}:")
                        if issue == "Other":
                            for number, message in data:
                                result_text.append(f"{number}\n{message}")
                        else:
                            result_text.extend([f"{number}" for number in data])
                        result_text

                # Join the result text into a single string
                display_text = "\n".join(result_text)

                # Display the result in a read-only text area
                st.text_area(f"Results for {file_name}", value=display_text, height=300, disabled=True)

                # Option to download the result as a text file
                st.download_button(
                    label=f"Download Results for {file_name}",
                    data=display_text,
                    file_name=f"processed_{file_name}",
                    mime="text/plain"
                )
    else:
        st.warning("No cleaned text available from Step 1. Please process the files first.")

elif data_source == 'Upload a new filtered file':
    if uploaded_filtered_files:
        if output_format == 'Show all results in one text area':
            combined_results = []
            for uploaded_file in uploaded_filtered_files:
                file_content = uploaded_file.read().decode("utf-8")

                # Process the file content
                result = process_messages_from_content(file_content, issue_patterns, ticket_order_pattern, id_pattern)

                # Prepare the result text for display
                result_text = []
                for issue, data in result.items():
                    result_text.append(f"{issue}:")
                    if issue == "Other":
                        for number, message in data:
                            result_text.append(f"{number}\n{message}")
                    else:
                        result_text.extend([f"{number}" for number in data])
                    result_text.append("\n")  # Add a newline for separation

                # Join the result text into a single string
                combined_results.append("\n".join(result_text))

            # Join all results into a single text area
            display_text = "\n\n".join(combined_results)

            # Display the result in a read-only text area
            st.text_area("Results", value=display_text, height=600, disabled=True)

            # Option to download the combined result as a text file
            st.download_button(
                label="Download Combined Results",
                data=display_text,
                file_name="combined_processed_results.txt",
                mime="text/plain"
            )
        else:
            for uploaded_file in uploaded_filtered_files:
                file_content = uploaded_file.read().decode("utf-8")

                # Process the file content
                result = process_messages_from_content(file_content, issue_patterns, ticket_order_pattern, id_pattern)

                # Prepare the result text for display
                result_text = []
                for issue, data in result.items():
                    result_text.append(f"{issue}:")
                    if issue == "Other":
                        for number, message in data:
                            result_text.append(f"{number}\n{message}")
                    else:
                        result_text.extend([f"{number}" for number in data])
                    result_text.append("\n")  # Add a newline for separation

                # Join the result text into a single string
                display_text = "\n".join(result_text)

                # Display the result in a read-only text area
                st.text_area(f"Results for {uploaded_file.name}", value=display_text, height=300, disabled=True)

                # Option to download the result as a text file
                st.download_button(
                    label=f"Download Results for {uploaded_file.name}",
                    data=display_text,
                    file_name=f"processed_{uploaded_file.name}",
                    mime="text/plain"
                )
    else:
        st.warning("Please upload at least one text file to process.")
