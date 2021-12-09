import logging
import os
import socket
import threading

from dramatiq import Middleware
from livelock.client import LiveNBLock

logger = logging.getLogger(__name__)

try:
    from sentry_sdk import capture_message, capture_exception
except ImportError:
    def capture_message(*args, **kwargs):
        pass


    def capture_exception(*args, **kwargs):
        pass


class LiveMonitorMiddleware(Middleware):
    lock_fields_separator = ':'
    worker_lock_prefix = 'drwork'
    actor_lock_prefix = 'dract'

    # Middleware object created for every worker process and shared between all threads
    def __init__(self):
        logger.debug('__init__ (PID %s thread %s)', os.getpid(), threading.get_ident())
        self.worker = None
        self.worker_lock = None
        self.storage = threading.local()

    def after_worker_boot(self, broker, worker):
        # Called in worker process main thread
        logger.debug('after_worker_boot (PID %s thread %s)', os.getpid(), threading.get_ident())
        self.worker = worker

        pid = os.getpid()
        hostname = socket.gethostname()
        self.worker_id = f'{hostname}PID{pid}'
        self.worker_queues = '!'.join(self.worker.consumer_whitelist)

        self.worker_lock = LiveNBLock(self.get_worker_lock_id())
        if not self.worker_lock.acquire():
            capture_message('not self.worker_lock.acquire()')

    def after_worker_shutdown(self, broker, worker):
        logger.debug('after_worker_shutdown (PID %s thread %s)', os.getpid(), threading.get_ident())
        if worker != self.worker:
            raise Exception('worker != self.worker')
        if self.worker_lock is not None:
            self.worker_lock.release()

    def before_worker_thread_shutdown(self, broker, thread):
        logger.debug('before_worker_thread_shutdown (PID %s thread %s)', os.getpid(), threading.get_ident())
        if hasattr(self.storage, 'actor_lock') and self.storage.actor_lock:
            self.storage.actor_lock.release()
            self.storage.actor_lock = None

    def after_process_message(self, broker, message, *, result=None, exception=None):
        logger.debug('after_process_message (PID %s thread %s)', os.getpid(), threading.get_ident())

        # if message skipped then self.storage.actor_lock may be not defined
        # if self.storage.actor_lock is not None:
        #     lock_id = self.get_message_lock_id(message)
        #     if self.storage.actor_lock.id != lock_id:
        #         capture_message('self.storage.actor_lock.id != lock_id')
        #         if self.storage.actor_lock:
        #             # locked
        #             pass
        #         else:
        #             capture_message('not locked self.storage.actor_lock')
        # else:
        #     capture_message('not self.storage.actor_lock')

        # Called from worker process, separate worker thread (not main thread)
        if hasattr(self.storage, 'actor_lock') and self.storage.actor_lock is not None:
            self.storage.actor_lock.release()
            self.storage.actor_lock = None

    after_skip_message = after_process_message

    def before_process_message(self, broker, message):
        # Called from worker process, separate worker thread (not main thread)
        logger.debug('before_process_message (PID %s thread %s)', os.getpid(), threading.get_ident())
        if hasattr(self.storage, 'actor_lock') and self.storage.actor_lock is not None:
            capture_message('self.storage.actor_lock is not None in before_process_message')
        lock_id = self.get_message_lock_id(message)
        self.storage.actor_lock = LiveNBLock(lock_id)
        if not self.storage.actor_lock.acquire():
            capture_message('not self.storage.actor_lock.acquire()')

    def get_message_lock_id(self, message):
        actor = message.actor_name
        message_id = message.message_id
        return f'{self.actor_lock_prefix}:{actor}:{message_id}:{self.worker_id}:TID{threading.get_ident()}'

    @classmethod
    def decode_message_lock_id(cls, lock_id):
        _, actor, message_id, host_pid, tid = lock_id.split(':')
        hostname, pid = host_pid.split('PID')
        tid = tid.replace('TID', '')
        return dict(actor=actor, message_id=message_id, worker_id=host_pid, hostname=hostname, pid=int(pid), thread_id=int(tid))

    def get_worker_lock_id(self):
        return f'{self.worker_lock_prefix}:{self.worker_id}:TC{self.worker.worker_threads}:{self.worker_queues}'

    @classmethod
    def decode_worker_lock_id(cls, lock_id):
        _, host_pid, tc, queues = lock_id.split(':')
        hostname, pid = host_pid.split('PID')
        worker_threads = tc.replace('TC', '')
        queues = queues.split('!')
        return dict(hostname=hostname, pid=int(pid), worker_id=host_pid, worker_threads=int(worker_threads), queues=queues)
