#!/usr/bin/env python 

import optparse
from sys import *
import os,sys,re
from optparse import OptionParser
import glob
import subprocess
from os import system
import linecache
import time
import shutil

#=========================
def setupParserOptions():
        parser = optparse.OptionParser()
        parser.set_usage("%prog -i <stack.img> --ctf=[per particle CTF file] --box=[boxsize] --firstRow=[first] --lastRow[last]")
        parser.add_option("-i",dest="stack",type="string",metavar="FILE",
                help="Raw gold particle stack in .img format (black particles, no normalization)")
	parser.add_option("--ctf",dest="ctf",type="string", metavar="STRING",
                help="Per particle CTF file")
	parser.add_option("--box",dest="box",type="int", metavar="INT",
                help="Box size of particles")
        parser.add_option("-d", action="store_true",dest="debug",default=False,
                help="debug")
        options,args = parser.parse_args()

        if len(args) > 0:
                parser.error("Unknown commandline options: " +str(args))

        if len(sys.argv) < 3:
                parser.print_help()
                sys.exit()
        params={}
        for i in parser.option_list:
                if isinstance(i.dest,str):
                        params[i.dest] = getattr(options,i.dest)
        return params

#=============================
def checkConflicts(params):
        if not params['stack']:
                print "\nWarning: no stack specified\n"
        elif not os.path.exists(params['stack']):
                print "\nError: stack file '%s' does not exist\n" % params['stack']
                sys.exit()
        if params['stack'][-4:] != '.img':
		print 'Stack extension %s is not recognized as .img file' %(params['stack'][-4:])
                sys.exit()

	if os.path.exists('%s.spi' %(params['stack'][:-4])):
		os.remove('%s.spi' %(params['stack'][:-4]))

        if os.path.exists('%s_intensity_vs_defocus.txt' %(params['stack'])):
                print "\nError: output file already exists, exiting.\n"
                sys.exit()

#=============================
def determine_intensity_vs_defocus(params):

	numParts = len(open(params['ctf'],'r').readlines())

	i = 1

	first = (params['box']/2)-1 
	last = (params['box']/2)+1

	while i <= numParts:

		trace = lineTrace('%s' %(params['stack'][:-4]),i,first, last,params['box'])
		traceNoise = lineTrace('%s' %(params['stack'][:-4]),i,first+20, last+20,params['box'])

		df1,df2,astig = getCTF(params['ctf'],i)	

		findMax(trace,'%s_intensity_vs_defocus.txt' %(params['stack'][:-4]),first,last,df1,df2,astig,i)
		findMax(traceNoise,'%s_intensity_vs_defocus_noise.txt' %(params['stack'][:-4]),first+20,last+20,df1,df2,astig,i)
		i = i + 1

#============================
def getCTF(input,particle):

	line = linecache.getline(input,particle)

	l = line.split()

	df1 = l[0]
	df2 = l[1]
	astig = l[2]

	return df1,df2,astig

#=============================
def findMax(input,output,first,last,df1,df2,astig,particle):

	f1 = open(input,'r')
	
	currentPeak = 0
	
	for line in f1: 

		if line[1] is ';':
			continue

		l = line.split()
		stdDev = float(l[3])
		if float(l[0]) >= first:

			if float(l[0]) <= last:

				if float(l[2])*-1 > currentPeak:
					currentPeak = float(l[2])*-1

	if os.path.exists(output) is True:
                o1 = open(output,'a')
                o1.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\n' %(str(particle),str(currentPeak/stdDev),str(currentPeak),str(stdDev),df1,df2,astig))	

	if os.path.exists(output) is False:
		o1 = open(output,'w')
		o1.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\n' %(str(particle),str(currentPeak/stdDev),str(currentPeak),str(stdDev),df1,df2,astig))

#==============================
def lineTrace(stack,particle,first,last,box):

	if os.path.exists('tmp_line_trace1.spi'):
		os.remove('tmp_line_trace1.spi')

	if os.path.exists('tmp_line_trace2.spi'):
                os.remove('tmp_line_trace2.spi')

	spi='FS [b] [f] [avg] [std]\n'
	spi+='%s@%s\n' %(stack,str(particle))
	spi+='AR\n'
	spi+='%s@%s\n' %(stack,str(particle))
	spi+='_9\n'
	spi+='(P1-[avg])\n'
	spi+='FS [e] [r] [avg2] [std2]\n'
	spi+='_9\n'
	spi+='LI D\n'
	spi+='_9\n'
	spi+='tmp_line_trace1\n'	
	spi+='R\n'
	spi+='%f-%f\n' %(first,last)
	spi+=';merge three pixels into single file\n'
	spi+='SD IC NEW\n'
	spi+='incore_doc\n'
	spi+='2,%f\n' %(box)
	spi+='do lb2 [row]=1,%f\n' %(box)
	spi+='[row2]=[row]+%f\n' %(box)
	spi+='[row3]=[row2]+%f\n' %(box)
	spi+='[row4]=[row3]+%f\n' %(box)
	spi+='UD IC [row] [pix1]\n'
	spi+='tmp_line_trace1\n'
	spi+='UD IC [row2] [pix2]\n'
	spi+='tmp_line_trace1\n'
	spi+='UD IC [row3] [pix3]\n'
	spi+='tmp_line_trace1\n'
	spi+='[avg]=([pix1]+[pix2]+[pix3])/3\n'
	spi+='SD IC [row] [avg] [std2]\n'
	spi+='incore_doc\n'
	spi+='lb2\n'
	spi+='UD ICE\n'
	spi+='tmp_line_trace1\n'
	spi+='SD IC COPY\n'
	spi+='incore_doc\n'
	spi+='tmp_line_trace2\n'
	spi+='SD ICE\n'
	spi+='incore_doc\n'
	runSpider(spi)
	
	return 'tmp_line_trace2.spi'

#=============================
def runSpider(lines):
       spifile = "currentSpiderScript.spi"
       if os.path.isfile(spifile):
               os.remove(spifile)
       spi=open(spifile,'w')
       spi.write("MD\n")
       spi.write("TR OFF\n")
       spi.write("MD\n")
       spi.write("VB OFF\n")
       spi.write("MD\n")
       spi.write("SET MP\n")
       spi.write("(8)\n")
       spi.write("\n")
       spi.write(lines)

       spi.write("\nEN D\n")
       spi.close()
       spicmd = "spider spi @currentSpiderScript"
       spiout = subprocess.Popen(spicmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stderr.read()
       output = spiout.strip().split()
       if "ERROR" in output:
               print "Spider Error, check 'currentSpiderScript.spi'\n"
               sys.exit()
       # clean up
       os.remove(spifile)
       if os.path.isfile("LOG.spi"):
               os.remove("LOG.spi")
       resultf = glob.glob("results.spi.*")
       if resultf:
               for f in resultf:
                       os.remove(f)

#==============================
if __name__ == "__main__":

        params=setupParserOptions()
        checkConflicts(params)
		
	#Converting particle stack in spider format
	cmd = 'proc2d %s %s.spi spiderswap' %(params['stack'],params['stack'][:-4])
	subprocess.Popen(cmd,shell=True).wait()
	
	determine_intensity_vs_defocus(params)

	#Cleanup 
	os.remove('tmp_line_trace1.spi')
	os.remove('tmp_line_trace2.spi')
	os.remove('%s.spi' %(params['stack'][:-4]))
