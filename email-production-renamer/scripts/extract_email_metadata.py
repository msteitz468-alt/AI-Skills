#!/usr/bin/env python3
"""
Extraction helper for the email-production-renamer skill.

This script is intentionally an evidence extractor, not the final naming engine.
It emits JSON so Codex/ChatGPT can review subjects, bodies, senders, and policy
candidates with AI judgment before moving/renaming files.

Supported inputs:
- .msg via Aspose.Email FOSS for Python, with extract_msg as a fallback
- .eml via Python's email package
- .txt as plain text email exports

Usage:
    python extract_email_metadata.py /path/to/email-folder > extracted_emails.json
    python extract_email_metadata.py /path/to/email-folder --attachments-dir /path/to/staging/attachments
"""
from __future__ import annotations

import argparse
import email
import email.policy
import hashlib
import json
import mimetypes
import os
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterable

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore

PACIFIC_TZ = "America/Los_Angeles"
SUPPORTED_EXTS = {".msg", ".eml", ".txt"}
POLICY_RE = re.compile(r"\b(?:[A-Z]{2,6}\s*[-#]?\s*\d{5,12}|\d{7,12})\b", re.IGNORECASE)
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


@dataclass
class ExtractedEmail:
    source_path: str
    filename: str
    extension: str
    source_sha256: str | None = None
    msg_decoder: str | None = None
    subject: str | None = None
    sender_name: str | None = None
    sender_email: str | None = None
    to: str | None = None
    cc: str | None = None
    date_header: str | None = None
    sent_time_raw: str | None = None
    received_time_raw: str | None = None
    pacific_timestamp: str | None = None
    body_preview: str | None = None
    policy_candidates: list[str] | None = None
    attachments: list[dict[str, Any]] | None = None
    warnings: list[str] | None = None


def clean_text(value: Any, limit: int | None = None) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\r", " ").replace("\n", " ")
    text = CONTROL_RE.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if limit and len(text) > limit:
        return text[: max(0, limit - 3)].rstrip() + "..."
    return text or None


def to_pacific_stamp(value: Any) -> str | None:
    if not value:
        return None
    dt: datetime | None = None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        for parser in (datetime.fromisoformat, parsedate_to_datetime):
            try:
                dt = parser(text)  # type: ignore[arg-type]
                break
            except Exception:
                continue
    if dt is None:
        return None
    if ZoneInfo is None:
        return dt.strftime("%Y%m%d %H%M")
    pacific = ZoneInfo(PACIFIC_TZ)
    if dt.tzinfo is None:
        # Treat timezone-less email library datetimes as Pacific to avoid accidental UTC shifts.
        dt = dt.replace(tzinfo=pacific)
    return dt.astimezone(pacific).strftime("%Y%m%d %H%M")


def policy_candidates(*parts: str | None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for part in parts:
        if not part:
            continue
        for match in POLICY_RE.findall(part):
            normalized = re.sub(r"\s+", "", match).upper().replace("#", "").replace("-", "")
            if normalized not in seen:
                seen.add(normalized)
                out.append(normalized)
    return out


def parse_sender(raw: str | None) -> tuple[str | None, str | None]:
    if not raw:
        return None, None
    name, addr = email.utils.parseaddr(raw)
    return clean_text(name) or None, clean_text(addr) or None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_component(value: str, fallback: str) -> str:
    value = CONTROL_RE.sub(" ", value)
    value = re.sub(r'[<>:"/\\|?*]', "_", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value or fallback


def unique_destination(folder: Path, filename: str) -> Path:
    candidate = folder / filename
    if not candidate.exists():
        return candidate
    iteration = 2
    while True:
        candidate = folder / f"{Path(filename).stem} ({iteration}){Path(filename).suffix}"
        if not candidate.exists():
            return candidate
        iteration += 1


def attachment_folder(root: Path | None, source_path: Path, source_sha256: str) -> Path | None:
    if root is None:
        return None
    folder = root / (safe_component(source_path.stem, "message") + "--" + source_sha256[:12])
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def attachment_record(
    index: int,
    original_name: str,
    data: bytes,
    mime_type: str | None,
    is_embedded_message: bool,
    output_folder: Path | None,
) -> dict[str, Any]:
    fallback_extension = ".msg" if is_embedded_message else ".bin"
    safe_name = safe_component(original_name, f"attachment-{index}{fallback_extension}")
    if not Path(safe_name).suffix and is_embedded_message:
        safe_name += ".msg"
    data_hash = hashlib.sha256(data).hexdigest()
    saved_path: str | None = None
    if output_folder is not None:
        preferred = output_folder / safe_name
        if preferred.exists() and sha256_file(preferred) == data_hash:
            destination = preferred
        else:
            destination = unique_destination(output_folder, safe_name)
            destination.write_bytes(data)
        saved_path = str(destination)
    return {
        "index": index,
        "original_name": original_name,
        "saved_name": Path(saved_path).name if saved_path else None,
        "saved_path": saved_path,
        "sha256": data_hash,
        "size_bytes": len(data),
        "mime_type": mime_type or mimetypes.guess_type(safe_name)[0],
        "is_embedded_message": is_embedded_message,
    }


def get_msg_attr(msg: Any, names: Iterable[str]) -> Any:
    for name in names:
        try:
            value = getattr(msg, name, None)
            if value:
                return value
        except Exception:
            continue
    return None


def extract_msg_with_aspose(path: Path, attachments_root: Path | None) -> ExtractedEmail:
    warnings: list[str] = []
    try:
        from aspose.email_foss.msg import CommonMessagePropertyId, MapiMessage  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"aspose-email-foss not installed or unavailable: {exc}") from exc

    source_hash = sha256_file(path)
    try:
        msg = MapiMessage.from_file(str(path))
    except Exception as exc:
        raise RuntimeError(f"Aspose failed to open .msg: {exc}") from exc

    try:
        def read_property(label: str, getter: Any) -> Any:
            try:
                return getter()
            except Exception as exc:
                warnings.append(f"{label} extraction warning: {exc}")
                return None

        subject = clean_text(read_property("subject", lambda: msg.subject), 300)
        body = clean_text(read_property("body", lambda: msg.body), 2500)
        if not body:
            body = clean_text(read_property("HTML body", lambda: msg.body_html), 2500)
        sender_name = clean_text(
            read_property(
                "sender name",
                lambda: msg.get_property_value(CommonMessagePropertyId.SENDER_NAME),
            ),
            200,
        )
        sender_email = clean_text(
            read_property(
                "sender email",
                lambda: msg.get_property_value(CommonMessagePropertyId.SENDER_EMAIL_ADDRESS),
            ),
            200,
        )
        recipients = read_property("recipients", lambda: list(msg.recipients)) or []

        def recipient_header(recipient_type: int) -> str | None:
            values: list[str] = []
            for recipient in recipients:
                if int(getattr(recipient, "recipient_type", 0) or 0) != recipient_type:
                    continue
                name = clean_text(getattr(recipient, "display_name", None))
                address = clean_text(getattr(recipient, "email_address", None))
                value = email.utils.formataddr((name or "", address)) if address else name
                if value:
                    values.append(value)
            return ", ".join(values) or None

        received = read_property(
            "received time",
            lambda: msg.get_property_value(CommonMessagePropertyId.MESSAGE_DELIVERY_TIME),
        )
        # PidTagClientSubmitTime is 0x0039 and is not exported by the package enum.
        sent = read_property("sent time", lambda: msg.get_property_value(0x0039))
        attachments: list[dict[str, Any]] = []
        output_folder = attachment_folder(attachments_root, path, source_hash)
        raw_attachments = read_property(
            "attachment list",
            lambda: list(msg.iter_attachments_info()),
        ) or []
        for index, attachment in enumerate(raw_attachments, start=1):
            try:
                original_name = clean_text(getattr(attachment, "filename", None), 255)
                is_embedded = bool(getattr(attachment, "is_embedded_message", False))
                if is_embedded and getattr(attachment, "embedded_message", None) is not None:
                    data = attachment.embedded_message.to_bytes()
                else:
                    data = bytes(getattr(attachment, "data", b"") or b"")
                attachments.append(
                    attachment_record(
                        index,
                        original_name or f"attachment-{index}",
                        data,
                        clean_text(getattr(attachment, "mime_type", None), 200),
                        is_embedded,
                        output_folder,
                    )
                )
            except Exception as exc:
                warnings.append(f"attachment {index} extraction warning: {exc}")

        validation_issues = read_property("validation issues", lambda: list(msg.validation_issues)) or []
        warnings.extend(f"Aspose validation issue: {issue}" for issue in validation_issues)
        return ExtractedEmail(
            source_path=str(path),
            filename=path.name,
            extension=path.suffix.lower(),
            source_sha256=source_hash,
            msg_decoder="aspose-email-foss",
            subject=subject,
            sender_name=sender_name,
            sender_email=sender_email,
            to=clean_text(recipient_header(1), 500),
            cc=clean_text(recipient_header(2), 500),
            sent_time_raw=clean_text(sent, 100),
            received_time_raw=clean_text(received, 100),
            pacific_timestamp=to_pacific_stamp(received) or to_pacific_stamp(sent),
            body_preview=body,
            policy_candidates=policy_candidates(subject, body),
            attachments=attachments,
            warnings=warnings,
        )
    finally:
        try:
            msg.close()
        except Exception:
            pass


def extract_msg_with_extract_msg(
    path: Path,
    attachments_root: Path | None,
    prior_warning: str,
) -> ExtractedEmail:
    warnings = [prior_warning]
    source_hash = sha256_file(path)
    try:
        import extract_msg  # type: ignore
    except Exception as exc:
        return ExtractedEmail(
            str(path),
            path.name,
            path.suffix.lower(),
            source_sha256=source_hash,
            warnings=warnings + [f"extract_msg fallback unavailable: {exc}"],
        )

    try:
        msg = extract_msg.Message(str(path))
    except Exception as exc:
        return ExtractedEmail(
            str(path),
            path.name,
            path.suffix.lower(),
            source_sha256=source_hash,
            warnings=warnings + [f"extract_msg fallback failed to open .msg: {exc}"],
        )

    try:
        subject = clean_text(get_msg_attr(msg, ["subject"]), 300)
        body = clean_text(get_msg_attr(msg, ["body", "htmlBody"]), 2500)
        sender_raw = clean_text(get_msg_attr(msg, ["sender", "senderName", "senderEmail"]), 300)
        sender_name = clean_text(get_msg_attr(msg, ["senderName"]), 200)
        sender_email = clean_text(get_msg_attr(msg, ["senderEmail"]), 200)
        if not sender_name and sender_raw:
            parsed_name, parsed_email = parse_sender(sender_raw)
            sender_name = parsed_name
            sender_email = sender_email or parsed_email
        received = get_msg_attr(msg, ["receivedTime", "date"])
        sent = get_msg_attr(msg, ["sentOn", "sentDate"])
        to_value = clean_text(get_msg_attr(msg, ["to"]), 500)
        cc_value = clean_text(get_msg_attr(msg, ["cc"]), 500)
        output_folder = attachment_folder(attachments_root, path, source_hash)
        attachments: list[dict[str, Any]] = []
        for index, attachment in enumerate(get_msg_attr(msg, ["attachments"]) or [], start=1):
            try:
                original_name = clean_text(
                    get_msg_attr(attachment, ["longFilename", "shortFilename", "name"]),
                    255,
                )
                data = get_msg_attr(attachment, ["data"])
                if not isinstance(data, bytes):
                    raise TypeError("attachment data is not a byte stream")
                attachments.append(
                    attachment_record(
                        index,
                        original_name or f"attachment-{index}",
                        data,
                        None,
                        False,
                        output_folder,
                    )
                )
            except Exception as exc:
                warnings.append(f"fallback attachment {index} extraction warning: {exc}")

        return ExtractedEmail(
            source_path=str(path),
            filename=path.name,
            extension=path.suffix.lower(),
            source_sha256=source_hash,
            msg_decoder="extract-msg-fallback",
            subject=subject,
            sender_name=sender_name,
            sender_email=sender_email,
            to=to_value,
            cc=cc_value,
            sent_time_raw=clean_text(sent, 100),
            received_time_raw=clean_text(received, 100),
            pacific_timestamp=to_pacific_stamp(received) or to_pacific_stamp(sent),
            body_preview=body,
            policy_candidates=policy_candidates(subject, body),
            attachments=attachments,
            warnings=warnings,
        )
    finally:
        try:
            msg.close()
        except Exception:
            pass


def extract_msg_file(path: Path, attachments_root: Path | None) -> ExtractedEmail:
    try:
        return extract_msg_with_aspose(path, attachments_root)
    except Exception as exc:
        return extract_msg_with_extract_msg(
            path,
            attachments_root,
            f"Aspose decode failed; used extract_msg fallback: {exc}",
        )


def extract_eml_file(path: Path) -> ExtractedEmail:
    warnings: list[str] = []
    try:
        data = path.read_bytes()
        msg = email.message_from_bytes(data, policy=email.policy.default)
    except Exception as exc:
        return ExtractedEmail(str(path), path.name, path.suffix.lower(), warnings=[f"failed to read .eml: {exc}"])

    subject = clean_text(msg.get("subject"), 300)
    sender_name, sender_email = parse_sender(msg.get("from"))
    body_parts: list[str] = []
    try:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain" and not part.get_filename():
                    body_parts.append(part.get_content())
        else:
            body_parts.append(msg.get_content())
    except Exception as exc:
        warnings.append(f"body extraction warning: {exc}")
    body = clean_text("\n".join(body_parts), 2500)
    date_header = clean_text(msg.get("date"), 100)

    return ExtractedEmail(
        source_path=str(path),
        filename=path.name,
        extension=path.suffix.lower(),
        source_sha256=sha256_file(path),
        subject=subject,
        sender_name=sender_name,
        sender_email=sender_email,
        to=clean_text(msg.get("to"), 500),
        cc=clean_text(msg.get("cc"), 500),
        date_header=date_header,
        pacific_timestamp=to_pacific_stamp(date_header),
        body_preview=body,
        policy_candidates=policy_candidates(subject, body),
        warnings=warnings,
    )


def extract_txt_file(path: Path) -> ExtractedEmail:
    warnings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return ExtractedEmail(str(path), path.name, path.suffix.lower(), warnings=[f"failed to read .txt: {exc}"])
    subject = None
    sender_name = None
    sender_email = None
    date_header = None
    for line in text.splitlines()[:100]:
        if subject is None and re.match(r"^subject:\s*", line, re.I):
            subject = clean_text(re.sub(r"^subject:\s*", "", line, flags=re.I), 300)
        elif sender_email is None and re.match(r"^(from|sender):\s*", line, re.I):
            sender_name, sender_email = parse_sender(re.sub(r"^(from|sender):\s*", "", line, flags=re.I))
        elif date_header is None and re.match(r"^(date|sent|received):\s*", line, re.I):
            date_header = clean_text(re.sub(r"^(date|sent|received):\s*", "", line, flags=re.I), 100)
    body = clean_text(text, 2500)
    return ExtractedEmail(
        source_path=str(path),
        filename=path.name,
        extension=path.suffix.lower(),
        source_sha256=sha256_file(path),
        subject=subject,
        sender_name=sender_name,
        sender_email=sender_email,
        date_header=date_header,
        pacific_timestamp=to_pacific_stamp(date_header),
        body_preview=body,
        policy_candidates=policy_candidates(subject, body),
        warnings=warnings,
    )


def extract_file(path: Path, attachments_root: Path | None = None) -> ExtractedEmail:
    ext = path.suffix.lower()
    if ext == ".msg":
        return extract_msg_file(path, attachments_root)
    if ext == ".eml":
        return extract_eml_file(path)
    if ext == ".txt":
        return extract_txt_file(path)
    return ExtractedEmail(str(path), path.name, ext, warnings=["unsupported extension"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract email metadata for AI-reviewed renaming.")
    parser.add_argument("input_folder", help="Folder containing .msg, .eml, or .txt email files")
    parser.add_argument("--recursive", action="store_true", help="Scan recursively")
    parser.add_argument(
        "--attachments-dir",
        help="Optional staging folder for lossless .msg attachment extraction",
    )
    args = parser.parse_args()

    root = Path(args.input_folder).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(json.dumps({"error": f"input folder is not a directory: {root}"}, indent=2), file=sys.stderr)
        return 2

    globber = root.rglob if args.recursive else root.glob
    files = sorted(p for p in globber("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS)
    attachments_root = (
        Path(args.attachments_dir).expanduser().resolve() if args.attachments_dir else None
    )
    if attachments_root is not None:
        attachments_root.mkdir(parents=True, exist_ok=True)
    records = [asdict(extract_file(path, attachments_root)) for path in files]
    print(
        json.dumps(
            {
                "input_folder": str(root),
                "attachments_dir": str(attachments_root) if attachments_root else None,
                "count": len(records),
                "emails": records,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
