import os, glob
def dump():
	f=open('index.html', 'w')
	f.write('<HTML>')
	f.write('\n')
	path = './status/'
	for infile in glob.glob(os.path.join(path, '*.txt')):
		g=open(infile, 'r')
		for line in g:
			f.write(infile)
			f.write('\t')
			f.write(line)
		g.close()
	f.write('</HTML>')
	f.close()