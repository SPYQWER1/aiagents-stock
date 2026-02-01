import os
import sys
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

def setup_logging(
    log_dir: str = "logs",
    log_level: int = logging.INFO,
    console_output: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    rotation_type: str = "size"  # "size" or "time"
) -> None:
    """
    配置全局日志系统。

    Args:
        log_dir: 日志文件存储目录
        log_level: 日志级别
        console_output: 是否输出到控制台
        max_bytes: 单个日志文件最大字节数（用于按大小轮转）
        backup_count: 保留的旧日志文件数量
        rotation_type: 轮转类型，"size" 按大小，"time" 按日期
    """
    # 确保日志目录存在
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 日志文件路径
    log_file = log_path / "aiagents_stock.log"

    # 创建 root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除现有的 handlers，避免重复添加
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 定义日志格式
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 文件 Handler
    if rotation_type == "time":
        # 按每天午夜轮转
        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when="midnight",
            interval=1,
            backupCount=backup_count,
            encoding="utf-8"
        )
    else:
        # 按文件大小轮转 (默认)
        file_handler = RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
    
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    root_logger.addHandler(file_handler)

    # 控制台 Handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        root_logger.addHandler(console_handler)

    # 抑制第三方库的详细日志
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("jieba").setLevel(logging.WARNING)
    logging.getLogger("numexpr").setLevel(logging.WARNING)
    logging.getLogger("pdfminer").setLevel(logging.WARNING)

    # 记录日志系统初始化完成
    logging.info(f"Logging initialized. Log file: {log_file}")

def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的 logger。
    
    Args:
        name: 模块名称
    
    Returns:
        logger 实例
    """
    return logging.getLogger(name)
