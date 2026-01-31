import streamlit as st
import pandas as pd
import json
import os
import re
import sqlite3
from typing import Dict, List, Any, Set, Tuple

# Konfigurasi halaman
st.set_page_config(
    page_title="Aplikasi Data Rumah Tangga",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import comparison page
from data_comparison_page import show_comparison_page

class RumahTanggaSearchApp:
    def __init__(self):
        self.data_dir = r""
        self.db_name = "rumah_tangga.db"
    
    def load_json_from_upload(self, uploaded_file) -> List[Dict]:
        """Memuat data dari uploaded JSON file"""
        try:
            if uploaded_file is not None:
                data = json.load(uploaded_file)
                return data
            return []
        except Exception as e:
            st.error(f"Error membaca file JSON: {str(e)}")
            return []
    
    @st.cache_resource
    def get_db_connection(_self):
        """Membuat koneksi ke SQLite database"""
        if not os.path.exists(_self.db_name):
            st.error(f"❌ Database tidak ditemukan: {_self.db_name}")
            st.info("💡 Jalankan script 'python csv_to_sqlite.py' terlebih dahulu untuk membuat database")
            return None

        conn = sqlite3.connect(_self.db_name, check_same_thread=False)
        # Enable case-insensitive LIKE
        conn.create_function("LOWER", 1, lambda x: x.lower() if x else x)
        return conn

    def check_database_status(self) -> bool:
        """Check apakah database tersedia dan tampilkan statistik"""
        if not os.path.exists(self.db_name):
            return False

        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM rumah_tangga')
            total_rows = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(DISTINCT id_ruta) FROM rumah_tangga')
            total_ruta = cursor.fetchone()[0]

            conn.close()

            st.success(f"✅ Database terkoneksi: {total_rows:,} baris data | {total_ruta:,} rumah tangga")
            return True

        except Exception as e:
            st.error(f"❌ Error membaca database: {str(e)}")
            return False
    
    def extract_names_from_kk(self, kk_field: str) -> List[str]:
        """Extract nama-nama dari field KK yang bisa berisi 1 atau 2 nama dipisahkan '/'"""
        if not kk_field or pd.isna(kk_field):
            return []
        
        # Split berdasarkan '/' dan bersihkan spasi
        names = [name.strip() for name in str(kk_field).split('/')]
        # Hapus nama kosong
        names = [name for name in names if name and name != '']
        return names
    
    def get_all_names_from_json(self, json_data: List[Dict]) -> Set[str]:
        """Mengambil semua nama unik dari data JSON"""
        all_names = set()
        
        for item in json_data:
            kk_names = self.extract_names_from_kk(item.get('KK', ''))
            all_names.update(kk_names)
        
        return all_names
    
    def get_unique_wilayah(self, json_data: List[Dict]) -> List[str]:
        """Mengambil daftar wilayah unik dari JSON (sorted)"""
        wilayah_set = set()
        for item in json_data:
            wilayah = item.get('wilayah', '').strip()
            if wilayah:
                wilayah_set.add(wilayah)
        return sorted(list(wilayah_set))

    def get_unique_wilayah_from_db(self, conn) -> List[str]:
        """Mengambil daftar wilayah unik dari database dengan format 'nama_kec / nama_desa' (sorted)"""
        if conn is None:
            return []

        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT nama_kec, nama_desa
            FROM rumah_tangga
            WHERE nama_kec IS NOT NULL AND nama_desa IS NOT NULL
            ORDER BY nama_kec, nama_desa
        """)

        wilayah_list = [f"{row[0]} / {row[1]}" for row in cursor.fetchall()]
        return wilayah_list
    
    def get_unique_kk_names(self, json_data: List[Dict]) -> List[str]:
        """Mengambil daftar KK unik dari JSON sesuai urutan asli (tidak diurutkan, tidak di-parse)"""
        kk_list = []
        seen = set()
        
        for item in json_data:
            kk = item.get('KK', '').strip()
            if kk and kk not in seen:
                kk_list.append(kk)
                seen.add(kk)
        
        return kk_list
    
    def get_unique_kk_names_by_wilayah(self, json_data: List[Dict], wilayah: str) -> List[str]:
        """Mengambil daftar KK unik dari JSON untuk wilayah tertentu"""
        kk_list = []
        seen = set()
        for item in json_data:
            if wilayah is None or wilayah == 'Semua' or item.get('wilayah', '').strip() == wilayah:
                kk = item.get('KK', '').strip()
                if kk and kk not in seen:
                    kk_list.append(kk)
                    seen.add(kk)
        return kk_list

    def get_unique_kk_from_db_by_wilayah(self, conn, wilayah: str) -> List[str]:
        """Mengambil daftar nama KK unik dari database untuk wilayah tertentu (hubungan == 1)"""
        if conn is None:
            return []

        cursor = conn.cursor()

        if wilayah and wilayah != 'Semua':
            # Parse wilayah filter (format: "nama_kec / nama_desa")
            parts = wilayah.split(' / ')
            if len(parts) == 2:
                kec_filter = parts[0].strip()
                desa_filter = parts[1].strip()

                cursor.execute("""
                    SELECT DISTINCT b2r203
                    FROM rumah_tangga
                    WHERE hubungan = 1
                      AND nama_kec = ?
                      AND nama_desa = ?
                      AND b2r203 IS NOT NULL
                    ORDER BY b2r203
                """, (kec_filter, desa_filter))
            else:
                cursor.execute("""
                    SELECT DISTINCT b2r203
                    FROM rumah_tangga
                    WHERE hubungan = 1
                      AND b2r203 IS NOT NULL
                    ORDER BY b2r203
                """)
        else:
            cursor.execute("""
                SELECT DISTINCT b2r203
                FROM rumah_tangga
                WHERE hubungan = 1
                  AND b2r203 IS NOT NULL
                ORDER BY b2r203
            """)

        kk_names = [row[0] for row in cursor.fetchall()]
        return kk_names

    def search_rumah_tangga_db(self, conn, json_data: List[Dict],
                               wilayah_filter: str = None, kk_filter: str = None) -> Tuple[pd.DataFrame, Dict]:
        """Mencari rumah tangga menggunakan SQLite database (lebih cepat)"""

        if conn is None:
            return pd.DataFrame(), {}

        cursor = conn.cursor()
        match_details = {}

        # Jika ada JSON data, gunakan logic pencarian nama
        if json_data:
            # Filter JSON data berdasarkan kriteria
            filtered_json = json_data
            if wilayah_filter and wilayah_filter != 'Semua':
                filtered_json = [item for item in filtered_json
                               if item.get('wilayah', '').strip() == wilayah_filter]

            if kk_filter and kk_filter != 'Semua':
                filtered_json = [item for item in filtered_json
                               if item.get('KK', '').strip() == kk_filter]

            # Ambil semua nama dari JSON yang sudah difilter
            search_names = self.get_all_names_from_json(filtered_json)

            if not search_names:
                return pd.DataFrame(), {}

            # Cari nama-nama tersebut di database
            all_ruta_ids = set()

            with st.spinner(f"Mencari {len(search_names)} nama dalam database..."):
                for name in search_names:
                    # Query untuk mencari nama (case insensitive)
                    cursor.execute("""
                        SELECT id_ruta, COUNT(*) as count
                        FROM rumah_tangga
                        WHERE LOWER(b2r203) LIKE LOWER(?)
                        GROUP BY id_ruta
                    """, (f'%{name}%',))

                    results = cursor.fetchall()
                    if results:
                        match_details[name] = sum(row[1] for row in results)
                        all_ruta_ids.update(row[0] for row in results)

            if not all_ruta_ids:
                return pd.DataFrame(), match_details

            # Ambil semua anggota rumah tangga untuk id_ruta yang cocok
            placeholders = ','.join('?' * len(all_ruta_ids))
            query = f"""
                SELECT * FROM rumah_tangga
                WHERE id_ruta IN ({placeholders})
                ORDER BY id_ruta
            """

            df = pd.read_sql_query(query, conn, params=list(all_ruta_ids))
            return df, match_details

        # Jika tidak ada JSON, filter berdasarkan wilayah dan/atau KK dari database
        else:
            conditions = []
            params = []

            if wilayah_filter and wilayah_filter != 'Semua':
                # Parse wilayah filter (format: "nama_kec / nama_desa")
                parts = wilayah_filter.split(' / ')
                if len(parts) == 2:
                    kec_filter = parts[0].strip()
                    desa_filter = parts[1].strip()
                    conditions.append("nama_kec = ?")
                    conditions.append("nama_desa = ?")
                    params.extend([kec_filter, desa_filter])

            if kk_filter and kk_filter != 'Semua':
                # Ambil id_ruta dari KK yang dipilih
                kk_query = "SELECT id_ruta FROM rumah_tangga WHERE hubungan = 1 AND b2r203 = ?"
                kk_params = [kk_filter]

                if conditions:
                    kk_query += " AND " + " AND ".join(conditions)
                    kk_params.extend(params)

                cursor.execute(kk_query, kk_params)
                ruta_ids = [row[0] for row in cursor.fetchall()]

                if not ruta_ids:
                    return pd.DataFrame(), {}

                # Ambil semua anggota dari rumah tangga tersebut
                placeholders = ','.join('?' * len(ruta_ids))
                query = f"SELECT * FROM rumah_tangga WHERE id_ruta IN ({placeholders}) ORDER BY id_ruta"
                df = pd.read_sql_query(query, conn, params=ruta_ids)
                return df, {}

            # Jika hanya filter wilayah
            elif conditions:
                query = f"SELECT * FROM rumah_tangga WHERE {' AND '.join(conditions)} ORDER BY id_ruta"
                df = pd.read_sql_query(query, conn, params=params)
                return df, {}

            # Jika tidak ada filter sama sekali
            else:
                return pd.DataFrame(), {}
    
    def get_household_summary(self, data: pd.DataFrame) -> Dict:
        """Membuat ringkasan data rumah tangga"""
        if data.empty:
            return {}
        
        summary = {
            'total_individuals': len(data),
            'total_households': data['id_ruta'].astype(str).nunique(),
            'kecamatan': data['nama_kec'].nunique(),
            'desa': data['nama_desa'].nunique(),
            'sls': data['nama_sls'].nunique()
        }
        
        return summary
    
    def display_results(self, results: pd.DataFrame, match_details: Dict, summary: Dict):
        """Menampilkan hasil pencarian"""
        if results.empty:
            st.toast("❌ Tidak ada data rumah tangga yang ditemukan")
            return
        
        try:
            # Summary
            st.toast(f"✅ Ditemukan {summary['total_households']} rumah tangga dengan {summary['total_individuals']} anggota")
            
            
            # Data Per Rumah Tangga
            st.subheader("🏠 Data Per Rumah Tangga")
            
            # Initialize session state for result filters if not exists
            if 'result_kec_filter' not in st.session_state:
                st.session_state.result_kec_filter = 'Semua'
            if 'result_desa_filter' not in st.session_state:
                st.session_state.result_desa_filter = 'Semua'
            
            # Apply filters
            filtered_results = results.copy()
            
            # Tampilkan data per rumah tangga
            if filtered_results.empty:
                st.warning("❌ Tidak ada data setelah filter diterapkan")
                return
                
            # Konversi ke string untuk menghindari error sorting mixed types
            unique_ruta_ids = filtered_results['id_ruta'].astype(str).unique()
            for i, ruta_id in enumerate(sorted(unique_ruta_ids), 1):
                # Filter data untuk rumah tangga ini (konversi ke string untuk matching)
                household_data = filtered_results[filtered_results['id_ruta'].astype(str) == ruta_id]
                first_row = household_data.iloc[0]
                
                with st.expander(f"Rumah Tangga {i}: ID {ruta_id} ({len(household_data)} anggota) | {first_row['nama_kec']} => {first_row['nama_desa']} => {first_row['nama_sls']}", expanded=False):
                    
                    # Tampilkan tabel anggota rumah tangga
                    st.write("**Daftar Anggota Rumah Tangga:**")
                    
                    # Siapkan data untuk tabel
                    table_data = []
                    for idx, member in household_data.iterrows():
                        nama = str(member.get('b2r203', 'N/A'))
                        hubungan = str(member.get('hubungan', 'N/A'))
                        jk = str(member.get('jk', 'N/A'))
                        umur = str(member.get('umur', '')) if pd.notna(member.get('umur')) else ''
                        b3r303 = str(member.get('b3r303', 'N/A')) if pd.notna(member.get('b3r303')) else 'N/A'
                        ijazah = str(member.get('ijazah', 'N/A')) if pd.notna(member.get('ijazah')) else 'N/A'
                        pendidikan = str(member.get('Pendidikan', 'N/A'))
                        
                        # Cek apakah nama ini yang dicari
                        is_matched = any(search_name.lower() in str(nama).lower() 
                                       for search_name in match_details.keys())
                        
                        table_data.append({
                            'Status': '🎯 COCOK' if is_matched else '',
                            'Nama': nama,
                            'Hubungan': hubungan,
                            'Jenis Kelamin': jk,
                            'Umur': umur,
                            'NIK': b3r303,
                            'Ijazah': ijazah,
                            'Pendidikan': pendidikan
                        })
                    
                    # Tampilkan tabel
                    table_df = pd.DataFrame(table_data)
                    st.dataframe(table_df, use_container_width=True, hide_index=True)
                    
        except Exception as e:
            st.error(f"❌ Error dalam menampilkan hasil: {str(e)}")
            st.write("**Detail error untuk debugging:**")
            st.write(f"- Tipe error: {type(e).__name__}")
            st.write(f"- Pesan error: {str(e)}")
            
            # Tampilkan info data untuk debugging
            with st.expander("Info Data untuk Debugging"):
                st.write("**Info kolom data:**")
                st.write(f"- Kolom tersedia: {list(results.columns)}")
                st.write(f"- Tipe data id_ruta: {results['id_ruta'].dtype}")
                st.write(f"- Sample id_ruta: {results['id_ruta'].head().tolist()}")
                st.write(f"- Unique id_ruta: {results['id_ruta'].nunique()} values")

def main():
    # Sidebar navigation
    st.sidebar.title("📋 Menu Navigasi")
    page = st.sidebar.radio(
        "Pilih Halaman:",
        ["🔍 Pencarian Data", "⚖️ Komparasi Data"],
        index=0
    )

    st.sidebar.markdown("---")
    st.sidebar.info(
        "**🔍 Pencarian Data**\n"
        "Mencari dan menampilkan data rumah tangga dari database.\n\n"
        "**⚖️ Komparasi Data**\n"
        "Membandingkan data dari CSV upload dengan database SQLite."
    )

    # Route to selected page
    if page == "⚖️ Komparasi Data":
        show_comparison_page()
        return

    # Otherwise show search page (default)
    st.title("🏠 Pencarian Data Rumah Tangga")
    st.markdown("Aplikasi untuk mencari rumah tangga")
    st.markdown("---")

    app = RumahTanggaSearchApp()

    # Initialize session state for main filters if not exists
    if 'wilayah_filter' not in st.session_state:
        st.session_state.wilayah_filter = 'Semua'
    if 'kk_filter' not in st.session_state:
        st.session_state.kk_filter = 'Semua'
    if 'json_data' not in st.session_state:
        st.session_state.json_data = []

    # File uploader untuk JSON
    st.subheader("📁 Upload File JSON (Opsional)")
    uploaded_file = st.file_uploader(
        "Upload file JSON yang berisi data KK dan wilayah untuk filtering",
        type=['json'],
        help="File JSON opsional. Jika tidak diupload, filter wilayah akan menggunakan data dari CSV."
    )

    # Process uploaded JSON file
    if uploaded_file is not None:
        json_data = app.load_json_from_upload(uploaded_file)
        st.session_state.json_data = json_data
        if json_data:
            st.success(f"✅ File JSON berhasil dimuat: {len(json_data)} entri")
    else:
        json_data = st.session_state.json_data
        if not json_data:
            st.info("ℹ️ Tidak ada file JSON yang diupload. Filter wilayah akan menggunakan format: Kecamatan / Desa dari data CSV.")

    st.markdown("---")

    # Check database status
    if not app.check_database_status():
        st.warning("⚠️ Database belum tersedia. Jalankan converter terlebih dahulu:")
        st.code("python csv_to_sqlite.py", language="bash")
        return

    # Get database connection
    conn = app.get_db_connection()
    if conn is None:
        return

    # Sidebar untuk filter
    col1, col2, col3 = st.columns(3, vertical_alignment="bottom")

    # Filter berdasarkan wilayah (dropdown) - dengan session state
    with col1:
        # Tentukan sumber wilayah berdasarkan ada tidaknya JSON
        if json_data:
            unique_wilayah = app.get_unique_wilayah(json_data)
        else:
            unique_wilayah = app.get_unique_wilayah_from_db(conn)

        wilayah_options = ['Semua'] + unique_wilayah
        wilayah_filter = st.selectbox(
            "Filter Wilayah:",
            options=wilayah_options,
            index=wilayah_options.index(st.session_state.wilayah_filter) if st.session_state.wilayah_filter in wilayah_options else 0,
            key="wilayah_selectbox"
        )
        st.session_state.wilayah_filter = wilayah_filter

    # Filter berdasarkan KK (dropdown) - dari JSON atau database
    with col2:
        if json_data:
            # Ambil daftar KK unik dari JSON sesuai wilayah terpilih
            filtered_kk_names = app.get_unique_kk_names_by_wilayah(
                json_data, st.session_state.wilayah_filter
            )
        else:
            # Ambil daftar KK unik dari database sesuai wilayah terpilih
            filtered_kk_names = app.get_unique_kk_from_db_by_wilayah(
                conn, st.session_state.wilayah_filter
            )

        kk_options = ['Semua'] + filtered_kk_names
        # Reset kk_filter jika tidak ada di opsi baru
        if st.session_state.kk_filter not in kk_options:
            st.session_state.kk_filter = 'Semua'
        kk_filter = st.selectbox(
            "Filter KK (Nama Kepala Keluarga):",
            options=kk_options,
            index=kk_options.index(st.session_state.kk_filter) if st.session_state.kk_filter in kk_options else 0,
            key="kk_selectbox"
        )
        st.session_state.kk_filter = kk_filter

    with col3:
        search_label = "🔍 Cari Data Rumah Tangga" if json_data else "🔍 Filter Data"
        if st.button(search_label, type="primary"):
            try:
                # Reset result filters when new search is performed
                st.session_state.result_kec_filter = 'Semua'
                st.session_state.result_desa_filter = 'Semua'

                results, match_details = app.search_rumah_tangga_db(
                    conn, json_data,
                    wilayah_filter if wilayah_filter != 'Semua' else None,
                    kk_filter if kk_filter != 'Semua' else None
                )
                summary = app.get_household_summary(results)
            except Exception as e:
                st.error(f"❌ Error dalam pencarian: {str(e)}")
                st.write("**Detail error:**")
                st.write(f"- Tipe error: {type(e).__name__}")
                st.write(f"- Pesan error: {str(e)}")

    # Menampilkan hasil di luar blok kolom
    if 'results' in locals() and 'match_details' in locals() and 'summary' in locals():
        app.display_results(results, match_details, summary)


    
    # Footer
    st.markdown("---")
    st.markdown("*Aplikasi Pencarian Data Rumah Tangga")

if __name__ == "__main__":
    main()
