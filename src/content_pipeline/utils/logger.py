"""Logger — Setup logging JSON."""
import logging, json
from pathlib import Path

class JSONFormatter(logging.Formatter):
    def format(self, record):
        d = {"timestamp":self.formatTime(record),"level":record.levelname,"logger":record.name,"message":record.getMessage(),"module":record.module,"function":record.funcName,"line":record.lineno}
        if record.exc_info: d["exception"] = self.formatException(record.exc_info)
        return json.dumps(d, ensure_ascii=False)

def setup_logger(level="INFO", log_file=None):
    logger = logging.getLogger(); logger.setLevel(getattr(logging, level.upper())); logger.handlers = []
    ch = logging.StreamHandler(); ch.setLevel(logging.DEBUG); ch.setFormatter(JSONFormatter()); logger.addHandler(ch)
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8"); fh.setLevel(logging.DEBUG); fh.setFormatter(JSONFormatter()); logger.addHandler(fh)
