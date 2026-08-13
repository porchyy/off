"""Daily PostureAI Excel report generation."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import select
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
        minute = datetime.fromisoformat(row.created_at).replace(second=0, microsecond=0).isoformat()
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

    summary.merge_cells("A1:B1")
    summary["A1"] = "PostureAI — รายงานท่านั่งรายวัน"
    summary["A1"].font = Font(bold=True, color="FFFFFF", size=14)
    summary["A1"].fill = HEADER_FILL
    summary["A1"].alignment = Alignment(horizontal="center")
    summary["A2"] = "วันที่"
    summary["B2"] = report_date
    summary["B2"].number_format = "dd/mm/yyyy"
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
    summary.column_dimensions["B"].width = 20

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
