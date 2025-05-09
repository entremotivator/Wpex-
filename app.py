import streamlit as st
import requests
import json
import base64
import time
import uuid
import webbrowser
import urllib.parse
from typing import Dict, List, Any, Optional
import pandas as pd
import plotly.express as px
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="WordPress CPT to n8n Converter",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
        color: #1E88E5;
    }
    .sub-header {
        font-size: 1.8rem;
        font-weight: 600;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        color: #0D47A1;
    }
    .card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        margin-bottom: 1rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin-bottom: 1rem;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        margin-bottom: 1rem;
    }
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        color: #856404;
        margin-bottom: 1rem;
    }
    .login-btn {
        background-color: #1E88E5;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.3rem;
        text-decoration: none;
        font-weight: 600;
        display: inline-block;
        text-align: center;
        cursor: pointer;
    }
    .login-btn:hover {
        background-color: #0D47A1;
    }
    .stButton>button {
        width: 100%;
    }
    .node-preview {
        border: 1px solid #e9ecef;
        border-radius: 0.5rem;
        padding: 1rem;
        background-color: #f8f9fa;
    }
    .sidebar-header {
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #1E88E5;
    }
    .cpt-button {
        margin-bottom: 0.5rem;
    }
    .footer {
        margin-top: 3rem;
        text-align: center;
        color: #6c757d;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "wordpress_url" not in st.session_state:
    st.session_state.wordpress_url = ""
if "username" not in st.session_state:
    st.session_state.username = ""
if "password" not in st.session_state:
    st.session_state.password = ""
if "auth_token" not in st.session_state:
    st.session_state.auth_token = ""
if "custom_post_types" not in st.session_state:
    st.session_state.custom_post_types = []
if "selected_cpt" not in st.session_state:
    st.session_state.selected_cpt = None
if "n8n_nodes" not in st.session_state:
    st.session_state.n8n_nodes = {}
if "auth_state" not in st.session_state:
    st.session_state.auth_state = str(uuid.uuid4())
if "auth_callback_received" not in st.session_state:
    st.session_state.auth_callback_received = False
if "cpt_data" not in st.session_state:
    st.session_state.cpt_data = {}
if "cpt_stats" not in st.session_state:
    st.session_state.cpt_stats = {}
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None
if "error_message" not in st.session_state:
    st.session_state.error_message = None
if "success_message" not in st.session_state:
    st.session_state.success_message = None

# Function to simulate WordPress OAuth flow
def generate_wordpress_auth_url(site_url: str) -> str:
    """
    Generate a URL for WordPress authentication
    
    In a real implementation, this would use the WordPress OAuth endpoints.
    For this demo, we'll create a simulated flow.
    """
    # In a real implementation, this would be the OAuth authorization URL
    # For demo purposes, we'll create a simulated URL
    callback_url = "http://localhost:8501/callback"
    state = st.session_state.auth_state
    
    # Clean up the site URL
    if not site_url.startswith(('http://', 'https://')):
        site_url = 'https://' + site_url
    
    # In a real implementation, this would be the actual WordPress OAuth URL
    # For demo purposes, we'll simulate with a redirect that would normally go to WP login
    auth_url = f"{site_url}/wp-admin/admin.php?page=auth-app&redirect_uri={urllib.parse.quote(callback_url)}&state={state}"
    
    return auth_url

# Function to handle the simulated OAuth callback
def handle_auth_callback() -> None:
    """
    Handle the callback from WordPress OAuth
    
    In a real implementation, this would exchange the authorization code for an access token.
    For this demo, we'll simulate the process.
    """
    # Simulate successful authentication
    st.session_state.authenticated = True
    st.session_state.auth_token = f"simulated_token_{uuid.uuid4()}"
    st.session_state.auth_callback_received = True
    st.session_state.success_message = "Authentication successful! You can now access your WordPress custom post types."
    
    # Fetch custom post types after successful authentication
    fetch_custom_post_types()

# Function to authenticate with WordPress REST API using Basic Auth
def authenticate_with_credentials(url: str, username: str, password: str) -> bool:
    """Authenticate with WordPress REST API using username and password"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        auth_url = f"{url}/wp-json/wp/v2/users/me"
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers = {
            "Authorization": f"Basic {credentials}"
        }
        response = requests.get(auth_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            st.session_state.authenticated = True
            st.session_state.wordpress_url = url
            st.session_state.success_message = "Authentication successful! You can now access your WordPress custom post types."
            return True
        else:
            st.session_state.error_message = f"Authentication failed: {response.status_code} - {response.text}"
            return False
    except Exception as e:
        st.session_state.error_message = f"Error connecting to WordPress: {str(e)}"
        return False

# Function to fetch custom post types
def fetch_custom_post_types() -> None:
    """Fetch custom post types from WordPress"""
    try:
        url = st.session_state.wordpress_url
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        types_url = f"{url}/wp-json/wp/v2/types"
        
        # Use token if available, otherwise use basic auth
        headers = {}
        if st.session_state.auth_token:
            headers["Authorization"] = f"Bearer {st.session_state.auth_token}"
        elif st.session_state.username and st.session_state.password:
            credentials = base64.b64encode(f"{st.session_state.username}:{st.session_state.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        response = requests.get(types_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            types_data = response.json()
            # Filter out built-in post types
            custom_types = [
                post_type for post_type, data in types_data.items() 
                if post_type not in ['post', 'page', 'attachment', 'revision', 'nav_menu_item', 'wp_block']
            ]
            st.session_state.custom_post_types = custom_types
            st.session_state.last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Initialize stats for each CPT
            for cpt in custom_types:
                if cpt not in st.session_state.cpt_stats:
                    st.session_state.cpt_stats[cpt] = {"count": 0, "last_updated": None}
        else:
            st.session_state.error_message = f"Could not retrieve post types: {response.status_code} - {response.text}"
    except Exception as e:
        st.session_state.error_message = f"Error getting custom post types: {str(e)}"

# Function to get posts of a specific custom post type
def get_cpt_posts(post_type: str) -> List[Dict]:
    """Get posts of a specific custom post type"""
    try:
        url = st.session_state.wordpress_url
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        posts_url = f"{url}/wp-json/wp/v2/{post_type}?per_page=100"
        
        # Use token if available, otherwise use basic auth
        headers = {}
        if st.session_state.auth_token:
            headers["Authorization"] = f"Bearer {st.session_state.auth_token}"
        elif st.session_state.username and st.session_state.password:
            credentials = base64.b64encode(f"{st.session_state.username}:{st.session_state.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        response = requests.get(posts_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            posts = response.json()
            # Update stats
            st.session_state.cpt_stats[post_type] = {
                "count": len(posts),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            return posts
        else:
            st.session_state.error_message = f"Could not retrieve posts: {response.status_code} - {response.text}"
            return []
    except Exception as e:
        st.session_state.error_message = f"Error getting posts: {str(e)}"
        return []

# Function to convert WordPress CPT to n8n node
def convert_to_n8n_node(post_type: str, posts: List[Dict]) -> Dict:
    """Convert WordPress custom post type to n8n node format"""
    if not posts:
        return {}
    
    # Extract fields from the first post to determine structure
    sample_post = posts[0]
    fields = list(sample_post.keys())
    
    # Create n8n node definition
    node = {
        "name": f"WordPress {post_type.capitalize()}",
        "description": f"Operations for WordPress {post_type} custom post type",
        "version": 1,
        "defaults": {
            "name": f"WordPress {post_type.capitalize()}"
        },
        "inputs": ["main"],
        "outputs": ["main"],
        "properties": [
            {
                "displayName": "Operation",
                "name": "operation",
                "type": "options",
                "options": [
                    {
                        "name": "Get All",
                        "value": "getAll"
                    },
                    {
                        "name": "Get One",
                        "value": "get"
                    },
                    {
                        "name": "Create",
                        "value": "create"
                    },
                    {
                        "name": "Update",
                        "value": "update"
                    },
                    {
                        "name": "Delete",
                        "value": "delete"
                    }
                ],
                "default": "getAll",
                "description": "Operation to perform"
            }
        ],
        "credentials": [
            {
                "name": "wordpressApi",
                "required": True
            }
        ]
    }
    
    # Add field properties for create/update operations
    for field in fields:
        if field in ['id', 'date', 'modified', 'guid', 'link', '_links']:
            continue  # Skip system fields
            
        field_type = "string"
        if isinstance(sample_post.get(field), int):
            field_type = "number"
        elif isinstance(sample_post.get(field), bool):
            field_type = "boolean"
        elif isinstance(sample_post.get(field), dict):
            field_type = "json"
        
        node["properties"].append({
            "displayName": field.capitalize().replace("_", " "),
            "name": field,
            "type": field_type,
            "default": "",
            "displayOptions": {
                "show": {
                    "operation": ["create", "update"]
                }
            }
        })
    
    # Add ID field for get, update, delete operations
    node["properties"].append({
        "displayName": "ID",
        "name": "id",
        "type": "number",
        "required": True,
        "displayOptions": {
            "show": {
                "operation": ["get", "update", "delete"]
            }
        },
        "default": 0,
        "description": f"ID of the {post_type} to operate on"
    })
    
    # Add additional options for getAll operation
    node["properties"].append({
        "displayName": "Return All",
        "name": "returnAll",
        "type": "boolean",
        "default": False,
        "displayOptions": {
            "show": {
                "operation": ["getAll"]
            }
        },
        "description": "Whether to return all results or only up to a given limit"
    })
    
    node["properties"].append({
        "displayName": "Limit",
        "name": "limit",
        "type": "number",
        "default": 50,
        "displayOptions": {
            "show": {
                "operation": ["getAll"],
                "returnAll": [False]
            }
        },
        "description": "Max number of results to return"
    })
    
    # Add additional filtering options
    node["properties"].append({
        "displayName": "Additional Options",
        "name": "additionalOptions",
        "type": "collection",
        "placeholder": "Add Option",
        "default": {},
        "displayOptions": {
            "show": {
                "operation": ["getAll", "get"]
            }
        },
        "options": [
            {
                "displayName": "Order By",
                "name": "orderBy",
                "type": "options",
                "options": [
                    {"name": "Date", "value": "date"},
                    {"name": "ID", "value": "id"},
                    {"name": "Title", "value": "title"},
                    {"name": "Slug", "value": "slug"}
                ],
                "default": "date",
                "description": "Field to order results by"
            },
            {
                "displayName": "Order",
                "name": "order",
                "type": "options",
                "options": [
                    {"name": "Ascending", "value": "asc"},
                    {"name": "Descending", "value": "desc"}
                ],
                "default": "desc",
                "description": "Direction to order results"
            },
            {
                "displayName": "Status",
                "name": "status",
                "type": "options",
                "options": [
                    {"name": "Published", "value": "publish"},
                    {"name": "Draft", "value": "draft"},
                    {"name": "Pending", "value": "pending"},
                    {"name": "Private", "value": "private"},
                    {"name": "Any", "value": "any"}
                ],
                "default": "publish",
                "description": "Filter by post status"
            }
        ]
    })
    
    return node

# Function to generate n8n workflow for a CPT
def generate_n8n_workflow(post_type: str, node_definition: Dict) -> Dict:
    """Generate a complete n8n workflow for a custom post type"""
    workflow = {
        "name": f"WordPress {post_type.capitalize()} Workflow",
        "nodes": [
            {
                "parameters": {
                    "rule": {
                        "interval": [
                            {
                                "field": "hours",
                                "minutesInterval": 1
                            }
                        ]
                    }
                },
                "name": "Schedule Trigger",
                "type": "n8n-nodes-base.scheduleTrigger",
                "typeVersion": 1,
                "position": [
                    250,
                    300
                ]
            },
            {
                "parameters": {
                    "operation": "getAll",
                    "returnAll": True
                },
                "name": f"WordPress {post_type.capitalize()}",
                "type": f"n8n-nodes-base.wordpress{post_type.capitalize()}",
                "typeVersion": 1,
                "position": [
                    500,
                    300
                ],
                "credentials": {
                    "wordpressApi": {
                        "id": "1",
                        "name": "WordPress account"
                    }
                }
            },
            {
                "parameters": {
                    "operation": "appendOrUpdate",
                    "documentId": {
                        "__rl": True,
                        "value": "1CxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxQ",
                        "mode": "list",
                        "cachedResultName": "WordPress Data Sheet",
                        "cachedResultUrl": "https://docs.google.com/spreadsheets/d/1CxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxQ/edit"
                    },
                    "sheetName": {
                        "__rl": True,
                        "value": 0,
                        "mode": "list",
                        "cachedResultName": "Sheet1",
                    },
                    "columns": {
                        "mappingMode": "autoMapInputData",
                        "value": {},
                        "matchingColumns": []
                    },
                    "options": {}
                },
                "name": "Google Sheets",
                "type": "n8n-nodes-base.googleSheets",
                "typeVersion": 3,
                "position": [
                    750,
                    300
                ]
            }
        ],
        "connections": {
            "Schedule Trigger": {
                "main": [
                    [
                        {
                            "node": f"WordPress {post_type.capitalize()}",
                            "type": "main",
                            "index": 0
                        }
                    ]
                ]
            },
            [f"WordPress {post_type.capitalize()}"]: {
                "main": [
                    [
                        {
                            "node": "Google Sheets",
                            "type": "main",
                            "index": 0
                        }
                    ]
                ]
            }
        }
    }
    
    return workflow

# Function to analyze CPT data
def analyze_cpt_data(posts: List[Dict]) -> Dict:
    """Analyze custom post type data and generate statistics"""
    if not posts:
        return {}
    
    analysis = {
        "total_posts": len(posts),
        "fields": {},
        "status_distribution": {},
        "creation_dates": {},
        "modification_dates": {}
    }
    
    # Get a list of all fields
    sample_post = posts[0]
    fields = list(sample_post.keys())
    
    # Analyze each field
    for field in fields:
        if field in ['id', 'date', 'modified', 'guid', 'link', '_links']:
            continue  # Skip system fields
            
        field_types = set()
        non_empty_values = 0
        
        for post in posts:
            if field in post and post[field]:
                non_empty_values += 1
                field_types.add(type(post[field]).__name__)
        
        analysis["fields"][field] = {
            "types": list(field_types),
            "fill_rate": round(non_empty_values / len(posts) * 100, 2) if posts else 0
        }
    
    # Analyze status distribution
    for post in posts:
        status = post.get('status', 'unknown')
        if status in analysis["status_distribution"]:
            analysis["status_distribution"][status] += 1
        else:
            analysis["status_distribution"][status] = 1
    
    # Analyze creation dates by month
    for post in posts:
        if 'date' in post:
            date_str = post['date']
            try:
                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                month_year = date_obj.strftime('%Y-%m')
                if month_year in analysis["creation_dates"]:
                    analysis["creation_dates"][month_year] += 1
                else:
                    analysis["creation_dates"][month_year] = 1
            except:
                pass
    
    # Sort dates chronologically
    analysis["creation_dates"] = dict(sorted(analysis["creation_dates"].items()))
    
    return analysis

# Sidebar for authentication and navigation
with st.sidebar:
    st.markdown('<div class="sidebar-header">WordPress CPT to n8n Converter</div>', unsafe_allow_html=True)
    
    if not st.session_state.authenticated:
        st.markdown("### Connect to WordPress")
        
        auth_tab1, auth_tab2 = st.tabs(["Login with WordPress", "Manual Credentials"])
        
        with auth_tab1:
            st.markdown("Enter your WordPress site URL and click the button to log in.")
            wordpress_url = st.text_input("WordPress Site URL", placeholder="example.com", value=st.session_state.wordpress_url)
            
            if st.button("Login with WordPress", key="login_button"):
                if wordpress_url:
                    st.session_state.wordpress_url = wordpress_url
                    auth_url = generate_wordpress_auth_url(wordpress_url)
                    
                    # In a real app, this would redirect to WordPress OAuth
                    # For demo purposes, we'll simulate the flow
                    st.markdown(f"""
                    <div class="info-box">
                        <p>In a real implementation, you would be redirected to WordPress to authenticate.</p>
                        <p>For this demo, we'll simulate a successful authentication.</p>
                        <a href="#" class="login-btn" onclick="setTimeout(function(){{window.location.reload()}}, 2000)">
                            Simulate WordPress Login
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Simulate the callback after a delay
                    if st.button("Complete Authentication", key="complete_auth"):
                        handle_auth_callback()
                        st.experimental_rerun()
                else:
                    st.warning("Please enter your WordPress site URL")
        
        with auth_tab2:
            st.markdown("Enter your WordPress credentials manually.")
            with st.form("manual_auth_form"):
                wordpress_url = st.text_input("WordPress URL", placeholder="example.com", value=st.session_state.wordpress_url)
                username = st.text_input("Username", value=st.session_state.username)
                password = st.text_input("Password", type="password", value=st.session_state.password)
                
                submit = st.form_submit_button("Connect")
                
                if submit:
                    if wordpress_url and username and password:
                        st.session_state.wordpress_url = wordpress_url
                        st.session_state.username = username
                        st.session_state.password = password
                        
                        if authenticate_with_credentials(wordpress_url, username, password):
                            fetch_custom_post_types()
                            st.experimental_rerun()
                    else:
                        st.warning("Please fill in all fields")
    else:
        st.markdown(f"""
        <div class="success-box">
            ✅ Connected to {st.session_state.wordpress_url}
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Disconnect", key="disconnect_btn"):
            st.session_state.authenticated = False
            st.session_state.wordpress_url = ""
            st.session_state.username = ""
            st.session_state.password = ""
            st.session_state.auth_token = ""
            st.session_state.custom_post_types = []
            st.session_state.selected_cpt = None
            st.session_state.n8n_nodes = {}
            st.session_state.cpt_data = {}
            st.session_state.cpt_stats = {}
            st.session_state.last_refresh = None
            st.experimental_rerun()
        
        st.markdown("### Custom Post Types")
        
        if st.button("Refresh Custom Post Types", key="refresh_cpt_btn"):
            fetch_custom_post_types()
            st.experimental_rerun()
        
        if st.session_state.last_refresh:
            st.caption(f"Last refreshed: {st.session_state.last_refresh}")
        
        if st.session_state.custom_post_types:
            for cpt in st.session_state.custom_post_types:
                # Show stats if available
                stats = ""
                if cpt in st.session_state.cpt_stats and st.session_state.cpt_stats[cpt]["count"] > 0:
                    stats = f" ({st.session_state.cpt_stats[cpt]['count']} items)"
                
                if st.button(f"{cpt.capitalize()}{stats}", key=f"cpt_{cpt}", use_container_width=True, 
                           help=f"View and convert {cpt} to n8n node"):
                    st.session_state.selected_cpt = cpt
                    posts = get_cpt_posts(cpt)
                    if posts:
                        st.session_state.cpt_data[cpt] = posts
                        st.session_state.n8n_nodes[cpt] = convert_to_n8n_node(cpt, posts)
                        # Generate analysis
                        analysis = analyze_cpt_data(posts)
                        st.session_state.cpt_stats[cpt]["analysis"] = analysis
                    st.experimental_rerun()
        else:
            st.info("No custom post types found. Click 'Refresh Custom Post Types' to try again.")
        
        # Quick links section
        st.markdown("### Quick Links")
        if st.session_state.wordpress_url:
            admin_url = f"{st.session_state.wordpress_url}/wp-admin"
            if not admin_url.startswith(('http://', 'https://')):
                admin_url = 'https://' + admin_url
            st.markdown(f"[WordPress Admin]({admin_url})")
        
        st.markdown("[n8n Documentation](https://docs.n8n.io/)")
        st.markdown("[WordPress REST API Docs](https://developer.wordpress.org/rest-api/)")

# Main content
st.markdown('<div class="main-header">WordPress CPT to n8n Node Converter</div>', unsafe_allow_html=True)

# Show success/error messages if any
if st.session_state.success_message:
    st.markdown(f"""
    <div class="success-box">
        {st.session_state.success_message}
    </div>
    """, unsafe_allow_html=True)
    # Clear the message after displaying
    st.session_state.success_message = None

if st.session_state.error_message:
    st.markdown(f"""
    <div class="warning-box">
        {st.session_state.error_message}
    </div>
    """, unsafe_allow_html=True)
    # Clear the message after displaying
    st.session_state.error_message = None

if not st.session_state.authenticated:
    st.markdown("""
    <div class="card">
        <h2>Transform WordPress Custom Post Types into n8n Nodes</h2>
        <p>Connect your WordPress site to automatically convert custom post types into n8n-compatible node definitions.</p>
        <p>This tool helps you integrate WordPress content with n8n workflows without writing any code.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Features section
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="card">
            <h3>🔄 Automatic Conversion</h3>
            <p>Automatically detect and convert WordPress custom post types into n8n node definitions.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card">
            <h3>📊 Data Analysis</h3>
            <p>Analyze your WordPress data structure and visualize content patterns.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="card">
            <h3>🔌 Ready for n8n</h3>
            <p>Export node definitions and sample workflows ready to use in n8n.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # How it works section
    st.markdown('<div class="sub-header">How It Works</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <ol>
            <li><strong>Connect your WordPress site</strong> - Use the login button in the sidebar to authenticate with your WordPress site</li>
            <li><strong>Select a custom post type</strong> - Browse your available custom post types in the sidebar</li>
            <li><strong>Generate n8n node</strong> - Convert the selected custom post type into an n8n node definition</li>
            <li><strong>Export and use</strong> - Download the node definition and import it into your n8n instance</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    
    # Example section
    with st.expander("See an example n8n node definition"):
        st.code("""
{
  "name": "WordPress Product",
  "description": "Operations for WordPress product custom post type",
  "version": 1,
  "defaults": {
    "name": "WordPress Product"
  },
  "inputs": ["main"],
  "outputs": ["main"],
  "properties": [
    {
      "displayName": "Operation",
      "name": "operation",
      "type": "options",
      "options": [
        {"name": "Get All", "value": "getAll"},
        {"name": "Get One", "value": "get"},
        {"name": "Create", "value": "create"},
        {"name": "Update", "value": "update"},
        {"name": "Delete", "value": "delete"}
      ],
      "default": "getAll",
      "description": "Operation to perform"
    },
    {
      "displayName": "Title",
      "name": "title",
      "type": "string",
      "default": "",
      "displayOptions": {
        "show": {"operation": ["create", "update"]}
      }
    },
    {
      "displayName": "Price",
      "name": "price",
      "type": "number",
      "default": 0,
      "displayOptions": {
        "show": {"operation": ["create", "update"]}
      }
    }
  ]
}
        """, language="json")
    
    # Get started section
    st.markdown('<div class="sub-header">Get Started</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card">
        <p>To get started, click the <strong>"Login with WordPress"</strong> button in the sidebar and enter your WordPress site URL.</p>
        <p>You'll be redirected to authenticate with your WordPress site, and then you can start converting your custom post types to n8n nodes.</p>
    </div>
    """, unsafe_allow_html=True)
    
else:
    if st.session_state.selected_cpt:
        cpt = st.session_state.selected_cpt
        
        st.markdown(f'<div class="sub-header">Custom Post Type: {cpt.capitalize()}</div>', unsafe_allow_html=True)
        
        # Create tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["n8n Node", "Data Explorer", "Analysis", "Workflow"])
        
        with tab1:
            st.markdown("### n8n Node Definition")
            if cpt in st.session_state.n8n_nodes:
                st.markdown("""
                <div class="info-box">
                    This is the n8n node definition for your custom post type. You can download this JSON file and use it to create a custom n8n node.
                </div>
                """, unsafe_allow_html=True)
                
                st.json(st.session_state.n8n_nodes[cpt])
                
                # Download buttons for n8n node
                col1, col2 = st.columns(2)
                with col1:
                    node_json = json.dumps(st.session_state.n8n_nodes[cpt], indent=2)
                    st.download_button(
                        label="Download Node Definition",
                        data=node_json,
                        file_name=f"wordpress-{cpt}-node.json",
                        mime="application/json"
                    )
                
                with col2:
                    # Implementation instructions
                    with st.expander("How to use this node definition"):
                        st.markdown("""
                        ### Using Your Custom n8n Node
                        
                        1. **Create a custom n8n node:**
                           - Save the JSON definition to a file
                           - Follow the [n8n custom nodes documentation](https://docs.n8n.io/integrations/creating-nodes/code/)
                        
                        2. **Alternative approach:**
                           - Use the HTTP Request node in n8n to call the WordPress REST API
                           - Use the endpoint: `https://your-site.com/wp-json/wp/v2/{custom-post-type}`
                        
                        3. **Authentication:**
                           - Create an Application Password in WordPress
                           - Use Basic Authentication with your credentials
                        """)
            else:
                st.info(f"Select {cpt} from the sidebar to generate the n8n node definition")
        
        with tab2:
            st.markdown("### Data Explorer")
            
            if cpt in st.session_state.cpt_data and st.session_state.cpt_data[cpt]:
                posts = st.session_state.cpt_data[cpt]
                
                # Data filtering options
                col1, col2 = st.columns(2)
                with col1:
                    # Get all possible statuses
                    statuses = list(set(post.get('status', 'unknown') for post in posts))
                    selected_status = st.selectbox("Filter by Status", ["All"] + statuses)
                
                with col2:
                    # Search functionality
                    search_term = st.text_input("Search", placeholder="Enter search term...")
                
                # Filter the data
                filtered_posts = posts
                if selected_status != "All":
                    filtered_posts = [post for post in filtered_posts if post.get('status') == selected_status]
                
                if search_term:
                    # Search in title and content if they exist
                    filtered_posts = [
                        post for post in filtered_posts 
                        if (
                            (isinstance(post.get('title'), dict) and search_term.lower() in post.get('title', {}).get('rendered', '').lower()) or
                            (isinstance(post.get('title'), str) and search_term.lower() in post.get('title', '').lower()) or
                            (isinstance(post.get('content'), dict) and search_term.lower() in post.get('content', {}).get('rendered', '').lower())
                        )
                    ]
                
                # Show data count
                st.markdown(f"Showing {len(filtered_posts)} of {len(posts)} items")
                
                # Create a more user-friendly data table
                if filtered_posts:
                    # Extract key fields for the table
                    table_data = []
                    for post in filtered_posts:
                        row = {
                            "ID": post.get('id', 'N/A'),
                            "Title": post.get('title', {}).get('rendered', 'Untitled') if isinstance(post.get('title'), dict) else post.get('title', 'Untitled'),
                            "Status": post.get('status', 'N/A'),
                            "Date": post.get('date', 'N/A')
                        }
                        table_data.append(row)
                    
                    # Convert to DataFrame for display
                    df = pd.DataFrame(table_data)
                    st.dataframe(df, use_container_width=True)
                    
                    # Item details expander
                    with st.expander("View Item Details"):
                        # Let user select an item to view details
                        item_ids = [str(post.get('id', 'N/A')) for post in filtered_posts]
                        item_titles = [post.get('title', {}).get('rendered', f"Item {i+1}") if isinstance(post.get('title'), dict) else post.get('title', f"Item {i+1}") for i, post in enumerate(filtered_posts)]
                        
                        # Create a dictionary mapping titles to indices
                        title_to_index = {f"{item_titles[i]} (ID: {item_ids[i]})": i for i in range(len(item_titles))}
                        
                        selected_item_title = st.selectbox("Select an item to view details", list(title_to_index.keys()))
                        selected_index = title_to_index[selected_item_title]
                        selected_item = filtered_posts[selected_index]
                        
                        # Display all fields for the selected item
                        st.json(selected_item)
                
                # Download button for raw data
                posts_json = json.dumps(posts, indent=2)
                st.download_button(
                    label="Download Raw JSON Data",
                    data=posts_json,
                    file_name=f"wordpress-{cpt}-data.json",
                    mime="application/json"
                )
            else:
                st.info(f"No data available for {cpt}. Select it from the sidebar to load data.")
        
        with tab3:
            st.markdown("### Data Analysis")
            
            if cpt in st.session_state.cpt_stats and "analysis" in st.session_state.cpt_stats[cpt]:
                analysis = st.session_state.cpt_stats[cpt]["analysis"]
                
                # Overview metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Items", analysis["total_posts"])
                
                with col2:
                    # Count unique fields
                    field_count = len(analysis["fields"])
                    st.metric("Fields", field_count)
                
                with col3:
                    # Count statuses
                    status_count = len(analysis["status_distribution"])
                    st.metric("Status Types", status_count)
                
                # Status distribution chart
                if analysis["status_distribution"]:
                    st.markdown("#### Status Distribution")
                    status_df = pd.DataFrame({
                        "Status": list(analysis["status_distribution"].keys()),
                        "Count": list(analysis["status_distribution"].values())
                    })
                    fig = px.pie(status_df, values="Count", names="Status", title="Content Status Distribution")
                    st.plotly_chart(fig, use_container_width=True)
                
                # Creation date timeline
                if analysis["creation_dates"]:
                    st.markdown("#### Content Creation Timeline")
                    dates_df = pd.DataFrame({
                        "Month": list(analysis["creation_dates"].keys()),
                        "Count": list(analysis["creation_dates"].values())
                    })
                    fig = px.line(dates_df, x="Month", y="Count", title="Content Creation Over Time")
                    st.plotly_chart(fig, use_container_width=True)
                
                # Field analysis
                if analysis["fields"]:
                    st.markdown("#### Field Analysis")
                    
                    # Create a dataframe for field analysis
                    field_data = []
                    for field_name, field_info in analysis["fields"].items():
                        field_data.append({
                            "Field": field_name,
                            "Types": ", ".join(field_info["types"]),
                            "Fill Rate (%)": field_info["fill_rate"]
                        })
                    
                    field_df = pd.DataFrame(field_data)
                    st.dataframe(field_df, use_container_width=True)
                    
                    # Field fill rate chart
                    st.markdown("#### Field Fill Rates")
                    fig = px.bar(
                        field_df, 
                        x="Field", 
                        y="Fill Rate (%)", 
                        title="Field Completion Rates",
                        labels={"Fill Rate (%)": "Completion %", "Field": "Field Name"}
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"No analysis available for {cpt}. Select it from the sidebar to generate analysis.")
        
        with tab4:
            st.markdown("### n8n Workflow")
            
            if cpt in st.session_state.n8n_nodes:
                # Generate a sample workflow
                workflow = generate_n8n_workflow(cpt, st.session_state.n8n_nodes[cpt])
                
                st.markdown("""
                <div class="info-box">
                    This is a sample n8n workflow that uses your custom post type. It fetches data from WordPress and exports it to Google Sheets.
                </div>
                """, unsafe_allow_html=True)
                
                # Display the workflow
                st.json(workflow)
                
                # Download button for workflow
                workflow_json = json.dumps(workflow, indent=2)
                st.download_button(
                    label="Download Sample Workflow",
                    data=workflow_json,
                    file_name=f"wordpress-{cpt}-workflow.json",
                    mime="application/json"
                )
                
                # Workflow usage instructions
                with st.expander("How to use this workflow"):
                    st.markdown("""
                    ### Importing the Workflow to n8n
                    
                    1. **Download the workflow JSON** using the button above
                    2. **In your n8n instance:**
                       - Go to Workflows
                       - Click "Import from File"
                       - Select the downloaded JSON file
                    
                    3. **Configure credentials:**
                       - Set up WordPress API credentials
                       - Configure Google Sheets credentials if using that node
                    
                    4. **Customize the workflow:**
                       - Adjust the schedule as needed
                       - Modify the Google Sheets document ID or other destination
                       - Add additional processing nodes as required
                    
                    5. **Activate the workflow** when you're ready to run it
                    """)
                
                # Workflow visualization placeholder
                st.markdown("#### Workflow Visualization")
                st.markdown("""
                <div class="node-preview">
                    <div style="display: flex; align-items: center; margin-bottom: 20px;">
                        <div style="width: 120px; height: 60px; background-color: #EFEFEF; border-radius: 5px; display: flex; align-items: center; justify-content: center; margin-right: 40px; border: 1px solid #DDD;">
                            Schedule<br>Trigger
                        </div>
                        <div style="width: 40px; height: 2px; background-color: #999;"></div>
                        <div style="width: 120px; height: 60px; background-color: #E1F5FE; border-radius: 5px; display: flex; align-items: center; justify-content: center; margin-right: 40px; margin-left: 10px; border: 1px solid #B3E5FC;">
                            WordPress<br>{cpt}
                        </div>
                        <div style="width: 40px; height: 2px; background-color: #999;"></div>
                        <div style="width: 120px; height: 60px; background-color: #E8F5E9; border-radius: 5px; display: flex; align-items: center; justify-content: center; border: 1px solid #C8E6C9;">
                            Google<br>Sheets
                        </div>
                    </div>
                    <p style="color: #666; font-style: italic; text-align: center;">This workflow runs on a schedule, fetches WordPress data, and exports it to Google Sheets.</p>
                </div>
                """.replace("{cpt}", cpt.capitalize()), unsafe_allow_html=True)
            else:
                st.info(f"No node definition available for {cpt}. Select it from the sidebar to generate a workflow.")
    else:
        # Dashboard view when authenticated but no CPT selected
        st.markdown('<div class="sub-header">WordPress Dashboard</div>', unsafe_allow_html=True)
        
        # Overview cards
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="card">
                <h3>Custom Post Types</h3>
                <p style="font-size: 2rem; font-weight: bold; text-align: center;">{cpt_count}</p>
            </div>
            """.replace("{cpt_count}", str(len(st.session_state.custom_post_types))), unsafe_allow_html=True)
        
        with col2:
            # Count total items across all CPTs
            total_items = sum(
                st.session_state.cpt_stats[cpt]["count"] 
                for cpt in st.session_state.cpt_stats 
                if "count" in st.session_state.cpt_stats[cpt]
            )
            
            st.markdown("""
            <div class="card">
                <h3>Total Content Items</h3>
                <p style="font-size: 2rem; font-weight: bold; text-align: center;">{item_count}</p>
            </div>
            """.replace("{item_count}", str(total_items)), unsafe_allow_html=True)
        
        with col3:
            # Count converted nodes
            node_count = len(st.session_state.n8n_nodes)
            
            st.markdown("""
            <div class="card">
                <h3>n8n Nodes Created</h3>
                <p style="font-size: 2rem; font-weight: bold; text-align: center;">{node_count}</p>
            </div>
            """.replace("{node_count}", str(node_count)), unsafe_allow_html=True)
        
        # CPT list with stats
        if st.session_state.custom_post_types:
            st.markdown('<div class="sub-header">Available Custom Post Types</div>', unsafe_allow_html=True)
            
            # Create a table of CPTs with their stats
            cpt_data = []
            for cpt in st.session_state.custom_post_types:
                count = st.session_state.cpt_stats.get(cpt, {}).get("count", 0)
                last_updated = st.session_state.cpt_stats.get(cpt, {}).get("last_updated", "Never")
                node_created = "Yes" if cpt in st.session_state.n8n_nodes else "No"
                
                cpt_data.append({
                    "Custom Post Type": cpt.capitalize(),
                    "Items": count,
                    "Last Updated": last_updated,
                    "n8n Node Created": node_created
                })
            
            # Convert to DataFrame and display
            if cpt_data:
                cpt_df = pd.DataFrame(cpt_data)
                st.dataframe(cpt_df, use_container_width=True)
                
                st.markdown("""
                <div class="info-box">
                    Click on a custom post type in the sidebar to view its data and generate an n8n node.
                </div>
                """, unsafe_allow_html=True)
            
            # If we have some stats, show a chart
            if any(st.session_state.cpt_stats.get(cpt, {}).get("count", 0) > 0 for cpt in st.session_state.custom_post_types):
                st.markdown('<div class="sub-header">Content Distribution</div>', unsafe_allow_html=True)
                
                # Create data for the chart
                chart_data = []
                for cpt in st.session_state.custom_post_types:
                    count = st.session_state.cpt_stats.get(cpt, {}).get("count", 0)
                    if count > 0:
                        chart_data.append({
                            "Custom Post Type": cpt.capitalize(),
                            "Count": count
                        })
                
                if chart_data:
                    chart_df = pd.DataFrame(chart_data)
                    fig = px.bar(
                        chart_df, 
                        x="Custom Post Type", 
                        y="Count", 
                        title="Content Items by Custom Post Type",
                        color="Custom Post Type"
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        # Getting started guide
        st.markdown('<div class="sub-header">Getting Started</div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="card">
            <h3>Next Steps</h3>
            <ol>
                <li><strong>Select a custom post type</strong> from the sidebar to explore its data</li>
                <li><strong>Generate an n8n node</strong> for your selected custom post type</li>
                <li><strong>Download the node definition</strong> to use in your n8n workflows</li>
                <li><strong>Create automated workflows</strong> that integrate your WordPress content with other systems</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="footer">
    WordPress CPT to n8n Node Converter | Created with Streamlit | v1.0.0
</div>
""", unsafe_allow_html=True)
