"""
Report Generator — Merangkum metrik sesi menjadi laporan klinis terstruktur.
"""

import json
from models.schemas import ClinicalReport, RiskLevel


class ReportGenerator:

    @staticmethod
    def to_dict(report: ClinicalReport) -> dict:
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
