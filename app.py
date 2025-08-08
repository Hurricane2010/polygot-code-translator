import streamlit as st
from pipeline import PolyglotPipeline, PythonVersionPipeline, AIOverviewAgent
import zipfile
import tempfile
import os
import shutil
from io import BytesIO
import difflib

st.set_page_config(page_title="Polyglot Code Translator 🌐", layout="wide")
st.title("Polyglot Code Translator 🌐")

# --- Helper for ZIP processing ---
def process_zip_files(uploaded_zip, processor, file_ext_map):
    translated_zip_io = BytesIO()
    with tempfile.TemporaryDirectory() as extract_dir, tempfile.TemporaryDirectory() as output_dir:
        with zipfile.ZipFile(uploaded_zip, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        for root, _, files in os.walk(extract_dir):
            for filename in files:
                src_path = os.path.join(root, filename)
                rel_path = os.path.relpath(src_path, extract_dir)

                if filename.endswith(".py"):
                    base_name = os.path.splitext(rel_path)[0]
                    new_ext = file_ext_map
                    rel_path = base_name + new_ext

                dest_path = os.path.join(output_dir, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)

                if filename.endswith(".py"):
                    try:
                        with open(src_path, "r", encoding="utf-8") as f:
                            code = f.read()
                        translated, _ = processor.run(code)
                        with open(dest_path, "w", encoding="utf-8") as f_out:
                            f_out.write(translated)
                    except Exception as e:
                        st.warning(f"Failed to process `{rel_path}`: {e}")
                        shutil.copyfile(src_path, dest_path)
                else:
                    shutil.copyfile(src_path, dest_path)

        with zipfile.ZipFile(translated_zip_io, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, output_dir)
                    zipf.write(file_path, arcname)

    translated_zip_io.seek(0)
    return translated_zip_io

# --- Helper for pastel diff highlighting ---
def generate_diff_html(original, modified):
    differ = difflib.HtmlDiff(wrapcolumn=80)
    html_diff = differ.make_table(
        original.splitlines(),
        modified.splitlines(),
        fromdesc="Original",
        todesc="Modified",
        context=True,
        numlines=3
    )
    pastel_css = """
    <style>
    table.diff {
        font-family: monospace;
        border-collapse: collapse;
        width: 100%;
    }
    .diff_header {
        background-color: #fdf6e3; /* soft beige */
        color: #444444;            /* dark gray text for readability */
        padding: 5px;
    }
    td.diff_header {
        text-align: right;
    }
    .diff_next {
        background-color: #eee8d5; /* light tan for separator lines */
    }
    .diff_add {
        background-color: #d4f4dd; /* pastel green */
        color: #1a3a1a;             /* dark green text */
    }
    .diff_chg {
        background-color: #fff5e6; /* pastel orange */
        color: #5a3d1a;            /* dark orange-brown text */
    }
    .diff_sub {
        background-color: #fce4e4; /* pastel pink/red */
        color: #5a1a1a;            /* dark red text */
    }
    </style>
    """

    return pastel_css + html_diff

# === Mode Selection ===
mode = st.radio(
    "Select operation mode:",
    ["Translate to another language", "Update/Downgrade Python version"]
)

if mode == "Translate to another language":
    target_lang = st.selectbox("Select target language", ["r", "java", "pyspark"])
else:
    python_version_target = st.selectbox(
        "Select Python version",
        ["3.11", "3.10", "3.9", "3.8", "3.7", "2.7"]
    )

uploaded = st.file_uploader("Upload Python file (.py) or ZIP (.zip)", type=["py", "zip"])
code_input = ""
source_name = None

if uploaded:
    if uploaded.name.endswith(".py"):
        try:
            code_input = uploaded.read().decode("utf-8")
            source_name = uploaded.name
        except UnicodeDecodeError:
            st.warning(f"File `{uploaded.name}` is not UTF-8 encoded.")
            code_input = ""
elif not uploaded:
    code_input = st.text_area("Or paste Python code here:", height=300)
    source_name = "Pasted code"

# === Process ZIP Upload ===
if uploaded and uploaded.name.endswith(".zip"):
    if st.button("Run 🚀", key="run_zip"):
        with st.spinner("Processing all Python files in ZIP..."):
            try:
                if mode == "Translate to another language":
                    processor = PolyglotPipeline(target_lang)
                    ext_map = { "r": ".R", "java": ".java", "pyspark": ".py" }[target_lang]
                else:
                    processor = PythonVersionPipeline(python_version_target)
                    ext_map = ".py"

                translated_zip = process_zip_files(uploaded, processor, ext_map)
                st.success("Processing complete! Download your ZIP below.")
                st.download_button(
                    label="📦 Download Processed ZIP",
                    data=translated_zip,
                    file_name=f"processed_{uploaded.name}",
                    mime="application/zip"
                )
            except Exception as e:
                st.error(f"Failed to process ZIP: {e}")

# === Process single file or pasted code ===
elif code_input.strip() and st.button("Run 🚀", key="run_code"):
    with st.spinner("Processing code..."):
        try:
            if mode == "Translate to another language":
                processor = PolyglotPipeline(target_lang)
            else:
                processor = PythonVersionPipeline(python_version_target)

            result, exec_outputs = processor.run(code_input)

            st.subheader(f"Resulting Code: `{source_name}`")
            if mode == "Translate to another language":
                language_map = {"r": "r", "java": "java", "pyspark": "python"}
                st.code(result, language=language_map.get(target_lang, "text"))
            else:
                st.code(result, language="python")

            # --- Show pastel diff ---
            st.subheader("Code Differences (Pastel Highlighting)")
            diff_html = generate_diff_html(code_input, result)
            st.markdown(diff_html, unsafe_allow_html=True)

            st.success("Processing complete!")

            st.subheader("Execution Results:")
            for i, output in enumerate(exec_outputs):
                if output is None:
                    continue
                with st.expander(f"Chunk {i+1} Execution Result", expanded=False):
                    if output["success"]:
                        st.markdown("✅ Executed successfully")
                        if output["output"]:
                            st.text_area("Output", output["output"], height=150)
                    else:
                        st.markdown("❌ Execution failed")
                        st.text_area("Error", output["error"], height=150)

            # AI Overview
            st.subheader("AI Overview Report")
            overview_agent = AIOverviewAgent()
            report = overview_agent.generate_report(code_input, result)
            st.markdown(report)

        except Exception as e:
            st.error(f"Error: {e}")
