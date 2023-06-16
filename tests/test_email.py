import sys
import logging
import yaml
from DataServer.email_sender import email_sender
sys.path.append("../")


def test_email_sent():
    logger = logging.getLogger()
    with open(sys.path[0]+ '/../sample-config.yaml', 'r') as config_stream:
        configDict = yaml.safe_load(config_stream)
    email_sender1 = email_sender(configDict=configDict, logger=logger)
    assert(email_sender1.send_email()==0)