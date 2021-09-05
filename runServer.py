import argparse
from DataServer.server import Server

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    server = Server('config.yaml', 'devices.yaml')
    server.run()
