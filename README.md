# APK Size Analyzer

A command-line tool to analyze Android APK/AAB size breakdown by module (assets, libraries, and your app base).

## Fitur Utama

* *Automatic* memetakan modul dari direktori `assets/` dan `lib/`.
* Menganalisis ukuran *compressed* dan *decompressed* per modul.
* Menghitung total size untuk **Asset**, **Library**, dan **App (base project)**.
* Menampilkan ringkasan per tipe dan total keseluruhan APK.
* Ekspor hasil ke format **Markdown**, **CSV**, atau **Excel**.

## Instalasi

1. Pastikan Python 3 terpasang (`python3 --version`).
2. Clone repo ini:

   ```bash
   git clone <url-repo-anda>
   cd <nama-folder>
   ```
3. (Optional) Install dependency untuk export Excel:

   ```bash
   pip3 install pandas openpyxl
   ```

## Penggunaan

```bash
python3 apk_size_report.py <path-ke-apk> [OPTIONS]
```

### Argumen

* `<path-ke-apk>`: File `.apk` atau `.aab` yang akan dianalisis.

### Options

| Flag                | Deskripsi                                                                |        |                                                                                       |
| ------------------- | ------------------------------------------------------------------------ | ------ | ------------------------------------------------------------------------------------- |
| `--show-structure`  | Tampilkan daftar semua path di `lib/` dan `assets/`, lalu keluar.        |        |                                                                                       |
| `--gen`             | Cetak mapping otomatis: `modules = { 'nama_modul': [...], ... }`.        |        |                                                                                       |
| \`--type \[asset    | lib                                                                      | all]\` | Filter jenis modul: `asset` (hanya assets), `lib` (hanya libraries), `all` (default). |
| `--md FILE.md`      | Simpan laporan dalam Markdown ke `FILE.md`.                              |        |                                                                                       |
| `--csv FILE.csv`    | Simpan laporan dalam CSV ke `FILE.csv`.                                  |        |                                                                                       |
| `--excel FILE.xlsx` | Simpan laporan dalam Excel ke `FILE.xlsx` (butuh `pandas` + `openpyxl`). |        |                                                                                       |

## Contoh

1. **Simpan laporan Markdown**:

   ```bash
   python3 apk_size_report.py app-release.apk --md report.md
   ```

2. **Simpan laporan Excel & CSV**:

   ```bash
   python3 apk_size_report.py app_11462.apk --gen --md report_app_size_11462.xlsx
   ```

## Struktur Laporan

* **Summary per Type**: Ringkasan total compressed/decompressed untuk Asset, Library, dan App.
* **Tabel Detail**: Ukuran per modul lengkap dengan kolom:

  * `Type`: Asset / Library / App
  * `SDK / Feature`: Nama modul (atau `App` untuk base project)
  * `Original Install (MB)`: Ukuran compressed modul
  * `Original After Decompress (MB)`: Ukuran decompressed modul
  * `Remaining Install (MB)`: Sisa compressed setelah modul diukur
  * `Remaining After Decompress (MB)`: Sisa decompressed setelah modul diukur
  * `Delta Install (MB)`: Sama dengan ukuran compressed modul
  * `Delta After Decompress (MB)`: Sama dengan ukuran decompressed modul

## Lisensi

MIT License © 2025
