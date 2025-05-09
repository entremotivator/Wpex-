import streamlit as st
import requests
import json

st.set_page_config(page_title="WordPress CPT to n8n", layout="wide")

# Initialize session state
for key in ["credentials_saved", "wp_url", "wp_user", "wp_pass"]:
    if key not in st.session_state:
        st.session_state[key] = ""

# Sidebar - WordPress Credentials
st.sidebar.header("WordPress Credentials")

if not st.session_state.get("credentials_saved"):
    wp_url = st.sidebar.text_input("WP Site URL", key="wp_url_input")
    wp_user = st.sidebar.text_input("Username", key="wp_user_input")
    wp_pass = st.sidebar.text_input("Password", type="password", key="wp_pass_input")

    if st.sidebar.button("Save Credentials"):
        st.session_state["wp_url"] = wp_url
        st.session_state["wp_user"] = wp_user
        st.session_state["wp_pass"] = wp_pass
        st.session_state["credentials_saved"] = True
        st.experimental_rerun()
else:
    st.sidebar.success("✅ Credentials saved!")
    wp_url = st.session_state.get("wp_url", "")
    wp_user = st.session_state.get("wp_user", "")
    wp_pass = st.session_state.get("wp_pass", "")

    if st.sidebar.button("Clear Credentials"):
        for key in ["credentials_saved", "wp_url", "wp_user", "wp_pass"]:
            st.session_state.pop(key, None)
        st.rerun()

# Sidebar - OAuth2 Credentials (Optional)
st.sidebar.header("Optional OAuth2")
oauth_token = st.sidebar.text_input("Access Token (OAuth2)", type="password")
refresh_token = st.sidebar.text_input("Refresh Token (Optional)", type="password")

# Sidebar - n8n Webhook
st.sidebar.header("n8n")
n8n_webhook = st.sidebar.text_input("n8n Webhook URL")

# Function to generate bearer token
def get_bearer_token(wp_url, username, password):
    try:
        auth_url = f"{wp_url}/wp-json/jwt-auth/v1/token"
        res = requests.post(auth_url, data={"username": username, "password": password})
        res.raise_for_status()
        return res.json().get("token")
    except Exception as e:
        st.error(f"Token Error: {e}")
        return None

# Main UI
st.title("📤 WordPress CPT to n8n")

st.subheader("1. Create Custom Post JSON")
cpt_type = st.text_input("Post Type", value="my_custom_post")
cpt_title = st.text_input("Post Title", value="My Post")
cpt_content = st.text_area("Post Content", value="Some content...")

if st.button("Generate & Send JSON"):
    cpt_json = {
        "post_type": cpt_type,
        "title": cpt_title,
        "content": cpt_content
    }
    st.json(cpt_json)

    if n8n_webhook:
        try:
            headers = {"Authorization": f"Bearer {oauth_token}"} if oauth_token else {}
            r = requests.post(n8n_webhook, json=cpt_json, headers=headers)
            r.raise_for_status()
            st.success(f"✅ Sent to n8n! Status Code: {r.status_code}")
            try:
                st.json(r.json())
            except:
                st.text(r.text)
        except Exception as e:
            st.error(f"❌ n8n error: {e}")
    else:
        st.download_button("Download .json", data=json.dumps(cpt_json, indent=2), file_name="cpt.json")

# Divider
st.divider()

# Generate WordPress Token (JWT)
st.subheader("2. 🔐 Generate WordPress Bearer Token (JWT Auth)")
if st.button("Get WordPress Token"):
    if all([wp_url, wp_user, wp_pass]):
        token = get_bearer_token(wp_url, wp_user, wp_pass)
        if token:
            st.success("JWT Token")
            st.code(token)
        else:
            st.warning("Could not retrieve token.")
    else:
        st.warning("Enter all credentials first.")

# Divider
st.divider()

# Pull .json files from DOM endpoint
st.subheader("3. 🌐 Load .json Files from Remote Endpoint")
json_feed_url = st.text_input("Enter Endpoint or Folder URL (must return .json or list of URLs)", placeholder="https://jsonplaceholder.typicode.com/posts")

if st.button("Fetch JSON Data"):
    try:
        res = requests.get(json_feed_url)
        res.raise_for_status()
        content = res.json()

        if isinstance(content, list):
            st.write(f"🗂 Found {len(content)} items")
            for i, item in enumerate(content, 1):
                if isinstance(item, str) and item.endswith(".json"):
                    st.markdown(f"{i}. 📁 [{item}]({item})")
                elif isinstance(item, dict):
                    with st.expander(f"Item {i}"):
                        st.json(item)
                else:
                    st.write(item)
        else:
            st.json(content)
    except Exception as e:
        st.error(f"❌ Could not load JSON: {e}")
