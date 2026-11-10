# PAKAR — PRD Revision v1.1

## REV-01 — Product Definition & Core Value Proposition

**Bagian yang direvisi:** Executive Summary, Section 1.3.

PAKAR adalah platform AI Co-Analyst berbasis Multi-Agent Swarm Intelligence yang membantu Business Analyst mengidentifikasi blind spot bisnis melalui simulasi interaksi stakeholder secara dinamis, analisis lintas fungsi, serta validasi asumsi menggunakan data eksternal maupun internal yang relevan.

PAKAR tidak hanya menganalisis risiko yang sudah tercantum dalam business plan, tetapi juga menemukan kemungkinan risiko baru melalui interaksi antar-persona, stakeholder discovery, dan pengujian berbagai kondisi bisnis.

**Tiga core capabilities:**
1. **Dynamic Stakeholder Discovery & Simulation:** Mengidentifikasi stakeholder eksplisit maupun tersembunyi dan mensimulasikan kemungkinan interaksinya.
2. **Evidence-Based Business Analysis:** Memvalidasi asumsi dan temuan menggunakan sumber data terpercaya seperti BPS, Bank Indonesia, regulasi resmi, dan data internal yang diizinkan.
3. **Emergent Blind Spot Discovery & Stress Testing:** Mengidentifikasi risiko baru dari interaksi antar-agent dan menguji perubahan strategi pada berbagai skenario.

Hasil simulasi merupakan hipotesis untuk diuji, bukan prediksi perilaku pasar yang telah tervalidasi.

---

## REV-02 — Dynamic Persona Generation sebagai Fitur P0

**Bagian yang direvisi:** Section 4 — Scope and Prioritization, Section 5.4.

**Perubahan:** Ganti ketentuan "4 specialist agents + orchestrator" sebagai batas desain MVP. Empat specialist agents tetap menjadi komponen analitis awal, tetapi tidak membatasi jumlah simulation personas.

### Functional Requirements

- **FR-PER-01:** Sistem mengekstrak business context dari dokumen: industri, lokasi, segmen konsumen, model bisnis, value proposition, dan asumsi strategis.
- **FR-PER-02:** Sistem mengidentifikasi stakeholder langsung, tidak langsung, dan stakeholder potensial yang tidak disebutkan dalam proposal.
- **FR-PER-03:** Sistem membangkitkan persona secara dinamis berdasarkan konteks, relevansi, dan data yang tersedia.
- **FR-PER-04:** Setiap persona memiliki identitas peran, tujuan, motivasi, kendala, pengetahuan, kepentingan, dan hubungan dengan stakeholder lainnya.
- **FR-PER-05:** Sistem mengecek kemiripan persona untuk mengurangi duplikasi dan meningkatkan keragaman perspektif.
- **FR-PER-06:** Jumlah persona bersifat configurable sesuai kebutuhan simulasi, kompleksitas masalah, dan batas komputasi.
- **FR-PER-07:** Setiap persona diberi label apakah profilnya didukung data, berasal dari asumsi pengguna, atau merupakan hipotesis sintetis.

### Acceptance Criteria

- Persona yang dihasilkan relevan terhadap industri dan masalah bisnis.
- Sistem mampu mengusulkan stakeholder yang tidak disebutkan secara eksplisit oleh pengguna.
- Pengguna dapat meninjau, menambahkan, menonaktifkan, atau mengubah persona sebelum simulasi berjalan.
- Sistem mampu menjalankan simulasi dengan beberapa persona yang memiliki kepentingan berbeda tanpa mengasumsikan bahwa jumlahnya mencerminkan proporsi konsumen nyata.

---

## REV-03 — Dual-Layer Multi-Agent Architecture

**Bagian yang direvisi:** Section 5.4 dan Section 7.

PAKAR mengimplementasikan dua jenis agent:

### A. Analytical Agents

Bertanggung jawab terhadap pemeriksaan faktual dan analisis domain tertentu.

- Market Research Agent
- Financial Analyst Agent
- Legal & Compliance Agent
- Risk Analyst Agent
- Data Analyst Agent (opsional sesuai kebutuhan analisis)

Setiap agent memiliki tools, kemampuan analisis, dan keluaran terstruktur.

### B. Simulation Personas

Merepresentasikan perspektif stakeholder yang relevan terhadap keputusan bisnis.

Contoh:
- Customer segments
- Competitors
- Suppliers
- Distributors
- Investors
- Employees
- Business partners
- Regulators
- Hidden or indirect stakeholders

Simulation Personas tidak harus memiliki akses langsung ke seluruh tools atau data internal perusahaan. Mereka bertindak berdasarkan profil dan konteks yang ditetapkan.

### Agent Orchestration

Orchestrator bertanggung jawab mengatur pembentukan persona, distribusi tugas, penjadwalan interaksi, pertukaran informasi, batas simulasi, dan koordinasi hasil analisis.

---

## REV-04 — Multi-Agent Ecosystem Simulation

**Bagian yang direvisi:** Section 5.5 — Multi-Agent Challenge and Arbitration.

**Perubahan utama:** Jangan membatasi sistem hanya pada perdebatan antara empat specialist agents.

Sistem harus mendukung simulasi interaksi dinamis antar-stakeholder melalui simulation engine.

### Functional Requirements

- **FR-SIM-01:** Persona dapat berinteraksi dengan persona lain berdasarkan kepentingan dan hubungan antar-stakeholder.
- **FR-SIM-02:** Simulasi mendukung berbagai jenis interaksi, seperti kerja sama, kompetisi, konflik kepentingan, negosiasi, dan respons terhadap perubahan pasar.
- **FR-SIM-03:** Persona dapat memperbarui posisi atau keputusan berdasarkan informasi yang diterima selama simulasi.
- **FR-SIM-04:** Sistem mempertahankan memory/state setiap persona selama satu simulation run.
- **FR-SIM-05:** Analytical Agents dapat mengevaluasi temuan simulasi serta memeriksa apakah hipotesis yang muncul memiliki bukti pendukung.
- **FR-SIM-06:** Simulasi memiliki stopping criteria, batas iterasi, serta token dan cost budget.
- **FR-SIM-07:** Sistem menyimpan jejak interaksi, perubahan state, dan asal-usul temuan untuk kebutuhan audit.

### Output

- Stakeholder interaction graph
- Simulation event timeline
- Emerging conflicts
- Potential behavioral responses
- Newly discovered business risks
- Unvalidated simulation hypotheses

---

## REV-05 — Emergent Blind Spot Discovery Engine

**Bagian yang direvisi:** Section 5.6 — Blind Spot Engine and Report.

Blind Spot Engine tidak hanya mendeteksi kekurangan atau kontradiksi pada business plan, tetapi juga mengevaluasi risiko yang muncul dari simulasi stakeholder.

### Kategori Blind Spot

1. **Document-Level Blind Spots:** Asumsi, kontradiksi, dan informasi yang hilang dari dokumen.
2. **Evidence-Level Blind Spots:** Klaim yang tidak sesuai atau belum didukung data eksternal.
3. **Stakeholder Blind Spots:** Pihak yang terdampak tetapi belum dipertimbangkan dalam strategi.
4. **Interaction-Based Blind Spots:** Risiko yang muncul karena konflik atau interaksi antar-stakeholder.
5. **Scenario-Based Blind Spots:** Kerentanan bisnis yang baru terlihat setelah kondisi pasar diubah.

### Mekanisme

Setiap temuan harus memiliki:
- Kategori dan severity.
- Agent atau persona yang mengidentifikasi temuan.
- Rangkaian interaksi yang menghasilkan temuan, jika ada.
- Supporting evidence dan evidence gaps.
- Penjelasan risiko serta potensi dampak.
- Tingkat keyakinan atau status ketidakpastian.
- Recommended validation action.

**Aturan penting:** Temuan simulasi tidak boleh otomatis dikategorikan sebagai fakta. Sistem harus membedakan antara risiko yang didukung bukti dan hipotesis risiko yang perlu divalidasi.

---

## REV-06 — Chaos Injection & Dynamic Scenario Simulation

**Bagian yang direvisi:** Section 5.7.

Chaos Injection tidak hanya menjalankan ulang perhitungan finansial, tetapi juga memungkinkan seluruh persona yang relevan merespons perubahan kondisi bisnis.

### Functional Requirements

- User dapat memasukkan perubahan harga, regulasi, biaya produksi, gangguan supplier, atau kondisi pasar.
- Orchestrator menentukan persona dan specialist agents yang terdampak.
- Simulation Engine menjalankan respons dan interaksi lanjutan.
- Analytical Agents melakukan kalkulasi ulang untuk metrik yang dapat dihitung secara deterministik.
- Sistem membandingkan keadaan sebelum dan setelah skenario.
- Report Agent menjelaskan risiko baru, perubahan posisi stakeholder, dan tindakan mitigasi.

Output mencakup:
- Baseline vs Scenario comparison.
- Perubahan hubungan dan respons stakeholder.
- Risiko baru atau risiko yang meningkat.
- Perubahan indikator kuantitatif yang dapat dihitung.
- Rekomendasi tindakan dan batas ketidakpastian.

---

## REV-07 — MiroFish Migration Strategy

**Bagian yang direvisi:** Section 7.1.

**Perubahan:** Batalkan instruksi yang menyatakan persona generator harus diganti dengan functional specialist agents dan OASIS social simulator dikeluarkan dari default critical path.

### Migration Direction

**Komponen yang diprioritaskan untuk dipertahankan dan diadaptasi:**
- Dynamic persona generation.
- Social simulation engine.
- Inter-agent interaction scheduling.
- Persona memory and state management.
- Knowledge graph / relationship modeling.
- Simulation timeline and event tracking.
- Simulation report generation.
- Agent interaction visualization.

**Komponen yang perlu dikembangkan:**
- Business context extraction.
- Business-specific persona attributes and prompts.
- Analytical specialist agents.
- BPS and official-data integration.
- Claim-to-evidence validation.
- Structured blind spot extraction.
- Business risk scoring and reporting.
- Scenario impact comparison.

Existing government-policy prompts dan domain-specific workflows diganti dengan konteks business analysis.

**Catatan implementasi:** Mapping fungsi, modul, dan dependensi harus dikonfirmasi setelah audit terhadap repository MiroFish yang sudah dimodifikasi.

---

## REV-08 — MVP Scope, Evaluation & Development Roadmap

**Bagian yang direvisi:** Section 4, Section 10, Section 11, dan Section 14.

### P0 — Core MVP

- Business document ingestion.
- Business context and assumption extraction.
- Dynamic stakeholder discovery.
- Dynamic persona generation.
- Multi-persona ecosystem simulation.
- Specialist analytical agents.
- Evidence retrieval dengan minimal satu sumber data resmi.
- Emergent blind spot identification.
- Structured risk and evidence report.
- Chaos Injection dengan perbandingan sebelum dan sesudah.

### P1 — Advanced Analysis

- Enhanced Nerve Center visualization.
- Advanced stakeholder relationship graph.
- Deterministic feasibility scoring.
- Big-data analytics menggunakan SQL/Python.
- Advanced simulation configuration.
- Expanded external data integrations.

### P2 — Enterprise Capabilities

- ERP/CRM integrations.
- Private or on-premise inference.
- Continuous business monitoring.
- Simulation at larger scale.
- Enterprise security and governance controls.

### Evaluation Requirements

PAKAR harus dievaluasi pada tiga dimensi:

**1. Stakeholder Discovery Quality**
- Relevansi stakeholder yang dihasilkan.
- Kelengkapan stakeholder dibandingkan daftar referensi dari evaluator manusia.
- Keragaman dan tingkat duplikasi persona.

**2. Blind Spot Detection Quality**
- Recall dan precision terhadap kumpulan risiko referensi.
- Jumlah temuan relevan yang tidak ditemukan oleh baseline.
- Evidence grounding dan tingkat unsupported findings.

**3. Simulation & Agent Effectiveness**
- Perbandingan hasil dengan single LLM dan multi-agent tanpa simulation personas.
- Konsistensi respons terhadap perubahan skenario.
- Kegunaan temuan menurut evaluator bisnis.
- Latency, token usage, dan biaya per simulasi.

Benchmark dilakukan menggunakan skenario yang sama dan kriteria evaluasi yang disepakati sebelumnya.

### MVP Acceptance Criteria

MVP dinyatakan memenuhi fungsi inti apabila dapat:

1. Mengunggah dan memahami dokumen ide bisnis.
2. Membentuk stakeholder dan persona berdasarkan konteks.
3. Menemukan minimal satu kandidat stakeholder yang tidak disebutkan dalam dokumen uji yang memang dirancang memiliki stakeholder terlewat.
4. Menjalankan simulasi interaksi yang dapat ditelusuri.
5. Mengidentifikasi temuan risiko dari dokumen maupun hasil interaksi.
6. Menghubungkan temuan faktual dengan data atau menandainya sebagai belum tervalidasi.
7. Menjalankan Chaos Injection yang memengaruhi perilaku persona dan menampilkan dampak yang bisa diverifikasi.
8. Menghasilkan laporan blind spot beserta rekomendasi validasi bagi Business Analyst.

Seluruh target kualitas dan performa akan ditetapkan serta diukur melalui pengujian MVP.