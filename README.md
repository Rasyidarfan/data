# 🏠 Aplikasi Data Rumah Tangga

Aplikasi Streamlit dengan 2 fitur utama: **Pencarian Data** dan **Komparasi Data**

## 📋 Deskripsi

Aplikasi berbasis SQLite database untuk mencari dan membandingkan data rumah tangga dengan performa tinggi (10-50x lebih cepat dari CSV).

## 📁 Struktur File

```
data/
├── rumah_tangga.db            # Database SQLite (68MB, 309K+ baris)
├── data_search_app.py         # Aplikasi utama (entry point)
├── data_comparison_page.py    # Modul halaman komparasi
├── requirements.txt           # Dependencies Python
├── .devcontainer/             # Dev Container config (VS Code)
└── README.md                  # File ini
```

## 🚀 Cara Menjalankan

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Jalankan Aplikasi

```bash
streamlit run data_search_app.py
```

Aplikasi akan terbuka di `http://localhost:8501`

### 3. Navigasi

Gunakan **sidebar menu** untuk memilih fitur:
- 🔍 **Pencarian Data**: Mencari data rumah tangga
- ⚖️ **Komparasi Data**: Membandingkan CSV upload vs database

---

## 🔍 Fitur 1: Pencarian Data

Mencari dan menampilkan data rumah tangga dari database SQLite.

### Filter yang Tersedia:

1. **Filter Wilayah** (Dropdown)
   - Format: `Kecamatan / Desa`
   - Otomatis load dari database

2. **Filter Kepala Keluarga** (Dropdown)
   - Filter berdasarkan nama KK
   - Dinamis sesuai wilayah terpilih

3. **Upload JSON** (Opsional)
   - Upload file JSON untuk filtering custom
   - Format: `{"wilayah": "...", "KK": "..."}`

### Output:

- ✅ **Ringkasan**: Total rumah tangga & anggota
- 🏠 **Data per Rumah Tangga**: Expandable cards
  - Nama, hubungan, jenis kelamin, umur
  - NIK, ijazah, pendidikan
  - Highlight nama yang cocok dengan pencarian
- 💾 **Download**: Export hasil ke CSV

### Performa:

- Query: **<100ms** untuk 300K+ baris
- Memory: **<50MB**
- Indexing pada: `id_ruta`, `b2r203`, `nama_kec`, `nama_desa`, `hubungan`

---

## ⚖️ Fitur 2: Komparasi Data

Membandingkan data dari CSV upload dengan database SQLite menggunakan fuzzy matching.

### Workflow (6 Langkah):

#### 1️⃣ Upload CSV
- Upload file CSV yang ingin dibandingkan
- Preview data otomatis ditampilkan

#### 2️⃣ Mapping Kolom Manual
Pilih 4 kolom dari CSV:
- **codeIdentity**: Kode wilayah (2+2+3+3 digit: prov+kab+kec+desa)
- **no_urut**: Nomor urut data
- **nama1**: Nama utama (wajib)
- **nama2**: Nama kedua (opsional)

#### 3️⃣ Parse codeIdentity
- Otomatis extract: provinsi, kabupaten, kecamatan, desa
- Lookup ke tabel `wilayah` untuk mendapatkan nama kec/desa

#### 4️⃣ Pilih Wilayah Manual
- Dropdown kecamatan & desa
- Auto-detection jika codeIdentity match dengan database
- Tampilkan jumlah data di database untuk wilayah terpilih

#### 5️⃣ Opsi Komparasi
- **Similarity Threshold** (50-100%): Minimum skor untuk match
- **Case Sensitive**: On/Off
- **Include Nama2**: Gunakan nama2 dalam matching (jika ada)

#### 6️⃣ Hasil Komparasi

3 Tabel output:

**Tabel 1: ✅ Data Berhasil Match**
- Kolom: `no_urut`, `nama_csv`, `nama2_csv`, `nama_sqlite`, `hubungan`, `jk`, `umur`, `Pendidikan`, `similarity`
- Sorting: Berdasarkan `no_urut`
- Menampilkan data yang berhasil di-match antara CSV dan database

**Tabel 2: ❌ Di CSV tapi Tidak di Database**
- Kolom: `no_urut`, `nama1`, `nama2`, `best_similarity`
- Data dari CSV yang tidak ditemukan match di database

**Tabel 3: 🔍 Kepala Keluarga di Database tapi Tidak di CSV**
- **Filter**: Hanya KK (`hubungan = 1`)
- Kolom: `b2r203`, `jk`, `umur`, `Pendidikan`, `nama_kec`, `nama_desa`
- Sorting: Berdasarkan nama
- Data KK di database yang tidak ditemukan di CSV

### Fitur Tambahan:

- ✅ **Copy-to-clipboard**: Semua tabel bisa dicopy dengan header (ke Excel/Sheets)
- 💾 **Download CSV**: Download setiap tabel ke file terpisah
- 📊 **Statistik**: Match rate, total CSV, total database, total matched

### Teknologi:

- **Fuzzy Matching**: `fuzzywuzzy` library dengan Levenshtein distance
- **Performance**: Matching <1 detik untuk ratusan baris

---

## 📊 Struktur Database

### Table: `rumah_tangga` (309,315 rows)

| Kolom | Deskripsi | Indexed |
|-------|-----------|---------|
| `id_ruta` | ID Rumah Tangga | ✅ |
| `b2r203` | Nama anggota | ✅ |
| `hubungan` | Hubungan dengan KK (1=KK) | ✅ |
| `jk` | Jenis kelamin | - |
| `umur` | Umur | - |
| `b3r303` | NIK | - |
| `ijazah` | Ijazah tertinggi | - |
| `Pendidikan` | Pendidikan terakhir | - |
| `nama_kec` | Nama kecamatan | ✅ |
| `nama_desa` | Nama desa | ✅ |
| `nama_sls` | Nama SLS | - |

### Table: `wilayah` (691 rows)

| Kolom | Deskripsi | Indexed |
|-------|-----------|---------|
| `kdprov`, `nmprov` | Kode & nama provinsi | - |
| `kdkab`, `nmkab` | Kode & nama kabupaten | - |
| `kdkec`, `nmkec` | Kode & nama kecamatan | ✅ |
| `kddesa`, `nmdesa` | Kode & nama desa | ✅ |

**Coverage**: 691 desa dari 3 kabupaten (Jayawijaya, Yalimo, Mamberamo Tengah)

---

## 🛠️ Dependencies

```txt
streamlit >= 1.28.0
pandas >= 1.5.0
fuzzywuzzy >= 0.18.0
python-Levenshtein >= 0.21.0
```

SQLite3 sudah built-in di Python.

---

## 💡 Tips Penggunaan

### Pencarian Data:
1. Mulai dengan filter wilayah untuk mempersempit hasil
2. Gunakan filter KK untuk mencari rumah tangga spesifik
3. Upload JSON untuk batch filtering multiple KK sekaligus
4. Case-insensitive search & partial matching otomatis aktif

### Komparasi Data:
1. **Prepare CSV** dengan minimal 3 kolom: codeIdentity, no_urut, nama
2. **Similarity Threshold 80%** adalah default yang baik
3. Gunakan **nama2** jika CSV punya alternatif nama (alias)
4. **Copy table langsung** ke Excel: Select cells → Ctrl+C/Cmd+C
5. **Download CSV** untuk dokumentasi dan analisis lebih lanjut

---

## 📈 Performa

| Metrik | Nilai |
|--------|-------|
| Database size | 68 MB |
| Total records | 309,315 |
| Search query | <100 ms |
| Comparison (100 rows) | <1 detik |
| Memory usage | <50 MB |

**10-50x lebih cepat** dibanding CSV parsing langsung!

---

## 🐳 Dev Container (VS Code)

Proyek sudah dilengkapi `.devcontainer/` untuk development di Docker container.

**Benefit:**
- Environment konsisten untuk semua developer
- Auto-install dependencies dari `requirements.txt`
- Auto-start aplikasi Streamlit saat container ready
- Auto-forward port 8501 dengan browser preview

**Cara pakai:**
1. Install Docker Desktop + VS Code + Extension "Dev Containers"
2. Buka folder di VS Code
3. Klik "Reopen in Container"
4. Wait... aplikasi otomatis jalan!

---

## ⚠️ Catatan

- Database `rumah_tangga.db` **WAJIB** ada sebelum menjalankan aplikasi
- Aplikasi membuka 2 halaman via sidebar navigation
- Port default: `8501`
- Untuk production, gunakan `--server.address 0.0.0.0` jika deploy ke server

---

**📧 Support**: Buka issue di repository jika ada pertanyaan

*Dibuat dengan Streamlit + SQLite untuk performa maksimal* ⚡
