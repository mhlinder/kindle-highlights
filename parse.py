
import argparse
import codecs
import collections
import json
import re
import textwrap

parser = argparse.ArgumentParser()
parser.add_argument('-w', '--write-file',
                    help = 'Write to a file',
                    action = 'store_true')
parser.add_argument('-j', '--json',
                    help = 'Generate JSON',
                    action = 'store_true')
                    
args = parser.parse_args()

def main(outbase = 'bib', json = False):
    bib = init_sources()
    if json:
        if outbase is None:
            print(bib.get_json())
        else:
            outfile = '{}.json'.format(outbase)
            print("Saving to file '{}'".format(outfile))
            with codecs.open(outfile, 'w', encoding = 'utf-8') as f:
                bib.get_json(f)
    else:
        if outbase is None:
            bib.print()
        else:
            outfile = '{}.txt'.format(outbase)
            print("Saving to file '{}'".format(outfile))
            bib.print(outfile)

def fill(s, width = 70, break_long_words = False, indent = 0):
    return textwrap.fill(s, width = width - indent,
                         break_long_words = break_long_words,
                         initial_indent = ' ' * indent,
                         subsequent_indent = ' ' * indent)

## Parse "My Clippings.txt" downloaded from Kindle
def init_sources(infile = 'My Clippings.txt'):
    with open(infile) as f:
        raw = f.read()

    def parse_hl(hl):
        return[line.rstrip() for line in hl.split('\n') if line != '']
    all_hl = [parse_hl(hl) for hl in raw.split(newline('==========', 1, 1)) if hl != '']

    bibliography = Bibliography()
    for hl in all_hl:
        citation = hl[0]
        location = hl[1]
        lines = hl[2:]
        # # Lines of code are, obviously, improperly formatted; but
        # # short of introducing a hard break via <br />, there doesn't
        # # seem to be a good way to force proper formatting, and that
        # # doesn't catch all edge cases.
        # for i in range(1, len(lines)):
        #     if re.search('^  ', lines[i]):
        #         lines[i-1] = '{}<br />'.format(lines[i-1])
        text = '\n'.join(lines)
        if re.search('Highlight', location):
            bibliography.add_hl(citation, location, text)
    bibliography.parse_segments()
    return bibliography

def newline(s, l = 0, r = 0):
    return '{0}{1}{2}'.format(l * '\n',
                              s,
                              r * '\n')

class Bibliography:
    def __init__(self):
        self.sources = {}
        self.citations = []
        self.nsource = 0
        self.seen = collections.defaultdict(lambda: False)

    def _add_source(self, citation):
        if not self.seen[citation]:
            self.seen[citation] = True
            self.sources[citation] = Source(citation)
            self.citations.append(citation)
            self.nsource = self.nsource + 1

    def add_hl(self, citation, location, text):
        self._add_source(citation)
        hl = Highlight(citation, location, text)
        self.sources[citation].add_hl(hl)

    def get_citations(self):
        return sorted(self.citations)

    def get_json(self, f = None):
        bib = {}
        for citation in self.citations:
            source = self.sources[citation]
            s = []
            for segment in source.segments:
                seg = {'Start' : segment.start,
                       'End'   : segment.end,
                       'Text'  : segment.text}
                s.append(seg)
            bib[citation] = s
        if f is None:
            return json.dumps(bib, sort_keys = True, indent = 4, ensure_ascii = False)
        else:
            json.dump(bib, f, sort_keys = True, indent = 4, ensure_ascii = False)
            
    def get_source(self, citation):
        return self.sources[citation]

    def parse_segments(self):
        for citation in self.citations:
            self.sources[citation].parse_segments()

    def print(self, outfile = None):
        if outfile is None:
            fpointer = None
        else:
            fpointer = codecs.open(outfile, 'w', encoding = 'utf-8')

        citations = self.get_citations()
        for citation in citations:
            self.sources[citation].print(fpointer)

        if outfile is not None:
            fpointer.close()

class Highlight:
    def __init__(self, citation, location, text):        
        self.citation = citation

        ## Remove copy text, and page number (if any)
        re_list = ['- Your Highlight on (page [0-9]+ \| )*Location ',
                   'Added on ']
        metadata = re.sub('|'.join(re_list), '', location).split(' | ')

        ## Highlight range endpoints
        loc = metadata[0].split('-')
        self.start = int(loc[0])
        self.end   = int(loc[1])

        ## Parse datetime
        datetime = metadata[1].split(', ')
        datetime = datetime[:-1] + datetime[-1].split(' ')

        months = {
            'January'   : 1,
            'February'  : 2,
            'March'     : 3,
            'April'     : 4,
            'May'       : 5,
            'June'      : 6,
            'July'      : 7,
            'August'    : 8,
            'September' : 9,
            'October'   : 10,
            'November'  : 11,
            'December'  : 12
        }

        ## Parse date
        d = datetime[:3]
        ## Split month and day
        d = d[:1] + d[1].split(' ') + d[2:]
        ## Convert month to integer
        d[1] = months[d[1]]
        ## Format day, year
        d[2] = int(d[2])
        d[3] = int(d[3])
        date = dict(zip(['DoW', 'Month', 'Day', 'Year'], d))

        t = [int(x) for x in datetime[3].split(':')]
        if datetime[4] == 'PM':
            t[0] = t[0] + 12
        time = dict(zip(['Hour', 'Minute', 'Second'], t))

        self.timestamp = ' '.join(['{0:04d}-{1:02d}-{2:02d}'.format(date['Year'],
                                                                    date['Month'],
                                                                    date['Day']),
                                   '{0:02d}:{1:02d}:{2:02d}'.format(time['Hour'],
                                                                    time['Minute'],
                                                                    time['Second'])])
        ## Remove unicode characters
        # self.text = text.replace(u'\u2018', '"').replace(u'\u2019', '"')
        self.text = text
        
class Source:
    def __init__(self, citation):
        self.all_hl = []
        self.locations = collections.defaultdict(list)
        self.indexes = []
        self.nhl = 0
        self.citation = citation
        self.segments = []

    def add_hl(self, hl):
        self.all_hl.append(hl)
        self.nhl = self.nhl + 1
        for offset in range(hl.start, hl.end+1):
            ## self.nhl is the index for the most recent highlight
            self.locations[offset].append(self.nhl)
            if offset not in self.indexes:
                self.indexes.append(offset)

    def parse_segments(self):
        locs = sorted(self.indexes)
        nloc = len(locs)
        
        i = 0
        l = locs[i]
        s = [l]
        s_ix = self.locations[l]
        
        while i < nloc - 1:
            i0 = i
            l0 = l
            
            i = i+1
            l = locs[i]

            if l - l0 == 1:
                s.append(l)
                ix = self.locations[l]
                for index in ix:
                    if index not in s_ix:
                        s_ix.append(index)
            else:
                s_ix.sort()
                hl = self.all_hl[max(s_ix)-1]
                self.segments.append(Segment(s, s_ix, hl))
                s = [l]
                s_ix = self.locations[l]
                
        s_ix.sort()
        hl = self.all_hl[max(s_ix)-1]
        self.segments.append(Segment(s, s_ix, hl))

    def print(self, fpointer, indent = 2):
        title = fill(self.citation, indent = indent)
        rule = '-' * (max([len(l) for l in title.split('\n')]) + indent)
        if fpointer is None:
            print(newline(rule, l = 1))
            print(title)
            print(newline(rule, r = 1))
        else:
            fpointer.write(newline(rule, l = 1, r = 1))
            fpointer.write(newline(format(title), r = 1))
            fpointer.write(newline(rule, r = 1))

        for segment in self.segments:
            segment.print(fpointer)
                

class Segment:
    def __init__(self, locations, members, hl):
        self.locations = locations
        self.start = hl.start
        self.end = hl.end
        self.timestamp = hl.timestamp
        self.text = hl.text

    def print(self, fpointer):
        text = "'{0}' ({1}-{2}, {3})".format(self.text, self.start, self.end, self.timestamp)
        text = fill(text)
        if fpointer is None:
            print(newline(text, r = 1))
        else:
            fpointer.write(newline(text, l = 1, r = 1))

if __name__ == '__main__':
    if args.json:
        if args.write_file:
            main(json = True)
        else:
            main(outbase = None, json = True)
        pass
    else:
        if args.write_file:
            main()
        else:
            main(outbase = None)
