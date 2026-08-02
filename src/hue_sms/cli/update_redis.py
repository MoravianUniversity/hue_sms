import os

from hue_sms.config import SRC_DIR, get_redis


def go():
    r = get_redis()

    log_path = os.path.join(SRC_DIR, "hue_log.log")
    with open(log_path) as logs:
        for line in logs:
            line = line.split(':')
            line = line[-1]

            if line.split()[0].lower() == 'color':
                r.hincrby('color_totals', line.split()[1].lower(), 1)


if __name__ == '__main__':
    go()
