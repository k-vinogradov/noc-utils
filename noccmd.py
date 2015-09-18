import argparse
import os


def load_config():
    from ConfigParser import SafeConfigParser

    config_filename = os.path.dirname(os.path.realpath(__file__)) + 'noccmd.conf'

    config = SafeConfigParser()
    if len(config.read(config_filename)) == 0:
        raise IOError('Couldn\'t read configuration from {0}'.format(config_filename))


if __name__ == '__main__':
    load_config()
