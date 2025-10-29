import streamlit as st
import os
import importlib

# ----------------------------
# Dynamic brand detection
# ----------------------------
BRANDS_DIR = "brands"

def discover_brands():
    """
    Discover all Python modules in the brands folder with a `run_page` function.
    Returns a list of tuples: (brand_name, run_page_function)
    """
    brands_modules = []

    for file in os.listdir(BRANDS_DIR):
        if file.endswith(".py") and file != "__init__.py":
            module_name = file[:-3]
            try:
                module = importlib.import_module(f"{BRANDS_DIR}.{module_name}")
                if hasattr(module, "run_page"):
                    brands_modules.append((module_name, module.run_page))
            except Exception as e:
                st.warning(f"Failed to load brand module '{module_name}': {e}")
    # Sort alphabetically
    brands_modules.sort(key=lambda x: x[0])
    return brands_modules

brands_modules = discover_brands()

# ----------------------------
# Home page
# ----------------------------
def page_home():
    st.title("📦 MCU / PLM Tools Dashboard")
    st.markdown("""
    **Quick guide**
    - Upload the buy/plm files for your brand.
    - Each brand has its own workflow.
    - VSPINK preserves metadata + month pivoting.
    - New brands are auto-detected and appear in the sidebar.
    """)

# ----------------------------
# Sidebar navigation
# ----------------------------
pages = ["Home"] + [name.capitalize() for name, _ in brands_modules]
page_choice = st.sidebar.radio("Select page", pages)

# ----------------------------
# Run selected page
# ----------------------------
if page_choice == "Home":
    page_home()
else:
    # Map sidebar choice to module run_page function
    for name, run_func in brands_modules:
        if page_choice.lower() == name.lower():
            run_func()
            break
