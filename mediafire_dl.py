#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import os
import os.path as osp
import re
import shutil
import sys
import tempfile
import requests
import six
import tqdm

def time_formatter(milliseconds: int) -> str:
    """Inputs time in milliseconds, to get beautified time,
    as string"""
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    weeks, days = divmod(days, 7)
    tmp = (
        ((str(weeks) + "w:") if weeks else "")
        + ((str(days) + "d:") if days else "")
        + ((str(hours) + "h:") if hours else "")
        + ((str(minutes) + "m:") if minutes else "")
        + ((str(seconds) + "s:") if seconds else "")
    )
    if tmp.endswith(":"):
        return tmp[:-1]
    else:
        return tmp
    
def humanbytes(size):
    if size in [None, ""]:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]:
        if size < 1024:
            break
        size /= 1024
    return f"{size:.2f} {unit}"

CHUNK_SIZE = 512 * 1024  # 512KB

def extractDownloadLink(contents):
    for line in contents.splitlines():
        m = re.search(r'href="((http|https)://download[^"]+)', line)
        if m:
            return m.groups()[0]

def download(url, output, quiet, sender_id):
    url_origin = url
    sess = requests.session()

    while True:
        res = sess.get(url, stream=True)
        if 'Content-Disposition' in res.headers:
            # This is the file
            break

        # Need to redirect with confiramtion
        url = extractDownloadLink(res.text)

        if url is None:
            print('Permission denied: %s' % url_origin, file=sys.stderr)
            print(
                "Maybe you need to change permission over "
                "'Anyone with the link'?",
                file=sys.stderr,
            )
            return

    if output is None:
        m = re.search(
            'filename="(.*)"', res.headers['Content-Disposition']
        )
        output = m.groups()[0]
        # output = osp.basename(url)

    output_is_path = isinstance(output, six.string_types)

    if not quiet:
        print('Downloading...', file=sys.stderr)
        print('From:', url_origin, file=sys.stderr)
        print(
            'To:',
            osp.abspath(output) if output_is_path else output,
            file=sys.stderr,
        )

    if output_is_path:
        tmp_file = tempfile.mktemp(
            suffix=tempfile.template,
            prefix=osp.basename(output),
            dir=osp.dirname(output),
        )
        f = open(tmp_file, 'wb')
    else:
        tmp_file = None
        f = output

    try:
        total = res.headers.get('Content-Length')
        if total is not None:
            total = int(total)
        if not quiet:
            start_dl = time.time()
            downloaded = []
            for chunk in res.iter_content(chunk_size=CHUNK_SIZE):
                f.write(chunk)
                for cont in range(len(chunk)):
                    downloaded.append(cont)
                percentage = (int(humanbytes(total)/humanbytes(len(downloaded))))*100
                gross = humanbytes(len(downloaded)) + "~" + humanbytes(total)
                speed = int(humanbytes(len(downloaded))/time_formatter(int((time.time() - start_dl))))
                eta = int((humanbytes(total) - humanbytes(len(downloaded)))/speed)
                msg = f"Downloading {percentage}%\ | {gross} | {speed}, [{eta}]"
                print(msg)
                
        if tmp_file:
            f.close()
            shutil.move(tmp_file, output)
    except IOError as e:
        print(e, file=sys.stderr)
        return
    finally:
        try:
            if tmp_file:
                os.remove(tmp_file)
        except OSError:
            pass
    return output


def main():
    desc = 'Simple command-line script to download files from mediafire'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('url', nargs='+')
    args = parser.parse_args()

    for url in args.url:
        download(url, output=None, quiet=False)


if __name__ == "__main__":
    main()
