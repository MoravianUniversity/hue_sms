"""Legacy entry point — prefer: python -m hue_sms.cli.update_redis"""

from hue_sms.cli.update_redis import go

if __name__ == "__main__":
    go()
