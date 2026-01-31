import streamlit as st
import pandas as pd
import sqlite3
from fuzzywuzzy import fuzz
from typing import Tuple, List, Dict

def parse_code_identity(code: str) -> Dict[str, str]:
    """Parse codeIdentity menjadi komponen wilayah"""
    # Clean code (remove spaces, dashes, dots)
    clean_code = str(code).replace(' ', '').replace('-', '').replace('.', '')

    return {
        'kdprov': clean_code[0:2] if len(clean_code) >= 2 else '',
        'kdkab': clean_code[2:4] if len(clean_code) >= 4 else '',
        'kdkec': clean_code[4:7] if len(clean_code) >= 7 else '',
        'kddesa': clean_code[7:10] if len(clean_code) >= 10 else '',
        'full_code': clean_code
    }

def lookup_wilayah(conn, parsed_code: Dict[str, str]) -> pd.DataFrame:
    """Lookup wilayah dari database berdasarkan kode"""
    try:
        query = """
            SELECT nmkab, nmkec, nmdesa
            FROM wilayah
            WHERE kdprov = ? AND kdkab = ? AND kdkec = ? AND kddesa = ?
        """
        result = pd.read_sql_query(
            query,
            conn,
            params=[
                parsed_code['kdprov'],
                parsed_code['kdkab'],
                parsed_code['kdkec'],
                parsed_code['kddesa']
            ]
        )
        return result
    except Exception as e:
        st.error(f"Error lookup wilayah: {e}")
        return pd.DataFrame()

def fuzzy_match_name(name1: str, name2: str, case_sensitive: bool = False) -> int:
    """Calculate similarity between two names"""
    if not case_sensitive:
        name1 = str(name1).upper()
        name2 = str(name2).upper()

    return fuzz.ratio(str(name1), str(name2))

def compare_data(
    csv_df: pd.DataFrame,
    sqlite_df: pd.DataFrame,
    similarity_threshold: int = 80,
    case_sensitive: bool = False,
    include_nama2: bool = False
) -> Tuple[List[Dict], List[Dict], pd.DataFrame]:
    """
    Compare CSV data dengan SQLite data
    Returns: (matched, csv_unmatched, sqlite_unmatched)
    """
    matched = []
    csv_unmatched = []
    sqlite_matched_ids = set()

    for idx, csv_row in csv_df.iterrows():
        nama_csv = csv_row['nama1']
        best_match = None
        best_similarity = 0
        best_idx = None

        # Try matching with all sqlite names
        for sql_idx, sql_row in sqlite_df.iterrows():
            nama_sql = sql_row['b2r203']
            similarity = fuzzy_match_name(nama_csv, nama_sql, case_sensitive)

            # Also try nama2 if included
            if include_nama2 and 'nama2' in csv_row and pd.notna(csv_row['nama2']):
                similarity2 = fuzzy_match_name(csv_row['nama2'], nama_sql, case_sensitive)
                similarity = max(similarity, similarity2)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = sql_row
                best_idx = sql_idx

        # Check if match is good enough
        if best_similarity >= similarity_threshold and best_match is not None:
            matched.append({
                'no_urut': csv_row['no_urut'],
                'nama_csv': nama_csv,
                'nama2_csv': csv_row.get('nama2', ''),
                'nama_sqlite': best_match['b2r203'],
                'hubungan': best_match['hubungan'],
                'jk': best_match['jk'],
                'umur': best_match.get('umur', ''),
                'Pendidikan': best_match.get('Pendidikan', ''),
                'similarity': best_similarity
            })
            sqlite_matched_ids.add(best_idx)
        else:
            csv_unmatched.append({
                'no_urut': csv_row['no_urut'],
                'nama1': nama_csv,
                'nama2': csv_row.get('nama2', ''),
                'codeIdentity': csv_row.get('codeIdentity', ''),
                'best_similarity': best_similarity if best_match is not None else 0
            })

    # Get unmatched from SQLite
    sqlite_unmatched = sqlite_df[~sqlite_df.index.isin(sqlite_matched_ids)].copy()

    return matched, csv_unmatched, sqlite_unmatched

def show_comparison_page():
    """Main function untuk halaman komparasi"""
    st.title("📊 Komparasi Data CSV vs Database")
    st.markdown("Upload CSV dan bandingkan dengan data di database SQLite")
    st.markdown("---")

    # Database connection
    db_path = "rumah_tangga.db"
    try:
        conn = sqlite3.connect(db_path)
    except Exception as e:
        st.error(f"❌ Gagal koneksi ke database: {e}")
        return

    # Initialize session state
    if 'comparison_results' not in st.session_state:
        st.session_state.comparison_results = None

    # STEP 1: Upload CSV
    st.subheader("1️⃣ Upload File CSV")
    uploaded_file = st.file_uploader(
        "Pilih file CSV",
        type=['csv'],
        help="Upload file CSV yang ingin dibandingkan dengan database"
    )

    if uploaded_file is not None:
        # Read CSV
        try:
            df = pd.read_csv(uploaded_file)
            st.success(f"✅ File berhasil diupload: {len(df)} baris")

            with st.expander("👀 Preview Data CSV", expanded=False):
                st.dataframe(df.head(10), use_container_width=True)
        except Exception as e:
            st.error(f"❌ Error membaca file: {e}")
            return

        st.markdown("---")

        # STEP 2: Column Mapping
        st.subheader("2️⃣ Mapping Kolom CSV")
        st.info("💡 Pilih kolom dari CSV yang sesuai dengan kebutuhan komparasi")

        col1, col2 = st.columns(2)

        available_cols = ['--- Pilih Kolom ---'] + list(df.columns)

        with col1:
            col_code = st.selectbox(
                "📍 Kolom codeIdentity (Kode Wilayah):",
                options=available_cols,
                help="Pilih kolom yang berisi kode wilayah (contoh: 9702300005400300)"
            )

            col_urut = st.selectbox(
                "🔢 Kolom No Urut:",
                options=available_cols,
                help="Pilih kolom yang berisi nomor urut"
            )

        with col2:
            col_nama1 = st.selectbox(
                "👤 Kolom Nama 1 (Utama):",
                options=available_cols,
                help="Pilih kolom nama utama untuk dibandingkan"
            )

            col_nama2 = st.selectbox(
                "👥 Kolom Nama 2 (Opsional):",
                options=['--- Tidak Ada ---'] + list(df.columns),
                help="Opsional: Kolom nama pasangan/anggota kedua"
            )

        # Show preview mapping
        if col_code != '--- Pilih Kolom ---':
            st.success(f"Preview: {col_code} → `{df[col_code].iloc[0]}`")

        st.markdown("---")

        # STEP 3: Parse & Auto-Detect Wilayah
        auto_kec = None
        auto_desa = None

        if col_code != '--- Pilih Kolom ---':
            st.subheader("3️⃣ Deteksi Wilayah dari codeIdentity")

            sample_code = str(df[col_code].iloc[0])
            parsed = parse_code_identity(sample_code)

            col_parse1, col_parse2 = st.columns([1, 1])

            with col_parse1:
                st.write("**Contoh kode:**", sample_code)
                st.json(parsed)

            with col_parse2:
                # Try lookup
                wilayah_result = lookup_wilayah(conn, parsed)

                if not wilayah_result.empty:
                    auto_kec = wilayah_result['nmkec'].iloc[0]
                    auto_desa = wilayah_result['nmdesa'].iloc[0]
                    st.success(f"✅ Wilayah ditemukan:\n\n**{auto_kec} / {auto_desa}**")
                else:
                    st.warning("⚠️ Kode tidak ditemukan di master wilayah BPS")

        st.markdown("---")

        # STEP 4: Manual Wilayah Selection
        st.subheader("4️⃣ Pilih Kecamatan & Desa")
        st.info("💡 Pilih wilayah untuk filter data dari database yang akan dibandingkan")

        # Get kecamatan list
        kec_list = pd.read_sql_query(
            "SELECT DISTINCT nama_kec FROM rumah_tangga ORDER BY nama_kec",
            conn
        )['nama_kec'].tolist()

        col_sel1, col_sel2 = st.columns(2)

        with col_sel1:
            default_kec_idx = 0
            if auto_kec and auto_kec in kec_list:
                default_kec_idx = kec_list.index(auto_kec)

            selected_kec = st.selectbox(
                "🏙️ Kecamatan:",
                options=kec_list,
                index=default_kec_idx
            )

        with col_sel2:
            # Get desa for selected kec
            desa_list = pd.read_sql_query(
                "SELECT DISTINCT nama_desa FROM rumah_tangga WHERE nama_kec = ? ORDER BY nama_desa",
                conn,
                params=[selected_kec]
            )['nama_desa'].tolist()

            default_desa_idx = 0
            if auto_desa and auto_desa in desa_list:
                default_desa_idx = desa_list.index(auto_desa)

            selected_desa = st.selectbox(
                "🏘️ Desa:",
                options=desa_list,
                index=default_desa_idx
            )

        # Show count
        count_query = pd.read_sql_query(
            "SELECT COUNT(*) as total FROM rumah_tangga WHERE nama_kec = ? AND nama_desa = ?",
            conn,
            params=[selected_kec, selected_desa]
        )
        total_db = count_query['total'].iloc[0]

        st.info(f"📍 Wilayah: **{selected_kec} / {selected_desa}** → {total_db:,} data di database")

        st.markdown("---")

        # STEP 5: Advanced Options
        st.subheader("5️⃣ Opsi Komparasi")

        col_opt1, col_opt2, col_opt3 = st.columns(3)

        with col_opt1:
            similarity_threshold = st.slider(
                "Minimum Similarity (%)",
                min_value=50,
                max_value=100,
                value=80,
                help="Threshold untuk menentukan nama dianggap match"
            )

        with col_opt2:
            case_sensitive = st.checkbox(
                "Case Sensitive",
                value=False,
                help="Perhatikan huruf besar/kecil"
            )

        with col_opt3:
            include_nama2 = st.checkbox(
                "Gunakan Nama 2",
                value=True if col_nama2 != '--- Tidak Ada ---' else False,
                disabled=col_nama2 == '--- Tidak Ada ---',
                help="Pertimbangkan Nama 2 dalam matching"
            )

        st.markdown("---")

        # STEP 6: Validation & Execute
        all_mapped = (
            col_code != '--- Pilih Kolom ---' and
            col_urut != '--- Pilih Kolom ---' and
            col_nama1 != '--- Pilih Kolom ---'
        )

        if all_mapped:
            st.subheader("6️⃣ Validasi & Eksekusi")

            with st.expander("📋 Ringkasan Konfigurasi", expanded=True):
                st.write("**Mapping Kolom:**")
                st.write(f"- codeIdentity: `{col_code}`")
                st.write(f"- No Urut: `{col_urut}`")
                st.write(f"- Nama 1: `{col_nama1}`")
                st.write(f"- Nama 2: `{col_nama2 if col_nama2 != '--- Tidak Ada ---' else 'Tidak digunakan'}`")

                st.write("\n**Wilayah:**")
                st.write(f"- Kecamatan: `{selected_kec}`")
                st.write(f"- Desa: `{selected_desa}`")

                st.write("\n**Opsi:**")
                st.write(f"- Similarity threshold: `{similarity_threshold}%`")
                st.write(f"- Case sensitive: `{case_sensitive}`")
                st.write(f"- Include Nama 2: `{include_nama2}`")

                st.write("\n**Data:**")
                st.write(f"- Baris di CSV: `{len(df)}`")
                st.write(f"- Baris di Database (filtered): `{total_db}`")

            if st.button("🔍 Mulai Komparasi", type="primary", use_container_width=True):
                with st.spinner("⏳ Memproses komparasi data..."):
                    # Prepare CSV data
                    csv_mapped = pd.DataFrame({
                        'no_urut': df[col_urut],
                        'nama1': df[col_nama1],
                        'codeIdentity': df[col_code]
                    })

                    if col_nama2 != '--- Tidak Ada ---':
                        csv_mapped['nama2'] = df[col_nama2]

                    # Get SQLite data (filtered)
                    sqlite_data = pd.read_sql_query("""
                        SELECT * FROM rumah_tangga
                        WHERE nama_kec = ? AND nama_desa = ?
                        ORDER BY id_ruta, hubungan
                    """, conn, params=[selected_kec, selected_desa])

                    # Do comparison
                    matched, csv_unmatched, sqlite_unmatched = compare_data(
                        csv_mapped,
                        sqlite_data,
                        similarity_threshold,
                        case_sensitive,
                        include_nama2
                    )

                    # Store in session state
                    st.session_state.comparison_results = {
                        'matched': matched,
                        'csv_unmatched': csv_unmatched,
                        'sqlite_unmatched': sqlite_unmatched,
                        'total_csv': len(csv_mapped),
                        'total_sqlite': len(sqlite_data)
                    }

                st.success("✅ Komparasi selesai!")
                st.rerun()
        else:
            st.warning("⚠️ Mapping belum lengkap. Lengkapi kolom di atas terlebih dahulu.")

    # Display Results
    if st.session_state.comparison_results is not None:
        results = st.session_state.comparison_results

        st.markdown("---")
        st.header("📊 Hasil Komparasi")

        # Statistics
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

        match_rate = len(results['matched']) / results['total_csv'] * 100 if results['total_csv'] > 0 else 0

        with col_stat1:
            st.metric("Total CSV", results['total_csv'])
        with col_stat2:
            st.metric("Total Database", results['total_sqlite'])
        with col_stat3:
            st.metric("Match", len(results['matched']))
        with col_stat4:
            st.metric("Match Rate", f"{match_rate:.1f}%")

        st.markdown("---")

        # Tabel 1: Matched
        st.subheader(f"✅ Tabel 1: Data Berhasil Match ({len(results['matched'])})")
        if results['matched']:
            df_matched = pd.DataFrame(results['matched'])
            # Sort by no_urut
            df_matched = df_matched.sort_values('no_urut')

            # Display with copy-to-clipboard enabled
            st.data_editor(
                df_matched,
                use_container_width=True,
                hide_index=True,
                disabled=True,
                key='table1'
            )

            # Download button
            csv1 = df_matched.to_csv(index=False)
            st.download_button(
                "📥 Download Tabel 1 (Matched)",
                csv1,
                "matched_data.csv",
                "text/csv",
                key='download-matched'
            )
        else:
            st.info("Tidak ada data yang match")

        st.markdown("---")

        # Tabel 2: CSV Unmatched
        st.subheader(f"❌ Tabel 2: Di CSV tapi Tidak di Database ({len(results['csv_unmatched'])})")
        if results['csv_unmatched']:
            df_csv_unmatched = pd.DataFrame(results['csv_unmatched'])
            df_csv_unmatched = df_csv_unmatched.sort_values('no_urut')

            # Display with copy-to-clipboard enabled
            st.data_editor(
                df_csv_unmatched,
                use_container_width=True,
                hide_index=True,
                disabled=True,
                key='table2'
            )

            csv2 = df_csv_unmatched.to_csv(index=False)
            st.download_button(
                "📥 Download Tabel 2 (CSV Unmatched)",
                csv2,
                "csv_unmatched.csv",
                "text/csv",
                key='download-csv-unmatched'
            )
        else:
            st.info("Semua data CSV berhasil match")

        st.markdown("---")

        # Tabel 3: SQLite Unmatched (hanya KK / hubungan = 1)
        df_sqlite_kk_only = results['sqlite_unmatched'][results['sqlite_unmatched']['hubungan'] == 1].copy()
        st.subheader(f"🔍 Tabel 3: Kepala Keluarga di Database tapi Tidak di CSV ({len(df_sqlite_kk_only)})")
        if len(df_sqlite_kk_only) > 0:
            df_sqlite_unmatched = df_sqlite_kk_only[
                ['b2r203', 'jk', 'umur', 'Pendidikan', 'nama_kec', 'nama_desa']
            ].copy()
            df_sqlite_unmatched = df_sqlite_unmatched.sort_values('b2r203')

            # Display with copy-to-clipboard enabled
            st.data_editor(
                df_sqlite_unmatched,
                use_container_width=True,
                hide_index=True,
                disabled=True,
                key='table3'
            )

            csv3 = df_sqlite_unmatched.to_csv(index=False)
            st.download_button(
                "📥 Download Tabel 3 (SQLite Unmatched KK)",
                csv3,
                "sqlite_unmatched_kk.csv",
                "text/csv",
                key='download-sqlite-unmatched'
            )
        else:
            st.info("Semua Kepala Keluarga di database berhasil match")

        # Reset button
        if st.button("🔄 Reset & Upload Baru"):
            st.session_state.comparison_results = None
            st.rerun()

    conn.close()

if __name__ == "__main__":
    show_comparison_page()
