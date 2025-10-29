import streamlit as st
import importlib
import pkgutil
import brands
import time
import os
from pathlib import Path

# -----------------------------
# Function to dynamically load brand modules
# -----------------------------
@st.cache_resource(ttl=10)  # refresh every 10 seconds
def load_brand_modules():
    """Auto-detect and import brand modules dynamically from the /brands folder."""
    modules = {}
    for _, name, _ in pkgutil.iter_modules(brands.__path__):
        try:
            mod = importlib.import_module(f"brands.{name}")
            if hasattr(mod, "render") and hasattr(mod, "name"):
                modules[name] = mod
        except Exception as e:
            st.warning(f"⚠️ Failed to load brand module '{name}': {e}")
    return modules

# -----------------------------
# Auto-refresh trigger (check folder timestamp)
# -----------------------------
def folder_last_modified(folder: Path):
    """Return latest modification timestamp of a folder."""
    return max(os.path.getmtime(p) for p in folder.rglob("*.py"))

# Track folder changes for auto-refresh
brands_path = Path(brands.__path__[0])
last_refresh_time = st.session_state.get("last_refresh_time", 0)
current_mod_time = folder_last_modified(brands_path)

if current_mod_time > last_refresh_time:
    st.cache_resource.clear()
    st.session_state["last_refresh_time"] = current_mod_time

# -----------------------------
# Load brand modules dynamically
# -----------------------------
brand_modules = load_brand_modules()

# -----------------------------
# Sidebar Navigation
# -----------------------------
st.sidebar.title("Accounts")
pages = ["🏠 Home"] + [mod.name for mod in brand_modules.values()]
choice = st.sidebar.radio("Choose page", pages)

# -----------------------------
# Main Page Rendering
# -----------------------------
if choice == "🏠 Home":
    st.title("📦 MCU Projection Tool")
    st.markdown(
        """
        Welcome to the **MCU Projection Tool** 👋  
        Use the sidebar to select a brand account.  
        You can use the same brand accounts which uses the same logic. 
        """
    )
    st.info("🔄 New brand modules in `/brands/` will appear automatically — no restart needed!")
else:
    # Render the selected brand page
    for mod in brand_modules.values():
        if mod.name == choice:
            mod.render()
            break
