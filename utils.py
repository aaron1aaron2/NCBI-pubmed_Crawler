import os
import sys
import logging
import traceback

def set_log(path, level=logging.INFO):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    LOG = logging.getLogger(path)
    LOG.setLevel(level)

    # create file handler which logs even debug messages
    fh = logging.FileHandler(path)
    fh.setLevel(level)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(level)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    # add the handlers to the logger
    LOG.addHandler(fh)
    LOG.addHandler(ch)

    return LOG

def get_error_message(e):
    error_class = e.__class__.__name__ #取得錯誤類型
    detail = e.args[0] #取得詳細內容
    cl, exc, tb = sys.exc_info() #取得Call Stack
    lastCallStack = traceback.extract_tb(tb)[-1] #取得Call Stack的最後一筆資料
    fileName, lineNum, funcName = lastCallStack[0], lastCallStack[1], lastCallStack[2]
    errMsg = "File \"{}\", line {}, in {}: [{}] {}".format(fileName, lineNum, funcName, error_class, detail)

    return errMsg