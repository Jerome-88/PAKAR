# Draft evaluasi bisnis PAKAR

Semua kasus di `business-cases.v0.json` sintetis. Daftar stakeholder/risiko merupakan hipotesis anotasi, belum ground truth. Evaluator bisnis independen perlu meninjau konteks, omissions, relevansi, batas evidence dan kriteria penilaian sebelum benchmark. Tidak ada hasil superiority yang diklaim.

Bandingkan single LLM, single LLM + tools, specialist tanpa persona, dan PAKAR lengkap memakai kasus/sumber, batas biaya/token dan akses tool yang sebanding. Bekukan model, prompt, versi sumber, seed dan aturan penilaian sebelum run. Jalankan beberapa pengulangan; laporkan variasi dan kegagalan, jangan hanya memilih run terbaik.

Rubric: relevansi/kelengkapan stakeholder dan duplikasi; precision/recall blind spot terhadap referensi yang direview; unsupported findings dan grounding; konsistensi scenario serta kegunaan bagi analis; latency, token dan biaya dengan coverage unknown yang eksplisit. Penilai kegunaan sebaiknya tidak mengetahui konfigurasi sistem yang menghasilkan laporan.

Hitungan unit economics adalah pemeriksaan aritmetika kondisional. Demand/profit tetap unknown jika input hilang. Konsensus persona tidak dihitung sebagai bukti eksternal. Tahap ini menyiapkan bahan evaluasi, belum menjalankan benchmark berbayar.
