"""Config sync service — clones Git repos and matches config files to SNEP devices.

Flow:
1. Clone/pull the Git repo (shallow, single branch)
2. List all files matching the file_extension
3. For each SNEP device, render the path_template with device context
4. If the rendered path matches a file in the repo, store the config
5. Track sync state (commit SHA, timestamp, status)
"""

import logging
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from snep.models import Device, DeviceModel
from snep.models.config_source import ConfigSource, DeviceConfig

logger = logging.getLogger(__name__)


async def sync_config_source(session: AsyncSession, source_id: str) -> dict:
    """Sync a config source — clone repo, match files to devices, store configs."""
    source = await session.get(ConfigSource, source_id)
    if not source:
        return {"error": "Config source not found"}

    now = datetime.now(timezone.utc)
    stats = {"matched": 0, "unmatched": 0, "updated": 0, "errors": [], "files_found": 0}

    tmp_dir = tempfile.mkdtemp(prefix="snep_config_")

    try:
        # Clone the repo
        clone_url = _build_clone_url(source.repo_url, source.auth_token)
        exit_code = os.system(
            f"git clone --depth 1 --branch {source.branch} --single-branch "
            f"'{clone_url}' '{tmp_dir}/repo' 2>/dev/null"
        )
        if exit_code != 0:
            source.last_sync_status = "failed"
            source.last_sync_message = "Git clone failed"
            source.last_sync_at = now
            await session.commit()
            return {"error": "Git clone failed. Check URL, branch, and auth token."}

        repo_dir = Path(tmp_dir) / "repo"

        # Get commit SHA
        commit_sha = ""
        git_head = repo_dir / ".git" / "HEAD"
        if git_head.exists():
            ref = git_head.read_text().strip()
            if ref.startswith("ref:"):
                ref_path = repo_dir / ".git" / ref.split(" ", 1)[1]
                if ref_path.exists():
                    commit_sha = ref_path.read_text().strip()[:12]
            else:
                commit_sha = ref[:12]

        # Find all config files
        ext = source.file_extension or ""
        all_files = {}
        for f in repo_dir.rglob("*"):
            if f.is_file() and not str(f.relative_to(repo_dir)).startswith(".git"):
                rel_path = str(f.relative_to(repo_dir))
                if not ext or rel_path.endswith(ext) or not ext.startswith("."):
                    all_files[rel_path] = f
                    stats["files_found"] += 1

        # Load all devices with relationships for path template rendering
        result = await session.execute(
            select(Device)
            .options(
                selectinload(Device.device_model).selectinload(DeviceModel.platform),
            )
            .where(Device.admin_state == "active")
        )
        devices = result.scalars().all()

        # For each device, render the path template and try to match
        env = Environment()
        for device in devices:
            try:
                ctx = _build_device_context(device)
                tmpl = env.from_string(source.path_template)
                expected_path = tmpl.render(**ctx)
            except Exception as e:
                stats["errors"].append(f"{device.hostname}: template error: {e}")
                continue

            # Try exact match, then case-insensitive, then without extension
            matched_file = None
            if expected_path in all_files:
                matched_file = all_files[expected_path]
            else:
                # Try case-insensitive
                for path, f in all_files.items():
                    if path.lower() == expected_path.lower():
                        matched_file = f
                        break
                # Try with/without extension
                if not matched_file:
                    base = expected_path.rsplit(".", 1)[0] if "." in expected_path else expected_path
                    for path, f in all_files.items():
                        path_base = path.rsplit(".", 1)[0] if "." in path else path
                        if path_base == base or path_base.lower() == base.lower():
                            matched_file = f
                            break
                # Try hostname anywhere in filename
                if not matched_file:
                    for path, f in all_files.items():
                        if device.hostname.lower() in Path(path).stem.lower():
                            matched_file = f
                            break

            if matched_file:
                config_text = matched_file.read_text(errors="replace")
                rel_path = str(matched_file.relative_to(repo_dir))

                # Upsert DeviceConfig
                existing = await session.execute(
                    select(DeviceConfig)
                    .where(DeviceConfig.device_id == device.id, DeviceConfig.config_type == "running")
                )
                dc = existing.scalar_one_or_none()
                if dc:
                    dc.config_text = config_text
                    dc.line_count = len(config_text.strip().split("\n"))
                    dc.source_id = source.id
                    dc.source_path = rel_path
                    dc.source_commit = commit_sha
                    stats["updated"] += 1
                else:
                    dc = DeviceConfig(
                        device_id=device.id, config_type="running",
                        config_text=config_text,
                        line_count=len(config_text.strip().split("\n")),
                        source_id=source.id, source_path=rel_path, source_commit=commit_sha,
                    )
                    session.add(dc)
                    stats["matched"] += 1
            else:
                stats["unmatched"] += 1

        # Update source state
        source.last_sync_at = now
        source.last_sync_commit = commit_sha
        source.last_sync_status = "success" if not stats["errors"] else "partial"
        source.last_sync_message = f"Matched {stats['matched'] + stats['updated']}/{len(devices)} devices from {stats['files_found']} files"

        await session.commit()

    except Exception as e:
        logger.error(f"Config sync failed: {e}")
        source.last_sync_status = "failed"
        source.last_sync_message = str(e)
        source.last_sync_at = now
        await session.commit()
        stats["errors"].append(str(e))

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return stats


def _build_clone_url(repo_url: str, auth_token: str | None) -> str:
    """Build authenticated clone URL."""
    if not auth_token:
        return repo_url
    # For HTTPS repos, inject token
    if repo_url.startswith("https://"):
        # https://github.com/... → https://token@github.com/...
        return repo_url.replace("https://", f"https://{auth_token}@")
    return repo_url


def _build_device_context(device: Device) -> dict:
    """Build context dict for path template rendering."""
    return {
        "device": {
            "hostname": device.hostname,
            "management_ip": str(device.management_ip) if device.management_ip else "",
            "serial_number": device.serial_number,
            "admin_state": device.admin_state,
            "tags": device.tags or {},
        },
        "platform": {
            "name": device.device_model.platform.name if device.device_model and device.device_model.platform else "cisco_ios",
        },
        "model": {
            "name": device.device_model.name if device.device_model else "generic",
            "display_name": device.device_model.display_name if device.device_model else "Generic",
        },
    }
