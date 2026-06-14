from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path

from services.app_logger import get_logger
from services.vpn_config_service import (
    load_vpn_config,
    resolve_activation_code,
    update_vpn_config,
)

logger = get_logger(__name__)

def _clean(value: object) -> str:
    return str(value or "").strip()


def _escape_double_quotes(value: str) -> str:
    return value.replace('"', '""')


def _escape_ps_single_quotes(value: str) -> str:
    return value.replace("'", "''")


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in values:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _mask_secret(text: str, secret: str) -> str:
    t = text or ""
    s = _clean(secret)
    if s:
        t = t.replace(s, "***")
    return t


def _status_is_connected(text: str) -> bool:
    s = _clean(text).lower()
    if not s:
        return False
    if "not connected" in s:
        return False
    return "connected" in s


def _status_is_disconnected(text: str) -> bool:
    s = _clean(text).lower()
    if not s:
        return False
    if "not connected" in s:
        return True
    if "disconnected" in s:
        return True
    return False


def _resolve_cli_binary(cli_dir_from_config: str = "") -> dict:
    candidates: list[str] = []

    cfg_dir = _clean(cli_dir_from_config)
    if cfg_dir:
        candidates.append(cfg_dir)

    pf = _clean(os.getenv("ProgramFiles"))
    pf86 = _clean(os.getenv("ProgramFiles(x86)"))

    if pf:
        candidates.append(str(Path(pf) / "ExpressVPN"))
        candidates.append(str(Path(pf) / "ExpressVPN" / "services"))
    if pf86:
        candidates.append(str(Path(pf86) / "ExpressVPN"))
        candidates.append(str(Path(pf86) / "ExpressVPN" / "services"))

    candidates.append(r"C:\Program Files\ExpressVPN")
    candidates.append(r"C:\Program Files\ExpressVPN\services")
    candidates.append(r"C:\Program Files (x86)\ExpressVPN")
    candidates.append(r"C:\Program Files (x86)\ExpressVPN\services")

    search_dirs = _dedupe_keep_order(candidates)

    exe_names = [
        "expressvpnctl.exe",
        "expressvpnctl",
        "ExpressVPN.CLI.exe",
        "ExpressVPN.CLI",
    ]

    checked: list[str] = []
    for folder in search_dirs:
        p = Path(folder)
        if not p.exists() or not p.is_dir():
            continue

        for exe_name in exe_names:
            exe_path = p / exe_name
            checked.append(str(exe_path))
            if exe_path.exists():
                logger.info("vpn cli resolved cli_dir=%s cli_exe=%s", str(p), str(exe_path))
                return {
                    "ok": True,
                    "cli_dir": str(p),
                    "cli_exe": str(exe_path),
                    "checked": checked,
                    "search_dirs": search_dirs,
                }

    logger.warning("vpn cli not found cfg_dir=%s checked_count=%s", cfg_dir, len(checked))
    return {
        "ok": False,
        "message": "expressvpnctl/ExpressVPN.CLI 실행 파일을 찾지 못했습니다.",
        "checked": checked,
        "search_dirs": search_dirs,
    }


def _run_cmd_non_admin(cli_dir: str, command_line: str, timeout_sec: int) -> dict:
    script = f'cd /d "{_escape_double_quotes(cli_dir)}" && {command_line}'
    try:
        proc = subprocess.run(
            ["cmd.exe", "/c", script],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        output = "\n".join([_clean(proc.stdout), _clean(proc.stderr)]).strip()
        return {"ok": proc.returncode == 0, "return_code": int(proc.returncode), "output": output}
    except subprocess.TimeoutExpired:
        return {"ok": False, "return_code": -1, "output": "timeout"}
    except Exception as exc:
        return {"ok": False, "return_code": -1, "output": str(exc)}


def _run_cmd_admin(cli_dir: str, command_line: str, timeout_sec: int) -> dict:
    tmp = tempfile.NamedTemporaryFile(prefix="vpn_admin_", suffix=".log", delete=False)
    tmp_path = tmp.name
    tmp.close()

    cmd_script = (
        f'cd /d "{_escape_double_quotes(cli_dir)}" && '
        f'{command_line} > "{_escape_double_quotes(tmp_path)}" 2>&1'
    )

    ps_script = (
        f"$cmd='{_escape_ps_single_quotes(cmd_script)}'; "
        "$p = Start-Process -FilePath 'cmd.exe' "
        "-Verb RunAs "
        "-WindowStyle Hidden "
        "-ArgumentList @('/c', $cmd) "
        "-Wait -PassThru; "
        "exit $p.ExitCode"
    )

    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=timeout_sec + 30,
            check=False,
        )

        file_output = ""
        try:
            file_output = Path(tmp_path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            file_output = ""

        parent_output = "\n".join([_clean(proc.stdout), _clean(proc.stderr)]).strip()
        merged = "\n".join([_clean(file_output), parent_output]).strip()

        return {"ok": proc.returncode == 0, "return_code": int(proc.returncode), "output": merged}
    except subprocess.TimeoutExpired:
        return {"ok": False, "return_code": -1, "output": "timeout(admin)"}
    except Exception as exc:
        return {"ok": False, "return_code": -1, "output": str(exc)}
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass


def _execute_cli(
    cli_dir: str,
    cli_exe: str,
    args: list[str],
    run_as_admin: bool,
    timeout_sec: int,
    mask_secret: str = "",
) -> dict:
    cmd_line = subprocess.list2cmdline([cli_exe] + args)
    runner = _run_cmd_admin if run_as_admin else _run_cmd_non_admin
    result = runner(cli_dir, cmd_line, timeout_sec)

    safe_cmd = _mask_secret(cmd_line, mask_secret)
    safe_output = _mask_secret(_clean(result.get("output")), mask_secret)

    logger.info(
        "vpn exec command=%s ok=%s return_code=%s",
        safe_cmd,
        bool(result.get("ok")),
        int(result.get("return_code", -1)),
    )
    
    if not bool(result.get("ok")):
        logger.warning("vpn exec failed output=%s", safe_output[:300])
    
    return {
        "ok": bool(result.get("ok")),
        "return_code": int(result.get("return_code", -1)),
        "command": safe_cmd,
        "output": safe_output,
    }


def _looks_like_already_logged_in(output: str) -> bool:
    s = _clean(output).lower()
    hints = [
        "already logged",
        "already signed",
        "already activated",
        "already have an account",
    ]
    return any(h in s for h in hints)


def _resolve_existing_file_path(value: str) -> str:
    v = _clean(value)
    if not v:
        return ""
    expanded = os.path.expandvars(os.path.expanduser(v))
    p = Path(expanded)
    if p.exists() and p.is_file():
        return str(p)
    return ""


def _try_login_with_tempfile(
    cli_dir: str,
    cli_exe: str,
    run_as_admin: bool,
    timeout_sec: int,
    activation_code: str,
) -> dict:
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".txt",
        delete=False,
        newline="\n",
    )
    login_file = tmp.name
    try:
        tmp.write(_clean(activation_code) + "\n")
        tmp.close()

        return _execute_cli(
            cli_dir=cli_dir,
            cli_exe=cli_exe,
            args=["login", login_file],
            run_as_admin=run_as_admin,
            timeout_sec=timeout_sec,
            mask_secret=activation_code,
        )
    finally:
        try:
            Path(login_file).unlink(missing_ok=True)
        except Exception:
            pass


def _try_login_with_activation_value(
    cli_dir: str,
    cli_exe: str,
    run_as_admin: bool,
    timeout_sec: int,
    activation_value: str,
) -> dict:
    file_path = _resolve_existing_file_path(activation_value)
    if file_path:
        return _execute_cli(
            cli_dir=cli_dir,
            cli_exe=cli_exe,
            args=["login", file_path],
            run_as_admin=run_as_admin,
            timeout_sec=timeout_sec,
        )

    return _try_login_with_tempfile(
        cli_dir=cli_dir,
        cli_exe=cli_exe,
        run_as_admin=run_as_admin,
        timeout_sec=timeout_sec,
        activation_code=activation_value,
    )


def _auto_disable_activate_before_publish() -> tuple[bool, str]:
    try:
        result = update_vpn_config({"activate_before_publish": False})
        if result.get("ok"):
            return True, "activate_before_publish=false saved"
        return False, str(result.get("message", "save failed"))
    except Exception as exc:
        return False, str(exc)


def _try_login_only(
    cli_dir: str,
    cli_exe: str,
    run_as_admin: bool,
    timeout_sec: int,
    activation_code_or_file: str,
) -> tuple[bool, list[dict], bool]:
    
    logger.info("vpn login attempt start run_as_admin=%s timeout_sec=%s", run_as_admin, timeout_sec)
    attempts: list[dict] = []

    login_res = _try_login_with_activation_value(
        cli_dir=cli_dir,
        cli_exe=cli_exe,
        run_as_admin=run_as_admin,
        timeout_sec=timeout_sec,
        activation_value=activation_code_or_file,
    )
    attempts.append(login_res)
    
    logger.info(
        "vpn login attempt result ok=%s return_code=%s",
        login_res.get("ok"),
        login_res.get("return_code"),
    )

    # True면 "이번 요청에서 login 성공/already 상태 확인됨"
    if login_res["ok"] or _looks_like_already_logged_in(login_res.get("output", "")):
        return True, attempts, True

    return False, attempts, False


def ensure_vpn_connected_before_publish(activation_code_override: str = "", trace_id: str = "") -> dict:
    trace = _clean(trace_id) or "-"
    logger.info("[trace_id=%s] ensure_vpn_connected_before_publish start", trace)
    
    cfg = load_vpn_config()
    if not bool(cfg.get("enabled", False)):
        logger.info("[trace_id=%s] vpn skipped: disabled", trace)
        return {"ok": True, "skipped": True, "message": "VPN disabled"}

    resolved_cli = _resolve_cli_binary(_clean(cfg.get("cli_dir")))
    if not resolved_cli.get("ok"):
        logger.warning("[trace_id=%s] vpn precheck failed: cli not found", trace)
        return {
            "ok": False,
            "message": resolved_cli.get("message", "VPN CLI not found"),
            "debug": resolved_cli,
        }

    cli_dir = _clean(resolved_cli.get("cli_dir"))
    cli_exe = _clean(resolved_cli.get("cli_exe"))
    run_as_admin = bool(cfg.get("run_as_admin", True))
    timeout_sec = int(cfg.get("command_timeout_sec", 120))
    connect_location = _clean(cfg.get("connect_location")) or "smart"

    debug_steps: list[dict] = []
    auto_updated = False
    auto_update_message = ""

    activation_value = resolve_activation_code(activation_code_override)
    should_login = bool(cfg.get("activate_before_publish", True)) and bool(activation_value)

    logger.info(
        "[trace_id=%s] vpn precheck config run_as_admin=%s should_login=%s connect_location=%s timeout_sec=%s",
        trace,
        run_as_admin,
        should_login,
        connect_location,
        timeout_sec,
    )

    if should_login:
        auth_ok, auth_attempts, login_done = _try_login_only(
            cli_dir=cli_dir,
            cli_exe=cli_exe,
            run_as_admin=run_as_admin,
            timeout_sec=timeout_sec,
            activation_code_or_file=activation_value,
        )
        debug_steps.extend(auth_attempts)

        if not auth_ok:
            last_output = ""
            if auth_attempts:
                try:
                    last_output = str(auth_attempts[-1].get("output", ""))
                except Exception:
                    last_output = ""
            logger.warning("[trace_id=%s] vpn auth(login) failed output=%s", trace, last_output[:300])
            return {
                "ok": False,
                "message": "VPN auth(login) failed",
                "debug": {
                    "steps": debug_steps,
                },
            }

        # login이 성공하거나 already 상태면 이후 자동 로그인 비활성화
        if login_done:
            saved_ok, saved_msg = _auto_disable_activate_before_publish()
            auto_updated = saved_ok
            auto_update_message = saved_msg
            logger.info(
                "[trace_id=%s] vpn auto disable activate_before_publish result ok=%s note=%s",
                trace,
                auto_updated,
                auto_update_message,
            )

    connect_args = ["connect", "smart"] if connect_location.lower() == "smart" else ["connect", connect_location]
    logger.info("[trace_id=%s] vpn connect start args=%s", trace, connect_args)
    
    connect_res = _execute_cli(
        cli_dir=cli_dir,
        cli_exe=cli_exe,
        args=connect_args,
        run_as_admin=run_as_admin,
        timeout_sec=timeout_sec,
    )
    debug_steps.append(connect_res)
    logger.info(
        "[trace_id=%s] vpn connect result ok=%s return_code=%s",
        trace,
        connect_res.get("ok"),
        connect_res.get("return_code"),
    )
    
    if not connect_res["ok"]:
        return {
            "ok": False,
            "message": "VPN connect failed",
            "debug": {
                "steps": debug_steps,
            },
        }

    settle_wait = int(cfg.get("settle_wait_sec", 3))
    if settle_wait > 0:
        time.sleep(settle_wait)

    status_res = _execute_cli(
        cli_dir=cli_dir,
        cli_exe=cli_exe,
        args=["status"],
        run_as_admin=run_as_admin,
        timeout_sec=min(60, max(10, timeout_sec)),
    )
    debug_steps.append(status_res)

    is_connected = _status_is_connected(status_res.get("output", ""))
    logger.info(
        "[trace_id=%s] vpn status result connected=%s output=%s",
        trace,
        is_connected,
        str(status_res.get("output", ""))[:200],
    )

    if not _status_is_connected(status_res.get("output", "")):
        return {
            "ok": False,
            "message": "VPN status is not connected",
            "debug": {
                "steps": debug_steps,
            },
        }

    logger.info("[trace_id=%s] ensure_vpn_connected_before_publish success", trace)
    return {
        "ok": True,
        "message": "VPN connected",
        "auto_login_disabled": auto_updated,  # True면 이번에 자동으로 false로 바뀜
        "auto_login_note": auto_update_message,
        "debug": {
            "steps": debug_steps,
        },
    }


def disconnect_vpn_after_publish(trace_id: str = "") -> dict:
    trace = _clean(trace_id) or "-"
    logger.info("[trace_id=%s] disconnect_vpn_after_publish start", trace)
    
    cfg = load_vpn_config()
    if not bool(cfg.get("enabled", False)):
        logger.info("[trace_id=%s] disconnect skipped: vpn disabled", trace)
        return {"ok": True, "skipped": True, "message": "VPN disabled"}

    resolved_cli = _resolve_cli_binary(_clean(cfg.get("cli_dir")))
    if not resolved_cli.get("ok"):
        logger.warning("[trace_id=%s] disconnect failed: cli not found", trace)
        return {
            "ok": False,
            "message": resolved_cli.get("message", "VPN CLI not found"),
            "debug": resolved_cli,
        }

    cli_dir = _clean(resolved_cli.get("cli_dir"))
    cli_exe = _clean(resolved_cli.get("cli_exe"))
    run_as_admin = bool(cfg.get("run_as_admin", True))
    timeout_sec = int(cfg.get("command_timeout_sec", 120))

    debug_steps: list[dict] = []

    disconnect_res = _execute_cli(
        cli_dir=cli_dir,
        cli_exe=cli_exe,
        args=["disconnect"],
        run_as_admin=run_as_admin,
        timeout_sec=timeout_sec,
    )
    debug_steps.append(disconnect_res)
    logger.info(
        "[trace_id=%s] vpn disconnect command result ok=%s return_code=%s",
        trace,
        disconnect_res.get("ok"),
        disconnect_res.get("return_code"),
    )

    status_res = _execute_cli(
        cli_dir=cli_dir,
        cli_exe=cli_exe,
        args=["status"],
        run_as_admin=run_as_admin,
        timeout_sec=min(60, max(10, timeout_sec)),
    )
    debug_steps.append(status_res)
    
    is_disconnected = _status_is_disconnected(status_res.get("output", ""))
    logger.info(
        "[trace_id=%s] vpn disconnect status disconnected=%s output=%s",
        trace,
        is_disconnected,
        str(status_res.get("output", ""))[:200],
    )

    if _status_is_disconnected(status_res.get("output", "")):
        return {
            "ok": True,
            "message": "VPN disconnected",
            "debug": {
                "steps": debug_steps,
            },
        }

    logger.warning("[trace_id=%s] disconnect_vpn_after_publish failed", trace)
    return {
        "ok": False,
        "message": "VPN disconnect failed",
        "debug": {
            "steps": debug_steps,
        },
    }
