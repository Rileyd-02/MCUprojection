import streamlit as st
import importlib
import pkgutil
import brands
import os
import time
from pathlib import Path

# -----------------------------
# Function to dynamically load brand modules
# -----------------------------
@st.cache_resource(ttl=10)  # Refresh cache every 10 seconds
def load_brand_modules():
    """Auto-detect and import brand modules dynamically from the /brands folder."""
    modules = {}
    for _, name, _ in pkgutil.iter_modules(brands.__path__):
        try:
            mod = importlib.import_module(f"brands.{name}")
            if hasattr(mod, "st") and hasattr(mod, "__name__"):
                # Display name = capitalize or custom attribute if defined
                display_name = getattr(mod, "name", name.replace("_", " ").title())
                modules[display_name] = mod
        except Exception as e:
            st.warning(f"⚠️ Failed to load brand module '{name}': {e}")
    return modules


# -----------------------------
# Folder change detection (auto-refresh)
# -----------------------------
def folder_last_modified(folder: Path):
    """Return the latest modification timestamp of all .py files in a folder."""
    return max(os.path.getmtime(p) for p in folder.rglob("*.py"))


# Track folder changes for auto-refresh
brands_path = Path(brands.__path__[0])
last_refresh_time = st.session_state.get("last_refresh_time", 0)
current_mod_time = folder_last_modified(brands_path)

if current_mod_time > last_refresh_time:
    st.cache_resource.clear()
    st.session_state["last_refresh_time"] = current_mod_time

# -----------------------------
# Load all brand modules dynamically
# -----------------------------
brand_modules = load_brand_modules()

# -----------------------------
# Sidebar Navigation
# -----------------------------
st.sidebar.title("🧾 Brand Accounts")
pages = ["🏠 Home"] + list(brand_modules.keys())
choice = st.sidebar.radio("Choose a brand", pages)

# -----------------------------
# Main Page Rendering
# -----------------------------
if choice == "🏠 Home":
    st.title("📦 MCU Projection Tool")
    st.markdown(
        """
        Welcome to the **MCU Projection Tool** 👋  
        Use the sidebar to select a brand module (like VSPink, Hugo Boss, NDC, CKUW, etc.).  

        **✨ Features**
        - Auto-detects new brand files in the `/brands` folder.
        - Auto-refreshes sidebar when new brand `.py` files are added.
        - Each brand page has its own logic and UI.
        """
    )
    st.info("🔄 Add new `.py` files under `/brands/` — they’ll appear here automatically!")
else:
    try:
        mod = brand_modules[choice]
        # Run the brand page
        if hasattr(mod, "st"):  # standard Streamlit module
            mod  # Just to ensure it's imported
        # Each brand script runs automatically in Streamlit context
        importlib.reload(mod)
    except Exception as e:
        st.error(f"❌ Error loading brand '{choice}': {e}")
