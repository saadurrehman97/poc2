
import streamlit as st
import sys
import os
from pathlib import Path
import json
import pandas as pd
from PIL import Image
import tempfile
import shutil
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import Config
from pipeline import run_full_pipeline
from vector_extractor import is_pdf_supported

# Page configuration
st.set_page_config(
    page_title="Neptune Plumbing Symbol Extractor",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS with beautiful loader
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* Beautiful Loader Animation */
    .loader-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 1rem;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    .loader-text {
        color: white;
        font-size: 1.2rem;
        font-weight: 500;
        margin-bottom: 1rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    .loader-status {
        color: rgba(255,255,255,0.9);
        font-size: 1rem;
        margin-top: 1rem;
        padding: 0.5rem 1rem;
        background: rgba(255,255,255,0.2);
        border-radius: 2rem;
        backdrop-filter: blur(10px);
    }
    
    .loader-bar {
        width: 300px;
        height: 10px;
        background: rgba(255,255,255,0.2);
        border-radius: 10px;
        overflow: hidden;
        position: relative;
    }
    
    .loader-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #ffd700, #ffa500);
        border-radius: 10px;
        animation: loading 2s ease-in-out infinite;
    }
    
    @keyframes loading {
        0% { width: 0%; margin-left: 0; }
        50% { width: 100%; margin-left: 0; }
        100% { width: 0%; margin-left: 100%; }
    }
    
    .pulse {
        animation: pulse 1.5s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    /* Processing stages */
    .stage-container {
        display: flex;
        justify-content: space-between;
        margin: 2rem 0;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 1rem;
    }
    
    .stage {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex: 1;
        position: relative;
    }
    
    .stage:not(:last-child):after {
        content: '';
        position: absolute;
        right: -10px;
        top: 50%;
        width: 20px;
        height: 2px;
        background: #dee2e6;
        transform: translateY(-50%);
    }
    
    .stage-icon {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: #e9ecef;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 0.5rem;
        font-size: 1.2rem;
    }
    
    .stage.active .stage-icon {
        background: #1f77b4;
        color: white;
        animation: pulse 1.5s ease-in-out infinite;
    }
    
    .stage.completed .stage-icon {
        background: #28a745;
        color: white;
    }
    
    .stage-label {
        font-size: 0.9rem;
        color: #6c757d;
    }
    
    .stage.active .stage-label {
        color: #1f77b4;
        font-weight: 600;
    }
    
    .stage.completed .stage-label {
        color: #28a745;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🔧 Neptune Plumbing Symbol Extractor</div>', 
            unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-Method Extraction: Vector + VLM + Object Detection (ONNX)</div>', 
            unsafe_allow_html=True)

# Sidebar configuration
st.sidebar.header("⚙️ Configuration")

# Model settings
st.sidebar.subheader("DFINE Detection Settings")
dfine_confidence = st.sidebar.slider(
    "Confidence Threshold",
    min_value=0.1,
    max_value=0.9,
    value=0.5,
    step=0.05,
    help="Lower = more detections, higher = more precise"
)

# Optional ONNX path override (if user wants to use a different model)
dfine_onnx_path = st.sidebar.text_input(
    "DFINE ONNX Path (optional)",
    value=Config.DFINE_ONNX_PATH,
    help="Path to DFINE ONNX model file. Leave as default unless you have a custom model."
)

st.sidebar.subheader("VLM Settings")
vlm_model = st.sidebar.text_input(
    "VLM Model",
    value=Config.VLM_MODEL,
    help="Ollama model name (ensure it's pulled)"
)

# Validation
st.sidebar.subheader("System Check")
pdf_status = "✅ Available" if is_pdf_supported() else "❌ Not installed"
st.sidebar.write(f"PDF Support: {pdf_status}")

validation_errors = Config.validate()
if validation_errors:
    st.sidebar.error("⚠️ Configuration Issues:")
    for error in validation_errors:
        st.sidebar.write(f"- {error}")
else:
    st.sidebar.success("✅ All systems ready")

# Main content area
st.header("📁 Upload Drawing")

# Initialize session state
if 'extraction_results' not in st.session_state:
    st.session_state.extraction_results = None
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
if 'uploaded_file_name' not in st.session_state:
    st.session_state.uploaded_file_name = None

uploaded_file = st.file_uploader(
    "Choose a PDF or image file",
    type=['pdf', 'png', 'jpg', 'jpeg'],
    help="Upload engineering drawings in PDF or image format"
)

if uploaded_file is not None:
    # Display file info
    file_details = {
        "Filename": uploaded_file.name,
        "File Size": f"{uploaded_file.size / 1024:.2f} KB",
        "File Type": uploaded_file.type
    }
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Filename", file_details["Filename"])
    with col2:
        st.metric("Size", file_details["File Size"])
    with col3:
        st.metric("Type", file_details["File Type"])
    
    # Process button
    if st.button("🚀 Start Extraction", type="primary", use_container_width=True):
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        try:
            # Create placeholder for loader
            loader_placeholder = st.empty()
            progress_placeholder = st.empty()
            stages_placeholder = st.empty()
            
            # Show beautiful loader
            with loader_placeholder.container():
                st.markdown("""
                <div class="loader-container">
                    <div class="loader-text pulse">🔧 Processing Your Drawing</div>
                    <div class="loader-bar">
                        <div class="loader-bar-fill"></div>
                    </div>
                    <div class="loader-status" id="status-text">Initializing pipeline...</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Stage indicators
                stages_placeholder.markdown("""
                <div class="stage-container">
                    <div class="stage active" id="stage1">
                        <div class="stage-icon">📄</div>
                        <div class="stage-label">Initialize</div>
                    </div>
                    <div class="stage" id="stage2">
                        <div class="stage-icon">🤖</div>
                        <div class="stage-label">Load Model</div>
                    </div>
                    <div class="stage" id="stage3">
                        <div class="stage-icon">🔍</div>
                        <div class="stage-label">Vector</div>
                    </div>
                    <div class="stage" id="stage4">
                        <div class="stage-icon">👁️</div>
                        <div class="stage-label">VLM</div>
                    </div>
                    <div class="stage" id="stage5">
                        <div class="stage-icon">🎯</div>
                        <div class="stage-label">DFINE</div>
                    </div>
                    <div class="stage" id="stage6">
                        <div class="stage-icon">📊</div>
                        <div class="stage-label">Results</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Function to update status
            def update_status(text, stage=None, progress=None):
                js = f"""
                <script>
                    document.getElementById('status-text').innerText = '{text}';
                </script>
                """
                st.markdown(f'<div class="loader-status" id="status-text">{text}</div>', unsafe_allow_html=True)
                
                if stage:
                    for i in range(1, 7):
                        st.markdown(f"""
                        <script>
                            document.getElementById('stage{i}').className = 'stage';
                        </script>
                        """, unsafe_allow_html=True)
                    st.markdown(f"""
                    <script>
                        document.getElementById('stage{stage}').className = 'stage active';
                    </script>
                    """, unsafe_allow_html=True)
                
                if progress is not None:
                    progress_placeholder.progress(progress)
                
                time.sleep(0.5)  # Small delay for visual effect
            
            # Run pipeline with status updates
            update_status("Initializing pipeline...", stage=1, progress=10)
            
            # Ensure workspace output directory exists
            Config.ensure_output_dir()
            
            update_status("Loading DFINE ONNX model...", stage=2, progress=20)
            
            # Update config with sidebar values
            Config.VLM_MODEL = vlm_model
            Config.DFINE_CONFIDENCE_THRESHOLD = dfine_confidence
            
            update_status("Extracting vector symbols...", stage=3, progress=40)
            
            # Run pipeline - pass ONNX path if changed
            results = run_full_pipeline(
                tmp_path,
                output_dir=Config.OUTPUT_BASE_DIR,
                dfine_conf=dfine_confidence,
                onnx_path=dfine_onnx_path if dfine_onnx_path != Config.DFINE_ONNX_PATH else None
            )
            
            update_status("VLM analysis in progress...", stage=4, progress=60)
            time.sleep(1)
            
            update_status("DFINE object detection...", stage=5, progress=80)
            time.sleep(1)
            
            update_status("Generating results...", stage=6, progress=95)
            time.sleep(1)
            
            # Get the actual output directory (with timestamp)
            actual_output_dir = Path(results['output_directory'])
            
            # Store results in session state to persist across reruns
            st.session_state.extraction_results = results
            st.session_state.extraction_output_dir = actual_output_dir
            st.session_state.uploaded_file_name = uploaded_file.name
            st.session_state.processing_complete = True
            
            # Clear loader
            loader_placeholder.empty()
            stages_placeholder.empty()
            progress_placeholder.empty()
            
            # Clean up temp files
            os.unlink(tmp_path)
            
        except Exception as e:
            # Clear loader on error
            loader_placeholder.empty()
            stages_placeholder.empty()
            progress_placeholder.empty()
            
            st.error(f"❌ Error during processing: {str(e)}")
            st.exception(e)
            
            # Clean up on error
            if 'tmp_path' in locals():
                try:
                    os.unlink(tmp_path)
                except:
                    pass

# Display results if processing was completed (persists across reruns)
if st.session_state.processing_complete and st.session_state.extraction_results is not None:
    results = st.session_state.extraction_results
    actual_output_dir = st.session_state.extraction_output_dir
    uploaded_file_name = st.session_state.uploaded_file_name
    
    # Display results
    st.success("🎉 Processing Complete!")
    
    # Summary metrics
    st.header("📊 Extraction Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Pages",
            results['metadata'].get('pages', 1)
        )
    
    with col2:
        dfine_total = results['aggregated']['dfine']['total_detections']
        st.metric(
            "DFINE Detections",
            dfine_total
        )
    
    with col3:
        if results['file_type'] == 'PDF':
            vector_total = sum(results['aggregated']['vector']['by_symbol'].values())
            st.metric(
                "Vector Symbols",
                vector_total
            )
        else:
            st.metric(
                "Vector Symbols",
                "N/A (Image)"
            )
    
    with col4:
        vlm_total = sum(results['aggregated']['vlm']['by_symbol'].values())
        st.metric(
            "VLM Symbols",
            vlm_total
        )
    
    # Best estimates table
    st.header("🏆 Final Best Estimates")
    
    if results['final_best_estimates']:
        df = pd.DataFrame([
            {"Symbol": sym, "Count": cnt} 
            for sym, cnt in sorted(
                results['final_best_estimates'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )
        ])
        st.dataframe(df, width='stretch', hide_index=True)
    else:
        st.info("No symbols detected")
    
    # Detailed comparison
    st.header("🔍 Detailed Comparison")
    
    if results['comparison']:
        comparison_df = pd.DataFrame(results['comparison'])
        
        # Select columns to display
        display_cols = ['category', 'symbol', 'vector_count', 'vlm_count', 
                       'dfine_count', 'best_estimate']
        available_cols = [col for col in display_cols if col in comparison_df.columns]
        
        st.dataframe(
            comparison_df[available_cols],
            width='stretch',
            hide_index=True
        )
    
    # Method breakdown
    st.header("📈 Method Breakdown")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("DFINE Classes")
        dfine_classes = results['aggregated']['dfine']['by_class']
        if dfine_classes:
            dfine_df = pd.DataFrame([
                {"Class": k.replace('_', ' ').title(), "Count": v}
                for k, v in sorted(dfine_classes.items(), 
                                  key=lambda x: x[1], reverse=True)
            ])
            st.dataframe(dfine_df, hide_index=True, height=300)
        else:
            st.info("No detections")
    
    with col2:
        if results['file_type'] == 'PDF':
            st.subheader("Vector Symbols")
            vector_symbols = results['aggregated']['vector']['by_symbol']
            if vector_symbols:
                vector_df = pd.DataFrame([
                    {"Symbol": k, "Count": v}
                    for k, v in sorted(vector_symbols.items(), 
                                      key=lambda x: x[1], reverse=True)
                ])
                st.dataframe(vector_df, hide_index=True, height=300)
            else:
                st.info("No symbols found")
        else:
            st.info("Vector extraction only for PDFs")
    
    with col3:
        st.subheader("VLM Symbols")
        vlm_symbols = results['aggregated']['vlm']['by_symbol']
        if vlm_symbols:
            vlm_df = pd.DataFrame([
                {"Symbol": k, "Count": v}
                for k, v in sorted(vlm_symbols.items(), 
                                  key=lambda x: x[1], reverse=True)
            ])
            st.dataframe(vlm_df, hide_index=True, height=300)
        else:
            st.info("No symbols found")
    
    # NEW: Symbol-to-Pipe Connections (STEP 4)
    st.header("🔗 Symbol-to-Pipe Connections (Step 4)")
    st.markdown("""
    This table shows the relationships between plumbing symbols/fixtures and the pipes connected to them.
    Each row represents a symbol-pipe connection mapping with its count.
    """)
    
    vlm_connections = results['aggregated']['vlm'].get('connections', [])
    if vlm_connections:
        # Convert connections list to DataFrame
        connections_df = pd.DataFrame([
            {
                "Symbol": conn.get('symbol', '').replace('_', ' ').title(),
                "Symbol ID": conn.get('symbol', ''),
                "Count": conn.get('count', 0),
                "Connected Pipe": conn.get('pipe', '')
            }
            for conn in vlm_connections
        ])
        
        # Sort by Symbol and Count (descending)
        connections_df = connections_df.sort_values(['Symbol ID', 'Count'], 
                                                   ascending=[True, False])
        
        st.dataframe(
            connections_df[['Symbol', 'Count', 'Connected Pipe']],
            width='stretch',
            hide_index=True,
            use_container_width=True
        )
        
        st.info(f"✅ Found {len(vlm_connections)} symbol-pipe connection mappings across {len(connections_df['Symbol'].unique())} unique symbols")
    else:
        st.warning("⚠️ No symbol-pipe connections detected. This may indicate that:")
        st.markdown("""
        - VLM connection extraction is disabled
        - The drawing clarity or quality is low
        - Symbols and pipes are not clearly connected/labeled in the drawing
        """)
    
    # Download section - 3 files: JSON, CSV, Full Image
    st.header("💾 Download Results")
    
    st.markdown("Download your complete extraction results:")
    
    # Find files
    json_path = actual_output_dir / "results.json"
    csv_path = actual_output_dir / "symbol_counts.csv"
    full_images = list(actual_output_dir.glob("full_image_detected*.jpg"))
    
    # Create download columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if json_path.exists():
            with open(json_path, 'rb') as f:
                st.download_button(
                    label="📥 Download JSON",
                    data=f.read(),
                    file_name=f"{Path(uploaded_file_name).stem}_results.json",
                    mime="application/json",
                    use_container_width=True
                )
    
    with col2:
        if csv_path.exists():
            with open(csv_path, 'rb') as f:
                st.download_button(
                    label="📥 Download CSV",
                    data=f.read(),
                    file_name=f"{Path(uploaded_file_name).stem}_symbols.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    
    with col3:
        if full_images:
            # Use the first full image
            full_image_path = full_images[0]
            with open(full_image_path, 'rb') as f:
                st.download_button(
                    label="📥 Download Full Image",
                    data=f.read(),
                    file_name=f"{Path(uploaded_file_name).stem}_detected.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )
    
    # Additional info about tiles
    tiles_dir = actual_output_dir / "detected_tiles"
    if tiles_dir.exists():
        tile_count = len(list(tiles_dir.glob("*.jpg")))
        st.info(f"📂 {tile_count} detected tile images saved in: {tiles_dir.name}/")
    
    # Clear results button
    st.divider()
    if st.button("🔄 Clear Results & Process Another File", use_container_width=True):
        st.session_state.extraction_results = None
        st.session_state.processing_complete = False
        st.session_state.uploaded_file_name = None
        st.rerun()

else:
    # Instructions when no file uploaded
    st.info("👆 Upload a PDF or image file to begin extraction")
    
    st.markdown("""
    ### How to Use
    
    1. **Upload** your engineering drawing (PDF or image)
    2. **Configure** settings in the sidebar (optional)
    3. **Click** "Start Extraction" to process
    4. **Download** results (JSON + CSV + Full Image)
    
    ### Extraction Methods
    
    - **Vector Extraction** (PDF only): Text-based extraction from PDF metadata
    - **VLM (Vision Language Model)**: AI-powered visual symbol recognition
    - **DFINE Object Detection (ONNX)**: Optimized deep learning model
    
    ### Output Files
    
    - **results.json**: Complete extraction data with all methods
    - **symbol_counts.csv**: Symbol counts in spreadsheet format
    - **full_image_detected.jpg**: Full annotated image with bounding boxes
    - **detected_tiles/**: Folder with individual tile detections
    
    ### Supported Formats
    
    - **PDF**: Multi-page engineering drawings
    - **Images**: PNG, JPG, JPEG (single page)
    
    ### About Your Model
    
    - Your trained DFINE model is exported to ONNX for fast, dependency‑free inference ✅
    - Class names are loaded from `classes.txt` (or hardcoded if file missing)
    - No PyTorch or D‑FINE repository needed – simple and reliable
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Neptune Plumbing v2.0 (ONNX)**")
st.sidebar.markdown("Multi-Method Symbol Extraction")
st.sidebar.markdown("Updated: Feb 2026")

