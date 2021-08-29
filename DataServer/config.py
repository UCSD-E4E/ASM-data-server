import yaml


class Config:
    required_keys = [
        'data_dir'
    ]

    def __init__(self, path: str):
        with open(path, 'r') as stream:
            self.__tree = yaml.safe_load(stream=stream)
        for key in self.required_keys:
            if key not in self.__tree:
                raise RuntimeError((f"Key {key} not found in configuration at",
                                    f" {path}"))

    def getDataDir(self):
        return self.__tree['data_dir']
