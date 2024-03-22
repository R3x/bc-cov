import subprocess

from bccov.utils.pylogger import get_logger

logger = get_logger("utils.command")


def run_cmd(
    command,
    env=None,
    cwd=None,
    verbose=False,
    timeout=25 * 60,
    error_msg="",
    raise_timeout=False,
):
    try:
        logger.debug(f"Running command : {command}\n with {cwd} and {env}")
        out = subprocess.run(
            command,
            env=env,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if verbose:
            print(f"STDOUT has {out.stdout.decode('latin-1')}")
            print(f"STDERR has {out.stderr.decode('latin-1')}")
        logger.debug(f"STDOUT has {out.stdout.decode('latin-1')}")
        logger.debug(f"STDERR has {out.stderr.decode('latin-1')}")
        return out.stdout.decode("latin-1"), out.stderr.decode("latin-1")
    except subprocess.TimeoutExpired as e:
        logger.error(
            f"The {error_msg} Command Timed out", extra={"cmd": command, "error": e}
        )
        return "", ""
    except Exception as e:
        logger.exception(f"{error_msg} failed", extra={"cmd": command, "error": e})
