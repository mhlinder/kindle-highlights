
.PHONY: parse rsync serve 

parse:
	python parse.py --json --write

rsync:
	rsync -aP --exclude '.git/' kindle-clip mhlinder:~/public_html/

serve:
	python2 -m SimpleHTTPServer 8000
