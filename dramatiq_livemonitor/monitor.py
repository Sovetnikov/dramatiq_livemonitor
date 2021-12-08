from livelock.client import LiveLock

from dramatiq_livemonitor.middleware import LiveMonitorMiddleware as MD


class DramatiqMonitor(object):
    @classmethod
    def workers(cls):
        result = []
        for item in LiveLock.find(MD.worker_lock_prefix+MD.lock_fields_separator+'*'):
            worker = MD.decode_worker_lock_id(item['lock_id'])
            worker['start_time'] = item['start_time']
            result.append(worker)
        return result

    @classmethod
    def tasks(cls):
        result = []
        for item in LiveLock.find(MD.actor_lock_prefix+MD.lock_fields_separator+'*'):
            task = MD.decode_message_lock_id(item['lock_id'])
            task['start_time'] = item['start_time']
            result.append(task)
        return result
