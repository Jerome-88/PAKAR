"""Bounded public discussion memory and conservative lexical repetition checks."""
import re
from difflib import SequenceMatcher


DECISIONS = {
    "Nilai dan harga": ("Nilai manfaat dibanding harga", "Menerima fitur lebih sederhana jika nilai uang lebih jelas", "Tambahan biaya tanpa manfaat yang penting bagi Anda"),
    "Kualitas dan kejelasan": ("Kualitas, kenyamanan dan informasi produk", "Menerima harga lebih tinggi jika kualitas yang relevan dapat diperiksa", "Ketidakjelasan fungsi atau informasi yang membuat pilihan keliru"),
    "Keandalan layanan": ("Ketersediaan dan konsistensi produk", "Menerima lebih sedikit variasi jika produk mudah diperoleh secara konsisten", "Ketergantungan pasokan yang mengganggu penggunaan rutin"),
    "Kemudahan penggunaan": ("Langkah penggunaan yang sederhana", "Menerima pilihan fitur lebih sedikit untuk mengurangi kerumitan", "Tambahan langkah atau kebingungan yang melebihi manfaat"),
    "Alternatif pilihan": ("Manfaat yang membedakan dari alternatif", "Menerima ide baru jika memberi keunggulan yang penting dari POV Anda", "Fitur baru yang tidak menawarkan alasan berganti dari alternatif"),
    "Dukungan setelah pembelian": ("Penanganan masalah dan keluhan", "Menerima risiko awal terbatas jika ada jalan penanganan yang masuk akal", "Kesulitan menangani kerusakan atau ketidaksesuaian produk"),
}
ROLE_DECISIONS = {
    "operator": ("Memilih usulan uji yang bisa dijalankan", "Menyederhanakan fitur untuk menguji manfaat utama", "Menjanjikan fakta, biaya atau kemampuan yang belum diketahui"),
    "supplier": ("Kelayakan produksi dan kepastian spesifikasi", "Menguji desain sederhana sebelum menambah kompleksitas", "Menjanjikan produksi atau biaya tanpa spesifikasi"),
    "competitor": ("Alasan konsumen memilih konsep dibanding alternatif", "Mengakui manfaat pesaing yang memang relevan sebagai hipotesis", "Mengarang strategi, hak paten atau fakta merek lain"),
    "regulator": ("Kejelasan arti klaim bagi pengguna", "Membatasi janji produk pada fungsi yang dapat dijelaskan", "Menetapkan kepatuhan hukum tanpa sumber dan review kompeten"),
}


def decision_contract(role, perspective=None):
    priority, compromise, red_line = DECISIONS.get(perspective, ROLE_DECISIONS.get(role, (
        "Konsekuensi keputusan bagi peran Anda", "Alternatif yang mengurangi hambatan utama", "Mengaku mengetahui informasi yang tidak dibagikan")))
    return {"priority": priority, "acceptable_compromise": compromise, "red_line": red_line,
            "rule": "Dahulukan prioritas ini. Anda boleh sependapat, tetapi tambahkan konsekuensi atau kompromi dari POV sendiri; jangan mengambil alih tugas persona lain."}


def normalized(text):
    text = re.sub(r"\bcustomer\s*\d+\b", "customer", (text or "").casefold())
    return re.sub(r"\W+", " ", text).strip()


def repetition_check(content, events, actor_id):
    text = normalized(content)
    if len(text) < 80:
        return None
    words = set(text.split())
    best = None
    for event in events:
        if event.get("kind") not in {"post_message", "reply_message"}:
            continue
        previous = normalized(event.get("content") or event.get("rationale"))
        if len(previous) < 80:
            continue
        own = event["actor_id"] == actor_id
        overlap = len(words & set(previous.split())) / max(1, len(words | set(previous.split())))
        similarity = SequenceMatcher(None, text, previous, autojunk=False).ratio()
        if similarity >= (.84 if own else .92) or overlap >= (.85 if own else .94):
            score = max(similarity, overlap)
            if best is None or score > best["similarity"]:
                best = {"matched_event_id": event["id"], "similarity": round(score, 4),
                        "comparison": "same_persona" if own else "another_persona", "method": "lexical-overlap-v1"}
    return best


def public_discussion_memory(events, actor_id, profiles):
    public = [event for event in events if event.get("visibility") == "public" and event.get("kind") in {"post_message", "reply_message"}]
    def excerpt(event):
        text = event.get("content") or event.get("rationale", "")
        return {"number": event["sequence"], "author": profiles[event["actor_id"]]["name"],
                "excerpt": text[:260], "truncated": len(text) > 260}
    own = [event for event in public if event["actor_id"] == actor_id]
    unanswered = [event for event in public if event.get("dialogue_act") in {"question", "challenge"}
                  and event.get("target_id") == actor_id
                  and not any(reply.get("reply_to") == event["id"] and reply["actor_id"] == actor_id for reply in public)]
    return {"your_previous_points": [excerpt(event) for event in own[-3:]],
            "questions_for_you": [excerpt(event) for event in unanswered[-3:]],
            "recent_other_points": [excerpt(event) for event in public if event["actor_id"] != actor_id][-3:],
            "task": "Jawab yang belum terjawab, bandingkan pilihan atau ajukan kompromi. Bila tidak ada tambahan dari prioritas Anda, boleh abstain. Jangan menerbitkan ulang poin yang sama."}


def withhold_repetition(comparison, previous_stance, proposed_stance):
    if not comparison:
        return False
    # A genuine update of one's own position is worth recording. A first turn
    # copying somebody else is still repetition, even from an undecided state.
    return comparison["comparison"] != "same_persona" or previous_stance == proposed_stance
