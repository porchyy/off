"""Daily PostureAI Excel report generation."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from io import BytesIO
from pathlib import Path
import re
from typing import Any
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import Alert, MinuteSummary, Sample

LOCAL_TZ = ZoneInfo("Asia/Bangkok")
HEADER_FILL = PatternFill("solid", fgColor="1E3A5F")
RISK_FILL = PatternFill("solid", fgColor="FDE2E2")


def local_day_bounds(report_date: date) -> tuple[str, str]:
    start = datetime.combine(report_date, time.min, tzinfo=LOCAL_TZ).astimezone(timezone.utc)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def local_today() -> date:
    return datetime.now(LOCAL_TZ).date()


def _utc_minute(timestamp: str) -> str:
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(second=0, microsecond=0).isoformat()


def local_day_label(timestamp: str) -> str:
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(LOCAL_TZ).date().isoformat()


def compact_legacy_samples(db: Session, risk_threshold: int) -> int:
    """Move old high-frequency rows into one aggregate per minute exactly once."""
    samples = list(db.scalars(select(Sample).order_by(Sample.id)))
    if not samples:
        return 0
    existing = {row.minute_start: row for row in db.scalars(select(MinuteSummary))}
    for sample in samples:
        minute_start = _utc_minute(sample.created_at)
        row = existing.get(minute_start)
        if row is None:
            row = MinuteSummary(
                minute_start=minute_start,
                score_sum=0.0,
                score_min=sample.score,
                score_max=sample.score,
                neck_sum=0.0,
                shoulders_sum=0.0,
                torso_sum=0.0,
                measurements=0,
                risk_measurements=0,
            )
            existing[minute_start] = row
            db.add(row)
        row.score_sum += sample.score
        row.score_min = min(row.score_min, sample.score)
        row.score_max = max(row.score_max, sample.score)
        row.neck_sum += sample.neck or 0.0
        row.shoulders_sum += sample.shoulders or 0.0
        row.torso_sum += sample.torso or 0.0
        row.measurements += 1
        row.risk_measurements += int(sample.score < risk_threshold)
    db.execute(delete(Sample))
    db.commit()
    return len(samples)


def prune_expired_reports(report_dir: Path, days: int) -> int:
    """Remove only dated PostureAI reports outside the same retention window."""
    if not report_dir.exists():
        return 0
    cutoff = local_today() - timedelta(days=days)
    removed = 0
    pattern = re.compile(r"PostureAI_(\d{4}-\d{2}-\d{2})\.xlsx$")
    for report in report_dir.iterdir():
        match = pattern.fullmatch(report.name)
        if not report.is_file() or match is None:
            continue
        try:
            report_date = date.fromisoformat(match.group(1))
        except ValueError:
            continue
        if report_date < cutoff:
            report.unlink()
            removed += 1
    return removed


def _minute_rows(db: Session, report_date: date, risk_threshold: int) -> list[dict[str, Any]]:
    start, end = local_day_bounds(report_date)
    buckets: dict[str, dict[str, Any]] = {}

    for row in db.scalars(
        select(MinuteSummary).where(MinuteSummary.minute_start >= start, MinuteSummary.minute_start < end)
    ):
        buckets[row.minute_start] = {
            "minute_start": row.minute_start,
            "score_sum": row.score_sum,
            "score_min": row.score_min,
            "score_max": row.score_max,
            "neck_sum": row.neck_sum,
            "shoulders_sum": row.shoulders_sum,
            "torso_sum": row.torso_sum,
            "measurements": row.measurements,
            "risk_measurements": row.risk_measurements,
        }

    # Include historical samples written before minute aggregation was introduced.
    legacy = db.scalars(select(Sample).where(Sample.created_at >= start, Sample.created_at < end))
    for row in legacy:
        minute = _utc_minute(row.created_at)
        bucket = buckets.setdefault(
            minute,
            {
                "minute_start": minute,
                "score_sum": 0.0,
                "score_min": row.score,
                "score_max": row.score,
                "neck_sum": 0.0,
                "shoulders_sum": 0.0,
                "torso_sum": 0.0,
                "measurements": 0,
                "risk_measurements": 0,
            },
        )
        bucket["score_sum"] += row.score
        bucket["score_min"] = min(bucket["score_min"], row.score)
        bucket["score_max"] = max(bucket["score_max"], row.score)
        bucket["neck_sum"] += row.neck or 0.0
        bucket["shoulders_sum"] += row.shoulders or 0.0
        bucket["torso_sum"] += row.torso or 0.0
        bucket["measurements"] += 1
        bucket["risk_measurements"] += int(row.score < risk_threshold)

    rows = []
    for bucket in buckets.values():
        count = max(1, bucket["measurements"])
        local_time = datetime.fromisoformat(bucket["minute_start"]).astimezone(LOCAL_TZ)
        risk_seconds = round(60 * bucket["risk_measurements"] / count)
        rows.append(
            {
                "time": local_time.replace(tzinfo=None),
                "score": bucket["score_sum"] / count,
                "score_min": bucket["score_min"],
                "score_max": bucket["score_max"],
                "neck": bucket["neck_sum"] / count,
                "shoulders": bucket["shoulders_sum"] / count,
                "torso": bucket["torso_sum"] / count,
                "measurements": count,
                "risk_seconds": risk_seconds,
                "status": "เสี่ยง" if risk_seconds else "ดี",
            }
        )
    return sorted(rows, key=lambda row: row["time"])


def _alert_rows(db: Session, report_date: date) -> list[Alert]:
    start, end = local_day_bounds(report_date)
    return list(db.scalars(select(Alert).where(Alert.created_at >= start, Alert.created_at < end).order_by(Alert.created_at)))


def build_daily_report(db: Session, report_date: date, risk_threshold: int) -> bytes:
    """Create a readable Excel workbook for one Bangkok calendar day."""
    minute_rows = _minute_rows(db, report_date, risk_threshold)
    alerts = _alert_rows(db, report_date)
    workbook = Workbook()
    summary = workbook.active
    summary.title = "สรุปรายวัน"
    detail = workbook.create_sheet("รายละเอียดรายนาที")
    alert_sheet = workbook.create_sheet("เหตุการณ์แจ้งเตือน")

    summary.merge_cells("A1:H1")
    summary["A1"] = "PostureAI — รายงานท่านั่งรายวัน"
    summary["A1"].font = Font(bold=True, color="FFFFFF", size=14)
    summary["A1"].fill = HEADER_FILL
    summary["A1"].alignment = Alignment(horizontal="center")
    summary["A2"] = "วันที่รายงาน"
    summary["B2"] = report_date
    summary["B2"].number_format = "dd/mm/yyyy"
    summary["A3"] = "หมายเหตุ"
    summary["B3"] = "รายงานนี้เก็บเฉพาะคะแนนและเหตุการณ์แจ้งเตือน ไม่เก็บภาพหรือวิดีโอ"
    summary["B3"].alignment = Alignment(wrap_text=True)
    if minute_rows:
        summary_rows = [
            ("คะแนนเฉลี่ย", "=IFERROR(AVERAGE('รายละเอียดรายนาที'!B2:B%d),0)" % (len(minute_rows) + 1)),
            ("คะแนนต่ำสุด", "=IFERROR(MIN('รายละเอียดรายนาที'!C2:C%d),0)" % (len(minute_rows) + 1)),
            ("คะแนนสูงสุด", "=IFERROR(MAX('รายละเอียดรายนาที'!D2:D%d),0)" % (len(minute_rows) + 1)),
            ("เวลาที่เสี่ยง (นาที)", "=IFERROR(SUM('รายละเอียดรายนาที'!I2:I%d)/60,0)" % (len(minute_rows) + 1)),
            ("จำนวนช่วงเวลาที่มีข้อมูล", len(minute_rows)),
        ]
    else:
        summary_rows = [
            ("คะแนนเฉลี่ย", 0), ("คะแนนต่ำสุด", 0), ("คะแนนสูงสุด", 0),
            ("เวลาที่เสี่ยง (นาที)", 0), ("จำนวนช่วงเวลาที่มีข้อมูล", 0),
        ]
    summary_rows.extend([("จำนวน Alert", len(alerts)), ("เกณฑ์คะแนนเสี่ยง", risk_threshold)])
    for row_index, (label, value) in enumerate(summary_rows, start=4):
        summary.cell(row_index, 1, label).font = Font(bold=True)
        summary.cell(row_index, 2, value)
        if row_index <= 7:
            summary.cell(row_index, 2).number_format = "0.0"
    summary.column_dimensions["A"].width = 28
    summary.column_dimensions["B"].width = 44

    detail_headers = [
        "เวลา", "คะแนนเฉลี่ย", "คะแนนต่ำสุด", "คะแนนสูงสุด", "คอเฉลี่ย", "ไหล่เฉลี่ย",
        "ลำตัวเฉลี่ย", "จำนวนการวัด", "เวลาที่เสี่ยง (วินาที)", "สถานะ",
    ]
    detail.append(detail_headers)
    for cell in detail[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
    for row in minute_rows:
        detail.append([
            row["time"], row["score"], row["score_min"], row["score_max"], row["neck"],
            row["shoulders"], row["torso"], row["measurements"], row["risk_seconds"], row["status"],
        ])
    for row in detail.iter_rows(min_row=2, max_col=9):
        row[0].number_format = "hh:mm"
        for cell in row[1:7]:
            cell.number_format = "0.0"
    detail.conditional_formatting.add(
        f"B2:B{max(2, len(minute_rows) + 1)}",
        CellIsRule(operator="lessThan", formula=[str(risk_threshold)], fill=RISK_FILL),
    )
    for column, width in enumerate((12, 14, 14, 14, 12, 12, 12, 16, 20, 12), start=1):
        detail.column_dimensions[get_column_letter(column)].width = width
    detail.freeze_panes = "A2"

    if minute_rows:
        trend_chart = LineChart()
        trend_chart.title = "แนวโน้มคะแนนท่านั่งตลอดวัน"
        trend_chart.y_axis.title = "คะแนน"
        trend_chart.x_axis.title = "เวลา"
        trend_chart.y_axis.scaling.min = 0
        trend_chart.y_axis.scaling.max = 100
        trend_chart.height = 8
        trend_chart.width = 18
        trend_chart.add_data(Reference(detail, min_col=2, min_row=1, max_row=len(minute_rows) + 1), titles_from_data=True)
        trend_chart.set_categories(Reference(detail, min_col=1, min_row=2, max_row=len(minute_rows) + 1))
        summary.add_chart(trend_chart, "D3")

    alert_sheet.append(["เวลา", "ระดับ", "ข้อความ"])
    for cell in alert_sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
    for alert in alerts:
        alert_sheet.append([
            datetime.fromisoformat(alert.created_at).astimezone(LOCAL_TZ).replace(tzinfo=None),
            alert.severity,
            alert.message,
        ])
    for cell in alert_sheet["A"][1:]:
        cell.number_format = "hh:mm"
    alert_sheet.column_dimensions["A"].width = 12
    alert_sheet.column_dimensions["B"].width = 12
    alert_sheet.column_dimensions["C"].width = 70
    alert_sheet.freeze_panes = "A2"

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def write_daily_report(db: Session, report_date: date, risk_threshold: int, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    target = report_dir / f"PostureAI_{report_date.isoformat()}.xlsx"
    temporary = target.with_suffix(".xlsx.tmp")
    temporary.write_bytes(build_daily_report(db, report_date, risk_threshold))
    temporary.replace(target)
    return target
