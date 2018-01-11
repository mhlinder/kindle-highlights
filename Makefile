
.PHONY: parse rsync serve 

parse:
	python parse.py --json --write

rsync:
	rsync -aP --exclude '.git/' ./ mhlinder:~/public_html/kindle-clip/

serve:
	python2 -m SimpleHTTPServer 8000
