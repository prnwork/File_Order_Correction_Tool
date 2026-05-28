import streamlit as st
import tempfile
import zipfile
import os
from PIL import Image

from logic import (
    ImageOrderLogic,
    ImageProcessor,
    LoggerManager
)

logger = LoggerManager()

st.set_page_config(
    page_title="Manuscript Image Order Tool",
    layout="wide"
)

st.title("📚 Manuscript Image Order Tool")

st.markdown("""
Upload manuscript images and automatically correct alternating
back-front scan ordering.
""")

uploaded_files = st.file_uploader(
    "Upload Images",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if uploaded_files:

    uploaded_files = sorted(uploaded_files, key=lambda x: x.name)

    image_names = [f.name for f in uploaded_files]

    st.success(f"{len(image_names)} images uploaded")

    # =========================
    # Thumbnail Preview
    # =========================

    st.subheader("🖼 Uploaded Images")

    thumb_cols = st.columns(5)

    for idx, file in enumerate(uploaded_files):

        img = Image.open(file)

        with thumb_cols[idx % 5]:
            st.image(img, caption=f"{idx+1}. {file.name}")

    st.divider()

    # =========================
    # Count Controls
    # =========================

    st.subheader("⚙ Correction Settings")

    col1, col2 = st.columns(2)

    with col1:
        first_count = st.number_input(
            "Correct images at beginning",
            min_value=0,
            max_value=len(image_names),
            value=0
        )

    with col2:
        last_count = st.number_input(
            "Correct images at end",
            min_value=0,
            max_value=len(image_names),
            value=0
        )

    intermediate = (
        len(image_names)
        - first_count
        - last_count
    )

    if intermediate < 0:
        st.error("Counts exceed total images")
        st.stop()

    st.warning(
        f"{intermediate} intermediate images will be reordered"
    )

    # =========================
    # Run Correction
    # =========================

    if st.button("🚀 Run Correction"):

        corrected_names = (
            ImageOrderLogic.correct_image_order(
                image_names,
                first_count,
                last_count
            )
        )

        st.success("Correction completed")

        # =================================
        # Build filename -> file mapping
        # =================================

        file_map = {
            file.name: file
            for file in uploaded_files
        }

        corrected_files = [
            file_map[name]
            for name in corrected_names
        ]

        # =========================
        # Before / After Preview
        # =========================

        st.subheader("📊 Before / After Comparison")

        preview_pairs = (
            ImageOrderLogic.create_preview_pairs(
                image_names,
                corrected_names
            )
        )

        for pair_idx, pair in enumerate(preview_pairs):

            before_pair, after_pair = pair

            st.markdown(f"### Pair {pair_idx + 1}")

            col1, col2 = st.columns(2)

            # BEFORE
            with col1:

                st.markdown("#### Before")

                for fname in before_pair:

                    if fname:

                        img = Image.open(file_map[fname])

                        st.image(
                            img,
                            caption=fname,
                            use_container_width=True
                        )

            # AFTER
            with col2:

                st.markdown("#### After")

                for fname in after_pair:

                    if fname:

                        img = Image.open(file_map[fname])

                        st.image(
                            img,
                            caption=fname,
                            use_container_width=True
                        )

            st.divider()

        # =========================
        # Download ZIP
        # =========================

        st.subheader("⬇ Download Corrected Files")

        temp_zip = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".zip"
        )

        with zipfile.ZipFile(
            temp_zip.name,
            'w',
            zipfile.ZIP_DEFLATED
        ) as zipf:

            for idx, file in enumerate(corrected_files):

                corrected_filename = (
                    f"{idx+1}_{file.name}"
                )

                temp_file = tempfile.NamedTemporaryFile(
                    delete=False
                )

                temp_file.write(file.getbuffer())
                temp_file.close()

                zipf.write(
                    temp_file.name,
                    corrected_filename
                )

        with open(temp_zip.name, "rb") as f:

            st.download_button(
                label="📦 Download Corrected ZIP",
                data=f,
                file_name="corrected_images.zip",
                mime="application/zip"
            )