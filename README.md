# NeuroMotorik Screener v2

![NeuroMotorik Screener](https://img.shields.io/badge/Status-Active-brightgreen)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.0%2B-teal)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Pose-orange)

**NeuroMotorik Screener** adalah aplikasi berbasis web yang memanfaatkan teknologi *Computer Vision* (AI) untuk melakukan skrining klinis dini terhadap gangguan neuro-motorik seperti **Stroke, Parkinson, dan Sarcopenia**.

Aplikasi ini menggunakan **Google MediaPipe Pose** untuk melacak pergerakan sendi (kerangka) pasien secara *real-time* menggunakan webcam standar, lalu mengirimkan data metrik tersebut via **WebSocket** ke server **FastAPI** untuk dianalisis menggunakan *Kinematic Engine*.

Fitur Utama:
- **Asymmetry Index (ASI):** Mengukur asimetri pergerakan sisi kiri dan kanan tubuh (Deteksi Risiko Stroke).
- **Power Spectral Density (PSD):** Menganalisis frekuensi tremor menggunakan Fast Fourier Transform (Deteksi Risiko Parkinson).
- **Sit-to-Stand (STS) Analysis:** Mengukur kecepatan transisi berdiri dan duduk (Deteksi Risiko Sarcopenia).
- **Clean Healthcare UI/UX:** Tema hijau medis (Emerald Green) yang profesional dan responsif.

---

## 🛠️ Persyaratan Sistem (Prerequisites)

Sebelum menjalankan aplikasi, pastikan komputer Anda telah terinstal:
1. **Python 3.9** atau lebih baru.
2. **Node.js** (Opsional, jika ingin menggunakan Vite untuk *frontend live-server*).
3. Webcam atau kamera yang terhubung ke PC/Laptop.

---

## 🚀 Cara Menjalankan Aplikasi

Aplikasi ini terdiri dari dua bagian: **Backend (Server)** dan **Frontend (Client)**. Anda harus menjalankan keduanya secara bersamaan.

### 1. Menjalankan Backend (Server FastAPI)

Buka terminal/command prompt, lalu masuk ke folder proyek:

```bash
# 1. Masuk ke folder server
cd server

# 2. Buat Virtual Environment (Sangat direkomendasikan)
python -m venv venv
venv\Scripts\activate   # Untuk Windows
# source venv/bin/activate  # Untuk Mac/Linux

# 3. Install semua dependencies
pip install -r requirements.txt

# 4. Jalankan server
python main.py
```
> Server backend akan berjalan di `http://0.0.0.0:8765` dan mendengarkan koneksi WebSocket di `/ws/stream`.

### 2. Menjalankan Frontend (Client Web)

Buka terminal **baru** (biarkan terminal server backend tetap jalan), lalu jalankan frontend:

**Cara A: Menggunakan Vite (Sangat disarankan untuk performa terbaik)**
```bash
# 1. Masuk ke folder client
cd client

# 2. Jalankan Vite server (bisa menggunakan npx)
npx vite
```
> Buka browser dan akses URL yang diberikan Vite (biasanya `http://localhost:5173/index.html`).

**Cara B: Menggunakan Python HTTP Server (Alternatif)**
```bash
# 1. Masuk ke folder client
cd client

# 2. Jalankan web server bawaan Python
python -m http.server 8000
```
> Buka browser dan akses `http://localhost:8000/index.html`.

---

## 💡 Cara Penggunaan Assessment

1. Buka halaman aplikasi di browser.
2. Masukkan **ID Pasien/Nama** dan **Usia** di kolom yang tersedia.
3. Pilih jenis instruksi/tes (Misal: *Angkat Kedua Tangan*).
4. Klik **Mulai Assessment**.
5. Izinkan akses kamera pada browser. Tunggu 2-3 detik hingga AI Model (MediaPipe) selesai dimuat.
6. Berdirilah di depan kamera hingga garis kerangka (*skeleton*) berwarna hijau muncul di layar.
7. Lakukan gerakan sesuai instruksi. Grafik ASI dan PSD akan bergerak secara real-time.
8. Setelah 60 detik (atau jika Anda klik **Hentikan**), sistem akan memproses data dan menampilkan **Laporan Analisis Klinis** lengkap dengan kesimpulan risikonya.

---

## 📂 Struktur Direktori

```text
NEUTROMOTORIK/
├── client/                     # Frontend (HTML, CSS, JS)
│   ├── css/style.css           # Tema UI (Healthcare Green)
│   ├── js/
│   │   ├── main.js             # Logika utama (Kamera & UI)
│   │   ├── skeleton-renderer.js# Modul penggambaran kerangka AI
│   │   ├── chart-manager.js    # Modul grafik real-time (Chart.js)
│   │   └── websocket-client.js # Modul komunikasi dengan server
│   └── index.html              # Halaman utama aplikasi
│
├── server/                     # Backend (Python FastAPI)
│   ├── core/                   # Logika AI & Kalkulasi Klinis (ASI, STS, Tremor)
│   ├── routers/                # Endpoint API dan WebSocket Handler
│   ├── main.py                 # Titik masuk (Entry point) server
│   └── requirements.txt        # Daftar library Python
│
└── .gitignore                  # Pengecualian file untuk Git
```

---

## 👨‍💻 Kontributor
Dibuat untuk **LOMBA OLIBI** - Pengembangan Sistem Skrining NeuroMotorik.
