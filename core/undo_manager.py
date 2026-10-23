"""
Менеджер отмены действий (стек).
"""


class UndoManager:
    def __init__(self, max_size=50):
        self.stack = []
        self.max_size = max_size

    def push(self, action):
        """
        action: dict с полями:
          - type: '1d_points' | '2d_points' | 'segment' | 'pencil'
          - data: любой объект (для восстановления)
        """
        self.stack.append(action)
        if len(self.stack) > self.max_size:
            self.stack.pop(0)

    def pop(self):
        if not self.stack:
            return None
        return self.stack.pop()

    def can_undo(self):
        return len(self.stack) > 0

    def clear(self):
        self.stack.clear()