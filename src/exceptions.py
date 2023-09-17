class WrongGenomeAssembly(Exception):
    def __init__(self, msg: str):
        self.msg = msg
        super().__init__(self.msg)


class WrongSignalType(Exception):
    def __init__(self, msg: str):
        self.msg = msg
        super().__init__(self.msg)

class DataNotFound(Exception):
    def __init__(self, msg: str):
        self.msg = msg
        super().__init__(self.msg)
