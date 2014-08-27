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
	parser.add_option("--firstRow",dest="first",type="int", metavar="INT",
                help="First row used for averaging across middle of box")
	parser.add_option("--lastRow",dest="last",type="int", metavar="INT",
                help="Last row used for averaging across middle of box")
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

        if os.path.exists('%s_intensity_vs_defocus.txt' %(params['stack'])):
                print "\nError: output file already exists, exiting.\n"
                sys.exit()

#=============================
def determine_intensity_vs_defocus(params):

	numParts = len(open(params['ctf'],'r').readlines())

	i = 1

	while i <= numParts:

		tracefile = lineTrace('%s' %(params['stack'][:-4]),i,params['first'],params['last'],params['box'])

		i = i + 1

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
	spi+='%f,%f\n' %(first,last)
	spi+=';merge three pixels into single file\n'
	spi+='SD IC NEW\n'
	spi+='incore_doc\n'
	spi+='2,%f\n' %(box)
	spi+='do lb2 [row]=1,%f\n' %(box)

		[row2]=[row]+256
		[row3]=[row2]+256
		[row4]=[row3]+256

		UD IC [row] [pix1]
		line_traces_average3rows_NoNoise_try2/def{*****[part]}

		UD IC [row2] [pix2]
                line_traces_average3rows_NoNoise_try2/def{*****[part]}
	
		UD IC [row3] [pix3]
                line_traces_average3rows_NoNoise_try2/def{*****[part]} 

		[avg]=([pix1]+[pix2]+[pix3])/3

		SD IC [row] [avg] [std2]
		incore_doc
	lb2	

	UD ICE
	line_traces_average3rows_NoNoise_try2/def{*****[part]}

	SD IC COPY
	incore_doc
	line_traces_average3rows_NoNoise_try2/def{*****[part]}_avg
	
	SD ICE
	incore_doc

	
#==============================
if __name__ == "__main__":

        params=setupParserOptions()
        checkConflicts(params)
		
	#Converting particle stack in spider format
	cmd = 'proc2d %s %s.spi spiderswap' %(params['stack'],params['stack'][:-4])
	subprocess.Popen(cmd,shell=True).wait()
	
	determine_intensity_vs_defocus(params)
