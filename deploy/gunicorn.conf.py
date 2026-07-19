# gunicorn 生产配置
# 用法: gunicorn -c deploy/gunicorn.conf.py api.app:app

import multiprocessing

# 绑定地址
bind = "0.0.0.0:8898"

# Worker 数量 (CPU * 2 + 1)
workers = min(multiprocessing.cpu_count() * 2 + 1, 8)

# Worker 类型
worker_class = "sync"
threads = 2

# 超时
timeout = 30
graceful_timeout = 10

# 日志
accesslog = "data/access.log"
errorlog = "data/gunicorn_error.log"
loglevel = "warning"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'

# 进程名
proc_name = "marketpulse"

# 安全
limit_request_line = 4094
limit_request_fields = 100

# 重启策略
max_requests = 10000
max_requests_jitter = 1000

# 预加载
preload_app = True
