import streamlit as st
import pandas as pd
import json
import os
import re
from typing import Dict, List, Any, Set, Tuple

# Konfigurasi halaman
st.set_page_config(
    page_title="Pencarian Data Rumah Tangga",
    page_icon="🏠",
    layout="wide"
)

class RumahTanggaSearchApp:
    def __init__(self):
        self.data_dir = r"D:\Program\data"
        self.json_file = os.path.join(self.data_dir, "data.json")
    
    @st.cache_data
    def load_json_data(_self) -> List[Dict]:
        """Memuat data dari file JSON"""
        try:
            with open(_self.json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error membaca file JSON: {str(e)}")
            return []
    
    @st.cache_data
    def load_csv_data(_self) -> pd.DataFrame:
        """Memuat dan menggabungkan semua file data*.csv"""
        try:
            import glob
            # Mencari semua file data*.csv
            csv_pattern = os.path.join(_self.data_dir, "data*.csv")
            csv_files = glob.glob(csv_pattern)
            
            if not csv_files:
                st.error("Tidak ada file data*.csv ditemukan")
                return pd.DataFrame()
            
            # Memuat dan menggabungkan semua file CSV
            dataframes = []
            for csv_file in csv_files:
                try:
                    df = pd.read_csv(csv_file)
                    dataframes.append(df)
                except Exception as e:
                    st.toast(f"⚠️ Error memuat {os.path.basename(csv_file)}: {str(e)}")
            
            if not dataframes:
                st.error("Tidak ada file CSV yang berhasil dimuat")
                return pd.DataFrame()
            
            # Gabungkan semua dataframes
            combined_df = pd.concat(dataframes, ignore_index=True)
            st.write(f"📊 Total gabungan: {len(combined_df)} baris dari {len(csv_files)} file")
            
            return combined_df
            
        except Exception as e:
            st.error(f"Error membaca file CSV: {str(e)}")
            return pd.DataFrame()
    
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
    
    def search_rumah_tangga(self, csv_data: pd.DataFrame, json_data: List[Dict], 
                           wilayah_filter: str = None, kk_filter: str = None) -> Tuple[pd.DataFrame, Dict]:
        """Mencari rumah tangga yang memiliki anggota dengan nama dari JSON"""
        
        # Filter JSON data berdasarkan kriteria
        filtered_json = json_data
        if wilayah_filter and wilayah_filter != 'Semua':
            filtered_json = [item for item in filtered_json 
                           if item.get('wilayah', '').strip() == wilayah_filter]
        
        if kk_filter and kk_filter != 'Semua':
            # Filter berdasarkan KK yang dipilih (exact match dengan field KK)
            filtered_json = [item for item in filtered_json 
                           if item.get('KK', '').strip() == kk_filter]
        
        # Ambil semua nama dari JSON yang sudah difilter (tetap parse untuk pencarian)
        search_names = self.get_all_names_from_json(filtered_json)
        
        if not search_names:
            return pd.DataFrame(), {}
        
        # Cari nama-nama tersebut di kolom b2r203
        matched_rows = []
        match_details = {}
        
        with st.spinner(f"Mencari {len(search_names)} nama dalam data CSV..."):
            for name in search_names:
                # Cari nama di kolom b2r203 (case insensitive)
                mask = csv_data['b2r203'].astype(str).str.contains(name, case=False, na=False)
                matching_rows = csv_data[mask]
                
                if not matching_rows.empty:
                    matched_rows.append(matching_rows)
                    match_details[name] = len(matching_rows)
        
        if not matched_rows:
            return pd.DataFrame(), match_details
        
        # Gabungkan semua baris yang cocok
        all_matched = pd.concat(matched_rows, ignore_index=True)
        
        # Ambil semua id_ruta yang unik dari hasil pencarian
        unique_ruta_ids = all_matched['id_ruta'].unique()
        
        # Ambil semua anggota rumah tangga untuk setiap id_ruta yang cocok
        complete_households = csv_data[csv_data['id_ruta'].isin(unique_ruta_ids)]
        
        return complete_households, match_details
    
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
            
            # Filter untuk hasil - dengan session state
            # col1, col2 = st.columns(2)
            # with col1:
            #     kec_options = ['Semua'] + sorted(results['nama_kec'].unique().tolist())
            #     selected_kec = st.selectbox(
            #         "Filter Kecamatan:",
            #         options=kec_options,
            #         index=kec_options.index(st.session_state.result_kec_filter) if st.session_state.result_kec_filter in kec_options else 0,
            #         key="result_kec_selectbox"
            #     )
            #     st.session_state.result_kec_filter = selected_kec
                
            # with col2:
            #     # Update desa options based on kec filter
            #     if selected_kec == 'Semua':
            #         desa_options = ['Semua'] + sorted(results['nama_desa'].unique().tolist())
            #     else:
            #         filtered_by_kec = results[results['nama_kec'] == selected_kec]
            #         desa_options = ['Semua'] + sorted(filtered_by_kec['nama_desa'].unique().tolist())
                
            #     selected_desa = st.selectbox(
            #         "Filter Desa:",
            #         options=desa_options,
            #         index=desa_options.index(st.session_state.result_desa_filter) if st.session_state.result_desa_filter in desa_options else 0,
            #         key="result_desa_selectbox"
            #     )
            #     st.session_state.result_desa_filter = selected_desa
            
            # Apply filters
            filtered_results = results.copy()
            # if selected_kec != 'Semua':
            #     filtered_results = filtered_results[filtered_results['nama_kec'] == selected_kec]
            # if selected_desa != 'Semua':
            #     filtered_results = filtered_results[filtered_results['nama_desa'] == selected_desa]
            
            # # Reset button for result filters
            # col1, col2, col3 = st.columns([1, 1, 2])
            # with col1:
            #     if st.button("🔄 Reset Filter Hasil", key="reset_result_filters"):
            #         st.session_state.result_kec_filter = 'Semua'
            #         st.session_state.result_desa_filter = 'Semua'
            #         st.rerun()
            
            # # Show filter info
            # with col3:
            #     if selected_kec != 'Semua' or selected_desa != 'Semua':
            #         filter_info = []
            #         if selected_kec != 'Semua':
            #             filter_info.append(f"Kec: {selected_kec}")
            #         if selected_desa != 'Semua':
            #             filter_info.append(f"Desa: {selected_desa}")
            #         st.info(f"Filter aktif: {', '.join(filter_info)}")
            
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
                        umur = str(member.get('umur', 'N/A')) if pd.notna(member.get('umur')) else 'N/A'
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
    st.title("🏠 Pencarian Data Rumah Tangga")
    st.markdown("Aplikasi untuk mencari rumah tangga")
    st.markdown("---")
    
    app = RumahTanggaSearchApp()
    
    # Initialize session state for main filters if not exists
    if 'wilayah_filter' not in st.session_state:
        st.session_state.wilayah_filter = 'Semua'
    if 'kk_filter' not in st.session_state:
        st.session_state.kk_filter = 'Semua'
    
    # Load data
    with st.spinner("Memuat data..."):
        json_data = app.load_json_data()
        csv_data = app.load_csv_data()
    
    if not json_data or csv_data.empty:
        st.toast("❌ Gagal memuat data. Pastikan file data.json dan data.csv tersedia.")
        return
    
    st.toast(f"✅ Data berhasil dimuat: {len(json_data)} entri JSON, {len(csv_data)} baris CSV")
    
    # Sidebar untuk filter
    col1, col2, col3 = st.columns(3, vertical_alignment="bottom")
    
    # Filter berdasarkan wilayah (dropdown) - dengan session state
    with col1:
        unique_wilayah = app.get_unique_wilayah(json_data)
        wilayah_options = ['Semua'] + unique_wilayah
        wilayah_filter = st.selectbox(
            "Filter Wilayah:",
            options=wilayah_options,
            index=wilayah_options.index(st.session_state.wilayah_filter) if st.session_state.wilayah_filter in wilayah_options else 0,
            key="wilayah_selectbox"
        )
        st.session_state.wilayah_filter = wilayah_filter
    
    # Filter berdasarkan KK (dropdown) - dengan session state
    with col2:
        # Ambil daftar KK unik dari JSON
        unique_kk_names = app.get_unique_kk_names(json_data)
        kk_options = ['Semua'] + unique_kk_names
        kk_filter = st.selectbox(
            "Filter KK (Nama Kepala Keluarga):",
            options=kk_options,
            index=kk_options.index(st.session_state.kk_filter) if st.session_state.kk_filter in kk_options else 0,
            key="kk_selectbox"
        )
        st.session_state.kk_filter = kk_filter
        

    with col3:
        if st.button("🔍 Cari Data Rumah Tangga", type="primary"):
            try:
                # Reset result filters when new search is performed
                st.session_state.result_kec_filter = 'Semua'
                st.session_state.result_desa_filter = 'Semua'
                
                results, match_details = app.search_rumah_tangga(
                    csv_data, json_data, 
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
