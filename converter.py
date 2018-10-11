
import argparse
import os
import glob
import subprocess
import sys

# subprocess.popen()
# for line in sys.stdin

"""

# Determine how many pages in the file $1
pages=$(pdfinfo $1 | grep -i pages | awk '{print $2}')
let pages=$pages-1

# Create a range 0-pages
range="seq 0 $pages"

# Create list of array indexed files
temp_name='ocr_dump_temp'
rm $file_name-modified.pdf > /dev/null
seq 0 $pages | parallel -k -j+0 "convert -density 300 \"$1[{}]\" -background white -alpha Off -depth 8 tiff:- | tesseract stdin stdout pdf" | pdfjoin /dev/stdin --outfile "$file_name-ocr.txt"

# Splice pdf pages created in parallel
# pdfjoin $temp_name*.pdf --outfile "$file_name-ocr.pdf"

# Cleanup
# rm $temp_name*.pdf
"""


def get_pages(path):
    cmd = subprocess.Popen(['pdfinfo', path], stdout=subprocess.PIPE)
    cmd2 = subprocess.Popen(['grep', '-i', 'pages'],
                            stdin=cmd.stdout, stdout=subprocess.PIPE)
    # cmd.wait(timeout=300)
    cmd3 = subprocess.check_output(['awk', "{print $2}"], stdin=cmd2.stdout)
    # cmd2.wait(timeout=300)

    return int(cmd3)


def parse(path, threads):
    pages = get_pages(path) - 1
    parallel_cmd = "convert -density 300 \'%s[{}]\' -background white -alpha Off -depth 8 tiff:- | tesseract stdin %s-ocr-temp{} pdf 2>/dev/null"
    parallel_cmd = parallel_cmd % (path, path.split('.')[0])

    cmd = subprocess.Popen(['seq', '0', str(pages)], stdout=subprocess.PIPE)
    cmd2 = subprocess.Popen(
        [
            'parallel',
            '-k',
            '--bar',
            '--progress',
            '-j',
            threads,
            parallel_cmd
        ],
        stdin=cmd.stdout
    )
    cmd.stdout.close()
    output = cmd2.communicate()
    return


def merge(path, dest):
    temp_files = sorted(glob.glob("%s-ocr-temp*.pdf" % path.split('.')[0]))
    cmd = subprocess.Popen(['pdfjoin'] + temp_files +
                           ['--outfile', dest], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cmd.wait()
    print("Done: %s" % dest)

    # Cleanup
    for f in glob.glob("%s-ocr-temp*.pdf" % path.split('.')[0]):
        os.remove(f)
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="""
        Convert PDF files to OCR PDF with multithreading. Uses GNU parallel
        to multithread individual pages through the tesseract OCR tool.
        """
    )

    parser.add_argument(
        'file',
        type=str,
        default=None,
        nargs=1,
        help='PDF file to read. If not supplied, use stdin'
    )

    parser.add_argument(
        '--threads', '-t',
        default=0,
        type=int,
        nargs=1,
        help='Number of parallel threads. Defaults to one thread per core.'
    )

    parser.add_argument(
        '--outfile', '-o',
        type=str,
        default=None,
        nargs=1,
        help='The destination file. If not supplied, append "ocr" to input.'
    )

    parser.add_argument(
        '--pipe', '-p',
        action='store_true',
        help='Pipe the resulting pdf to stdout.'
    )

    args = parser.parse_args()

    # Parallel takes +0 to mean one thread per core
    threads = str(args.threads) if args.threads else '+0'
    file_name = args.file[0].split('.')[0]
    out = args.outfile[0] if args.outfile else file_name + '-ocr.pdf'

    parse(args.file[0], threads)
    merge(args.file[0], out)
