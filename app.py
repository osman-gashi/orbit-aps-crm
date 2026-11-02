import streamlit as st
import pandas as pd
import requests
import hashlib
import urllib.parse
from datetime import datetime, date

# Page configuration for Mobile and Desktop
st.set_page_config(page_title="ORBIT APS - Cloud CRM", layout="wide", page_icon="🚀")

# ================= Supabase Cloud Configuration =================
SUPABASE_URL = "https://basjceecsheqakocawen.supabase.co"
SUPABASE_KEY = "sb_publishable_HIeAUtwDHImDOqfUE-7Jbg_JbP3l2Lm"

def supabase_request(method: str, endpoint: str, json_data=None):
    """Smart request handler compatible with both sb_publishable_ and legacy keys."""
    url = f"{SUPABASE_URL.rstrip('/')}{endpoint}"
    
    # Primary headers for sb_publishable_ keys (without Authorization Bearer)
    headers_primary = {
        "apikey": SUPABASE_KEY.strip(),
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    # Fallback headers including Authorization Bearer
    headers_fallback = {
        "apikey": SUPABASE_KEY.strip(),
        "Authorization": f"Bearer {SUPABASE_KEY.strip()}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    
    try:
        res = requests.request(method, url, headers=headers_primary, json=json_data, timeout=10)
        if res.status_code in [401, 403]:
            res = requests.request(method, url, headers=headers_fallback, json=json_data, timeout=10)
        return res
    except Exception as e:
        return e

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ================= Database Functions (Users & Leads) =================
def get_user(username: str):
    res = supabase_request("GET", f"/rest/v1/users?username=eq.{urllib.parse.quote(username)}")
    if isinstance(res, Exception):
        return None
    if res.status_code == 200:
        try:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0]
        except Exception:
            return None
    return None

def create_user(username: str, password: str, calendly: str):
    payload = {
        "username": username,
        "password_hash": hash_password(password),
        "calendly_link": calendly
    }
    res = supabase_request("POST", "/rest/v1/users", json_data=payload)
    if isinstance(res, Exception):
        return False, f"Network error: {str(res)}"
    if res.status_code in [200, 201]:
        return True, "Account created successfully!"
    return False, f"Status {res.status_code}: {res.text}"

def update_user_calendly(username: str, calendly: str):
    res = supabase_request(
        "PATCH",
        f"/rest/v1/users?username=eq.{urllib.parse.quote(username)}",
        json_data={"calendly_link": calendly}
    )
    return not isinstance(res, Exception) and res.status_code in [200, 204]

def fetch_user_leads(username: str) -> pd.DataFrame:
    res = supabase_request("GET", f"/rest/v1/leads?owner=eq.{urllib.parse.quote(username)}&order=id.desc")
    if not isinstance(res, Exception) and res.status_code == 200:
        try:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                return pd.DataFrame(data)
        except Exception:
            pass
    return pd.DataFrame(columns=[
        "id", "owner", "first_name", "full_name", "platform", 
        "group_name", "state_county", "profile_url", "context_notes", 
        "status", "date_added", "last_updated"
    ])

def insert_lead(payload: dict):
    res = supabase_request("POST", "/rest/v1/leads", json_data=payload)
    return not isinstance(res, Exception) and res.status_code in [200, 201]

def update_lead_db(lead_id: int, username: str, payload: dict):
    res = supabase_request(
        "PATCH",
        f"/rest/v1/leads?id=eq.{lead_id}&owner=eq.{urllib.parse.quote(username)}",
        json_data=payload
    )
    return not isinstance(res, Exception) and res.status_code in [200, 204]

def delete_lead_db(lead_id: int, username: str):
    res = supabase_request(
        "DELETE",
        f"/rest/v1/leads?id=eq.{lead_id}&owner=eq.{urllib.parse.quote(username)}"
    )
    return not isinstance(res, Exception) and res.status_code in [200, 204]

# ================= Session Management & Login =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.calendly_link = ""

if not st.session_state.logged_in:
    st.title("🔐 ORBIT APS")
    
    auth_tab1, auth_tab2 = st.tabs(["🔑 Sign in", "➕ Sign up (New Account)"])
    
    with auth_tab1:
        with st.form("login_form"):
            login_user = st.text_input("Username:").strip().lower()
            login_pass = st.text_input("Password:", type="password")
            submit_login = st.form_submit_button("Login")
            
            if submit_login:
                user_data = get_user(login_user)
                if user_data and user_data.get("password_hash") == hash_password(login_pass):
                    st.session_state.logged_in = True
                    st.session_state.username = login_user
                    st.session_state.calendly_link = user_data.get("calendly_link", "")
                    st.rerun()
                else:
                    st.error("❌ Wrong Username or Password.")

    with auth_tab2:
        with st.form("signup_form"):
            new_user = st.text_input("Username:").strip().lower()
            new_pass = st.text_input("Password:", type="password")
            new_cal = st.text_input("Calendly link:", "https://calendly.com/")
            submit_signup = st.form_submit_button("Create Account")
            
            if submit_signup:
                if len(new_user) < 3 or len(new_pass) < 4:
                    st.warning("⚠️ Username must be at least 3 characters and password at least 4 characters.")
                elif get_user(new_user):
                    st.error("⚠️ Username is already taken.")
                else:
                    ok, msg = create_user(new_user, new_pass, new_cal)
                    if ok:
                        st.success("✅ Account created! You can now sign in from the first tab.")
                    else:
                        st.error(f"❌ Database Error: {msg}")
    st.stop()

# ================= Main Dashboard (After Login) =================
current_user = st.session_state.username

# Sidebar
st.sidebar.title(f"👤 Welcome, {current_user.capitalize()}")
if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🔗 Booking Link Settings")
calendly_input = st.sidebar.text_input("Calendly link:", st.session_state.calendly_link)
if calendly_input != st.session_state.calendly_link:
    if st.sidebar.button("💾 Save New Link"):
        update_user_calendly(current_user, calendly_input)
        st.session_state.calendly_link = calendly_input
        st.sidebar.success("Saved!")

st.sidebar.markdown("---")
st.sidebar.subheader("📝 Text Generator")
gen_name = st.sidebar.text_input("First Name:", "John")
gen_group = st.sidebar.text_input("Group Name:", "Wholesaling Houses Full Time")
gen_state = st.sidebar.text_input("State/County:", "Texas")

script_type = st.sidebar.selectbox("MSG TYPE:", [
    "1. Standard DM", 
    "2. Qualification Question", 
    "3. Calendar Invite"
])

if script_type == "1. Standard DM":
    generated_script = f"Hey {gen_name}, saw your recent post in the {gen_group} group regarding off-market inventory in {gen_state}. Quick question—are you currently scaling your outbound caller team this quarter, or are you mostly relying on direct mail and inbound? We run dedicated cold calling squads specifically for wholesalers in {gen_state} to secure 3-5 qualified seller appointments per week. Would you be open to reviewing our outbound workflow in a brief 15-minute walkthrough?"
elif script_type == "2. Qualification Question":
    generated_script = f"Are you guys currently running dedicated cold callers for off-market deals in {gen_state}, or relying primarily on PPC and inbound?"
else:
    generated_script = f"Awesome {gen_name}! Let's set up a brief 15-minute strategy call with our leadership team to walk you through our caller infrastructure. You can grab a time that works best for you right here: {calendly_input}"

st.sidebar.code(generated_script, language="text")

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Zillow Search")
search_target = st.sidebar.text_input("Client/Company:")
if search_target:
    li_q = urllib.parse.quote(f"{search_target} Real Estate Wholesaler")
    fb_q = urllib.parse.quote(f"{search_target} Real Estate")
    st.sidebar.markdown(f"🔗 [Search in LinkedIn](https://www.linkedin.com/search/results/all/?keywords={li_q})")
    st.sidebar.markdown(f"🔗 [Search in Facebook](https://www.facebook.com/search/top?q={fb_q})")

# Fetch current user's leads
df_all = fetch_user_leads(current_user)
today_str = date.today().isoformat()

today_outreach = len(df_all[df_all['date_added'] == today_str]) if not df_all.empty else 0
total_leads = len(df_all)
qualified_count = len(df_all[df_all['status'].isin(['Qualified', 'Booked Call', 'Closed Deal'])]) if not df_all.empty else 0
booked_count = len(df_all[df_all['status'].isin(['Booked Call', 'Closed Deal'])]) if not df_all.empty else 0
closed_count = len(df_all[df_all['status'] == 'Closed Deal']) if not df_all.empty else 0

st.title("📊 Setter Cloud Operations & Sales Dashboard")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Today's Goal: 20-30", f"{today_outreach} / 30", delta=f"{today_outreach - 20} vs minimum")
col2.metric("Total Clients", total_leads)
col3.metric("Qualified Clients", qualified_count)
col4.metric("Booked Calls", booked_count)
col5.metric("Profits", f"${closed_count * 100} + ${closed_count * 50}/mo")

st.progress(min(today_outreach / 30.0, 1.0))

tab1, tab2 = st.tabs(["➕ Add New Client", "📋 Manage & Update Clients"])

with tab1:
    with st.form("add_lead_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        first_name = c1.text_input("First Name *")
        full_name = c2.text_input("Full Name / Company")
        platform = c3.selectbox("Platform", ["Facebook", "LinkedIn", "Zillow -> FB", "Zillow -> LinkedIn"])
        
        c4, c5, c6 = st.columns(3)
        group_name = c4.text_input("Group Name", "Wholesaling Houses Full Time")
        state_county = c5.text_input("State/County *")
        profile_url = c6.text_input("Profile URL *")
        
        c7, c8 = st.columns([2, 1])
        context_notes = c7.text_area("Notes")
        status = c8.selectbox("Status", [
            "DM Sent",
            "Replied / In Conversation",
            "Qualified",
            "Booked Call",
            "Closed Deal",
            "Not Interested"
        ], index=0)
        
        if st.form_submit_button("💾 Save"):
            if not first_name.strip() or not profile_url.strip():
                st.error("⚠️ First Name and Profile URL are required.")
            else:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                payload = {
                    "owner": current_user,
                    "first_name": first_name.strip(),
                    "full_name": full_name.strip(),
                    "platform": platform,
                    "group_name": group_name.strip(),
                    "state_county": state_county.strip(),
                    "profile_url": profile_url.strip(),
                    "context_notes": context_notes.strip(),
                    "status": status,
                    "date_added": today_str,
                    "last_updated": now_str
                }
                if insert_lead(payload):
                    st.success(f"✅ {first_name} Saved Successfully!")
                    st.rerun()

with tab2:
    if not df_all.empty:
        search_q = st.text_input("🔍 Search by name, state, or status:")
        df_show = df_all.drop(columns=["owner"])
        if search_q:
            df_show = df_show[
                df_show['first_name'].str.contains(search_q, case=False, na=False) |
                df_show['state_county'].str.contains(search_q, case=False, na=False) |
                df_show['status'].str.contains(search_q, case=False, na=False)
            ]
        st.dataframe(df_show, use_container_width=True)
        
        csv_bytes = df_show.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Export CSV", csv_bytes, f"{current_user}_leads_{today_str}.csv", "text/csv")
        
        st.markdown("### 🔄 Update or Delete a Client")
        u1, u2, u3, u4 = st.columns([1, 2, 2, 1])
        lead_id = u1.selectbox("Client ID:", df_all['id'].tolist())
        new_status = u2.selectbox("New Status:", [
            "DM Sent",
            "Replied / In Conversation",
            "Qualified",
            "Booked Call",
            "Closed Deal",
            "Not Interested"
        ])
        extra_note = u3.text_input("Add New Note:")
        
        if u4.button("Update Status"):
            old_notes = df_all[df_all['id'] == lead_id]['context_notes'].values[0] or ""
            updated_notes = f"{old_notes} | {extra_note}" if extra_note else old_notes
            update_lead_db(lead_id, current_user, {
                "status": new_status,
                "context_notes": updated_notes,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            st.success("✅ Updated!")
            st.rerun()
            
        if st.button("🗑️ Delete Client"):
            delete_lead_db(lead_id, current_user)
            st.warning("Deleted!")
            st.rerun()
    else:
        st.info("There is no data in your account yet. Start by adding your first client via the first tab!")