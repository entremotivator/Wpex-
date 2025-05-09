import streamlit as st
import requests
import json
import base64
import time
import uuid
import webbrowser
import urllib.parse
import os
import re
import hashlib
import hmac
import random
import string
from typing import Dict, List, Any, Optional, Tuple, Union
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import altair as alt
from PIL import Image
from io import BytesIO

# Set page config
st.set_page_config(
    page_title="Enterprise WordPress Integration Hub",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
with open("styles/main.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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
if "taxonomies" not in st.session_state:
    st.session_state.taxonomies = []
if "selected_cpt" not in st.session_state:
    st.session_state.selected_cpt = None
if "selected_taxonomy" not in st.session_state:
    st.session_state.selected_taxonomy = None
if "n8n_nodes" not in st.session_state:
    st.session_state.n8n_nodes = {}
if "zapier_integrations" not in st.session_state:
    st.session_state.zapier_integrations = {}
if "make_scenarios" not in st.session_state:
    st.session_state.make_scenarios = {}
if "auth_state" not in st.session_state:
    st.session_state.auth_state = str(uuid.uuid4())
if "auth_callback_received" not in st.session_state:
    st.session_state.auth_callback_received = False
if "cpt_data" not in st.session_state:
    st.session_state.cpt_data = {}
if "taxonomy_data" not in st.session_state:
    st.session_state.taxonomy_data = {}
if "media_data" not in st.session_state:
    st.session_state.media_data = {}
if "cpt_stats" not in st.session_state:
    st.session_state.cpt_stats = {}
if "taxonomy_stats" not in st.session_state:
    st.session_state.taxonomy_stats = {}
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None
if "error_message" not in st.session_state:
    st.session_state.error_message = None
if "success_message" not in st.session_state:
    st.session_state.success_message = None
if "site_info" not in st.session_state:
    st.session_state.site_info = {}
if "user_info" not in st.session_state:
    st.session_state.user_info = {}
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "integration_history" not in st.session_state:
    st.session_state.integration_history = []
if "field_mappings" not in st.session_state:
    st.session_state.field_mappings = {}
if "sync_settings" not in st.session_state:
    st.session_state.sync_settings = {
        "auto_sync": False,
        "sync_interval": 60,  # minutes
        "last_sync": None,
        "sync_targets": []
    }
if "api_logs" not in st.session_state:
    st.session_state.api_logs = []
if "favorites" not in st.session_state:
    st.session_state.favorites = []
if "recent_items" not in st.session_state:
    st.session_state.recent_items = []
if "custom_templates" not in st.session_state:
    st.session_state.custom_templates = []
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "dashboard"

# Constants
MAX_API_LOGS = 100
MAX_RECENT_ITEMS = 10
INTEGRATION_PLATFORMS = ["n8n", "Zapier", "Make (Integromat)", "Pipedream", "Power Automate", "Custom Webhook"]
SYNC_INTERVALS = [5, 15, 30, 60, 120, 360, 720, 1440]  # minutes
DEFAULT_TEMPLATE_TYPES = ["Content Sync", "E-commerce", "Membership", "Events", "Newsletter", "CRM"]

# Utility Functions
def generate_api_key() -> str:
    """Generate a random API key"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def log_api_request(endpoint: str, method: str, status_code: int, response_time: float) -> None:
    """Log API request to session state"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "response_time": response_time
    }
    
    # Add to beginning of list and maintain max size
    st.session_state.api_logs.insert(0, log_entry)
    if len(st.session_state.api_logs) > MAX_API_LOGS:
        st.session_state.api_logs = st.session_state.api_logs[:MAX_API_LOGS]

def add_to_recent_items(item_type: str, item_id: str, item_name: str) -> None:
    """Add item to recent items list"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Check if item already exists and remove it
    st.session_state.recent_items = [
        item for item in st.session_state.recent_items 
        if not (item["type"] == item_type and item["id"] == item_id)
    ]
    
    # Add new item at the beginning
    st.session_state.recent_items.insert(0, {
        "type": item_type,
        "id": item_id,
        "name": item_name,
        "timestamp": timestamp
    })
    
    # Maintain max size
    if len(st.session_state.recent_items) > MAX_RECENT_ITEMS:
        st.session_state.recent_items = st.session_state.recent_items[:MAX_RECENT_ITEMS]

def format_date(date_str: str) -> str:
    """Format ISO date string to readable format"""
    try:
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_obj.strftime("%b %d, %Y %H:%M")
    except:
        return date_str

def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text to specified length"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."

def get_content_preview(content: Any) -> str:
    """Extract readable preview from WordPress content field"""
    if not content:
        return ""
    
    if isinstance(content, dict) and 'rendered' in content:
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', content['rendered'])
        return truncate_text(text, 100)
    elif isinstance(content, str):
        return truncate_text(content, 100)
    
    return ""

def calculate_hash(data: str, secret: str) -> str:
    """Calculate HMAC hash for webhook security"""
    return hmac.new(
        secret.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

# Authentication Functions
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
    st.session_state.success_message = "Authentication successful! You can now access your WordPress site data."
    
    # Fetch site information
    fetch_site_info()
    
    # Fetch custom post types and taxonomies
    fetch_wordpress_data()

def authenticate_with_credentials(url: str, username: str, password: str) -> bool:
    """Authenticate with WordPress REST API using username and password"""
    start_time = time.time()
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        auth_url = f"{url}/wp-json/wp/v2/users/me"
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers = {
            "Authorization": f"Basic {credentials}"
        }
        response = requests.get(auth_url, headers=headers, timeout=10)
        
        # Log the API request
        response_time = time.time() - start_time
        log_api_request(auth_url, "GET", response.status_code, response_time)
        
        if response.status_code == 200:
            st.session_state.authenticated = True
            st.session_state.wordpress_url = url
            st.session_state.username = username
            st.session_state.password = password
            st.session_state.user_info = response.json()
            st.session_state.success_message = "Authentication successful! You can now access your WordPress site data."
            
            # Fetch site information
            fetch_site_info()
            
            # Fetch custom post types and taxonomies
            fetch_wordpress_data()
            
            return True
        else:
            st.session_state.error_message = f"Authentication failed: {response.status_code} - {response.text}"
            return False
    except Exception as e:
        st.session_state.error_message = f"Error connecting to WordPress: {str(e)}"
        return False

def fetch_site_info() -> None:
    """Fetch WordPress site information"""
    start_time = time.time()
    try:
        url = st.session_state.wordpress_url
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        site_url = f"{url}/wp-json"
        
        # Use token if available, otherwise use basic auth
        headers = {}
        if st.session_state.auth_token:
            headers["Authorization"] = f"Bearer {st.session_state.auth_token}"
        elif st.session_state.username and st.session_state.password:
            credentials = base64.b64encode(f"{st.session_state.username}:{st.session_state.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        response = requests.get(site_url, headers=headers, timeout=10)
        
        # Log the API request
        response_time = time.time() - start_time
        log_api_request(site_url, "GET", response.status_code, response_time)
        
        if response.status_code == 200:
            site_data = response.json()
            st.session_state.site_info = {
                "name": site_data.get("name", "WordPress Site"),
                "description": site_data.get("description", ""),
                "url": site_data.get("url", url),
                "home": site_data.get("home", url),
                "gmt_offset": site_data.get("gmt_offset", 0),
                "timezone": site_data.get("timezone_string", "UTC"),
                "site_logo": None,  # Would need additional API call
                "api_version": "v2"  # Default to v2
            }
            
            # Try to get site icon if available
            try:
                icon_url = f"{url}/wp-json/wp/v2/settings"
                icon_response = requests.get(icon_url, headers=headers, timeout=10)
                if icon_response.status_code == 200:
                    settings = icon_response.json()
                    if "site_logo" in settings:
                        st.session_state.site_info["site_logo"] = settings["site_logo"]
            except:
                pass  # Ignore errors for optional data
        else:
            st.session_state.error_message = f"Could not retrieve site information: {response.status_code} - {response.text}"
    except Exception as e:
        st.session_state.error_message = f"Error getting site information: {str(e)}"

# Data Fetching Functions
def fetch_wordpress_data() -> None:
    """Fetch all WordPress data (post types, taxonomies, etc.)"""
    fetch_custom_post_types()
    fetch_taxonomies()
    fetch_media_library_stats()
    
    # Update last refresh timestamp
    st.session_state.last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def fetch_custom_post_types() -> None:
    """Fetch custom post types from WordPress"""
    start_time = time.time()
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
        
        # Log the API request
        response_time = time.time() - start_time
        log_api_request(types_url, "GET", response.status_code, response_time)
        
        if response.status_code == 200:
            types_data = response.json()
            # Filter out built-in post types
            custom_types = [
                post_type for post_type, data in types_data.items() 
                if post_type not in ['revision', 'nav_menu_item', 'wp_block', 'wp_template', 'wp_template_part', 'wp_global_styles']
            ]
            st.session_state.custom_post_types = custom_types
            
            # Initialize stats for each CPT
            for cpt in custom_types:
                if cpt not in st.session_state.cpt_stats:
                    st.session_state.cpt_stats[cpt] = {
                        "count": 0, 
                        "last_updated": None,
                        "rest_base": types_data[cpt].get("rest_base", cpt),
                        "name": types_data[cpt].get("name", cpt.capitalize()),
                        "description": types_data[cpt].get("description", ""),
                        "hierarchical": types_data[cpt].get("hierarchical", False),
                        "supports": types_data[cpt].get("supports", {}),
                        "viewable": types_data[cpt].get("viewable", True)
                    }
                else:
                    # Update metadata but keep stats
                    st.session_state.cpt_stats[cpt].update({
                        "rest_base": types_data[cpt].get("rest_base", cpt),
                        "name": types_data[cpt].get("name", cpt.capitalize()),
                        "description": types_data[cpt].get("description", ""),
                        "hierarchical": types_data[cpt].get("hierarchical", False),
                        "supports": types_data[cpt].get("supports", {}),
                        "viewable": types_data[cpt].get("viewable", True)
                    })
        else:
            st.session_state.error_message = f"Could not retrieve post types: {response.status_code} - {response.text}"
    except Exception as e:
        st.session_state.error_message = f"Error getting custom post types: {str(e)}"

def fetch_taxonomies() -> None:
    """Fetch taxonomies from WordPress"""
    start_time = time.time()
    try:
        url = st.session_state.wordpress_url
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        taxonomies_url = f"{url}/wp-json/wp/v2/taxonomies"
        
        # Use token if available, otherwise use basic auth
        headers = {}
        if st.session_state.auth_token:
            headers["Authorization"] = f"Bearer {st.session_state.auth_token}"
        elif st.session_state.username and st.session_state.password:
            credentials = base64.b64encode(f"{st.session_state.username}:{st.session_state.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        response = requests.get(taxonomies_url, headers=headers, timeout=10)
        
        # Log the API request
        response_time = time.time() - start_time
        log_api_request(taxonomies_url, "GET", response.status_code, response_time)
        
        if response.status_code == 200:
            taxonomies_data = response.json()
            # Get all taxonomies
            taxonomies = list(taxonomies_data.keys())
            st.session_state.taxonomies = taxonomies
            
            # Initialize stats for each taxonomy
            for tax in taxonomies:
                if tax not in st.session_state.taxonomy_stats:
                    st.session_state.taxonomy_stats[tax] = {
                        "count": 0, 
                        "last_updated": None,
                        "rest_base": taxonomies_data[tax].get("rest_base", tax),
                        "name": taxonomies_data[tax].get("name", tax.capitalize()),
                        "description": taxonomies_data[tax].get("description", ""),
                        "hierarchical": taxonomies_data[tax].get("hierarchical", False),
                        "types": taxonomies_data[tax].get("types", [])
                    }
                else:
                    # Update metadata but keep stats
                    st.session_state.taxonomy_stats[tax].update({
                        "rest_base": taxonomies_data[tax].get("rest_base", tax),
                        "name": taxonomies_data[tax].get("name", tax.capitalize()),
                        "description": taxonomies_data[tax].get("description", ""),
                        "hierarchical": taxonomies_data[tax].get("hierarchical", False),
                        "types": taxonomies_data[tax].get("types", [])
                    })
        else:
            st.session_state.error_message = f"Could not retrieve taxonomies: {response.status_code} - {response.text}"
    except Exception as e:
        st.session_state.error_message = f"Error getting taxonomies: {str(e)}"

def fetch_media_library_stats() -> None:
    """Fetch media library statistics"""
    start_time = time.time()
    try:
        url = st.session_state.wordpress_url
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        media_url = f"{url}/wp-json/wp/v2/media?per_page=1"
        
        # Use token if available, otherwise use basic auth
        headers = {}
        if st.session_state.auth_token:
            headers["Authorization"] = f"Bearer {st.session_state.auth_token}"
        elif st.session_state.username and st.session_state.password:
            credentials = base64.b64encode(f"{st.session_state.username}:{st.session_state.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        response = requests.get(media_url, headers=headers, timeout=10)
        
        # Log the API request
        response_time = time.time() - start_time
        log_api_request(media_url, "GET", response.status_code, response_time)
        
        if response.status_code == 200:
            # Get total count from headers
            total_media = int(response.headers.get('X-WP-Total', 0))
            
            # Store in session state
            st.session_state.media_data = {
                "total_count": total_media,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            st.session_state.error_message = f"Could not retrieve media stats: {response.status_code} - {response.text}"
    except Exception as e:
        st.session_state.error_message = f"Error getting media stats: {str(e)}"

def get_cpt_posts(post_type: str, params: Dict = None) -> List[Dict]:
    """Get posts of a specific custom post type with optional filtering"""
    start_time = time.time()
    try:
        url = st.session_state.wordpress_url
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Get the REST base if available
        rest_base = st.session_state.cpt_stats.get(post_type, {}).get("rest_base", post_type)
        
        # Build URL with parameters
        base_url = f"{url}/wp-json/wp/v2/{rest_base}"
        if params:
            query_params = "&".join([f"{k}={v}" for k, v in params.items()])
            posts_url = f"{base_url}?{query_params}"
        else:
            posts_url = f"{base_url}?per_page=100"
        
        # Use token if available, otherwise use basic auth
        headers = {}
        if st.session_state.auth_token:
            headers["Authorization"] = f"Bearer {st.session_state.auth_token}"
        elif st.session_state.username and st.session_state.password:
            credentials = base64.b64encode(f"{st.session_state.username}:{st.session_state.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        response = requests.get(posts_url, headers=headers, timeout=15)
        
        # Log the API request
        response_time = time.time() - start_time
        log_api_request(posts_url, "GET", response.status_code, response_time)
        
        if response.status_code == 200:
            posts = response.json()
            
            # Get total count from headers
            total_posts = int(response.headers.get('X-WP-Total', len(posts)))
            
            # Update stats
            st.session_state.cpt_stats[post_type].update({
                "count": total_posts,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # Add to recent items
            add_to_recent_items("cpt", post_type, st.session_state.cpt_stats[post_type]["name"])
            
            return posts
        else:
            st.session_state.error_message = f"Could not retrieve posts: {response.status_code} - {response.text}"
            return []
    except Exception as e:
        st.session_state.error_message = f"Error getting posts: {str(e)}"
        return []

def get_taxonomy_terms(taxonomy: str, params: Dict = None) -> List[Dict]:
    """Get terms of a specific taxonomy with optional filtering"""
    start_time = time.time()
    try:
        url = st.session_state.wordpress_url
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Get the REST base if available
        rest_base = st.session_state.taxonomy_stats.get(taxonomy, {}).get("rest_base", taxonomy)
        
        # Build URL with parameters
        base_url = f"{url}/wp-json/wp/v2/{rest_base}"
        if params:
            query_params = "&".join([f"{k}={v}" for k, v in params.items()])
            terms_url = f"{base_url}?{query_params}"
        else:
            terms_url = f"{base_url}?per_page=100"
        
        # Use token if available, otherwise use basic auth
        headers = {}
        if st.session_state.auth_token:
            headers["Authorization"] = f"Bearer {st.session_state.auth_token}"
        elif st.session_state.username and st.session_state.password:
            credentials = base64.b64encode(f"{st.session_state.username}:{st.session_state.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        response = requests.get(terms_url, headers=headers, timeout=15)
        
        # Log the API request
        response_time = time.time() - start_time
        log_api_request(terms_url, "GET", response.status_code, response_time)
        
        if response.status_code == 200:
            terms = response.json()
            
            # Get total count from headers
            total_terms = int(response.headers.get('X-WP-Total', len(terms)))
            
            # Update stats
            st.session_state.taxonomy_stats[taxonomy].update({
                "count": total_terms,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            # Add to recent items
            add_to_recent_items("taxonomy", taxonomy, st.session_state.taxonomy_stats[taxonomy]["name"])
            
            return terms
        else:
            st.session_state.error_message = f"Could not retrieve terms: {response.status_code} - {response.text}"
            return []
    except Exception as e:
        st.session_state.error_message = f"Error getting terms: {str(e)}"
        return []

def get_media_items(params: Dict = None) -> List[Dict]:
    """Get media items with optional filtering"""
    start_time = time.time()
    try:
        url = st.session_state.wordpress_url
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Build URL with parameters
        base_url = f"{url}/wp-json/wp/v2/media"
        if params:
            query_params = "&".join([f"{k}={v}" for k, v in params.items()])
            media_url = f"{base_url}?{query_params}"
        else:
            media_url = f"{base_url}?per_page=20"  # Default to smaller page size for media
        
        # Use token if available, otherwise use basic auth
        headers = {}
        if st.session_state.auth_token:
            headers["Authorization"] = f"Bearer {st.session_state.auth_token}"
        elif st.session_state.username and st.session_state.password:
            credentials = base64.b64encode(f"{st.session_state.username}:{st.session_state.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        response = requests.get(media_url, headers=headers, timeout=15)
        
        # Log the API request
        response_time = time.time() - start_time
        log_api_request(media_url, "GET", response.status_code, response_time)
        
        if response.status_code == 200:
            media_items = response.json()
            
            # Get total count from headers
            total_media = int(response.headers.get('X-WP-Total', len(media_items)))
            
            # Update stats
            st.session_state.media_data.update({
                "total_count": total_media,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            return media_items
        else:
            st.session_state.error_message = f"Could not retrieve media: {response.status_code} - {response.text}"
            return []
    except Exception as e:
        st.session_state.error_message = f"Error getting media: {str(e)}"
        return []

# Integration Generation Functions
def convert_to_n8n_node(post_type: str, posts: List[Dict]) -> Dict:
    """Convert WordPress custom post type to n8n node format"""
    if not posts:
        return {}
    
    # Extract fields from the first post to determine structure
    sample_post = posts[0]
    fields = list(sample_post.keys())
    
    # Get post type info
    post_type_info = st.session_state.cpt_stats.get(post_type, {})
    post_type_name = post_type_info.get("name", post_type.capitalize())
    post_type_description = post_type_info.get("description", f"Operations for WordPress {post_type} custom post type")
    
    # Create n8n node definition
    node = {
        "name": f"WordPress {post_type_name}",
        "description": post_type_description,
        "version": 1,
        "defaults": {
            "name": f"WordPress {post_type_name}"
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
    
    # Add metadata
    node["metadata"] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "wordpress_url": st.session_state.wordpress_url,
        "post_type": post_type,
        "post_type_name": post_type_name,
        "field_count": len(node["properties"]),
        "sample_fields": fields[:10] if len(fields) > 10 else fields
    }
    
    return node

def generate_n8n_workflow(post_type: str, node_definition: Dict) -> Dict:
    """Generate a complete n8n workflow for a custom post type"""
    # Get post type info
    post_type_info = st.session_state.cpt_stats.get(post_type, {})
    post_type_name = post_type_info.get("name", post_type.capitalize())
    
    workflow = {
        "name": f"WordPress {post_type_name} Workflow",
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
                    "returnAll": True,
                    "additionalOptions": {
                        "orderBy": "date",
                        "order": "desc",
                        "status": "publish"
                    }
                },
                "name": f"WordPress {post_type_name}",
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
                            "node": f"WordPress {post_type_name}",
                            "type": "main",
                            "index": 0
                        }
                    ]
                ]
            },
            [f"WordPress {post_type_name}"]: {
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
        },
        "settings": {
            "executionOrder": "v1",
            "saveManualExecutions": true,
            "callerPolicy": "any",
            "errorWorkflow": ""
        },
        "staticData": null,
        "tags": [
            "WordPress",
            "Integration",
            f"{post_type}"
        ],
        "pinData": {},
        "versionId": "",
        "triggerCount": 0,
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat()
    }
    
    return workflow

def generate_zapier_integration(post_type: str, posts: List[Dict]) -> Dict:
    """Generate Zapier integration for a custom post type"""
    if not posts:
        return {}
    
    # Extract fields from the first post to determine structure
    sample_post = posts[0]
    fields = list(sample_post.keys())
    
    # Get post type info
    post_type_info = st.session_state.cpt_stats.get(post_type, {})
    post_type_name = post_type_info.get("name", post_type.capitalize())
    post_type_description = post_type_info.get("description", f"Operations for WordPress {post_type} custom post type")
    
    # Create Zapier integration definition
    integration = {
        "title": f"WordPress {post_type_name}",
        "description": post_type_description,
        "version": "1.0.0",
        "platformVersion": "10.0.0",
        "triggers": [
            {
                "key": "new_item",
                "noun": post_type_name,
                "display": {
                    "label": f"New {post_type_name}",
                    "description": f"Triggers when a new {post_type_name.lower()} is created."
                },
                "operation": {
                    "type": "polling",
                    "perform": {
                        "url": f"{{{{bundle.authData.website_url}}}}/wp-json/wp/v2/{post_type}",
                        "params": {
                            "per_page": "5",
                            "orderby": "date",
                            "order": "desc",
                            "_embed": "true"
                        },
                        "headers": {
                            "Authorization": "Basic {{{{bundle.authData.api_key}}}}"
                        }
                    },
                    "sample": sample_post,
                    "outputFields": [
                        {"key": "id", "label": "ID", "type": "integer"},
                    ]
                }
            },
            {
                "key": "updated_item",
                "noun": post_type_name,
                "display": {
                    "label": f"Updated {post_type_name}",
                    "description": f"Triggers when a {post_type_name.lower()} is updated."
                },
                "operation": {
                    "type": "polling",
                    "perform": {
                        "url": f"{{{{bundle.authData.website_url}}}}/wp-json/wp/v2/{post_type}",
                        "params": {
                            "per_page": "5",
                            "orderby": "modified",
                            "order": "desc",
                            "_embed": "true"
                        },
                        "headers": {
                            "Authorization": "Basic {{{{bundle.authData.api_key}}}}"
                        }
                    },
                    "sample": sample_post,
                    "outputFields": [
                        {"key": "id", "label": "ID", "type": "integer"},
                    ]
                }
            }
        ],
        "actions": [
            {
                "key": "create_item",
                "noun": post_type_name,
                "display": {
                    "label": f"Create {post_type_name}",
                    "description": f"Creates a new {post_type_name.lower()}."
                },
                "operation": {
                    "perform": {
                        "url": f"{{{{bundle.authData.website_url}}}}/wp-json/wp/v2/{post_type}",
                        "method": "POST",
                        "headers": {
                            "Authorization": "Basic {{{{bundle.authData.api_key}}}}"
                        },
                        "body": {}
                    },
                    "sample": sample_post,
                    "inputFields": []
                }
            },
            {
                "key": "update_item",
                "noun": post_type_name,
                "display": {
                    "label": f"Update {post_type_name}",
                    "description": f"Updates an existing {post_type_name.lower()}."
                },
                "operation": {
                    "perform": {
                        "url": f"{{{{bundle.authData.website_url}}}}/wp-json/wp/v2/{post_type}/{{{{bundle.inputData.id}}}}",
                        "method": "PUT",
                        "headers": {
                            "Authorization": "Basic {{{{bundle.authData.api_key}}}}"
                        },
                        "body": {}
                    },
                    "sample": sample_post,
                    "inputFields": [
                        {"key": "id", "label": "ID", "type": "integer", "required": True}
                    ]
                }
            }
        ],
        "authentication": {
            "type": "basic",
            "test": {
                "url": "{{bundle.authData.website_url}}/wp-json/wp/v2/users/me"
            },
            "fields": [
                {
                    "key": "website_url",
                    "label": "WordPress Website URL",
                    "type": "string",
                    "required": True,
                    "helpText": "Your WordPress website URL (e.g., https://example.com)"
                },
                {
                    "key": "api_key",
                    "label": "API Key",
                    "type": "string",
                    "required": True,
                    "helpText": "Your WordPress API key (Base64 encoded username:password or application password)"
                }
            ]
        }
    }
    
    # Add field definitions for triggers and actions
    output_fields = []
    input_fields = []
    
    for field in fields:
        if field in ['_links']:
            continue  # Skip system fields
            
        field_type = "string"
        if isinstance(sample_post.get(field), int):
            field_type = "integer"
        elif isinstance(sample_post.get(field), bool):
            field_type = "boolean"
        elif isinstance(sample_post.get(field), dict):
            field_type = "object"
        
        # Add to output fields (for triggers)
        output_fields.append({
            "key": field,
            "label": field.capitalize().replace("_", " "),
            "type": field_type
        })
        
        # Add to input fields (for actions)
        if field not in ['id', 'date', 'modified', 'guid', 'link']:
            input_fields.append({
                "key": field,
                "label": field.capitalize().replace("_", " "),
                "type": field_type
            })
    
    # Add fields to triggers and actions
    for trigger in integration["triggers"]:
        trigger["operation"]["outputFields"] = output_fields
    
    for action in integration["actions"]:
        if action["key"] == "create_item":
            action["operation"]["inputFields"] = input_fields
        elif action["key"] == "update_item":
            action["operation"]["inputFields"] = [{"key": "id", "label": "ID", "type": "integer", "required": True}] + input_fields
    
    # Add metadata
    integration["metadata"] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "wordpress_url": st.session_state.wordpress_url,
        "post_type": post_type,
        "post_type_name": post_type_name,
        "field_count": len(fields),
        "sample_fields": fields[:10] if len(fields) > 10 else fields
    }
    
    return integration

def generate_make_scenario(post_type: str, posts: List[Dict]) -> Dict:
    """Generate Make (Integromat) scenario for a custom post type"""
    if not posts:
        return {}
    
    # Extract fields from the first post to determine structure
    sample_post = posts[0]
    
    # Get post type info
    post_type_info = st.session_state.cpt_stats.get(post_type, {})
    post_type_name = post_type_info.get("name", post_type.capitalize())
    
    # Create Make scenario definition
    scenario = {
        "name": f"WordPress {post_type_name} to Google Sheets",
        "blueprint": {
            "name": f"WordPress {post_type_name} to Google Sheets",
            "description": f"Automatically sync WordPress {post_type_name} data to Google Sheets",
            "modules": [
                {
                    "id": "wp-trigger",
                    "name": "WordPress",
                    "type": "trigger",
                    "module": "wordpress",
                    "metadata": {
                        "instant": False
                    },
                    "settings": {
                        "url": "{{config.wordpress_url}}",
                        "username": "{{config.wordpress_username}}",
                        "password": "{{config.wordpress_password}}",
                        "limit": 10,
                        "postType": post_type,
                        "orderBy": "date",
                        "order": "DESC"
                    }
                },
                {
                    "id": "sheets-action",
                    "name": "Google Sheets",
                    "type": "action",
                    "module": "google-sheets",
                    "metadata": {},
                    "settings": {
                        "mode": "append",
                        "spreadsheetId": "{{config.spreadsheet_id}}",
                        "sheetName": f"{post_type_name} Data",
                        "columns": {}
                    },
                    "mapping": {}
                }
            ],
            "connections": [
                {
                    "from": "wp-trigger",
                    "to": "sheets-action"
                }
            ],
            "metadata": {
                "version": "1",
                "scenario": {
                    "roundtrips": 1,
                    "maxErrors": 3,
                    "autoCommit": True,
                    "sequential": False,
                    "confidential": False,
                    "dataloss": False,
                    "dlq": False
                }
            }
        },
        "config": {
            "wordpress_url": st.session_state.wordpress_url,
            "wordpress_username": "YOUR_USERNAME",
            "wordpress_password": "YOUR_PASSWORD",
            "spreadsheet_id": "YOUR_SPREADSHEET_ID"
        }
    }
    
    # Create field mappings for Google Sheets
    columns = {}
    mapping = {}
    
    # Add standard fields
    standard_fields = ["id", "title", "status", "date", "modified", "link"]
    for i, field in enumerate(standard_fields):
        if field in sample_post:
            column_letter = chr(65 + i)  # A, B, C, etc.
            
            # Handle nested fields like title.rendered
            if field == "title" and isinstance(sample_post[field], dict) and "rendered" in sample_post[field]:
                columns[column_letter] = field.capitalize()
                mapping[column_letter] = f"{{{{wp-trigger.title.rendered}}}}"
            else:
                columns[column_letter] = field.capitalize()
                mapping[column_letter] = f"{{{{wp-trigger.{field}}}}}"
    
    # Add custom fields (limit to 10 for simplicity)
    custom_fields = [f for f in sample_post.keys() if f not in standard_fields and f != "_links"][:10]
    for i, field in enumerate(custom_fields):
        column_letter = chr(65 + len(standard_fields) + i)  # Continue after standard fields
        columns[column_letter] = field.capitalize().replace("_", " ")
        
        # Handle nested fields
        if isinstance(sample_post[field], dict):
            # For simplicity, just map the first nested field or use JSON stringify
            mapping[column_letter] = f"{{{{json(wp-trigger.{field})}}}}"
        else:
            mapping[column_letter] = f"{{{{wp-trigger.{field}}}}}"
    
    # Add mappings to scenario
    scenario["blueprint"]["modules"][1]["settings"]["columns"] = columns
    scenario["blueprint"]["modules"][1]["mapping"] = mapping
    
    # Add metadata
    scenario["metadata"] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "wordpress_url": st.session_state.wordpress_url,
        "post_type": post_type,
        "post_type_name": post_type_name,
        "field_count": len(sample_post.keys()),
        "mapped_fields": list(mapping.values())
    }
    
    return scenario

def generate_webhook_config(post_type: str) -> Dict:
    """Generate webhook configuration for a custom post type"""
    # Get post type info
    post_type_info = st.session_state.cpt_stats.get(post_type, {})
    post_type_name = post_type_info.get("name", post_type.capitalize())
    
    # Generate a webhook secret
    webhook_secret = generate_api_key()
    
    # Create webhook configuration
    webhook_config = {
        "name": f"WordPress {post_type_name} Webhook",
        "description": f"Webhook configuration for {post_type_name} events",
        "events": [
            "create",
            "update",
            "delete"
        ],
        "target_url": "https://your-webhook-endpoint.com/webhook",
        "secret": webhook_secret,
        "status": "active",
        "format": "json",
        "post_type": post_type,
        "delivery": {
            "max_attempts": 3,
            "retry_interval": 60  # seconds
        },
        "security": {
            "signature_header": "X-WordPress-Signature",
            "signature_algorithm": "sha256"
        },
        "sample_payload": {
            "event": "create",
            "post_type": post_type,
            "post_id": 123,
            "timestamp": datetime.now().isoformat(),
            "data": {}  # Would contain post data
        },
        "implementation": {
            "php": f"""
// Add this code to your WordPress theme's functions.php or a custom plugin

// Register webhook for {post_type_name}
add_action('init', 'register_{post_type}_webhook');
function register_{post_type}_webhook() {{
    // Hook into post events
    add_action('save_post_{post_type}', 'trigger_{post_type}_webhook', 10, 3);
    add_action('before_delete_post', 'trigger_{post_type}_delete_webhook', 10, 1);
}}

// Function to trigger webhook on create/update
function trigger_{post_type}_webhook($post_id, $post, $update) {{
    // Skip revisions and auto-saves
    if (wp_is_post_revision($post_id) || wp_is_post_autosave($post_id)) {{
        return;
    }}
    
    // Get post data
    $post_data = get_post($post_id, ARRAY_A);
    
    // Prepare payload
    $payload = array(
        'event' => $update ? 'update' : 'create',
        'post_type' => '{post_type}',
        'post_id' => $post_id,
        'timestamp' => date('c'),
        'data' => $post_data
    );
    
    // Send webhook
    send_webhook_request($payload);
}}

// Function to trigger webhook on delete
function trigger_{post_type}_delete_webhook($post_id) {{
    // Check if it's the right post type
    if (get_post_type($post_id) !== '{post_type}') {{
        return;
    }}
    
    // Prepare payload
    $payload = array(
        'event' => 'delete',
        'post_type' => '{post_type}',
        'post_id' => $post_id,
        'timestamp' => date('c')
    );
    
    // Send webhook
    send_webhook_request($payload);
}}

// Function to send webhook request
function send_webhook_request($payload) {{
    // Webhook URL
    $webhook_url = 'https://your-webhook-endpoint.com/webhook';
    
    // Webhook secret
    $webhook_secret = '{webhook_secret}';
    
    // Convert payload to JSON
    $json_payload = json_encode($payload);
    
    // Generate signature
    $signature = hash_hmac('sha256', $json_payload, $webhook_secret);
    
    // Send request
    $response = wp_remote_post($webhook_url, array(
        'headers' => array(
            'Content-Type' => 'application/json',
            'X-WordPress-Signature' => $signature
        ),
        'body' => $json_payload,
        'timeout' => 15
    ));
    
    // Log errors
    if (is_wp_error($response)) {{
        error_log('Webhook error: ' . $response->get_error_message());
    }}
}}
"""
        }
    }
    
    return webhook_config

# Data Analysis Functions
def analyze_cpt_data(posts: List[Dict]) -> Dict:
    """Analyze custom post type data and generate statistics"""
    if not posts:
        return {}
    
    analysis = {
        "total_posts": len(posts),
        "fields": {},
        "status_distribution": {},
        "creation_dates": {},
        "modification_dates": {},
        "authors": {},
        "content_length": {
            "min": float('inf'),
            "max": 0,
            "avg": 0,
            "distribution": {}
        }
    }
    
    # Get a list of all fields
    sample_post = posts[0]
    fields = list(sample_post.keys())
    
    # Analyze each field
    for field in fields:
        if field in ['_links']:
            continue  # Skip system fields
            
        field_types = set()
        non_empty_values = 0
        unique_values = set()
        
        for post in posts:
            if field in post and post[field]:
                non_empty_values += 1
                field_types.add(type(post[field]).__name__)
                
                # For simple types, track unique values
                if isinstance(post[field], (str, int, bool)):
                    unique_values.add(str(post[field]))
                elif isinstance(post[field], dict) and 'rendered' in post[field]:
                    # Handle WP rendered fields
                    unique_values.add(str(post[field]['rendered']))
        
        analysis["fields"][field] = {
            "types": list(field_types),
            "fill_rate": round(non_empty_values / len(posts) * 100, 2) if posts else 0,
            "unique_values": len(unique_values),
            "cardinality": "high" if len(unique_values) > len(posts) * 0.8 else "medium" if len(unique_values) > len(posts) * 0.3 else "low"
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
    
    # Analyze modification dates by month
    for post in posts:
        if 'modified' in post:
            date_str = post['modified']
            try:
                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                month_year = date_obj.strftime('%Y-%m')
                if month_year in analysis["modification_dates"]:
                    analysis["modification_dates"][month_year] += 1
                else:
                    analysis["modification_dates"][month_year] = 1
            except:
                pass
    
    # Analyze authors
    for post in posts:
        if 'author' in post:
            author_id = post['author']
            if author_id in analysis["authors"]:
                analysis["authors"][author_id] += 1
            else:
                analysis["authors"][author_id] = 1
    
    # Analyze content length
    total_length = 0
    length_distribution = {
        "very_short": 0,  # 0-100 chars
        "short": 0,       # 100-500 chars
        "medium": 0,      # 500-2000 chars
        "long": 0,        # 2000-5000 chars
        "very_long": 0    # 5000+ chars
    }
    
    for post in posts:
        content_length = 0
        if 'content' in post:
            if isinstance(post['content'], dict) and 'rendered' in post['content']:
                # Remove HTML tags for more accurate length
                content = re.sub(r'<[^>]+>', '', post['content']['rendered'])
                content_length = len(content)
            elif isinstance(post['content'], str):
                content_length = len(post['content'])
        
        if content_length > 0:
            # Update min/max
            analysis["content_length"]["min"] = min(analysis["content_length"]["min"], content_length)
            analysis["content_length"]["max"] = max(analysis["content_length"]["max"], content_length)
            total_length += content_length
            
            # Update distribution
            if content_length < 100:
                length_distribution["very_short"] += 1
            elif content_length < 500:
                length_distribution["short"] += 1
            elif content_length < 2000:
                length_distribution["medium"] += 1
            elif content_length < 5000:
                length_distribution["long"] += 1
            else:
                length_distribution["very_long"] += 1
    
    # Calculate average content length
    if len(posts) > 0:
        analysis["content_length"]["avg"] = round(total_length / len(posts), 2)
    else:
        analysis["content_length"]["avg"] = 0
    
    # If no content was found, reset min
    if analysis["content_length"]["min"] == float('inf'):
        analysis["content_length"]["min"] = 0
    
    analysis["content_length"]["distribution"] = length_distribution
    
    # Sort dates chronologically
    analysis["creation_dates"] = dict(sorted(analysis["creation_dates"].items()))
    analysis["modification_dates"] = dict(sorted(analysis["modification_dates"].items()))
    
    return analysis

def analyze_taxonomy_data(terms: List[Dict]) -> Dict:
    """Analyze taxonomy terms and generate statistics"""
    if not terms:
        return {}
    
    analysis = {
        "total_terms": len(terms),
        "fields": {},
        "hierarchy": {
            "top_level": 0,
            "nested": 0,
            "max_depth": 0
        },
        "term_usage": {},
        "creation_dates": {}
    }
    
    # Get a list of all fields
    sample_term = terms[0]
    fields = list(sample_term.keys())
    
    # Analyze each field
    for field in fields:
        if field in ['_links']:
            continue  # Skip system fields
            
        field_types = set()
        non_empty_values = 0
        unique_values = set()
        
        for term in terms:
            if field in term and term[field]:
                non_empty_values += 1
                field_types.add(type(term[field]).__name__)
                
                # For simple types, track unique values
                if isinstance(term[field], (str, int, bool)):
                    unique_values.add(str(term[field]))
        
        analysis["fields"][field] = {
            "types": list(field_types),
            "fill_rate": round(non_empty_values / len(terms) * 100, 2) if terms else 0,
            "unique_values": len(unique_values)
        }
    
    # Analyze hierarchy
    for term in terms:
        if term.get('parent', 0) == 0:
            analysis["hierarchy"]["top_level"] += 1
        else:
            analysis["hierarchy"]["nested"] += 1
    
    # Calculate max depth (simplified approach)
    parent_map = {term['id']: term.get('parent', 0) for term in terms}
    max_depth = 0
    
    for term_id in parent_map:
        depth = 0
        current_id = term_id
        
        while parent_map.get(current_id, 0) != 0 and depth < 10:  # Limit to avoid infinite loops
            depth += 1
            current_id = parent_map.get(current_id)
        
        max_depth = max(max_depth, depth)
    
    analysis["hierarchy"]["max_depth"] = max_depth
    
    # Analyze term usage if count is available
    for term in terms:
        if 'count' in term:
            usage = term['count']
            if usage in analysis["term_usage"]:
                analysis["term_usage"][usage] += 1
            else:
                analysis["term_usage"][usage] = 1
    
    # Sort usage for better visualization
    analysis["term_usage"] = dict(sorted(analysis["term_usage"].items()))
    
    return analysis

# UI Components
def render_header():
    """Render the application header"""
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown('<div class="app-header">Enterprise WordPress Integration Hub</div>', unsafe_allow_html=True)
        
        if st.session_state.authenticated:
            site_name = st.session_state.site_info.get("name", st.session_state.wordpress_url)
            st.markdown(f'<div class="site-info">Connected to: <span class="site-name">{site_name}</span></div>', unsafe_allow_html=True)
    
    with col2:
        if st.session_state.authenticated:
            # Display user info if available
            if st.session_state.user_info:
                user_name = st.session_state.user_info.get("name", "User")
                user_avatar = st.session_state.user_info.get("avatar_urls", {}).get("24", "")
                
                st.markdown(f"""
                <div class="user-info">
                    <span class="user-avatar">{f'<img src="{user_avatar}" width="24" height="24" />' if user_avatar else '👤'}</span>
                    <span class="user-name">{user_name}</span>
                </div>
                """, unsafe_allow_html=True)

def render_sidebar():
    """Render the application sidebar"""
    with st.sidebar:
        st.markdown('<div class="sidebar-header">WordPress Integration Hub</div>', unsafe_allow_html=True)
        
        # Dark mode toggle
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### Settings")
        with col2:
            if st.toggle("🌙", value=st.session_state.dark_mode, key="dark_mode_toggle"):
                st.session_state.dark_mode = True
            else:
                st.session_state.dark_mode = False
        
        if not st.session_state.authenticated:
            render_auth_sidebar()
        else:
            render_authenticated_sidebar()

def render_auth_sidebar():
    """Render the authentication sidebar"""
    st.markdown("### Connect to WordPress")
    
    auth_tab1, auth_tab2 = st.tabs(["Login with WordPress", "Manual Credentials"])
    
    with auth_tab1:
        st.markdown("Enter your WordPress site URL and click the button to log in.")
        wordpress_url = st.text_input("WordPress Site URL", placeholder="example.com", value=st.session_state.wordpress_url)
        
        if st.button("Login with WordPress", key="login_button", use_container_width=True):
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
                if st.button("Complete Authentication", key="complete_auth", use_container_width=True):
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
            
            submit = st.form_submit_button("Connect", use_container_width=True)
            
            if submit:
                if wordpress_url and username and password:
                    st.session_state.wordpress_url = wordpress_url
                    st.session_state.username = username
                    st.session_state.password = password
                    
                    if authenticate_with_credentials(wordpress_url, username, password):
                        st.experimental_rerun()
                else:
                    st.warning("Please fill in all fields")
    
    # Quick demo option
    with st.expander("Quick Demo"):
        st.markdown("Try the app with demo data without connecting to WordPress.")
        if st.button("Load Demo Data", key="demo_button", use_container_width=True):
            # Simulate authentication with demo data
            st.session_state.authenticated = True
            st.session_state.wordpress_url = "https://demo-wordpress-site.com"
            st.session_state.auth_token = f"demo_token_{uuid.uuid4()}"
            
            # Load demo site info
            st.session_state.site_info = {
                "name": "Demo WordPress Site",
                "description": "A demo site for testing the WordPress Integration Hub",
                "url": "https://demo-wordpress-site.com",
                "home": "https://demo-wordpress-site.com",
                "gmt_offset": 0,
                "timezone": "UTC",
                "site_logo": None,
                "api_version": "v2"
            }
            
            # Load demo user info
            st.session_state.user_info = {
                "id": 1,
                "name": "Demo User",
                "url": "",
                "description": "",
                "link": "https://demo-wordpress-site.com/author/demo-user/",
                "slug": "demo-user",
                "avatar_urls": {
                    "24": "",
                    "48": "",
                    "96": ""
                }
            }
            
            # Load demo custom post types
            st.session_state.custom_post_types = ["post", "page", "product", "event", "testimonial"]
            
            # Load demo taxonomies
            st.session_state.taxonomies = ["category", "post_tag", "product_cat", "event_type"]
            
            # Initialize demo stats
            for cpt in st.session_state.custom_post_types:
                st.session_state.cpt_stats[cpt] = {
                    "count": random.randint(10, 100),
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "rest_base": cpt,
                    "name": cpt.capitalize(),
                    "description": f"Demo {cpt} post type",
                    "hierarchical": False,
                    "supports": {"title": True, "editor": True},
                    "viewable": True
                }
            
            for tax in st.session_state.taxonomies:
                st.session_state.taxonomy_stats[tax] = {
                    "count": random.randint(5, 30),
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "rest_base": tax,
                    "name": tax.replace("_", " ").capitalize(),
                    "description": f"Demo {tax} taxonomy",
                    "hierarchical": tax in ["category", "product_cat"],
                    "types": ["post"] if tax in ["category", "post_tag"] else ["product"] if tax == "product_cat" else ["event"]
                }
            
            # Load demo media stats
            st.session_state.media_data = {
                "total_count": random.randint(50, 200),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            st.session_state.last_refresh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.success_message = "Demo data loaded successfully!"
            
            st.experimental_rerun()

def render_authenticated_sidebar():
    """Render the sidebar for authenticated users"""
    # Connection status
    st.markdown(f"""
    <div class="connection-status">
        <div class="status-indicator connected"></div>
        <div class="status-text">Connected to WordPress</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Navigation
    st.markdown("### Navigation")
    
    nav_items = [
        {"id": "dashboard", "icon": "📊", "label": "Dashboard"},
        {"id": "content", "icon": "📄", "label": "Content Types"},
        {"id": "integrations", "icon": "🔄", "label": "Integrations"},
        {"id": "sync", "icon": "⏱️", "label": "Sync Settings"},
        {"id": "templates", "icon": "📋", "label": "Templates"},
        {"id": "logs", "icon": "📝", "label": "API Logs"},
        {"id": "settings", "icon": "⚙️", "label": "Settings"}
    ]
    
    for item in nav_items:
        if st.button(f"{item['icon']} {item['label']}", key=f"nav_{item['id']}", use_container_width=True):
            st.session_state.active_tab = item['id']
            st.experimental_rerun()
    
    # Quick actions
    st.markdown("### Quick Actions")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Refresh Data", key="refresh_data_btn"):
            fetch_wordpress_data()
            st.session_state.success_message = "Data refreshed successfully!"
            st.experimental_rerun()
    
    with col2:
        if st.button("Disconnect", key="disconnect_btn"):
            # Clear session state
            for key in list(st.session_state.keys()):
                if key not in ["dark_mode"]:  # Keep some settings
                    del st.session_state[key]
            
            # Reset authentication state
            st.session_state.authenticated = False
            st.experimental_rerun()
    
    # Recent items
    if st.session_state.recent_items:
        st.markdown("### Recent Items")
        
        for item in st.session_state.recent_items[:5]:  # Show only 5 most recent
            item_type = item["type"]
            item_id = item["id"]
            item_name = item["name"]
            
            if st.button(f"{item_name}", key=f"recent_{item_type}_{item_id}", use_container_width=True):
                if item_type == "cpt":
                    st.session_state.selected_cpt = item_id
                    st.session_state.active_tab = "content"
                elif item_type == "taxonomy":
                    st.session_state.selected_taxonomy = item_id
                    st.session_state.active_tab = "content"
                st.experimental_rerun()
    
    # Footer
    st.markdown("""
    <div class="sidebar-footer">
        <div class="version">Enterprise WordPress Integration Hub v1.0</div>
        <div class="copyright">© 2023 All Rights Reserved</div>
    </div>
    """, unsafe_allow_html=True)

def render_dashboard():
    """Render the dashboard view"""
    st.markdown('<div class="section-header">Dashboard</div>', unsafe_allow_html=True)
    
    # Overview cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        cpt_count = len(st.session_state.custom_post_types)
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-title">Content Types</div>
            <div class="stat-value">{cpt_count}</div>
            <div class="stat-description">Custom post types</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Count total items across all CPTs
        total_items = sum(
            st.session_state.cpt_stats[cpt]["count"] 
            for cpt in st.session_state.cpt_stats 
            if "count" in st.session_state.cpt_stats[cpt]
        )
        
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-title">Content Items</div>
            <div class="stat-value">{total_items}</div>
            <div class="stat-description">Total content entries</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Count total taxonomies
        tax_count = len(st.session_state.taxonomies)
        
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-title">Taxonomies</div>
            <div class="stat-value">{tax_count}</div>
            <div class="stat-description">Classification systems</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Media count
        media_count = st.session_state.media_data.get("total_count", 0)
        
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-title">Media Items</div>
            <div class="stat-value">{media_count}</div>
            <div class="stat-description">Images, videos, etc.</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Content distribution chart
    st.markdown('<div class="subsection-header">Content Distribution</div>', unsafe_allow_html=True)
    
    # Create data for the chart
    chart_data = []
    for cpt in st.session_state.custom_post_types:
        count = st.session_state.cpt_stats.get(cpt, {}).get("count", 0)
        name = st.session_state.cpt_stats.get(cpt, {}).get("name", cpt.capitalize())
        if count > 0:
            chart_data.append({
                "Content Type": name,
                "Count": count
            })
    
    if chart_data:
        chart_df = pd.DataFrame(chart_data)
        fig = px.bar(
            chart_df, 
            x="Content Type", 
            y="Count", 
            title="Content Items by Type",
            color="Content Type"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No content data available. Select content types from the sidebar to load data.")
    
    # Recent activity and integration status
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="subsection-header">Recent Activity</div>', unsafe_allow_html=True)
        
        # Show recent API logs
        if st.session_state.api_logs:
            logs_df = pd.DataFrame([
                {
                    "Time": log["timestamp"],
                    "Endpoint": truncate_text(log["endpoint"], 30),
                    "Method": log["method"],
                    "Status": log["status_code"],
                    "Response Time (s)": round(log["response_time"], 2)
                }
                for log in st.session_state.api_logs[:5]  # Show only 5 most recent
            ])
            
            st.dataframe(logs_df, use_container_width=True, hide_index=True)
        else:
            st.info("No recent activity to display.")
    
    with col2:
        st.markdown('<div class="subsection-header">Integration Status</div>', unsafe_allow_html=True)
        
        # Show integration status
        integration_status = [
            {"Platform": "n8n", "Status": "Active" if st.session_state.n8n_nodes else "Not Configured"},
            {"Platform": "Zapier", "Status": "Active" if st.session_state.zapier_integrations else "Not Configured"},
            {"Platform": "Make (Integromat)", "Status": "Active" if st.session_state.make_scenarios else "Not Configured"},
            {"Platform": "Webhooks", "Status": "Not Configured"},
            {"Platform": "Data Sync", "Status": "Active" if st.session_state.sync_settings["auto_sync"] else "Disabled"}
        ]
        
        status_df = pd.DataFrame(integration_status)
        st.dataframe(status_df, use_container_width=True, hide_index=True)
    
    # Quick actions
    st.markdown('<div class="subsection-header">Quick Actions</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="action-card">
            <div class="action-title">Create Integration</div>
            <div class="action-description">Generate a new integration for your WordPress content</div>
            <button class="action-button" onclick="parent.window.location.href='#'">Start</button>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="action-card">
            <div class="action-title">Configure Sync</div>
            <div class="action-description">Set up automatic data synchronization</div>
            <button class="action-button" onclick="parent.window.location.href='#'">Configure</button>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="action-card">
            <div class="action-title">Export Data</div>
            <div class="action-description">Export your WordPress data in various formats</div>
            <button class="action-button" onclick="parent.window.location.href='#'">Export</button>
        </div>
        """, unsafe_allow_html=True)

def render_content_explorer():
    """Render the content explorer view"""
    st.markdown('<div class="section-header">Content Explorer</div>', unsafe_allow_html=True)
    
    # Tabs for different content types
    tab1, tab2, tab3 = st.tabs(["Custom Post Types", "Taxonomies", "Media Library"])
    
    with tab1:
        render_cpt_explorer()
    
    with tab2:
        render_taxonomy_explorer()
    
    with tab3:
        render_media_explorer()

def render_cpt_explorer():
    """Render the custom post type explorer"""
    # CPT selection
    if st.session_state.custom_post_types:
        # Create a grid of buttons for CPT selection
        cols = st.columns(3)
        for i, cpt in enumerate(st.session_state.custom_post_types):
            col_idx = i % 3
            with cols[col_idx]:
                cpt_name = st.session_state.cpt_stats.get(cpt, {}).get("name", cpt.capitalize())
                cpt_count = st.session_state.cpt_stats.get(cpt, {}).get("count", "?")
                
                # Create a card-like button
                if st.button(
                    f"{cpt_name} ({cpt_count})",
                    key=f"cpt_select_{cpt}",
                    use_container_width=True,
                    help=f"View and analyze {cpt_name} data"
                ):
                    st.session_state.selected_cpt = cpt
                    # Fetch data if not already loaded
                    if cpt not in st.session_state.cpt_data or not st.session_state.cpt_data[cpt]:
                        posts = get_cpt_posts(cpt)
                        if posts:
                            st.session_state.cpt_data[cpt] = posts
                            # Generate analysis
                            analysis = analyze_cpt_data(posts)
                            st.session_state.cpt_stats[cpt]["analysis"] = analysis
                    st.experimental_rerun()
    else:
        st.info("No custom post types found. Click 'Refresh Data' in the sidebar to fetch content types.")
    
    # Display selected CPT data
    if st.session_state.selected_cpt:
        cpt = st.session_state.selected_cpt
        cpt_name = st.session_state.cpt_stats.get(cpt, {}).get("name", cpt.capitalize())
        
        st.markdown(f'<div class="subsection-header">{cpt_name} Explorer</div>', unsafe_allow_html=True)
        
        # Check if we have data
        if cpt in st.session_state.cpt_data and st.session_state.cpt_data[cpt]:
            posts = st.session_state.cpt_data[cpt]
            
            # Create tabs for different views
            data_tab1, data_tab2, data_tab3, data_tab4 = st.tabs(["Data Explorer", "Analysis", "Schema", "Integration"])
            
            with data_tab1:
                render_cpt_data_explorer(cpt, posts)
            
            with data_tab2:
                render_cpt_analysis(cpt)
            
            with data_tab3:
                render_cpt_schema(cpt, posts)
            
            with data_tab4:
                render_cpt_integration_options(cpt, posts)
        else:
            # Fetch data
            st.info(f"Loading {cpt_name} data...")
            posts = get_cpt_posts(cpt)
            if posts:
                st.session_state.cpt_data[cpt] = posts
                # Generate analysis
                analysis = analyze_cpt_data(posts)
                st.session_state.cpt_stats[cpt]["analysis"] = analysis
                st.experimental_rerun()
            else:
                st.error(f"No data found for {cpt_name} or error fetching data.")

def render_cpt_data_explorer(cpt: str, posts: List[Dict]):
    """Render the data explorer for a custom post type"""
    # Data filtering options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Get all possible statuses
        statuses = list(set(post.get('status', 'unknown') for post in posts))
        selected_status = st.selectbox("Filter by Status", ["All"] + statuses)
    
    with col2:
        # Sort options
        sort_options = ["Date (Newest)", "Date (Oldest)", "Title (A-Z)", "Title (Z-A)", "ID (Ascending)", "ID 
