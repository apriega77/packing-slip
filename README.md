# Packing Slip

Situs statis untuk konten affiliate + generator pin Pinterest.
Nama "Packing Slip" hanya placeholder, ganti di `data/site.json`.

## Struktur

- `content/posts/*.md` : artikel. Frontmatter berisi judul, tanggal, dan daftar `pins`.
- `content/pages/*.md` : halaman tetap (disclosure).
- `data/links.json` : daftar link affiliate. Isi `url` dengan link affiliate kamu dan ubah `affiliate` jadi `true`.
- `data/site.json` : nama situs, `base_url`, nama board Pinterest.
- `build.py` : membangun situs ke `dist/`.
- `pins/make_pins.py` : membuat gambar pin 1000x1500 dan `pins/out/pins.csv`.
- `.github/workflows/deploy.yml` : deploy otomatis ke GitHub Pages saat push ke `main`.

## Menjalankan

```
pip install -r requirements.txt
python pins/make_pins.py
python build.py
```

Buka `dist/index.html` untuk melihat hasilnya.

## Menulis link affiliate di artikel

Tulis `[Systeme.io](aff:systeme)`. Kuncinya (`systeme`) dicari di `data/links.json`.
Selama `affiliate` masih `false`, link mengarah ke situs resmi dan keterangan
affiliate di artikel tidak ditampilkan. Setelah `true`, link diberi
`rel="sponsored nofollow"` dan keterangan affiliate muncul otomatis.

## Yang perlu diisi sebelum online

1. `base_url` di `data/site.json` (alamat GitHub Pages atau domain kamu).
2. Link affiliate di `data/links.json`.
3. Di repo GitHub: Settings > Pages > Source = GitHub Actions.

## Catatan

- Kolom `pins.csv` belum dicocokkan dengan template unggah massal Pinterest yang
  berlaku. Sesuaikan nama kolomnya dengan template dari akun Pinterest Business kamu.
- Harga dan batas paket di artikel dibaca dari halaman resmi pada tanggal di
  frontmatter `checked`. Periksa ulang sebelum memperbarui artikel.
- Font di `pins/fonts/` berlisensi SIL Open Font License (file OFL disertakan).

## Aturan desain dan tulisan

Arah desain ada di `DESIGN.md` (masih draf). Proyek ini mengikuti aturan
anti-slop (github.com/miqdadbadjuber/anti-slop). Laporan pemeriksaan terakhir
ada di folder `anti-slop/`.
