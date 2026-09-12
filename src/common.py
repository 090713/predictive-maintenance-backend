from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import traceback
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def json_default(obj):
    if isinstance(obj, np.integer): return int(obj)
    if isinstance(obj, np.floating): return float(obj)
    if isinstance(obj, np.ndarray): return obj.tolist()
    if isinstance(obj, Path): return str(obj)
    if isinstance(obj, datetime): return obj.isoformat()
    raise TypeError(type(obj).__name__)

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=json_default, allow_nan=False), encoding='utf-8')

def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def config(name):
    path = Path(os.getenv('PM_CONFIG_DIR', str(ROOT/'configs'))) / f'{name}.yaml'
    return yaml.safe_load(path.read_text(encoding='utf-8'))

def log_event(filename, **event):
    directory = Path(os.getenv('PM_LOG_DIR', str(ROOT/'logs')))
    directory.mkdir(parents=True, exist_ok=True)
    with (directory/filename).open('a', encoding='utf-8') as f:
        f.write(json.dumps({'timestamp': utc_now(), **event}, default=json_default, allow_nan=False)+'\n')

def log_error(stage, exc):
    log_event('error.log', stage=stage, exception_type=type(exc).__name__, message=str(exc), traceback=''.join(traceback.format_exception(type(exc),exc,exc.__traceback__)))

@contextmanager
def stage(name):
    started = time.perf_counter()
    log_event('training.log', stage=name, status='started')
    try:
        yield
    except Exception as exc:
        log_error(name, exc)
        raise
    else:
        log_event('training.log', stage=name, status='completed', duration_seconds=time.perf_counter()-started)

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
