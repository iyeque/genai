from collections import deque
from typing import Any, Optional

class Channel:
    def __init__(self, buffer_size: Optional[int] = None):
        self.buffer_size = buffer_size
        self.queue = deque()
        self.waiting_senders = deque()
        self.waiting_receivers = deque()

    def send(self, value: Any):
        if self.buffer_size is None or len(self.queue) < self.buffer_size:
            self.queue.append(value)
            if self.waiting_receivers:
                receiver = self.waiting_receivers.popleft()
                receiver.resume(value)
        else:
            # Blocking send
            op = ChannelOperation(value)
            self.waiting_senders.append(op)
            return op

    def receive(self):
        if self.queue:
            return self.queue.popleft()
        elif self.waiting_senders:
            sender = self.waiting_senders.popleft()
            value = sender.value
            self.queue.append(value)
            return self.queue.popleft()
        else:
            # Blocking receive
            op = ChannelOperation(None)
            self.waiting_receivers.append(op)
            return op


class ChannelOperation:
    def __init__(self, value: Optional[Any]):
        self.value = value
        self.completed = False

    def resume(self, value: Any):
        self.value = value
        self.completed = True


class Scheduler:
    def __init__(self):
        self.tasks = deque()

    def add_task(self, task: Any):
        self.tasks.append(task)

    def run(self):
        while self.tasks:
            task = self.tasks.popleft()
            try:
                next(task)
                self.tasks.append(task)
            except StopIteration:
                pass