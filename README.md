# Hotel Reviews Data Ingestion Pipeline (CI/CD to Azure Functions)

Pipeline otomatisasi *data ingestion* yang menarik dataset ulasan hotel dari server MinIO VPS melalui FastAPI (**Hotel Reviews Intake API**) dan menyimpannya ke **Azure Blob Storage** secara terjadwal maupun manual menggunakan **Azure Functions (Python v2)** serta **GitHub Actions CI/CD**.

---

## Arsitektur & Komponen Sistem

* **Sumber Data (Source API):** `https://upload-data-hotel.duckdns.org`
  * `GET /api/uploads` — Mengambil daftar metadata file dataset yang tersedia.
  * `GET /api/uploads/{id}/download` — Mengunduh file CSV dari MinIO VPS (memerlukan otorisasi token).
* **Compute (Azure Function App):** `hotel-review-ea`
  * **Resource Group:** `rg-hotel-review-prod`
  * **Region:** `East Asia`
  * **OS & Runtime:** Linux — Python `3.11` (App Service Plan `B1`)
  * **Fungsi Aktif:**
    1. `hotel_reviews_scheduler` (**Timer Trigger**): Berjalan otomatis setiap 6 jam (`0 0 */6 * * *`).
    2. `manual_trigger_ingestion` (**HTTP Trigger**): Endpoint `/api/trigger-ingestion` (`AuthLevel.FUNCTION`) untuk memicu *ingestion* secara manual.
* **Data Store (Azure Blob Storage):**
  * **Storage Account:** `rghotelreviewprod8aa1`
  * **Container:** `hotel-reviews-ingested` (data tersimpan rapi per direktori `batch_YYYYMMDD_HHMMSS/`).
* **CI/CD Automation:** GitHub Actions (`.github/workflows/ci-cd-pipeline.yaml`)
  * **CI - Lint & Unit Test:** Validasi sintaks dengan `flake8` dan pengujian unit dengan `pytest`.
  * **CD - Deploy to Azure Function App:** *Deployment* otomatis ke `hotel-review-ea` setiap kali ada *push* atau *merge* ke branch `main`.

---

## Struktur Direktori Repositori

```text
ci-cd-ingest/
├── .github/
│   └── workflows/
│       └── ci-cd-pipeline.yaml   # Konfigurasi pipeline CI/CD GitHub Actions
├── tests/                        # Unit test untuk pengujian otomatis (pytest)
├── function_app.py               # Kode utama Azure Functions v2 (Timer & HTTP Trigger)
├── host.json                     # Konfigurasi runtime Azure Functions v2 & Extension Bundle
├── requirements.txt              # Daftar dependensi Python (termasuk pin cryptography==42.0.8)
└── README.md                     # Dokumentasi setup, kolaborasi Git, dan verifikasi
```

---

## Prasyarat (Prerequisites)

Sebelum menjalankan proyek di komputer lokal, pastikan perangkat Anda sudah terpasang:

* **Python 3.11** (sesuai versi runtime di Azure Linux App Service)
* **Git**
* **Azure Functions Core Tools v4** *(opsional, jika ingin menjalankan fungsi secara lokal melalui terminal)*
* **Kredensial rahasia proyek** — Mintalah nilai `API_AUTH_TOKEN` dan `AZURE_STORAGE_CONNECTION_STRING` kepada pengelola repositori. **Jangan pernah meng-commit kredensial ke GitHub.**

---

## Panduan Setup & Menjalankan Secara Lokal

### 1. Clone Repositori

```bash
git clone https://github.com/decaldara20/ci-cd-ingest.git
cd ci-cd-ingest
```

### 2. Buat & Aktifkan Virtual Environment

* **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```
* **Linux / macOS:**
  ```bash
  python3.11 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Install Dependensi

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Catatan:** Paket `cryptography==42.0.8` dikunci secara eksplisit di `requirements.txt` untuk menjaga kompatibilitas GLIBC pada container Linux Debian di Azure App Service.

### 4. Konfigurasi Variabel Lingkungan Lokal (`local.settings.json`)

Buat file `local.settings.json` di direktori utama proyek (file ini otomatis diabaikan oleh `.gitignore`), lalu isi dengan struktur berikut:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsFeatureFlags": "EnableWorkerIndexing",
    "API_BASE_URL": "https://upload-data-hotel.duckdns.org",
    "API_AUTH_TOKEN": "MASUKKAN_TOKEN_OTORISASI_API_DI_SINI",
    "AZURE_STORAGE_CONNECTION_STRING": "MASUKKAN_CONNECTION_STRING_STORAGE_DI_SINI"
  }
}
```

### 5. Jalankan Linter, Unit Test, & Fungsi Lokal

Pastikan kode bebas dari error sebelum di-push ke GitHub:

```bash
# Cek gaya penulisan & sintaks kode
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Jalankan unit test
pytest

# (Opsional) Jalankan Azure Functions secara lokal
func start
```

> Jika `func start` dijalankan, Anda dapat menguji trigger manual melalui browser atau `curl` ke `http://localhost:7071/api/trigger-ingestion`.

---

## Alur Kolaborasi Git & CI/CD Deployment

1. **Tarik Pembaruan Terbaru dari `main`:**
   ```bash
   git checkout main
   git pull origin main
   ```
2. **Buat Branch Fitur Baru:**
   ```bash
   git checkout -b feat/nama-perubahan
   ```
3. **Commit & Push ke Branch Fitur:**
   ```bash
   git add .
   git commit -m "feat: deskripsi singkat perubahan"
   git push origin feat/nama-perubahan
   ```
4. **Buat Pull Request (PR):**
   * Buka repositori di GitHub, lalu buat **Pull Request** dari branch fitur Anda menuju `main`.
   * Setelah PR di-review dan di-merge ke `main`, workflow **CI-CD Hotel Reviews Ingestion Pipeline** di tab **Actions** otomatis berjalan untuk menguji kode dan men-deploy versi terbaru ke Function App `hotel-review-ea` (menggunakan secret `AZURE_FUNCTIONAPP_PUBLISH_PROFILE`).

---

## Verifikasi di Portal Azure

### 1. Pengujian Manual Pipeline (`manual_trigger_ingestion`)

1. Buka **Portal Azure** → **Resource Group** `rg-hotel-review-prod` → **Function App** `hotel-review-ea`.
2. Pada bagian **Functions**, klik `manual_trigger_ingestion` → masuk ke menu **Code + Test**.
3. Klik **Test/Run** → **Run**.
4. Pastikan panel **Output** menampilkan **HTTP response code: `200 OK`** beserta JSON ringkasan daftar file CSV yang berhasil diunduh dan diunggah.

### 2. Verifikasi File CSV di Azure Blob Storage

1. Buka **Storage Account** `rghotelreviewprod8aa1` di Portal Azure.
2. Masuk ke menu **Data storage** → **Containers** → klik container `hotel-reviews-ingested`.
3. Jika muncul pemberitahuan izin Microsoft Entra ID, klik tautan **(Switch to Access key)** di bagian atas daftar blob.
4. Buka folder `batch_YYYYMMDD_HHMMSS/` terbaru untuk memastikan seluruh file CSV dari MinIO VPS telah tersimpan dengan ukuran file yang valid.
