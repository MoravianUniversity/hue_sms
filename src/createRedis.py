"""Legacy entry point — prefer: python -m hue_sms.cli.createRedis"""

from hue_sms.cli.createRedis import go

if __name__ == "__main__":
    go()
