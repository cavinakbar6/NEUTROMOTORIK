"""
Report Generator — Merangkum metrik sesi menjadi laporan klinis terstruktur.
"""

import json
from models.schemas import ClinicalReport, RiskLevel


class ReportGenerator:

    @staticmethod
    def to_dict(report: ClinicalReport) -> dict:
        # ── Rehab sessions: return gamification-friendly structure ──
        if report.instruction and report.instruction.startswith("rehab_"):
            avg_form = report.shoulder_angle_L_mean  # Re-purposed field for form score
            total_reps = int(report.meanASI)          # Re-purposed field for rep count
            duration = report.transition_duration or 0.0
            instruction_label = "Angkat Tangan" if report.instruction == "rehab_arm_raise" else "Jongkok & Berdiri"
            if avg_form >= 85:
                summary = "Kualitas gerakan sempurna!"
            elif avg_form >= 60:
                summary = "Kualitas gerakan baik!"
            elif avg_form >= 30:
                summary = "Kualitas gerakan cukup, perlu perbaikan."
            else:
                summary = "Latihan belum optimal, coba lagi."
            return {
                "report_id": report.session_id,
                "patient_id": report.patient_id,
                "timestamp": report.timestamp.isoformat(),
                "instruction": report.instruction,
                "instruction_label": instruction_label,
                "reps": total_reps,
                "score": round(avg_form, 1),
                "duration_s": round(duration, 1),
                "risk_levels": {
                    "stroke": "normal",
                    "parkinson": "normal",
                    "sarcopenia": "normal",
                },
                "confidence_scores": {
                    "overall": round(min(100, avg_form), 1),
                },
                "recommendation": summary,
                "narrative": report.ai_narrative or f"Latihan {instruction_label} selesai: {total_reps} repetisi, skor {avg_form:.0f}%. {summary}",
            }

        # ── Clinical sessions: original report generation ──
        # Compute confidence scores (0-1 scale)
        stroke_conf = min(1.0, report.meanASI / 0.15) if report.meanASI > 0 else 0.0
        parkinson_conf = 0.0
        if report.dominant_freq and 3.0 <= report.dominant_freq <= 15.0:
            if report.dominant_freq >= 4.0 and report.dominant_freq <= 12.0:
                parkinson_conf = 0.7 + (report.tremor_duration_pct or 0) * 0.3
            else:
                parkinson_conf = 0.3 + (report.tremor_duration_pct or 0) * 0.3
        sarcopenia_conf = 0.0
        if report.transition_duration:
            sarcopenia_conf = min(1.0, report.transition_duration / 7.0)

        return {
            "report_id": report.session_id,
            "patient_id": report.patient_id,
            "timestamp": report.timestamp.isoformat(),
            "instruction": report.instruction,
            "metrics": {
                "asymmetry": {
                    "meanASI": round(report.meanASI, 4),
                    "maxASI": round(report.maxASI, 4),
                    "shoulder_angle_L": round(report.shoulder_angle_L_mean, 1),
                    "shoulder_angle_R": round(report.shoulder_angle_R_mean, 1),
                    "angle_asymmetry": round(report.angle_asymmetry, 1),
                },
                "tremor": {
                    "dominant_freq_hz": round(report.dominant_freq, 2) if report.dominant_freq else None,
                    "amplitude": round(report.tremor_amplitude, 6) if report.tremor_amplitude else None,
                    "duration_pct": round((report.tremor_duration_pct or 0) * 100, 1),
                },
                "sit_to_stand": {
                    "duration_s": round(report.transition_duration, 2) if report.transition_duration else None,
                    "velocity": round(report.transition_velocity, 4) if report.transition_velocity else None,
                },
            },
            "risk_levels": {
                "stroke": report.stroke_risk.value,
                "parkinson": report.parkinson_risk.value,
                "sarcopenia": report.sarcopenia_risk.value,
            },
            "confidence_scores": {
                "stroke": round(stroke_conf, 3),
                "parkinson": round(parkinson_conf, 3),
                "sarcopenia": round(sarcopenia_conf, 3),
            },
            "recommendation": ReportGenerator._recommendation(report),
            "narrative": ReportGenerator._narrative(report),
        }

    @staticmethod
    def _recommendation(r: ClinicalReport) -> str:
        if any(x == RiskLevel.REFERAL for x in [r.stroke_risk, r.parkinson_risk, r.sarcopenia_risk]):
            return "REKOMENDASI: Rujukan klinis — segera konsultasikan dengan dokter spesialis."
        if any(x == RiskLevel.MONITOR for x in [r.stroke_risk, r.parkinson_risk, r.sarcopenia_risk]):
            return "REKOMENDASI: Monitoring — assessment ulang dalam 1-3 bulan."
        return "REKOMENDASI: Normal — tidak terdeteksi indikasi anomali signifikan."

    @staticmethod
    def _narrative(r: ClinicalReport) -> str:
        lines = []
        lines.append(f"Laporan Screening Neuro-Motorik — {r.timestamp.strftime('%d %B %Y, %H:%M')}")

        # Stroke
        lines.append(f"\n[Asimetri] ASI: {r.meanASI:.3f} | Sudut L: {r.shoulder_angle_L_mean:.1f}° | R: {r.shoulder_angle_R_mean:.1f}°")
        if r.stroke_risk == RiskLevel.REFERAL:
            lines.append(f"  → Indikasi asimetri signifikan. Rujukan neurologis direkomendasikan.")
        elif r.stroke_risk == RiskLevel.MONITOR:
            lines.append(f"  → Asimetri ringan. Monitoring berkala direkomendasikan.")
        else:
            lines.append(f"  → Simetri dalam batas normal.")

        # Parkinson
        if r.dominant_freq:
            lines.append(f"\n[Tremor] Freq: {r.dominant_freq:.1f} Hz | Amplitudo: {r.tremor_amplitude:.4f} | Durasi: {r.tremor_duration_pct*100:.0f}%")
            if r.parkinson_risk == RiskLevel.REFERAL:
                lines.append(f"  → Pola tremor patologis terdeteksi. Evaluasi neurologis direkomendasikan.")
            elif r.parkinson_risk == RiskLevel.MONITOR:
                lines.append(f"  → Aktivitas frekuensi transisi. Monitoring direkomendasikan.")
            else:
                lines.append(f"  → Tidak terdeteksi tremor patologis.")

        # Sarcopenia
        if r.transition_duration:
            lines.append(f"\n[Sit-to-Stand] Durasi: {r.transition_duration:.2f}s")
            if r.sarcopenia_risk == RiskLevel.REFERAL:
                lines.append(f"  → Transisi lambat. Evaluasi komposisi tubuh direkomendasikan.")
            elif r.sarcopenia_risk == RiskLevel.MONITOR:
                lines.append(f"  → Durasi di batas atas normal.")
            else:
                lines.append(f"  → Transisi dalam batas normal.")

        return "\n".join(lines)
