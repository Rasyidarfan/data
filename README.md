# 🏠 Aplikasi Pencarian Data Rumah Tangga

## 📋 Deskripsi
Aplikasi Streamlit untuk mencari dan menampilkan data rumah tangga berdasarkan pencarian nama dari file JSON ke dalam file CSV.

## 🎯 Cara Kerja
1. **Data JSON** berisi daftar wilayah dan nama Kepala Keluarga (KK)
2. **Data CSV** berisi data lengkap anggota rumah tangga
3. Aplikasi akan mencari nama-nama dari JSON di kolom `b2r203` dalam CSV
4. Menampilkan seluruh anggota rumah tangga (berdasarkan `id_ruta`) yang memiliki nama yang cocok

## 📁 Struktur File
```
D:\Program\data\
├── data.json              # Data KK dan wilayah
├── data.csv               # Data lengkap anggota rumah tangga  
├── contoh_data.csv        # Contoh struktur data CSV
├── data_search_app.py     # Aplikasi Streamlit
├── requirements.txt       # Dependencies Python
├── run_data_search.bat    # File untuk menjalankan aplikasi
└── README.md              # File instruksi ini
```

## 🚀 Cara Menjalankan

### Opsi 1: Menggunakan Batch File (Mudah)
1. Klik dua kali file `run_data_search.bat`
2. Aplikasi akan terbuka di browser

### Opsi 2: Manual via Command Line
```bash
cd D:\Program\data
pip install -r requirements.txt
streamlit run data_search_app.py
```

## 🔍 Fitur Aplikasi

### Filter Pencarian:
- **Filter Wilayah**: Pilih wilayah tertentu dari dropdown
- **Filter KK**: Cari berdasarkan nama Kepala Keluarga

### Hasil Pencarian:
- ✅ Ringkasan: Total rumah tangga dan anggota
- 📋 Detail nama yang ditemukan
- 📊 Data lengkap semua anggota rumah tangga
- 🏠 Data per rumah tangga dengan highlight nama yang cocok
- 💾 Download hasil dalam format CSV

### Filter Tambahan:
- Filter hasil berdasarkan Kecamatan
- Filter hasil berdasarkan Desa

## 📊 Struktur Data

### data.json
```json
{
  "wilayah": "9702340005001B00344",
  "KK": "AMOS LOGO / ARKI LOGO"
}
```

### data.csv (Kolom Utama)
- `id_ruta`: ID Rumah Tangga (yang sama = satu rumah tangga)
- `b2r203`: Nama anggota rumah tangga
- `nama_kec`: Nama Kecamatan
- `nama_desa`: Nama Desa
- `hubungan`: Hubungan dengan KK
- `jk`: Jenis Kelamin
- `umur`: Umur

## 💡 Tips Penggunaan

1. **KK dengan 2 nama**: Field KK yang berisi "NAMA1 / NAMA2" akan dipecah menjadi 2 nama terpisah
2. **Pencarian**: Case-insensitive, akan mencari partial match
3. **Rumah Tangga**: Semua anggota dengan `id_ruta` yang sama akan ditampilkan
4. **Performance**: Untuk file CSV besar, loading mungkin memakan waktu

## ⚠️ Catatan
- Pastikan file `data.json` dan `data.csv` tersedia di folder yang sama
- Untuk file CSV besar (>30MB), pastikan RAM komputer mencukupi
- Aplikasi akan terbuka di `http://localhost:8501`

## 🛠️ Dependencies
- Python 3.7+
- Streamlit >= 1.28.0
- Pandas >= 1.5.0

---
*Dibuat menggunakan MCP Filesystem dan Streamlit*
